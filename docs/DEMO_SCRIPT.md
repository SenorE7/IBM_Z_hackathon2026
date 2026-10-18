# 3-Minute Demo Script — Ghazipur Landfill Fire & Contamination Shield

A timed walkthrough for the datathon submission video. Narration is ~450 words (≈150 wpm).

## Pre-flight (before you hit record)
1. Start the dashboard: `python dashboard/app.py` → open **http://localhost:5000** full-screen.
2. Let the sim clock advance to a **daytime hour** (e.g. 12:00–21:00) so the baseline map is lively.
3. Make sure the **Heatwave slider is at 0%** and **Live weather is OFF** to start.
4. Zoom the map so the 12-zone cluster and the nearby plant markers are both visible.
5. Have the four side panels (alert, dig order, routing, crew plan) in view.

## The script

| Time | On screen | Narration |
|---|---|---|
| **0:00–0:20** | Title slide / aerial of Ghazipur | "Delhi's Ghazipur landfill is a 65-metre mountain of waste that catches fire again and again — blanketing nearby homes and schools in toxic smoke. Crews are digging it down, but every day they face two urgent questions: which part will burn next, and where do we put what we dig out?" |
| **0:20–0:40** | Cut to the dashboard | "Our Fire & Contamination Shield answers both, in real time, on one screen. It's a three-stage AI pipeline — **Predict, Decide, Generate** — and it's built to run on IBM LinuxONE." |
| **0:40–1:05** | Tick **Live weather** ON; point to green pill + green map | "First, **Predict**. A machine-learning model scores all twelve zones for fire risk over the next 24 hours. I'll switch on the live weather feed — it's pulling Ghazipur's **actual** conditions right now from Open-Meteo. It's humid today, so the risk is genuinely low: the map stays green." |
| **1:05–1:40** | Turn Live OFF; **drag Heatwave slider to 100%** slowly | "But watch a pre-monsoon heatwave. As I raise the temperature and drop the humidity, the model **re-predicts live** — zones swell and turn red, the max-risk reading climbs past 80%, and four zones light up as critical. This is early warning the site has never had." |
| **1:40–2:15** | Point to **Dig order**, then **Routing table** + map lines + unallocated | "Now, **Decide**. The system digs the **riskiest zone first**, then an optimisation engine routes the excavated waste — soil, combustibles, plastics, textiles, rubble — to the **nearest plant with spare capacity**: waste-to-energy, cement kilns, the Panipat textile recyclers. It never overloads a plant, and it **flags what won't fit** — here, the tonnes with nowhere to go today." |
| **2:15–2:40** | Point to **Resident alert**, then **Crew plan** | "Finally, **Generate**. A language model writes two things automatically: a plain-English **smoke alert** for the neighbourhoods **downwind** of the fire — naming them — and the crews' **daily dig-and-dispatch plan**, down to the truck counts." |
| **2:40–3:00** | Back to full dashboard / closing slide | "It's honest: the landfill sensors are simulated and labelled, every figure is sourced, and the weather is real. And because it runs in a container on **IBM LinuxONE**, any city — Mumbai to Manchester — can deploy this same node. **Predict the fire. Plan the dig. Protect the people.**" |

## Recording tips
- Do the **Live → Heatwave** contrast in one continuous take — the live re-prediction is the "wow" moment.
- Drag the slider **slowly** so the recolour + readouts changing are clearly visible.
- Keep the **"SIMULATED SENSOR DATA"** badge in frame when you mention honesty.
- If you want a backup, the key frames are saved in `docs/` (`dashboard_live_weather.png`,
  `demo_heatwave_high.png`).
