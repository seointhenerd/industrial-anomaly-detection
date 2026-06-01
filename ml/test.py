"""Phase 3 — Test anomaly detection on real data + simulated anomalies."""

import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tensorflow import keras

DATA_PATH  = Path(__file__).parent.parent / "data" / "sensor_log.csv"
SCALER_PKL = Path(__file__).parent / "scaler.pkl"
THRESH_PKL = Path(__file__).parent / "threshold.pkl"
MODEL_PATH = Path(__file__).parent / "anomaly_model.keras"
PLOTS_DIR  = Path(__file__).parent / "plots"

# ── Load ──────────────────────────────────────────────────────────────────────
model = keras.models.load_model(MODEL_PATH)

with open(SCALER_PKL, "rb") as f:
    scaler = pickle.load(f)
with open(THRESH_PKL, "rb") as f:
    threshold = pickle.load(f)

df       = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
features = ["temperature", "humidity", "pressure"]
X        = scaler.transform(df[features].values)

print(f"Loaded {len(df)} rows")
print(f"Anomaly threshold: {threshold:.6f}\n")

# ── Inference on full dataset ─────────────────────────────────────────────────
X_pred    = model.predict(X, verbose=0)
recon_err = np.mean(np.square(X - X_pred), axis=1)
anomalies = np.where(recon_err > threshold)[0]

print(f"=== Real Data Results ===")
print(f"Total rows   : {len(df)}")
print(f"Anomalies    : {len(anomalies)} ({100*len(anomalies)/len(df):.1f}%)")
if len(anomalies) > 0:
    print("\nAnomalous rows (first 10):")
    for idx in anomalies[:10]:
        row = df.iloc[idx]
        print(f"  row {idx:4d} | {row['timestamp']} | "
              f"temp={row['temperature']}°C  hum={row['humidity']}%  "
              f"pres={row['pressure']}hPa  err={recon_err[idx]:.6f}")

# ── Simulate fake anomalies ───────────────────────────────────────────────────
fake = np.array([
    [45.0, 95.0, 940.0],
    [45.0, 95.0, 940.0],
    [45.0, 95.0, 940.0],
    [45.0, 95.0, 940.0],
    [45.0, 95.0, 940.0],
])
fake_norm  = scaler.transform(fake)
fake_pred  = model.predict(fake_norm, verbose=0)
fake_err   = np.mean(np.square(fake_norm - fake_pred), axis=1)
fake_flags = fake_err > threshold

print(f"\n=== Simulated Anomalies (temp=45°C, humidity=95%, pressure=940hPa) ===")
for i, (err, flagged) in enumerate(zip(fake_err, fake_flags)):
    result = "FLAGGED ✓" if flagged else "missed ✗"
    print(f"  sample {i+1}: recon_error={err:.6f}  →  {result}")

all_caught = fake_flags.all()
print(f"\nAll 5 fake anomalies caught: {'YES ✓' if all_caught else 'NO ✗'}")

# ── Plot reconstruction error ─────────────────────────────────────────────────
plt.figure(figsize=(14, 4))
plt.plot(recon_err, linewidth=0.7, color="#3498db", label="Reconstruction error")
plt.axhline(threshold, color="#e74c3c", linestyle="--", linewidth=1.2, label=f"Threshold ({threshold:.6f})")
if len(anomalies) > 0:
    plt.scatter(anomalies, recon_err[anomalies], color="#e74c3c", s=20, zorder=5, label="Anomaly")
plt.xlabel("Sample index")
plt.ylabel("MSE reconstruction error")
plt.title("Reconstruction Error over Time")
plt.legend()
plt.tight_layout()
out_path = PLOTS_DIR / "reconstruction_error.png"
plt.savefig(out_path, dpi=150)
plt.close()
print(f"\nPlot saved → {out_path}")
