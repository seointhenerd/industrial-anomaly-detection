# Industrial Anomaly Detection System

> Real-time edge AI system that detects environmental anomalies locally on embedded hardware — no cloud dependency.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![C++](https://img.shields.io/badge/C++-Arduino-00599C?style=flat-square&logo=cplusplus&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)
![PlatformIO](https://img.shields.io/badge/PlatformIO-ESP32-orange?style=flat-square&logo=platformio&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32--S3-Espressif-red?style=flat-square)

---

## Overview

A multi-device edge AI system that continuously reads environmental sensor data, runs anomaly detection inference directly on embedded Linux hardware, triggers hardware alerts, captures visual evidence, and streams everything to a live web dashboard — entirely on the local network.

The core ML model is a 6-layer autoencoder (471 parameters) trained on normal operating conditions. Anomalies are flagged when reconstruction error exceeds a threshold derived from the training distribution (mean + 2σ = 0.000026). Inference runs as pure Python on the Arduino Uno Q with zero external dependencies.

---

## System Architecture

```
┌─────────────┐   I2C    ┌────────────────────┐   WiFi / UDP (5s)   ┌─────────────────────┐
│   BME280    │─────────▶│  ESP32-S3-N16R8    │────────────────────▶│   Mac               │
│  temp + hum │          │  Sensor Node       │    JSON payload      │   receiver.py       │
└─────────────┘          │  C++ / PlatformIO  │                      └──────────┬──────────┘
                         └────────────────────┘                                 │
                                                                                │ ADB shell
                                                                                ▼
                                                                   ┌─────────────────────┐
                                                                   │  Arduino Uno Q       │
                                                                   │  Qualcomm QRB2210    │
                                                                   │  Debian Linux arm64  │
                                                                   │  Python autoencoder  │
                                                                   └──────────┬──────────┘
                                                                              │
                                                              ┌───────────────┴───────────────┐
                                                              │           anomaly?            │
                                                              ▼                               ▼
                                                   ┌──────────────────┐         ┌────────────────────┐
                                                   │  Red LED ON      │         │  HTTP GET          │
                                                   │  GPIO sysfs      │         │  /snapshot         │
                                                   └──────────────────┘         └─────────┬──────────┘
                                                                                           │
                                                                              ┌────────────▼──────────┐
                                                                              │  ESP32-S3-CAM         │
                                                                              │  OV2640 · HTTP server │
                                                                              └─────────┬─────────────┘
                                                                                        │ JPEG
                                                                              ┌─────────▼─────────────┐
                                                                              │  FastAPI Dashboard    │
                                                                              │  localhost:8000       │
                                                                              │  Chart.js · live data │
                                                                              └───────────────────────┘
```

---

## Hardware

### Components

| Device | Role | Notes |
|---|---|---|
| ESP32-S3-N16R8 | Sensor node | Reads BME280, sends UDP, NTP timestamps |
| BME280 | Environmental sensor | Temperature + humidity via I2C |
| Arduino Uno Q (WCBN3536A) | Edge inference | Qualcomm QRB2210, Debian Linux, Python 3 |
| ESP32-S3-CAM (OV2640) | Camera server | JPEG snapshots over HTTP |
| Mac | Hub | Runs receiver.py, ADB bridge, FastAPI dashboard |

### BME280 → ESP32-S3 Wiring

| BME280 Pin | ESP32-S3 Pin | Notes |
|---|---|---|
| VCC | 3.3V | Do not use 5V |
| GND | GND | |
| SDA | GPIO 8 | I2C data |
| SCL | GPIO 9 | I2C clock |
| SDO | GND | Sets I2C address to 0x76 |
| CSB | 3.3V | Selects I2C mode |

---

## Project Structure

```
industrial-anomaly-detection/
├── firmware/
│   ├── esp32-sensor-node/         ← C++ sensor firmware (PlatformIO)
│   │   ├── src/main.cpp
│   │   ├── include/config.h       ← WiFi credentials (gitignored)
│   │   └── platformio.ini
│   └── esp32-s3-cam/              ← C++ camera HTTP server (PlatformIO)
│       ├── src/main.cpp
│       ├── include/config.h       ← WiFi credentials (gitignored)
│       └── platformio.ini
├── receiver/
│   ├── receiver.py                ← UDP listener + ADB bridge + anomaly logger
│   └── collect.py                 ← Data collection only (no inference)
├── ml/
│   ├── explore.py                 ← Data exploration + normalization
│   ├── train.py                   ← Autoencoder training (Keras)
│   ├── test.py                    ← Model validation
│   ├── export_weights.py          ← Export Keras weights → JSON
│   ├── deploy_uno_q.py            ← Push inference files to Uno Q via ADB
│   └── inference_uno_q.py         ← Pure Python inference (runs on Uno Q)
├── dashboard/
│   ├── server.py                  ← FastAPI backend
│   └── static/index.html          ← Dark-theme live dashboard
├── data/                          ← sensor_log.csv + anomaly_log.csv (gitignored)
├── snapshots/                     ← JPEG anomaly snapshots (gitignored)
├── start.sh                       ← Launch everything in one command
└── README.md
```

---

## ML Pipeline

```
sensor_log.csv
      │
      ▼
explore.py          → normalize features (MinMaxScaler), drop pressure
      │
      ▼
train.py            → Input(2) → Dense(16) → Dense(8) → Dense(4)
                               → Dense(8)  → Dense(16) → Dense(2)
                      471 parameters · trained on normal data only
                      threshold = mean + 2σ of reconstruction error
      │
      ▼
export_weights.py   → model_weights.json  (weights + scaler params)
      │
      ▼
deploy_uno_q.py     → adb push model_weights.json + inference_uno_q.py
      │
      ▼
inference_uno_q.py  → pure Python forward pass · returns anomaly / confidence / error
```

**To retrain with new data:**
```bash
# 1. Collect normal readings
python3 receiver/collect.py

# 2. Retrain
cd ml && .venv/bin/python train.py

# 3. Export + redeploy
.venv/bin/python export_weights.py
.venv/bin/python deploy_uno_q.py
```

---

## Key Engineering Decisions

### 1. Pressure dropped from ML features
The BME280 pressure readings during the training window spanned only 0.8 hPa (998.5–999.3 hPa). The following day, normal atmospheric variation put pressure 24 standard deviations from the training mean — flagging every reading as an anomaly. Pressure was removed as a feature entirely. The model now uses temperature and humidity only, which have enough natural variation in training data to form a stable distribution.

### 2. Pure Python inference instead of TFLite
The Arduino Uno Q runs Debian Linux under the `arduino` user, which has no `pip`, no `root`, and no `ensurepip`. TFLite deployment was not feasible. Instead, Keras model weights were exported to a JSON file and a pure Python forward pass was written using only the standard library — no installation required, no runtime dependency. The model runs directly via `python3 inference_uno_q.py` invoked over ADB.

### 3. Separate PlatformIO projects per board
Two ESP32-S3 boards are connected to the host Mac simultaneously during development — the sensor node (USB CDC on `/dev/cu.usbmodem2101`) and the camera (TTL on `/dev/cu.usbserial-110`). Without explicit `upload_port` and `monitor_port` in each `platformio.ini`, PlatformIO auto-selects a port and can flash the wrong board. Each project locks its own port to prevent accidental overwrites.

---

## Getting Started

### Prerequisites

- [PlatformIO](https://platformio.org/) for firmware
- Python 3.11+ on Mac
- ADB installed (`brew install android-platform-tools`)
- Arduino Uno Q connected via USB with ADB enabled
- ESP32-S3-CAM and ESP32-S3 sensor node on the same WiFi network as the Mac

### Configuration

Copy the config templates and fill in credentials:

```bash
cp firmware/esp32-sensor-node/include/config.example.h \
   firmware/esp32-sensor-node/include/config.h

cp firmware/esp32-s3-cam/include/config.example.h \
   firmware/esp32-s3-cam/include/config.h
```

Set `UDP_HOST` in `esp32-sensor-node/include/config.h` to your Mac's local IP.

### Flash Firmware

```bash
# Sensor node
cd firmware/esp32-sensor-node && pio run --target upload

# Camera
cd firmware/esp32-s3-cam && pio run --target upload
```

### Run

```bash
# Install dashboard dependencies (first time only)
python3 -m venv dashboard/.venv
dashboard/.venv/bin/pip install fastapi uvicorn

# Start everything
./start.sh [camera-ip]
```

Open **http://localhost:8000**

---

## Dashboard

| Panel | Description |
|---|---|
| Live Sensor Feed | Chart.js line graph — temperature (orange) + humidity (blue), last 50 readings, refreshes every 5s |
| Stat Cards | Current temperature, humidity, and OK / ANOMALY status |
| Anomaly Events | Scrollable feed of detections, newest first — red border if confidence > 80% |
| Latest Snapshot | Most recent JPEG from ESP32-S3-CAM, pulled from full anomaly history |
