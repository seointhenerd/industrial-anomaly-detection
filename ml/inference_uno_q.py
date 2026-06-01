"""Anomaly detection inference — pure Python, no external dependencies.

Usage:
    python3 inference_uno_q.py '{"temperature": 26.5, "humidity": 41.9, "pressure": 998.8}'
"""

import json
import math
import sys
from pathlib import Path

WEIGHTS_PATH = Path(__file__).parent / "model_weights.json"


def load_model(path):
    with open(path) as f:
        return json.load(f)


def scale(x, data_min, data_max):
    return [(x[i] - data_min[i]) / (data_max[i] - data_min[i]) for i in range(len(x))]


def dense(x, W, b, activation):
    n_in, n_out = len(x), len(b)
    out = [sum(x[j] * W[j][k] for j in range(n_in)) + b[k] for k in range(n_out)]
    if activation == "relu":
        return [max(0.0, v) for v in out]
    return out


def forward(x_scaled, layers):
    out = x_scaled
    for layer in layers:
        out = dense(out, layer["W"], layer["b"], layer["activation"])
    return out


def reconstruction_error(original, reconstructed):
    return sum((o - r) ** 2 for o, r in zip(original, reconstructed)) / len(original)


def confidence(recon_err, threshold):
    ratio = recon_err / threshold
    return min(1.0, math.tanh(ratio))


def run_inference(reading: dict, model_data: dict) -> dict:
    features  = model_data["features"]
    data_min  = model_data["scaler"]["data_min"]
    data_max  = model_data["scaler"]["data_max"]
    threshold = model_data["threshold"]

    x_raw    = [reading[f] for f in features]
    x_scaled = scale(x_raw, data_min, data_max)
    x_recon  = forward(x_scaled, model_data["layers"])
    err      = reconstruction_error(x_scaled, x_recon)
    is_anomaly = err > threshold

    return {
        "anomaly":              is_anomaly,
        "confidence":           round(confidence(err, threshold), 4),
        "reconstruction_error": round(err, 6),
        "threshold":            round(threshold, 6),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 inference_uno_q.py '{\"temperature\": 26.5, \"humidity\": 41.9, \"pressure\": 998.8}'")
        sys.exit(1)

    reading    = json.loads(sys.argv[1])
    model_data = load_model(WEIGHTS_PATH)
    result     = run_inference(reading, model_data)

    print(json.dumps(result, indent=2))
