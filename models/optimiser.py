"""
Model B - Dig-order + distribution planner.

OPTIMISATION, NOT machine learning. Uses a networkx min-cost flow to route excavated
landfill waste fractions to processing plants, minimising transport distance from Ghazipur
while respecting each plant's daily capacity, and reporting any unallocated tonnes.

Inputs come from Model A (per-zone fire risk) and operational settings (daily excavation
target, optional incoming fresh-textile tonnes). All real-world figures (fraction split,
plant capacities, distances) are documented in docs/SOURCES.md. Pure-Python deps only
(pandas, networkx) so it runs on IBM LinuxONE / s390x.
"""

from pathlib import Path
import json

import pandas as pd
import networkx as nx

# Waste-fraction split of excavated legacy waste. ASSUMPTION within sourced ranges -
# see docs/SOURCES.md. Must sum to 1.0.
FRACTIONS = {
    "fine_soil": 0.52,
    "rdf": 0.18,
    "plastics": 0.08,
    "textiles": 0.05,
    "inert": 0.17,
}

DEFAULT_EXCAVATION_TARGET = 12_000  # tonnes/day (Ghazipur target, see docs/SOURCES.md)
OVERFLOW_PENALTY = 100_000          # cost of leaving a tonne unallocated (>> any distance)


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_plants(path=None) -> pd.DataFrame:
    path = Path(path) if path else _root() / "data" / "plants.csv"
    df = pd.read_csv(path)
    df["accepts"] = df["accepts"].str.split("|")
    return df


def rank_zones(risks: dict) -> list:
    """Return [(zone_id, risk), ...] sorted by risk descending (riskiest dug first)."""
    return sorted(risks.items(), key=lambda kv: (-kv[1], kv[0]))


def build_dig_plan(risks: dict, excavation_target: float, per_zone_cap: float = None) -> list:
    """Fill the daily excavation target from the highest-risk zones first."""
    if per_zone_cap is None:
        per_zone_cap = max(1.0, excavation_target / 4)
    plan, remaining = [], excavation_target
    for zone_id, risk in rank_zones(risks):
        if remaining <= 0:
            break
        dig = min(per_zone_cap, remaining)
        plan.append({"zone_id": int(zone_id), "risk": round(float(risk), 4),
                     "excavate_tonnes": round(dig, 1)})
        remaining -= dig
    return plan


def split_fractions(tonnes: float, incoming_textile: float = 0.0) -> dict:
    frac = {f: tonnes * p for f, p in FRACTIONS.items()}
    frac["textiles"] += incoming_textile  # fresh incoming textiles join the textile stream
    return frac


def _route(fractions: dict, plants: pd.DataFrame):
    """networkx min-cost flow: SRC -> fraction -> plant -> SINK, plus overflow edges."""
    supplies = {f: int(round(v)) for f, v in fractions.items() if v > 0}
    G = nx.DiGraph()
    SRC, SINK = "SRC", "SINK"

    for f, s in supplies.items():
        G.add_edge(SRC, ("f", f), capacity=s, weight=0)
        G.add_edge(("f", f), SINK, capacity=s, weight=OVERFLOW_PENALTY)  # unallocated

    for _, p in plants.iterrows():
        pj = ("p", p["plant_id"])
        G.add_edge(pj, SINK, capacity=int(p["daily_capacity_tpd"]), weight=0)
        for f in p["accepts"]:
            if f in supplies:
                G.add_edge(("f", f), pj, capacity=supplies[f],
                           weight=int(round(p["distance_km"])))

    flow = nx.max_flow_min_cost(G, SRC, SINK)

    routing, cost = [], 0
    pmeta = {p["plant_id"]: p for _, p in plants.iterrows()}
    allocated_by_plant = {pid: 0 for pid in pmeta}
    unallocated = {}
    for f in supplies:
        for dest, amt in flow.get(("f", f), {}).items():
            if amt <= 0:
                continue
            if dest == SINK:
                unallocated[f] = unallocated.get(f, 0) + amt
            elif isinstance(dest, tuple) and dest[0] == "p":
                pid = dest[1]
                p = pmeta[pid]
                routing.append({
                    "fraction": f, "plant_id": pid, "plant": p["name"],
                    "plant_type": p["type"], "tonnes": amt,
                    "distance_km": int(p["distance_km"]),
                })
                allocated_by_plant[pid] += amt
                cost += amt * int(round(p["distance_km"]))

    utilisation = [{
        "plant_id": pid, "plant": pmeta[pid]["name"], "type": pmeta[pid]["type"],
        "capacity_tpd": int(pmeta[pid]["daily_capacity_tpd"]),
        "allocated_tonnes": allocated_by_plant[pid],
        "utilisation_pct": round(100 * allocated_by_plant[pid] / int(pmeta[pid]["daily_capacity_tpd"]), 1),
    } for pid in pmeta]

    return routing, utilisation, unallocated, cost


def optimise(risks: dict, excavation_target: float = DEFAULT_EXCAVATION_TARGET,
             incoming_textile: float = 0.0, plants: pd.DataFrame = None) -> dict:
    """Produce the full dig-order + distribution plan as a JSON-serialisable dict."""
    plants = load_plants() if plants is None else plants
    dig_plan = build_dig_plan(risks, excavation_target)
    total_excavated = round(sum(d["excavate_tonnes"] for d in dig_plan), 1)
    fractions = split_fractions(total_excavated, incoming_textile)
    routing, utilisation, unallocated, cost = _route(fractions, plants)

    return {
        "excavation_target_tonnes": excavation_target,
        "incoming_textile_tonnes": incoming_textile,
        "total_excavated_tonnes": total_excavated,
        "zone_risk_ranking": [{"zone_id": int(z), "risk": round(float(r), 4)}
                              for z, r in rank_zones(risks)],
        "dig_order": dig_plan,
        "fractions_tonnes": {f: round(v, 1) for f, v in fractions.items()},
        "routing": [{**r, "tonnes": round(r["tonnes"], 1)} for r in routing],
        "plant_utilisation": utilisation,
        "unallocated_tonnes": {f: round(v, 1) for f, v in unallocated.items()},
        "total_unallocated_tonnes": round(sum(unallocated.values()), 1),
        "total_transport_cost_tonne_km": round(cost, 1),
    }


def zone_risks_from_latest(model_path=None, data_path=None) -> dict:
    """Helper: load Model A and compute per-zone fire risk from the latest hour of data."""
    import joblib
    model_path = Path(model_path) if model_path else _root() / "models" / "fire_model.joblib"
    data_path = Path(data_path) if data_path else _root() / "data" / "landfill_sensors.csv"
    bundle = joblib.load(model_path)
    model, features = bundle["model"], bundle["features"]
    df = pd.read_csv(data_path, parse_dates=["timestamp"])
    latest = df[df["timestamp"] == df["timestamp"].max()].sort_values("zone_id")
    proba = model.predict_proba(latest[features])[:, 1]
    return {int(z): float(p) for z, p in zip(latest["zone_id"], proba)}


if __name__ == "__main__":
    risks = zone_risks_from_latest()
    print(json.dumps(optimise(risks), indent=2))
