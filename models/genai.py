"""
Model C - GenAI action engine.

Turns Model A (per-zone fire risk) + Model B (distribution plan JSON) + wind direction into
two plain-English outputs:
  1. a resident smoke/health alert for areas DOWNWIND of the highest-risk zone;
  2. a daily excavation & truck-dispatch plan for site crews.

v1 = deterministic templates (offline, no API keys, no network) - the guaranteed path.
v2 = generate_with_llm(): uses an open-weights IBM Granite model when available (e.g. on
LinuxONE) and falls back to templates otherwise.

Pure-Python by default (stdlib only) so it runs on IBM LinuxONE / s390x. All data is
SIMULATED. Truck capacity and other constants are documented in docs/SOURCES.md.
"""

from math import ceil

TRUCK_CAPACITY_T = 10  # tonnes per tipper truck. ASSUMPTION - see docs/SOURCES.md

# 8-point compass -> indicative localities around Ghazipur (for the downwind warning).
# Indicative only; real plume modelling is future work.
DIRS8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
DOWNWIND_AREAS = {
    "N":  ["Dilshad Garden", "Vivek Vihar"],
    "NE": ["Vasundhara", "Kaushambi (Ghaziabad)"],
    "E":  ["Khoda Colony", "Vaishali"],
    "SE": ["Kondli", "Gharoli"],
    "S":  ["Kalyanpuri", "Trilokpuri"],
    "SW": ["Mayur Vihar Phase 3", "Kondli"],
    "W":  ["Mayur Vihar", "Patparganj"],
    "NW": ["Anand Vihar", "Karkardooma"],
}


def _compass(bearing_deg: float) -> str:
    return DIRS8[round((bearing_deg % 360) / 45) % 8]


def _top_zone(risks: dict):
    zone_id = max(risks, key=risks.get)
    return int(zone_id), float(risks[zone_id])


# --- v1: templates -----------------------------------------------------------

def build_resident_alert(risks: dict, wind_direction_deg: float) -> str:
    """Wind direction is the direction the wind blows FROM (meteorological)."""
    zone_id, risk = _top_zone(risks)
    from_dir = _compass(wind_direction_deg)
    to_dir = _compass(wind_direction_deg + 180)  # smoke travels downwind
    areas = ", ".join(DOWNWIND_AREAS[to_dir])
    return (
        "SMOKE / HEALTH ALERT - Ghazipur landfill  [SIMULATED]\n"
        f"Highest fire risk today: Zone {zone_id} (risk {risk:.0%}).\n"
        f"Wind is from the {from_dir}, so smoke would drift toward the {to_dir} - "
        f"affecting: {areas}.\n"
        "Residents and schools in these areas should: limit outdoor activity, keep windows "
        "closed, use an N95 mask if outside, and seek help for any breathing difficulty. "
        "Vulnerable groups (children, elderly, asthmatics) take extra care."
    )


def build_crew_plan(plan: dict) -> str:
    """Daily excavation + truck-dispatch plan from the Model B JSON."""
    lines = ["DAILY EXCAVATION & TRUCK-DISPATCH PLAN - Ghazipur  [SIMULATED]"]
    lines.append(f"Target: excavate {plan['total_excavated_tonnes']:,.0f} t today "
                 f"(truck capacity {TRUCK_CAPACITY_T} t).")

    lines.append("\n1) DIG ORDER (riskiest zone first):")
    for i, d in enumerate(plan["dig_order"], 1):
        lines.append(f"   {i}. Zone {d['zone_id']} - dig {d['excavate_tonnes']:,.0f} t "
                     f"(risk {d['risk']:.0%})")

    lines.append("\n2) TRUCK DISPATCH (fraction -> plant):")
    for r in plan["routing"]:
        trucks = ceil(r["tonnes"] / TRUCK_CAPACITY_T)
        lines.append(f"   {r['tonnes']:>7,.0f} t {r['fraction']:9s} -> {r['plant']} "
                     f"({r['distance_km']} km): {trucks} trucks")

    if plan.get("total_unallocated_tonnes", 0) > 0:
        un = ", ".join(f"{v:,.0f} t {f}" for f, v in plan["unallocated_tonnes"].items())
        lines.append(f"\n3) WARNING - unallocated (no capacity today): {un}. "
                     "Arrange additional offtake or carry forward to tomorrow.")
    else:
        lines.append("\n3) All excavated waste allocated within plant capacity.")
    return "\n".join(lines)


# --- v2: optional LLM (IBM Granite), with safe fallback ----------------------

def generate_with_llm(kind: str, context: str, model_name: str = "ibm-granite/granite-3.1-2b-instruct"):
    """
    Try to generate text with an open-weights IBM Granite model via transformers.
    Returns the generated string, or None if the model/library is unavailable (caller
    then falls back to templates). Never raises; never requires network at import time.
    """
    try:
        from transformers import pipeline  # noqa: lazy import
        prompt = (
            f"You are an emergency-response assistant for a landfill. Write a {kind} "
            f"in plain English based on this data:\n{context}"
        )
        gen = pipeline("text-generation", model=model_name)
        out = gen(prompt, max_new_tokens=256, do_sample=False)
        return out[0]["generated_text"]
    except Exception:
        return None


def generate(risks: dict, plan: dict, wind_direction_deg: float, use_llm: bool = False) -> dict:
    """Produce both outputs. Uses Granite if use_llm and it is available, else templates."""
    engine = "template"
    resident_alert = build_resident_alert(risks, wind_direction_deg)
    crew_plan = build_crew_plan(plan)

    if use_llm:
        a = generate_with_llm("resident smoke/health alert",
                              f"{resident_alert}")
        c = generate_with_llm("crew excavation and dispatch plan", f"{crew_plan}")
        if a and c:
            resident_alert, crew_plan, engine = a, c, "granite-llm"

    return {"engine": engine, "resident_alert": resident_alert, "crew_plan": crew_plan}


if __name__ == "__main__":
    from optimiser import optimise, zone_risks_from_latest, _root
    import pandas as pd

    risks = zone_risks_from_latest()
    plan = optimise(risks, excavation_target=12_000, incoming_textile=200)

    # Wind direction of the highest-risk zone from the latest hour of SIMULATED data.
    top_zone, _ = _top_zone(risks)
    df = pd.read_csv(_root() / "data" / "landfill_sensors.csv", parse_dates=["timestamp"])
    latest = df[df["timestamp"] == df["timestamp"].max()]
    wind = float(latest[latest["zone_id"] == top_zone]["wind_direction_deg"].iloc[0])

    result = generate(risks, plan, wind, use_llm=False)
    print(f"[engine: {result['engine']}]  wind_from={wind:.0f} deg\n")
    print(result["resident_alert"])
    print("\n" + "-" * 64 + "\n")
    print(result["crew_plan"])
