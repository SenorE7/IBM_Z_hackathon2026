"""
Synthetic sensor-data generator for the Ghazipur Landfill Fire & Contamination Shield
(IBM Z Datathon 2026, Theme 1).

Produces hourly readings for 12 landfill zones over 90 days (2026-04-01 onward, so the
window spans the hot pre-monsoon April-June period, when landfill fires peak).

SIMULATED DATA - disclosed as simulated, not real sensor measurements. However the
*relationships* between the features and fire risk are grounded in published landfill-fire
science (see docs/SOURCES.md):

  * Fire-weather term (McArthur FDI form): risk rises with temperature, wind and drought
    (days since rain), and falls with humidity.
  * Thermal self-heating term: risk climbs steeply as surface temperature approaches the
    ~80 C smouldering-onset threshold for decomposing MSW.
  * Methane term: risk rises as methane approaches the 5% lower explosive limit
    (50,000 ppm); below the LEL the mixture is too dilute to ignite.

Dependencies: pandas, numpy only (pure enough for IBM LinuxONE / s390x).
Output: data/landfill_sensors.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

# --- configuration -----------------------------------------------------------
N_ZONES = 12
DAYS = 90
HOURS = DAYS * 24
START = pd.Timestamp("2026-04-01 00:00:00")
TARGET_FIRE_RATE = 0.065  # middle of the typical 5-8% band

# Ghazipur landfill bounding box
LAT_MIN, LAT_MAX = 28.623, 28.628
LON_MIN, LON_MAX = 77.325, 77.330

# Physical reference points (see docs/SOURCES.md)
SMOULDER_ONSET_C = 80.0      # ~80 C = onset of potential smouldering in decomposing MSW
METHANE_LEL_PPM = 50_000.0   # 5% v/v lower explosive limit for methane

OUT_PATH = Path(__file__).resolve().parent / "landfill_sensors.csv"


def build_zone_profile():
    """Per-zone character: location + a self-heating/methane 'hotspot' propensity."""
    grid_lat = np.linspace(LAT_MIN + 0.0006, LAT_MAX - 0.0006, 3)
    grid_lon = np.linspace(LON_MIN + 0.0006, LON_MAX - 0.0006, 4)
    coords = np.array([(la, lo) for la in grid_lat for lo in grid_lon])
    coords[:, 0] += RNG.normal(0, 0.0002, N_ZONES)
    coords[:, 1] += RNG.normal(0, 0.0002, N_ZONES)
    coords[:, 0] = np.clip(coords[:, 0], LAT_MIN, LAT_MAX)
    coords[:, 1] = np.clip(coords[:, 1], LON_MIN, LON_MAX)

    # Hotspot propensity 0..1 (skewed: most zones calm, a few run hot).
    hotspot = RNG.random(N_ZONES) ** 1.8
    # Background surface methane baseline (ppm), log-normal: most low, long tail.
    methane_base = RNG.lognormal(mean=np.log(2500), sigma=0.7, size=N_ZONES)
    return coords, hotspot, methane_base


def build_time_series():
    """Site-level hourly drivers shared by all zones."""
    timestamps = START + pd.to_timedelta(np.arange(HOURS), unit="h")
    doy = timestamps.dayofyear.to_numpy()
    hour = timestamps.hour.to_numpy()

    # Seasonal mean temp: hot through Apr-Jun, peaking late May (pre-monsoon Delhi).
    seasonal = 30.0 + 9.0 * np.sin(np.pi * (doy - 91) / 120.0)
    diurnal = 7.0 * np.sin(2 * np.pi * (hour - 9) / 24.0)
    ambient_base = seasonal + diurnal

    # Daytime solar loading on the landfill surface.
    solar = 14.0 * np.clip(np.sin(np.pi * (hour - 6) / 12.0), 0, None)

    # Rain: rare in the dry season, ramping toward the late-June monsoon onset.
    p_rain = 0.002 + 0.020 * np.clip((doy - 160) / 21.0, 0, 1)
    rain = RNG.random(HOURS) < p_rain
    days_since_rain = np.empty(HOURS)
    cur = 10.0
    for i in range(HOURS):
        cur = 0.0 if rain[i] else cur + 1.0 / 24.0
        days_since_rain[i] = cur

    return timestamps, ambient_base, solar, days_since_rain


def _standardize(x):
    return (x - x.mean()) / (x.std() + 1e-9)


def generate():
    coords, hotspot, methane_base = build_zone_profile()
    timestamps, ambient_base, solar, days_since_rain = build_time_series()

    frames = []
    for z in range(N_ZONES):
        ambient = ambient_base + RNG.normal(0, 1.0, HOURS)

        # Methane: warmer -> more microbial generation; hotspot zones vent much more,
        # occasionally approaching the explosive range. Clipped to a plausible window.
        activity = 1.0 + 0.02 * (ambient - 30.0)
        methane = (
            methane_base[z] * activity
            + hotspot[z] * 22_000.0 * (0.6 + 0.4 * RNG.random(HOURS))
            + RNG.normal(0, 500, HOURS)
        )
        methane = np.clip(methane, 150, 80_000)

        # Surface temp: ambient + solar + decomposition/self-heating heat. Hotspot zones
        # carry a large subsurface-heat offset, so they can approach the ~80 C threshold.
        decomp_heat = 4.0 + hotspot[z] * 40.0 + 0.00015 * methane
        surface = ambient + solar + decomp_heat + RNG.normal(0, 2.0, HOURS)

        # Humidity: inversely related to temperature, boosted right after rain.
        rain_boost = 30.0 * np.exp(-days_since_rain / 2.0)
        humidity = np.clip(
            70.0 - 1.2 * (ambient - 25.0) + rain_boost + RNG.normal(0, 5.0, HOURS),
            5, 100,
        )

        wind_speed = np.clip(RNG.gamma(2.0, 5.0, HOURS), 0, 45)
        wind_direction = RNG.uniform(0, 360, HOURS)

        frames.append(pd.DataFrame({
            "timestamp": timestamps,
            "zone_id": z + 1,
            "zone_lat": round(coords[z, 0], 6),
            "zone_lon": round(coords[z, 1], 6),
            "methane_ppm": methane,
            "surface_temp_c": surface,
            "ambient_temp_c": ambient,
            "humidity_pct": humidity,
            "wind_speed_kmh": wind_speed,
            "wind_direction_deg": wind_direction,
            "days_since_rain": days_since_rain,
        }))

    df = pd.concat(frames, ignore_index=True)

    # --- fire label: physically-grounded latent risk + noise ------------------
    # 1) Fire-weather (McArthur FDI form): hotter, drier, windier, longer drought -> riskier.
    drought = np.clip(df["days_since_rain"].to_numpy(), 0, 21)
    fire_weather = (
        0.0338 * df["ambient_temp_c"].to_numpy()
        - 0.0345 * df["humidity_pct"].to_numpy()
        + 0.0234 * df["wind_speed_kmh"].to_numpy()
        + 0.5 * np.log(drought + 1.0)
    )
    # 2) Thermal self-heating: steep rise as surface temp approaches the 80 C threshold.
    thermal = np.clip((df["surface_temp_c"].to_numpy() - (SMOULDER_ONSET_C - 25)) / 10.0, 0, None)
    # 3) Methane: rises toward the 5% LEL; little effect well below it.
    methane_term = np.clip(df["methane_ppm"].to_numpy() / METHANE_LEL_PPM, 0, 1.5)

    score = (
        1.0 * _standardize(fire_weather)
        + 1.1 * _standardize(thermal)
        + 1.0 * _standardize(methane_term)
        + RNG.normal(0, 0.5, len(df))
    )

    # Solve intercept so the mean fire probability hits the target rate.
    lo, hi = -15.0, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if (1.0 / (1.0 + np.exp(-(score + mid)))).mean() > TARGET_FIRE_RATE:
            hi = mid
        else:
            lo = mid
    prob = 1.0 / (1.0 + np.exp(-(score + (lo + hi) / 2.0)))
    df["fire_next_24h"] = (RNG.random(len(df)) < prob).astype(int)

    # Tidy numeric precision.
    df["methane_ppm"] = df["methane_ppm"].round(0)
    df["surface_temp_c"] = df["surface_temp_c"].round(2)
    df["ambient_temp_c"] = df["ambient_temp_c"].round(2)
    df["humidity_pct"] = df["humidity_pct"].round(1)
    df["wind_speed_kmh"] = df["wind_speed_kmh"].round(1)
    df["wind_direction_deg"] = df["wind_direction_deg"].round(1)
    df["days_since_rain"] = df["days_since_rain"].round(2)
    return df


def summarise(df):
    fire_rate = df["fire_next_24h"].mean()
    print("=" * 62)
    print("SIMULATED LANDFILL SENSOR DATA  (grounded in landfill-fire science)")
    print("=" * 62)
    print(f"Rows:       {len(df):,}   Zones: {df['zone_id'].nunique()}")
    print(f"Date range: {df['timestamp'].min()}  ->  {df['timestamp'].max()}")
    print(f"Fire rate:  {fire_rate:.2%}  ({int(df['fire_next_24h'].sum()):,} fire rows)")
    print()
    print("Feature ranges:")
    for c in ["methane_ppm", "surface_temp_c", "ambient_temp_c", "humidity_pct",
              "wind_speed_kmh", "days_since_rain"]:
        print(f"  {c:18s} {df[c].min():8.1f}  ..  {df[c].max():8.1f}")
    print()
    drivers = ["methane_ppm", "surface_temp_c", "humidity_pct", "days_since_rain", "wind_speed_kmh"]
    means = df.groupby("fire_next_24h")[drivers].mean().round(1)
    means.index = ["no fire (0)", "fire (1)"]
    print("Average driver values, fire vs no-fire:")
    print(means.T.to_string())
    print("=" * 62)


if __name__ == "__main__":
    df = generate()
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df):,} rows -> {OUT_PATH}\n")
    summarise(df)
