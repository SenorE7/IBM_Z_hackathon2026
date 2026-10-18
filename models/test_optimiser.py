"""
Test / demo for Model B (optimiser). Computes per-zone risk from Model A on the latest
hour of SIMULATED data, runs the distribution optimiser, and prints the dig order and
routing table in human-readable form (plus asserts capacities are never exceeded).
"""

from optimiser import optimise, zone_risks_from_latest, load_plants


def main():
    risks = zone_risks_from_latest()
    plan = optimise(risks, excavation_target=12_000, incoming_textile=200)

    print("=" * 64)
    print("MODEL B - DIG ORDER + DISTRIBUTION PLAN   (optimisation, not ML)")
    print("SIMULATED sensor data")
    print("=" * 64)
    print(f"Excavation target : {plan['excavation_target_tonnes']:,} t"
          f"   (+{plan['incoming_textile_tonnes']} t incoming textiles)")
    print(f"Total excavated   : {plan['total_excavated_tonnes']:,} t")

    print("\nDIG ORDER (riskiest first):")
    for i, d in enumerate(plan["dig_order"], 1):
        print(f"  {i}. zone {d['zone_id']:2d}  risk={d['risk']:.3f}  dig {d['excavate_tonnes']:,} t")

    print("\nWASTE FRACTIONS (t):")
    for f, v in plan["fractions_tonnes"].items():
        print(f"  {f:10s} {v:>8,.1f}")

    print("\nROUTING TABLE:")
    print(f"  {'fraction':10s} {'plant':32s} {'t':>8s} {'km':>4s}")
    for r in plan["routing"]:
        print(f"  {r['fraction']:10s} {r['plant']:32s} {r['tonnes']:>8,.1f} {r['distance_km']:>4d}")

    print("\nPLANT UTILISATION:")
    for u in plan["plant_utilisation"]:
        print(f"  {u['plant']:32s} {u['allocated_tonnes']:>7,} / {u['capacity_tpd']:>6,} t"
              f"  ({u['utilisation_pct']:>5.1f}%)")
        assert u["allocated_tonnes"] <= u["capacity_tpd"], "capacity exceeded!"

    print(f"\nUnallocated: {plan['unallocated_tonnes']}  "
          f"(total {plan['total_unallocated_tonnes']:,} t)")
    print(f"Transport cost: {plan['total_transport_cost_tonne_km']:,} tonne-km")
    print("=" * 64)
    print("OK - capacities respected.")


if __name__ == "__main__":
    main()
