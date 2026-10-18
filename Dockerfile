# Container image for the Ghazipur Landfill Fire & Contamination Shield dashboard.
# Multi-arch base (works on IBM LinuxONE / s390x as well as x86). Build with podman or docker.
FROM python:3.12-slim

# Build tools for numpy/pandas/scipy/scikit-learn on s390x, where prebuilt wheels may be
# absent and pip builds from source. (Harmless on x86, where wheels are used.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ gfortran libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
# Flask dev server binds 0.0.0.0:5000 (see dashboard/app.py).
CMD ["python", "dashboard/app.py"]
