"""Phase 5 — Deploy inference engine to Arduino Uno Q via ADB."""

import json
import subprocess
import sys
from pathlib import Path

ML_DIR      = Path(__file__).parent
WEIGHTS     = ML_DIR / "model_weights.json"
INFERENCE   = ML_DIR / "inference_uno_q.py"
DEVICE_DIR  = "/home/arduino"


def adb(*args):
    result = subprocess.run(["adb", "shell", *args], capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def adb_push(local, remote):
    result = subprocess.run(["adb", "push", str(local), remote], capture_output=True, text=True)
    print(f"  push {local.name} → {remote}  {'OK' if result.returncode == 0 else 'FAILED'}")
    return result.returncode == 0


# ── Step 1: Create directory on device ───────────────────────────────────────
print("=== Step 1: Create /data/anomaly on Uno Q ===")
out, rc = adb(f"mkdir -p {DEVICE_DIR}")
print(f"  mkdir {DEVICE_DIR}: {'OK' if rc == 0 else out}")

# ── Step 2: Push files ────────────────────────────────────────────────────────
print("\n=== Step 2: Push files via ADB ===")
ok = adb_push(WEIGHTS,   f"{DEVICE_DIR}/model_weights.json")
ok = adb_push(INFERENCE, f"{DEVICE_DIR}/inference_uno_q.py") and ok

if not ok:
    print("Push failed — check ADB connection.")
    sys.exit(1)

# ── Step 3: Verify files on device ───────────────────────────────────────────
print("\n=== Step 3: Verify files on device ===")
out, _ = adb(f"ls -lh {DEVICE_DIR}/")
print(out)

# ── Step 4: Run test readings on device ──────────────────────────────────────
print("\n=== Step 4: Run inference on Uno Q ===")

test_cases = [
    ("normal reading",   {"temperature": 26.5,  "humidity": 41.9, "pressure": 998.8}),
    ("borderline",       {"temperature": 30.2,  "humidity": 85.0, "pressure": 999.3}),
    ("extreme anomaly",  {"temperature": 45.0,  "humidity": 95.0, "pressure": 940.0}),
]

all_passed = True
for label, reading in test_cases:
    payload = json.dumps(reading).replace('"', '\\"')
    cmd     = f"python3 {DEVICE_DIR}/inference_uno_q.py \"{payload}\""
    out, rc = adb(cmd)
    if rc != 0:
        print(f"  [{label}] ERROR: {out}")
        all_passed = False
        continue
    result = json.loads(out)
    status = "ANOMALY" if result["anomaly"] else "NORMAL "
    print(f"  [{label}]  {status}  confidence={result['confidence']}  "
          f"recon_err={result['reconstruction_error']}")

print(f"\nDeployment {'succeeded' if all_passed else 'FAILED'}.")
