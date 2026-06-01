"""Phase 1 — Data exploration, preprocessing, and normalization."""

import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

DATA_PATH  = Path(__file__).parent.parent / "data" / "sensor_log.csv"
PLOTS_DIR  = Path(__file__).parent / "plots"
SCALER_OUT = Path(__file__).parent / "scaler.pkl"
NORM_OUT   = Path(__file__).parent / "data_normalized.npy"

PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
features = ["temperature", "humidity", "pressure"]

print(f"Loaded {len(df)} rows from {DATA_PATH.name}\n")

# ── Stats ─────────────────────────────────────────────────────────────────────
print("=== Basic Statistics ===")
print(df[features].describe().round(3))
print()

# ── Missing values ────────────────────────────────────────────────────────────
missing = df[features].isnull().sum()
print("=== Missing Values ===")
print(missing)
print()

# ── Outlier check (beyond 3 std from mean) ────────────────────────────────────
print("=== Outliers (beyond 3σ) ===")
for col in features:
    mean, std = df[col].mean(), df[col].std()
    outliers  = df[(df[col] < mean - 3 * std) | (df[col] > mean + 3 * std)]
    print(f"  {col}: {len(outliers)} outlier(s)")
print()

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
fig.suptitle("Sensor Overview — BME280 readings", fontsize=13)

axes[0].plot(df["timestamp"], df["temperature"], color="#e74c3c", linewidth=0.8)
axes[0].set_ylabel("Temperature (°C)")
axes[0].axhline(df["temperature"].mean(), color="#e74c3c", linestyle="--", alpha=0.5, label="mean")
axes[0].legend(fontsize=8)

axes[1].plot(df["timestamp"], df["humidity"], color="#3498db", linewidth=0.8)
axes[1].set_ylabel("Humidity (%)")
axes[1].axhline(df["humidity"].mean(), color="#3498db", linestyle="--", alpha=0.5, label="mean")
axes[1].legend(fontsize=8)

axes[2].plot(df["timestamp"], df["pressure"], color="#2ecc71", linewidth=0.8)
axes[2].set_ylabel("Pressure (hPa)")
axes[2].axhline(df["pressure"].mean(), color="#2ecc71", linestyle="--", alpha=0.5, label="mean")
axes[2].legend(fontsize=8)

plt.xlabel("Time")
plt.tight_layout()
out_path = PLOTS_DIR / "sensor_overview.png"
plt.savefig(out_path, dpi=150)
plt.close()
print(f"Plot saved → {out_path}")

# ── Normalize ─────────────────────────────────────────────────────────────────
scaler = MinMaxScaler()
X = df[features].values
X_norm = scaler.fit_transform(X)

with open(SCALER_OUT, "wb") as f:
    pickle.dump(scaler, f)
np.save(NORM_OUT, X_norm)

print(f"Scaler saved → {SCALER_OUT}")
print(f"Normalized data saved → {NORM_OUT}  shape={X_norm.shape}")
print(f"\nNormalized range check (should all be [0, 1]):")
for i, col in enumerate(features):
    print(f"  {col}: min={X_norm[:, i].min():.4f}  max={X_norm[:, i].max():.4f}")
