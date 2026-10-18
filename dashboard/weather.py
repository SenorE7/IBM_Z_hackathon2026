"""
Real-time weather for Ghazipur via the Open-Meteo free API (no API key required).

Pure-Python (stdlib urllib only) so it runs on IBM LinuxONE / s390x. Returns None on ANY
failure (no network, timeout, bad response) so callers fall back to simulated weather.
Results are cached for ~10 minutes to avoid hammering the API on every dashboard poll.

Only WEATHER is real here (temperature, humidity, wind, rainfall). Per-zone landfill
surface temperature and methane are NOT available as real feeds and remain simulated.
"""

import json
import time
import urllib.parse
import urllib.request

GHAZIPUR_LAT, GHAZIPUR_LON = 28.6257, 77.3277
_CACHE = {"ts": 0.0, "data": None}
_TTL = 600  # seconds


def get_live_weather(timeout: float = 6.0):
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    try:
        params = urllib.parse.urlencode({
            "latitude": GHAZIPUR_LAT, "longitude": GHAZIPUR_LON,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
            "daily": "precipitation_sum",
            "past_days": 14, "forecast_days": 1,
            "wind_speed_unit": "kmh", "timezone": "auto",
        })
        url = "https://api.open-meteo.com/v1/forecast?" + params
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            j = json.load(resp)

        cur = j["current"]
        # Days since last meaningful rain (>= 1 mm), counted back from today.
        precip = j.get("daily", {}).get("precipitation_sum", []) or []
        dsr = 0
        for v in reversed(precip):
            if v is not None and v >= 1.0:
                break
            dsr += 1

        data = {
            "ambient_temp_c": float(cur["temperature_2m"]),
            "humidity_pct": float(cur["relative_humidity_2m"]),
            "wind_speed_kmh": float(cur["wind_speed_10m"]),
            "wind_direction_deg": float(cur["wind_direction_10m"]),
            "days_since_rain": float(dsr),
            "observed_at": cur.get("time"),
            "source": "Open-Meteo",
        }
        _CACHE.update(ts=now, data=data)
        return data
    except Exception:
        return None


if __name__ == "__main__":
    print(get_live_weather())
