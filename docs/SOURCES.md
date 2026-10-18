# Sources & data provenance

Every real-world figure used anywhere in this project is listed here with its source.

**Status legend**
- **SOURCED** — backed by the cited URL.
- **APPROX** — approximate location/distance; the cited source gives the rough figure or it
  is estimated from map coordinates. Treat as indicative.
- **ASSUMPTION** — a modelling choice we made (e.g. an exact split or a plant capacity with
  no public figure), derived from sourced ranges or typical industry values.
- **UNVERIFIED** — no source found; do not present as fact.

> The sensor dataset (`data/landfill_sensors.csv`) is **SIMULATED**, not measured. Per-zone
> methane and 12-zone spatial resolution do **not** exist in any real public source
> (TROPOMI methane ~7 km; VIIRS fire ~375 m vs the ~500 m landfill footprint), which is why
> the sensor stream is simulated. See "Real-data limits" below.

---

## Ghazipur landfill

| Figure | Value used | Status | Source |
|---|---|---|---|
| In operation since | 1984 | SOURCED | NGT/CPCB report (below) |
| Total legacy waste | ~82.39 lakh MT (~8.2 M tonnes) | SOURCED | NGT/CPCB report |
| Height | ~65 m | SOURCED | NGT/CPCB report |
| Biomining rate (target) | 7,000 → 12,000 tonnes/day | SOURCED | Daily Pioneer |
| Excavators deployed | 35 | SOURCED | Daily Pioneer / The Tribune |
| Target clearance | by Dec 2027 | SOURCED | Daily Pioneer |

- Daily Pioneer — https://dailypioneer.com/news/biomining-in-ghazipur-landfill-to-rise-to-12000-tonnes-daily-by-july-31
- NGT/CPCB report (OA 481 of 2024, Ghazipur fire) — https://www.greentribunal.gov.in/sites/default/files/news_updates/REPORT%20BY%20CPCB%20IN%20OA%20NO.%20481%20of%202024%20NEWS%20ITEM%20TITLED%20MAJOR%20FIRE%20ERUPTS%20AT%20DELHI,S%20GHAZIPUR%20LANDFILL%20SITE%20SMOKE%20ENGULFS%20REGION.pdf

## Waste-fraction composition (biomined legacy waste, India)

Published ranges (by weight): soil-like material (SLM) ~40–65%, RDF/combustibles ~15–25%,
inerts ~9–20%, recyclables <1–5%. Karnataka example: 65% SLM / 25% RDF / 9% inert / <1% recyclable.

- CSE — Legacy Waste Management (Dr Richa Singh) — https://cdn.cseindia.org/docs/Legacy-wastemanagement/Richa_Symposium_Richa-Singh.pdf

**Split used by Model B** (must sum to 100%). The 5-way split below is an **ASSUMPTION**:
we subdivide the sourced "combustibles ~15–25%" band into RDF / plastics / textiles for
routing, and fold recyclables into inerts. Values chosen within the sourced ranges.

| Fraction | % used | Status |
|---|---|---|
| Fine soil (SLM) | 52% | ASSUMPTION (within sourced 40–65%) |
| RDF / combustibles | 18% | ASSUMPTION (within sourced 15–25% combustibles) |
| Plastics | 8% | ASSUMPTION (subset of combustibles) |
| Textiles | 5% | ASSUMPTION (subset of combustibles) |
| Inert | 17% | ASSUMPTION (within sourced 9–20%) |

## Fire-risk model (how the simulated label is generated)

The sensor data is simulated, but the relationship between features and `fire_next_24h` is
grounded in published landfill-fire science. Three terms combine into a latent risk:

| Term | Basis | Value/threshold | Status | Source |
|---|---|---|---|---|
| Fire-weather (temp↑, humidity↓, wind↑, drought↑) | McArthur Fire Danger Index form | coeffs 0.0338·T − 0.0345·RH + 0.0234·wind + 0.5·ln(drought+1) | SOURCED (form) | McArthur FDI |
| Thermal self-heating | MSW smoulder onset | risk climbs as surface temp → **80 °C** | SOURCED | EPA subsurface smouldering |
| Methane | lower explosive limit | risk rises toward **50,000 ppm (5% LEL)** | SOURCED | ATSDR landfill gas |
| Seasonality | landfill fires peak Mar–Aug | Apr–Jun hot window modelled | SOURCED | SCS Engineers |

- SCS Engineers — Understanding & Managing Landfill Fires — https://www.scsengineers.com/wp-content/uploads/2025/01/Understanding-and-Managing-Landfill-Fires-2024.pdf
- EPA — Subsurface Smouldering Event (80 °C threshold, 100–300 °C smoulder) — https://semspub.epa.gov/work/07/30286004.pdf
- ATSDR — Landfill Gas Safety (methane LEL 5% = 50,000 ppm) — https://www.atsdr.cdc.gov/hac/landfill/pdfs/landfill_2001_ch3.pdf
- McArthur Fire Danger Index formula — https://dayboro.au/fire-danger-index/

## Destination plants (used in `data/plants.csv`)

Capacities marked SOURCED are real plant figures; others are ASSUMPTION. Coordinates and
distances from Ghazipur are APPROX (indicative, for routing-cost demonstration).

| Plant (type) | Capacity used | Capacity status | Dist. from Ghazipur | Dist. status |
|---|---|---|---|---|
| Okhla Waste-to-Energy (wte) | 1,800 TPD | SOURCED | ~15 km | APPROX |
| Cement kiln — RDF co-processing (cement_kiln) | 1,200 TPD | ASSUMPTION | ~120 km | APPROX |
| Compost / soil-reuse site (soil_reuse) | 7,000 TPD | ASSUMPTION | ~5 km | APPROX |
| Panipat textile hub (textile_hub) | 300 TPD | SOURCED | ~90 km | APPROX (per project brief) |
| Inert / road-fill (inert_road) | 3,000 TPD | ASSUMPTION | ~10 km | APPROX |

> Capacities for soil-reuse, inert and cement are ASSUMPTION values chosen so the daily
> excavation target (12,000 t) is *mostly* processable; a small combustible shortfall is
> left deliberately so the optimiser demonstrates reporting of unallocated tonnes.

- Delhi WtE capacities (Okhla 1,800 TPD etc.) — BioEnergy Times — https://bioenergytimes.com/delhi-to-expand-biogas-and-waste-processing-capacity-by-13550-tpd-to-cut-landfill-burden/
- Panipat textile recycling (~250–300 TPD, world's largest hub) — The Tribune — https://www.tribuneindia.com/news/haryana/handloom-city-panipat-weaves-worlds-largest-recycling-empire/
- RDF co-processing in cement kilns + SLM/polythene reuse (Indore model) — IIPA — https://www.iipa.org.in/cms/public/uploads/550301652178662.pdf

## Other modelling constants

| Constant | Value | Status |
|---|---|---|
| Truck (tipper) capacity for dispatch counts | ~10 tonnes | ASSUMPTION (typical 9–16 t) |
| Daily excavation target (default) | 12,000 tonnes/day | SOURCED (Ghazipur target, above) |
| Number of landfill zones | 12 | ASSUMPTION (operational sub-division for the demo; not a real published zoning) |
| Per-zone daily excavation cap | excavation_target / 4 | ASSUMPTION (so the day's dig draws from the top few highest-risk zones) |
| Dashboard excavation target vs heatwave | 8,000 t (0%) → 14,000 t (100%) | ASSUMPTION (high fire risk → excavate more aggressively; drives live route changes) |
| Dashboard heatwave shift at 100% | +10 °C air, +16 °C surface, −35% RH | ASSUMPTION (severe but plausible heatwave; India heatwaves run ~5–12 °C above normal) |

## Real-data limits (why sensors are simulated)

- Weather (temp/humidity/wind/precip): **real + free** via Open-Meteo (no key) —
  https://open-meteo.com/en/docs — **now wired into the dashboard's "Live weather" toggle**
  (real current Ghazipur air temp, humidity, wind, and days-since-rain drive the model;
  per-zone surface temp + methane stay simulated).
- Fire detections: **real + free** via NASA FIRMS VIIRS 375 m (Earthdata login) —
  https://firms.modaps.eosdis.nasa.gov/active_fire/ — reserved for future work.
- Methane at per-zone resolution: **does not exist publicly.** TROPOMI ~7 km, GHGSat is
  commercial/snapshot — https://www.science.org/doi/10.1126/sciadv.abn9683
