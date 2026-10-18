# Pipeline flowchart

Predict → Decide → Generate, feeding one live dashboard.

```mermaid
flowchart LR
  SIM["Simulated zone sensors<br/>surface temp, methane"] --> A
  OM["Open-Meteo live weather<br/>temp, humidity, wind, rain"] -. optional live toggle .-> A
  A["Model A - Predict<br/>Fire-risk classifier (ML)"] -->|per-zone risk| B
  B["Model B - Decide<br/>Dig order + waste routing (optimisation)"] -->|routing JSON| C
  A -->|top risk + wind| C
  C["Model C - Generate<br/>Alerts + crew plan (GenAI)"] --> ALERT["Resident smoke / health alert"]
  C --> PLAN["Crew excavation + truck dispatch"]
  A --> DASH["Dashboard (Flask + Leaflet)"]
  B --> DASH
  C --> DASH
```

**Data honesty:** the zone sensor stream (surface temperature, methane) is **simulated**;
weather can be **live** (Open-Meteo). Model B is **optimisation**, not ML. See
[SOURCES.md](SOURCES.md).
