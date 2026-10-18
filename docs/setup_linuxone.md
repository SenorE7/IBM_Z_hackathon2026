# Running on IBM LinuxONE (s390x Linux)

Everything here is CPU-only and pure-Python-friendly. No GPU, no x86-only binaries, no
secrets or API keys. Internet is only needed for: `pip install`, the optional **Live
weather** toggle (Open-Meteo), and the map tiles — the rest runs offline.

## 0. Prerequisites
- Linux on IBM Z / LinuxONE (**s390x**), **Python 3.11+** (3.12 recommended), and `git`.

## 1. Clone the repo
```bash
git clone https://github.com/SenorE7/IBM_Z_hackathon2026.git
cd IBM_Z_hackathon2026
```

## 2. Create a Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 3. Install dependencies
```bash
pip install -r requirements.txt
```
**s390x note:** `numpy`, `pandas`, `scipy` and `scikit-learn` are CPU-only but compiled.
If pip cannot find prebuilt s390x wheels and falls back to building from source, install
build tools first:
```bash
# Debian/Ubuntu:
sudo apt-get update && sudo apt-get install -y gcc g++ gfortran libopenblas-dev
# RHEL / UBI:
sudo dnf install -y gcc gcc-c++ gcc-gfortran openblas-devel
```
Alternatively use **conda-forge**, which ships s390x builds:
```bash
conda install -c conda-forge flask pandas numpy scipy scikit-learn joblib networkx
```

## 4. (Optional) Retrain Model A
The trained model is committed at `models/fire_model.joblib`, so you can skip this. To
regenerate the data + model:
```bash
python data/generate_data.py
pip install notebook nbconvert ipykernel
python -m nbconvert --to notebook --execute --inplace notebooks/01_fire_model.ipynb
```

## 5. Run the pieces
```bash
# Model B optimiser (dig order + routing):
cd models && python test_optimiser.py && cd ..

# Model C GenAI (resident alert + crew plan):
cd models && python genai.py && cd ..

# Dashboard (Flask + Leaflet):
python dashboard/app.py
# then open http://<host>:5000
```

## 6. Container (podman or docker)
```bash
podman build -t ghazipur-shield .
podman run --rm -p 5000:5000 ghazipur-shield
# open http://localhost:5000      (docker build / docker run work identically)
```

## 7. (Optional) IBM Granite LLM for Model C
By default Model C uses offline templates (no keys, no network). To use an open-weights
**IBM Granite** model on LinuxONE, install a transformers runtime and call
`genai.generate(..., use_llm=True)` — see `generate_with_llm()` in `models/genai.py`. It
falls back to templates automatically if the model/library is unavailable.

## Notes
- **No API keys or secrets** are required anywhere. The Live weather toggle uses Open-Meteo
  (keyless) and degrades gracefully to simulated data offline.
- Sensor data is **simulated** and labelled as such; every real-world figure is sourced in
  `docs/SOURCES.md`.
