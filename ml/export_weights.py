"""Export model weights and scaler params as JSON for Uno Q deployment."""

import json
import pickle
from pathlib import Path

import numpy as np
from tensorflow import keras

MODEL_PATH  = Path(__file__).parent / "anomaly_model.keras"
SCALER_PKL  = Path(__file__).parent / "scaler.pkl"
THRESH_PKL  = Path(__file__).parent / "threshold.pkl"
WEIGHTS_OUT = Path(__file__).parent / "model_weights.json"

model = keras.models.load_model(MODEL_PATH)

with open(SCALER_PKL, "rb") as f:
    scaler = pickle.load(f)
with open(THRESH_PKL, "rb") as f:
    threshold = pickle.load(f)

# ── Extract Dense layer weights ───────────────────────────────────────────────
layers_data = []
for layer in model.layers:
    if not hasattr(layer, "kernel"):
        continue
    act = layer.activation.__name__
    layers_data.append({
        "W":          layer.kernel.numpy().tolist(),
        "b":          layer.bias.numpy().tolist(),
        "activation": act,
    })

# ── Extract MinMaxScaler params ───────────────────────────────────────────────
scaler_params = {
    "data_min": scaler.data_min_.tolist(),
    "data_max": scaler.data_max_.tolist(),
}

payload = {
    "layers":    layers_data,
    "scaler":    scaler_params,
    "threshold": threshold,
    "features":  ["temperature", "humidity"],
}

with open(WEIGHTS_OUT, "w") as f:
    json.dump(payload, f)

print(f"Exported {len(layers_data)} layers → {WEIGHTS_OUT}")
print(f"Scaler min: {scaler_params['data_min']}")
print(f"Scaler max: {scaler_params['data_max']}")
print(f"Threshold:  {threshold:.6f}")
print(f"File size:  {WEIGHTS_OUT.stat().st_size / 1024:.1f} KB")
