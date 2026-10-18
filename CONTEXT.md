# Ghazipur Landfill Fire & Contamination Shield

**IBM Z Datathon 2026 — Theme 1: Real-time AI for critical decisions**

## The project

Real-time decision-support for Delhi's Ghazipur landfill, built as a
**Predict → Decide → Generate** pipeline:

- **Model A — Fire-risk classifier (ML).** Predicts per-zone fire risk in the next 24h from
  sensor features (methane, surface/ambient temp, humidity, wind, days since rain).
- **Model B — Dig-order + distribution planner (OPTIMISATION, not ML).** Ranks the 12 zones
  by risk (riskiest dug first), splits excavated waste into fractions, and routes them to
  processing plants by capacity while minimising transport distance (networkx min-cost flow).
- **Model C — GenAI action engine (LLM).** Produces plain-English resident smoke/health
  alerts (downwind of the highest-risk zone) and a daily excavation & truck-dispatch plan for
  crews. Template-based offline; optional open-weights **IBM Granite** model on LinuxONE.
- **Dashboard (Flask + Leaflet.js).** Risk map of the 12 zones, plant markers + routing
  lines, a simulated live sensor stream, and a "heatwave" slider that changes risk/routes/
  alerts live.

## Data

- **SIMULATED sensor data** (`data/landfill_sensors.csv`) — labelled as simulated everywhere
  (code, docs, and dashboard). It is not real sensor measurement.
- **Real-world figures** (landfill size, waste-fraction percentages, plant capacities) are
  documented with source URLs in **`docs/SOURCES.md`**; anything without a source is marked
  **UNVERIFIED**.
- **Open-Meteo weather is live** via the dashboard's optional "Live weather" toggle — real
  current Ghazipur air temp, humidity, wind and days-since-rain feed the model, while per-zone
  surface temperature and methane stay simulated (no real feed exists for those). NASA FIRMS
  fire detections remain future work.

## Compute / hard constraint

- Must run on **IBM LinuxONE (s390x Linux)**: CPU-only, no GPU, no x86-only binaries, no
  Streamlit, no pyarrow. **No secrets in code or commits.**
- Laptop is for prototyping; model training/inference targets LinuxONE Jupyter Lab.

## Future work (explicitly out of current scope)

- Fast-fashion diversion toggle (incoming textile trucks → Panipat mills)
- Computer-vision classifiers (textile / waste image classification)
- Waste-composition classifier
- Landfill-growth forecast
- Real-data site-level model (NASA FIRMS + Open-Meteo); multi-landfill / city-scale expansion

---

# Repo / environment setup

Environment: Windows 11 Pro, Python 3.14.5, pip 26.1.1, git 2.54 (Git for Windows with
Git Credential Manager). User: SenorE7 / eobehie@gmail.com.

## Tooling

- **Jupyter Notebook 7.6.3** installed via pip (user install). Its scripts folder
  (`C:\Users\Manny\AppData\Roaming\Python\Python314\Scripts`) is **not on PATH**, so use
  `python -m notebook` / `python -m jupyterlab` to launch, and `python -m nbconvert`
  (not `jupyter nbconvert`) to execute notebooks headlessly.
- Repo: **`SenorE7/IBM_Z_hackathon2026`**, cloned to
  `C:\Users\Manny\Documents\IBM_Z_hackathon2026`. Default branch `main`.
- Auth via a fine-grained PAT (single-repo, Contents read/write, 7-day expiry) cached in
  the local git config. Revoke at https://github.com/settings/tokens when done.

## Folder structure

```
data/        simulated data + generators (+ plants.csv)
models/      trained model artifact + optimiser + genai code
dashboard/   Flask app + Leaflet map UI
notebooks/   model training / prototyping notebooks
docs/        plan, sources, deployment + submission material
```

## Working loop

Edit code / `.ipynb` → run (`python script.py` or
`python -m nbconvert --to notebook --execute --inplace nb.ipynb`) → `git commit` →
`git push origin main`.

## Progress

- [x] Jupyter installed, repo connected, working loop verified
- [x] Simulated hourly sensor dataset (`data/generate_data.py` → `data/landfill_sensors.csv`)
- [ ] Step 0 — doc corrections + `docs/SOURCES.md`
- [ ] Step 1 — Model A fire-risk classifier
- [ ] Step 2 — Model B dig-order + optimiser
- [ ] Step 3 — Model C GenAI alerts + plan
- [ ] Step 4 — Flask + Leaflet dashboard
- [ ] Step 5 — end-to-end checkpoint
- [ ] Step 6 — LinuxONE readiness (requirements, setup doc, container)
- [ ] Step 7 — submission docs (README, flowchart)
