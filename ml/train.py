"""Phase 2 — Train autoencoder anomaly detection model."""

import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import train_test_split
from tensorflow import keras
from tensorflow.keras import layers

NORM_DATA   = Path(__file__).parent / "data_normalized.npy"
PLOTS_DIR   = Path(__file__).parent / "plots"
MODEL_OUT   = Path(__file__).parent / "anomaly_model.keras"
THRESH_OUT  = Path(__file__).parent / "threshold.pkl"

PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
X = np.load(NORM_DATA)
X_train, X_val = train_test_split(X, test_size=0.2, random_state=42, shuffle=True)
print(f"Train: {X_train.shape}  Val: {X_val.shape}")

# ── Build autoencoder ─────────────────────────────────────────────────────────
inputs  = keras.Input(shape=(2,))
encoded = layers.Dense(16, activation="relu")(inputs)
encoded = layers.Dense(8,  activation="relu")(encoded)
encoded = layers.Dense(4,  activation="relu")(encoded)
decoded = layers.Dense(8,  activation="relu")(encoded)
decoded = layers.Dense(16, activation="relu")(decoded)
outputs = layers.Dense(2,  activation="linear")(decoded)

model = keras.Model(inputs, outputs, name="anomaly_autoencoder")
model.compile(optimizer="adam", loss="mse")
model.summary()

# ── Train ─────────────────────────────────────────────────────────────────────
early_stop = keras.callbacks.EarlyStopping(
    monitor="val_loss", patience=10, restore_best_weights=True
)

history = model.fit(
    X_train, X_train,
    validation_data=(X_val, X_val),
    epochs=100,
    batch_size=32,
    callbacks=[early_stop],
    verbose=1,
)

# ── Plot training loss ─────────────────────────────────────────────────────────
plt.figure(figsize=(10, 4))
plt.plot(history.history["loss"],     label="Train loss")
plt.plot(history.history["val_loss"], label="Val loss")
plt.xlabel("Epoch")
plt.ylabel("MSE Loss")
plt.title("Autoencoder Training Loss")
plt.legend()
plt.tight_layout()
loss_plot = PLOTS_DIR / "training_loss.png"
plt.savefig(loss_plot, dpi=150)
plt.close()
print(f"\nLoss plot saved → {loss_plot}")

# ── Compute anomaly threshold ─────────────────────────────────────────────────
X_pred    = model.predict(X_train, verbose=0)
recon_err = np.mean(np.square(X_train - X_pred), axis=1)
threshold = float(recon_err.mean() + 2 * recon_err.std())

with open(THRESH_OUT, "wb") as f:
    pickle.dump(threshold, f)

model.save(MODEL_OUT)

print(f"Model saved    → {MODEL_OUT}")
print(f"Threshold saved → {THRESH_OUT}")
print(f"\nAnomaly threshold: {threshold:.6f}")
print(f"  (mean recon error={recon_err.mean():.6f}, std={recon_err.std():.6f})")
