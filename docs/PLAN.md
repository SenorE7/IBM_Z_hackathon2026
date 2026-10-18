# Plan: Ghazipur Landfill Fire & Contamination Shield (IBM Z Datathon 2026)

## Context

Build the datathon project end-to-end as a **Predict (ML) → Decide (optimisation) →
Generate (LLM)** pipeline for Theme 1 (Real-time AI for critical decisions). This plan
**supersedes and corrects** the earlier `CONTEXT.md`/`docs/PLAN.md` framing.

**Corrections applied (per user):**
- The brief does **NOT** require 3 models — remove every "3-model / mandatory hybrid" claim.
- **Honest labels everywhere:** Model B is **OPTIMISATION, not ML**; sensor data is **SIMULATED**.
- **Cut to "Future work":** fast-fashion diversion toggle, all computer-vision classifiers,
  waste-composition classifier, landfill-growth forecast.
- New `docs/SOURCES.md` lists every real-world figure with a source URL; any figure without
  a source is marked **UNVERIFIED**.
- Drop the old "cut the rules layer by 8pm" rule (invalid framing).

## Hard constraints
- Must run on **IBM LinuxONE (s390x Linux)**: CPU-only, no GPU, no x86-only binaries, no
  Streamlit, no pyarrow. No secrets in code or commits.
- **Honesty flag (libraries):** `networkx`, `Flask`, `joblib` are pure-Python. 
  `numpy`/`pandas`/`scikit-learn` are CPU-only but have **compiled** components — available
  on s390x via conda-forge / IBM Z channels, not "pure-Python." Avoid pyarrow-backed pandas
  features. Step 6 pins versions and documents this. If s390x install of scikit-learn fails,
  STOP and flag — do not silently swap in a hand-rolled model.

## Execution protocol (every step)
Build **one step at a time, in order**. After each step: **run it -> show the output ->
commit + push with the exact message**. On any failure: **STOP, show the exact error**, do
not skip ahead or invent workarounds silently.

## Step 0 — Doc corrections + SOURCES (prep)
- Rewrite `CONTEXT.md`: Predict->Decide->Generate; Model A (ML) / Model B (optimisation) /
  Model C (GenAI); **SIMULATED** data label; remove 3-model/mandatory/toggle/8pm; add a
  **Future work** section listing the cut items.
- Create `docs/SOURCES.md`: Ghazipur tonnage/height/biomining rate, waste-fraction %s, plant
  capacities, Panipat throughput — each with a source URL; unsourced figures -> **UNVERIFIED**.
- Proposed commit (no message was specified for prep): `"Docs: honest framing + SOURCES.md"`

## Step 1 — Model A: fire-risk classifier (ML)
`notebooks/01_fire_model.ipynb`: load `data/landfill_sensors.csv`; **time split** (first
70 days train, last 20 test); `sklearn RandomForestClassifier(class_weight='balanced')`;
print accuracy, precision, recall, F1, confusion matrix, feature importances; save
`models/fire_model.joblib`. Execute headlessly via
`python -m nbconvert --to notebook --execute --inplace`.
Commit: **"Model A fire-risk classifier"**

## Step 2 — Model B: dig order + optimiser (OPTIMISATION, not ML)
- `data/plants.csv`: ~5 plants (WtE, cement kiln, compost/soil reuse, Panipat textile hub,
  inert/road-fill) — `name, lat, lon, accepted fractions, daily capacity` (values sourced in
  `docs/SOURCES.md`).
- `models/optimiser.py`: inputs = Model A risk per zone (latest hour of data), daily
  excavation target (tonnes), optional incoming textile tonnes (single number only).
  (a) rank 12 zones by risk, top = dig first;
  (b) split excavated waste into fractions (fine soil, RDF/combustibles, plastics, textiles,
  inert) using `docs/SOURCES.md` percentages;
  (c) route fractions -> plants via **networkx min-cost flow**; cost = distance from Ghazipur;
  never exceed capacity; report unallocated tonnes. Return **JSON**.
- Add a test script printing the dig order + routing table.
Commit: **"Model B optimiser"**

## Step 3 — Model C: GenAI alerts + plan (LLM)
`models/genai.py`: inputs = Model A risks, Model B JSON, wind direction. Outputs:
(1) plain-English resident smoke/health alert for areas **downwind** of the highest-risk zone;
(2) daily excavation & truck-dispatch plan for crews.
v1 = **templates** (offline, no keys); v2 = `generate_with_llm()` calling an open-weights
**IBM Granite** model when available on LinuxONE, falling back to templates.
Commit: **"Model C GenAI"**

## Step 4 — Dashboard
`dashboard/app.py` (**Flask**) + one HTML page using **Leaflet.js**:
- Map: 12 zones as circles green/amber/red by risk; plants as markers; straight lines
  Ghazipur->plant with thickness by tonnes.
- Simulated live stream: advance one hour of data every 3 s and refresh.
- **"Heatwave" slider 0–100%**: raises temperatures / lowers humidity before prediction so
  risks, routes and alerts visibly change.
- Panels: dig order, routing table, resident alert, crew plan.
- Visible label: **"Simulated sensor data"**.
Run: `python dashboard/app.py` -> http://localhost:5000
Commit: **"Dashboard v1"**

## Step 5 — CHECKPOINT (STOP)
Report whether the slider changes map + routes + alert **end-to-end**. Fallback if broken:
Model B -> fixed allocation table; Model C -> template-only.

## Step 6 — LinuxONE readiness
`requirements.txt` (pinned versions); `docs/setup_linuxone.md` (exact commands to clone on an
s390x VM, install deps, run the notebook + dashboard); a `Dockerfile`/`Containerfile`
(podman-compatible) for the dashboard. Do **not** connect to any server.
Commit: **"LinuxONE deployment files"**

## Step 7 — Submission polish
`README.md`: problem, solution, architecture, how to run, tech stack, and a **DISCLOSURES**
section (every OSS library with links; datasets = simulated + Open-Meteo + NASA FIRMS; AI
tools = Claude Code). `docs/flowchart.md` with a **Mermaid** diagram of the pipeline.
Commit: **"Submission docs"**

## Files
- **New:** `docs/SOURCES.md`, `notebooks/01_fire_model.ipynb`, `data/plants.csv`,
  `models/optimiser.py`, `models/genai.py`, `dashboard/app.py` (+ template/static),
  `requirements.txt`, `docs/setup_linuxone.md`, `Dockerfile`/`Containerfile`, `README.md`,
  `docs/flowchart.md`.
- **Edit:** `CONTEXT.md`.
- **Reuse:** `data/landfill_sensors.csv`, zone ids/coords from `data/generate_data.py`.
- **Artifact:** `models/fire_model.joblib`.

## Technical notes / decisions
- **networkx min-cost flow:** scale tonnes to integer units; graph source->fraction->plant->sink;
  add a high-cost overflow edge so the problem stays feasible and unallocated tonnes are
  captured/reported; cost = `round(distance_km)`. Pure-Python.
- **Time split:** dataset spans 2026-04-01 -> 2026-06-29 (90 days); train = first 70 days,
  test = last 20.
- **Model A features:** methane_ppm, surface_temp_c, ambient_temp_c, humidity_pct,
  wind_speed_kmh, wind_direction_deg, days_since_rain -> label `fire_next_24h`; imbalance via
  `class_weight='balanced'`.
- **Dashboard risk:** reuse `fire_model.joblib` to predict per-zone risk for the current
  simulated hour.
- **Granite:** optional/deferred; the template path is the guaranteed one.

## Verification (per step)
- S1: notebook executes headlessly; metrics + confusion matrix + importances printed;
  `fire_model.joblib` reloads.
- S2: test script prints dig order (riskiest first) + routing table; sum to each plant <=
  capacity; unallocated reported; output is valid JSON.
- S3: alert names the correct downwind area for a given wind direction; plan matches Model B
  JSON; template path works offline with no keys.
- S4: dashboard serves at :5000; slider visibly changes colours, routes and alert; "Simulated
  sensor data" label visible.
- S6: `requirements.txt` installs clean; container builds with podman; setup commands exact.
- S7: README runs as written; Mermaid renders.

## Future work (explicitly cut now)
Fast-fashion diversion toggle; computer-vision textile classifier; waste-composition
classifier; landfill-growth forecast; real-data (NASA FIRMS / Open-Meteo) site-level model;
multi-landfill / city-scale expansion.
