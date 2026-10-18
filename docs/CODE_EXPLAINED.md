# Code Explained — plain English

A walkthrough of every code file in the project, explained for a non-programmer. The system
has three "brains" — **Model A** (predicts fire), **Model B** (plans the digging/trucking),
**Model C** (writes the alerts) — plus a **dashboard** that shows it all on a map.

---

## 1. `data/generate_data.py` — makes the fake-but-realistic sensor data

This script invents 90 days of hourly readings for 12 landfill zones, because real per-zone
sensors don't exist. The *relationships* in it are based on real landfill-fire science.

- `import numpy / pandas` — load the two maths/tables toolkits we use.
- `RNG = np.random.default_rng(42)` — a random-number generator with a fixed "seed" (42) so
  the data comes out the **same every time** (reproducible).
- `N_ZONES = 12`, `DAYS = 90`, `HOURS = DAYS*24` — the size of the dataset: 12 zones × 90
  days × 24 hours = 25,920 rows.
- `START = ... 2026-04-01` — the data begins on 1 April (the hot pre-monsoon season when
  fires peak).
- `TARGET_FIRE_RATE = 0.065` — we aim for about 6.5% of readings to end in a fire (fires
  are rare).
- `LAT_MIN/MAX`, `LON_MIN/MAX` — the GPS box the landfill sits in.
- `SMOULDER_ONSET_C = 80.0` — the real ~80 °C temperature where decomposing rubbish can
  start to smoulder.
- `METHANE_LEL_PPM = 50000.0` — the real methane level (5%) above which the gas can ignite.
- `OUT_PATH = ...landfill_sensors.csv` — where the finished data file is saved.

**`build_zone_profile()`** — gives each of the 12 zones its own character:
- Lays the 12 zones out on a tidy 3×4 grid inside the GPS box, then nudges each one a little
  randomly so they're not perfectly lined up.
- `hotspot = RNG.random(N_ZONES) ** 1.8` — a "how dangerous" score 0–1 for each zone, skewed
  so **most zones are calm and a few run hot**.
- `methane_base = RNG.lognormal(...)` — each zone's baseline methane level; most low, a few
  very high (a "long tail").

**`build_time_series()`** — the weather that all zones share, hour by hour:
- `seasonal = 30 + 9*sin(...)` — average temperature that rises through April–June and peaks
  in late May.
- `diurnal = 7*sin(...)` — the daily up-and-down (hot afternoons, cool nights).
- `ambient_base = seasonal + diurnal` — combine them into the air temperature for each hour.
- `solar = 14*...` — extra heating of the landfill surface during daytime.
- `p_rain = ...` then `rain = RNG.random() < p_rain` — rain is rare in the dry season and
  more likely near the late-June monsoon; this randomly decides which hours it rains.
- The `for` loop building `days_since_rain` — counts how long it's been since it last rained
  (resets to 0 on a rainy hour, otherwise ticks up).

**`generate()`** — builds the actual table, zone by zone:
- `ambient = ambient_base + small noise` — each zone's air temp (slightly different per zone).
- `activity = 1 + 0.02*(ambient-30)` — warmer air → more microbe activity → more methane.
- `methane = base*activity + hotspot*22000*... + noise` — each zone's methane: higher in hot
  zones, occasionally approaching the explosive level. `clip(150, 80000)` keeps it in a
  plausible range.
- `decomp_heat = 4 + hotspot*40 + 0.00015*methane` — internal heat from rotting waste;
  hotspot zones get a big boost.
- `surface = ambient + solar + decomp_heat + noise` — the landfill **surface temperature**;
  hotspot zones can approach the 80 °C smoulder threshold.
- `humidity = 70 - 1.2*(ambient-25) + rain_boost + noise` — drops when it's hot, jumps up
  after rain; `clip(5,100)` keeps it a sensible percentage.
- `wind_speed` / `wind_direction` — random but realistic wind.
- `frames.append(pd.DataFrame({...}))` — save this zone's columns into a table.
- `df = pd.concat(frames)` — stack all 12 zones' tables into one.

**The fire label** (the thing Model A learns to predict):
- `fire_weather = 0.0338*temp - 0.0345*humidity + 0.0234*wind + 0.5*ln(drought)` — the real
  **McArthur fire-danger formula**: hotter, drier, windier, longer-dry = more dangerous.
- `thermal = clip((surface - 55)/10, 0, ...)` — risk that climbs as the surface nears 80 °C.
- `methane_term = clip(methane/50000, 0, 1.5)` — risk that climbs as methane nears the
  explosive limit.
- `score = standardise(each term) + noise` — combine the three drivers into one risk score.
- The `for` loop with `lo/hi/mid` — a binary search that tunes the overall level so exactly
  ~6.5% of rows catch fire.
- `prob = 1/(1+exp(-score))` then `fire_next_24h = (random < prob)` — turn the score into a
  probability, then flip a weighted coin to decide fire / no-fire for each row.
- The `round(...)` lines — tidy the numbers to sensible decimal places.

**`summarise(df)`** — prints a report: row count, fire rate, the range of each column, and
the average conditions for fire vs no-fire rows (so you can see fires really do line up with
heat + methane + dryness).

**`if __name__ == "__main__":`** — when you run the file, it generates the data, saves the CSV,
and prints the summary.

---

## 2. `notebooks/01_fire_model.ipynb` — trains Model A (the fire predictor)

A Jupyter notebook with a few cells:

- **Cell 1 (text):** explains the data is simulated and that we train/test by time.
- **Cell 2 (load):** finds the data file, reads `landfill_sensors.csv` into a table, prints
  the row count and column names.
- **Cell 3 (split):** cuts the data by date — the **first 70 days are for training**, the
  **last 20 days for testing** (so we never let the model "see the future"). Lists the input
  columns (`FEATURES`) and the thing to predict (`fire_next_24h`).
- **Cell 4 (train):** creates a **RandomForestClassifier** — a model made of 300 decision
  "trees" that vote. `class_weight='balanced'` tells it to take rare fires seriously. `.fit()`
  learns the patterns from the training data.
- **Cell 5 (evaluate):** predicts on the unseen test data and prints accuracy, precision,
  recall, F1, a confusion matrix, and a full report — honest scores on data it never trained on.
- **Cell 6 (save):** lists which features mattered most (surface temp + methane come top),
  then saves the trained model to `models/fire_model.joblib` so the dashboard can reuse it
  without retraining.

---

## 3. `models/optimiser.py` — Model B (dig order + where to send the waste)

This is **optimisation, not machine learning** — it does maths to find the cheapest valid plan.

- `FRACTIONS = {fine_soil:0.52, rdf:0.18, ...}` — how dug-up waste splits into types (must add
  to 100%).
- `DEFAULT_EXCAVATION_TARGET = 12000` — tonnes dug per day by default.
- `OVERFLOW_PENALTY = 100000` — a big "cost" for waste that can't be placed, so the optimiser
  only leaves waste unplaced as a last resort.
- `_root()` — finds the project's top folder so file paths work anywhere.
- `load_plants()` — reads `data/plants.csv` (the processing plants and their capacities) and
  splits the "accepts" column (e.g. `rdf|plastics`) into a list.
- `rank_zones(risks)` — sorts the 12 zones from most to least fire risk (riskiest dug first).
- `build_dig_plan(...)` — fills the day's digging target starting from the riskiest zone, up
  to a per-zone cap, and records how many tonnes come from each zone.
- `split_fractions(tonnes, incoming_textile)` — splits the dug tonnes into the five waste
  types; adds any incoming fresh textiles to the textile pile.
- **`_route(fractions, plants)`** — the heart of it, using the `networkx` library:
  - Builds a flow network: a START point → one node per waste type → one node per plant → an
    END point.
  - Each waste type can only go to plants that accept it; each plant edge has a **cost =
    distance** from Ghazipur and the plant's **capacity** as a limit.
  - An "overflow" edge lets leftover waste exit at a huge cost (so it's reported as
    unallocated, not hidden).
  - `nx.max_flow_min_cost(...)` solves it: push all the waste through at the **lowest total
    distance** without exceeding any plant's capacity.
  - Then it reads the answer back into a routing list, a per-plant utilisation list, the
    unallocated amounts, and the total transport cost.
- **`optimise(...)`** — ties it together: rank zones → build dig plan → split fractions →
  route → return one tidy dictionary (JSON) with the dig order, routing, utilisation and
  leftovers.
- **`zone_risks_from_latest(...)`** — a helper that loads Model A and uses it to score the 12
  zones from the most recent hour of data (so Model B has risks to work with).
- `if __name__ == "__main__":` — running the file prints the full plan as JSON.

---

## 4. `models/test_optimiser.py` — a quick check of Model B

- Gets the latest per-zone risks, runs `optimise(...)` for a 12,000 t day (+200 t textiles).
- Prints it all nicely: the dig order, the waste-type amounts, the routing table, and each
  plant's utilisation.
- `assert u["allocated_tonnes"] <= u["capacity_tpd"]` — a safety check that **no plant is ever
  overloaded**; if it were, the program would stop with an error.
- Prints the leftover (unallocated) tonnes and the transport cost, then "OK".

---

## 5. `models/genai.py` — Model C (writes the alerts and the crew plan)

- `TRUCK_CAPACITY_T = 10` — assume each truck carries ~10 tonnes (used to count trucks).
- `DIRS8` and `DOWNWIND_AREAS` — the 8 compass directions and the real neighbourhoods near
  Ghazipur in each direction (for the smoke warning).
- `_compass(bearing)` — turns an angle in degrees into N/NE/E/… .
- `_top_zone(risks)` — finds the single highest-risk zone.
- **`build_resident_alert(...)`** — writes the public smoke warning: finds the top-risk zone,
  works out which way the wind carries the smoke (opposite to where it blows *from*), names
  the affected areas, and adds health advice.
- **`build_crew_plan(plan)`** — writes the crew's work order from Model B's output: the dig
  order, then for each routing line how many trucks are needed (tonnes ÷ 10), and a warning
  listing any waste that couldn't be placed.
- **`generate_with_llm(...)`** — *optional*: tries to use an open-source **IBM Granite** AI
  model to write the text; if that library/model isn't available it quietly returns nothing
  (so we fall back to the templates). It never crashes and never needs the internet.
- **`generate(...)`** — the main entry point: always builds the template versions; if asked
  (and Granite is available) it swaps in the AI-written versions. Returns both texts plus which
  "engine" was used.
- `if __name__ == "__main__":` — a demo: scores the zones, runs the optimiser, grabs the top
  zone's wind, and prints the alert + the crew plan.

---

## 6. `dashboard/weather.py` — the real-time weather feed (Open-Meteo)

- Uses only Python's built-in `urllib` (no extra libraries, no API key) so it runs anywhere.
- `GHAZIPUR_LAT/LON` — the coordinates we ask about.
- `_CACHE` and `_TTL = 600` — remembers the last answer for 10 minutes so we don't spam the
  weather service on every dashboard refresh.
- **`get_live_weather()`**:
  - If we have a recent cached answer, return it.
  - Otherwise build the Open-Meteo web address asking for current temperature, humidity, wind,
    and the last 14 days of rainfall.
  - Fetch it, read the JSON reply.
  - Count **days since it last rained** (≥1 mm) from the rainfall history.
  - Return a tidy dictionary of the real conditions.
  - `except Exception: return None` — if anything goes wrong (no internet, timeout), return
    nothing so the app falls back to simulated weather.

---

## 7. `dashboard/app.py` — the web server that ties everything together

- Imports Flask (the web framework) and our own `optimiser`, `genai`, `weather` modules.
- `ROOT = ...` and `sys.path.insert(...)` — set up folder paths so imports work.
- On startup it **loads once**: the trained model (`fire_model.joblib`), the sensor data CSV,
  the sorted list of timestamps, the plants table, and Ghazipur's coordinates.
- **`color_for(risk)`** — maps a risk number to a colour: ≥0.15 red, ≥0.05 amber, else green.
- **`apply_heatwave(rows, pct)`** — the slider's effect: at 100% it adds +10 °C to air, +16 °C
  to the surface, and removes 35% humidity (floor 8%) before predicting.
- **`compute_state(hour_idx, heatwave_pct, live)`** — the brain of the dashboard; for a given
  hour + slider + live-toggle it:
  1. Picks that hour's 12 zone rows.
  2. If **live** is on, fetches real weather and overwrites air temp/humidity/wind/drought
     (keeping each zone's simulated surface-heat on top); records the weather mode.
  3. Applies the heatwave shift.
  4. Runs **Model A** to get each zone's fire risk, and builds the coloured zone list.
  5. Scales the day's dig target with the heatwave (8,000→14,000 t) and runs **Model B**.
  6. Finds the top zone's wind and runs **Model C** for the alert + crew plan.
  7. Totals the tonnes going to each plant (for the map lines).
  8. Returns one big dictionary with everything the web page needs.
- **`@app.route("/")`** — serves the web page (`index.html`).
- **`@app.route("/api/state")`** — the data feed: reads `hour`, `heatwave`, `live` from the
  request and returns `compute_state(...)` as JSON.
- `app.run(host="0.0.0.0", port=5000)` — starts the server on port 5000, reachable on the
  network (needed inside a container).

---

## 8. `dashboard/templates/index.html` — the web page (map + panels)

**`<head>`** — loads the Leaflet map library from a CDN and defines the styling (`<style>`):
colours, the header badge, the two-column layout (map left, panels right), the pill chips, the
card panels, and the map-key box.

**`<body>` top:**
- The **header** with the title, the orange **"SIMULATED SENSOR DATA"** badge, and a subtitle
  explaining the Predict→Decide→Generate pipeline.
- The **controls bar**: the **Live weather** checkbox, the **Heatwave** slider, and a row of
  info "pills" (heatwave %, max risk, zones at risk, excavate t/day, unallocated, clock, wind,
  weather source) — each with a hover tooltip — plus the colour legend.
- The **map** `<div>` with the map-key overlay, and the four **panels**: resident alert, dig
  order, routing table, crew plan — each with a one-line description of which model feeds it.

**`<script>` (the live behaviour):**
- `COLORS` — the three risk colours.
- `L.map(...).setView([Ghazipur], 12)` — creates the map centred on Ghazipur; `L.tileLayer`
  adds the OpenStreetMap background; `layer` is a group we redraw each update.
- `let hour = 0` — which simulated hour we're showing.
- **`render(s)`** — draws one update from the server data `s`:
  - Clears the old shapes, drops a Ghazipur pin.
  - For each plant: draws a line from Ghazipur (thickness = tonnes) and a marker.
  - For each zone: draws a circle whose **colour and size grow with risk**.
  - Fills the readout pills (max risk, zones at risk, target, unallocated, clock, wind), and
    colours the max-risk pill by severity.
  - Sets the weather pill to LIVE (green), SIMULATED, or "live unavailable".
  - Writes the alert and crew-plan text, and builds the dig-order and routing tables (adding a
    red "Unallocated" row if there's leftover waste).
- **`refresh()`** — asks the server (`/api/state?...`) for the current hour + slider + live
  setting and calls `render`.
- The two `addEventListener` lines — refresh immediately when you move the slider or toggle
  live weather.
- `refresh()` then `setInterval(... 3000)` — draw once now, then **advance one hour every 3
  seconds**, giving the "live stream" effect.

---

## 9. `data/plants.csv` — the processing-plant network (data, not code)

A small table: for each of ~5 plants its id, name, type (waste-to-energy, cement kiln,
soil-reuse, textile hub, inert/road-fill), GPS location, distance from Ghazipur, daily
capacity in tonnes, and which waste types it accepts. Model B reads this to plan routing.

---

## 10. `Dockerfile` & `requirements.txt` — packaging

- **`requirements.txt`** — the exact versions of the libraries the project needs, so anyone
  (including IBM LinuxONE) installs the same ones.
- **`Dockerfile`** — a recipe to build a self-contained container: start from a slim Python
  image, add the compilers needed on IBM's s390x chip, install the requirements, copy the
  code in, open port 5000, and run the dashboard. Works with `podman` or `docker`.

---

*Data note:* the landfill sensor stream is **simulated** and labelled as such; weather can be
**live** (Open-Meteo); Model B is **optimisation**, not ML. Every real-world figure is sourced
in `docs/SOURCES.md`.
