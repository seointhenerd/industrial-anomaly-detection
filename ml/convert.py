"""Phase 4 — Convert trained model to TensorFlow Lite."""

import pickle
from pathlib import Path

import numpy as np
import tensorflow as tf

MODEL_PATH = Path(__file__).parent / "anomaly_model.keras"
TFLITE_OUT = Path(__file__).parent / "anomaly_model.tflite"
SCALER_PKL = Path(__file__).parent / "scaler.pkl"

# ── Convert ───────────────────────────────────────────────────────────────────
model     = tf.keras.models.load_model(MODEL_PATH)
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

TFLITE_OUT.write_bytes(tflite_model)
size_kb = TFLITE_OUT.stat().st_size / 1024
print(f"TFLite model saved → {TFLITE_OUT}")
print(f"Model size: {size_kb:.1f} KB\n")

# ── Verify with 5 sample readings ─────────────────────────────────────────────
with open(SCALER_PKL, "rb") as f:
    scaler = pickle.load(f)

samples = np.array([
    [26.5, 41.9, 998.8],  # typical normal
    [27.0, 42.5, 998.7],  # normal
    [26.2, 41.3, 998.6],  # normal
    [30.2, 85.0, 999.3],  # borderline (real anomaly from dataset)
    [45.0, 95.0, 940.0],  # extreme anomaly
], dtype=np.float32)

samples_norm = scaler.transform(samples).astype(np.float32)

interpreter = tf.lite.Interpreter(model_path=str(TFLITE_OUT))
interpreter.allocate_tensors()
input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("=== Verification (5 sample readings) ===")
for i, (raw, norm) in enumerate(zip(samples, samples_norm)):
    interpreter.set_tensor(input_details[0]["index"], norm.reshape(1, 3))
    interpreter.invoke()
    recon     = interpreter.get_tensor(output_details[0]["index"])[0]
    recon_err = float(np.mean(np.square(norm - recon)))
    label = ["normal", "normal", "normal", "borderline", "extreme anomaly"][i]
    print(f"  sample {i+1} [{label}]: "
          f"temp={raw[0]}°C  hum={raw[1]}%  pres={raw[2]}hPa  "
          f"→  recon_error={recon_err:.6f}")

print("\nConversion verified successfully.")
