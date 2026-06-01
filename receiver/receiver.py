"""UDP receiver — receives ESP32 sensor packets, runs ML inference on Uno Q, controls alert LED,
and captures snapshots from ESP32-S3-CAM on anomaly events."""

import csv
import json
import os
import socket
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

UDP_IP   = "0.0.0.0"
UDP_PORT = 5005

CSV_PATH       = Path(__file__).parent.parent / "data" / "sensor_log.csv"
ANOMALY_PATH   = Path(__file__).parent.parent / "data" / "anomaly_log.csv"
SNAPSHOTS_DIR  = Path(__file__).parent.parent / "snapshots"

CSV_HEADERS     = ["timestamp", "temperature", "humidity", "pressure"]
ANOMALY_HEADERS = ["timestamp", "temperature", "humidity", "pressure",
                   "reconstruction_error", "confidence", "snapshot_file"]

LED_PATH         = "/sys/class/leds/red:user/brightness"
INFERENCE_SCRIPT = "/home/arduino/inference_uno_q.py"
ESP32_CAM_IP     = os.environ.get("ESP32_CAM_IP", "")


def set_alert_led(on: bool) -> None:
    value = "1" if on else "0"
    subprocess.run(["adb", "shell", f"echo {value} > {LED_PATH}"], capture_output=True)


def run_inference(temp: float, humidity: float) -> dict | None:
    payload = json.dumps({"temperature": temp, "humidity": humidity})
    result  = subprocess.run(
        ["adb", "shell", f"python3 {INFERENCE_SCRIPT} '{payload}'"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return json.loads(result.stdout.strip())


def capture_snapshot(ts: str) -> str:
    if not ESP32_CAM_IP:
        return ""
    filename = "anomaly_" + ts.replace(" ", "_").replace(":", "-") + ".jpg"
    out_path = SNAPSHOTS_DIR / filename
    try:
        url = f"http://{ESP32_CAM_IP}/snapshot"
        with urllib.request.urlopen(url, timeout=3) as resp:
            out_path.write_bytes(resp.read())
        print(f"📸 Snapshot saved: {filename}")
        return filename
    except Exception as e:
        print(f"⚠️  Snapshot failed: {e}")
        return ""


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Listening on UDP port {UDP_PORT}")
    print(f"Sensor log  : {CSV_PATH}")
    print(f"Anomaly log : {ANOMALY_PATH}")
    print(f"Snapshots   : {SNAPSHOTS_DIR}")
    if ESP32_CAM_IP:
        print(f"Camera IP   : {ESP32_CAM_IP}")
    else:
        print("Camera IP   : not set — run: export ESP32_CAM_IP=<ip>")
    print("Press Ctrl+C to stop.\n")

    sensor_file = open(CSV_PATH, "a", newline="")
    sensor_writer = csv.DictWriter(sensor_file, fieldnames=CSV_HEADERS)
    if CSV_PATH.stat().st_size == 0:
        sensor_writer.writeheader()

    anomaly_file = open(ANOMALY_PATH, "a", newline="")
    anomaly_writer = csv.DictWriter(anomaly_file, fieldnames=ANOMALY_HEADERS)
    if ANOMALY_PATH.stat().st_size == 0:
        anomaly_writer.writeheader()

    alert_active = False
    set_alert_led(False)

    count = 0
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            payload  = json.loads(data.decode())

            ts       = datetime.fromtimestamp(payload["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            temp     = float(payload["temperature"])
            humidity = float(payload["humidity"])
            pressure = float(payload["pressure"])

            inference = run_inference(temp, humidity)

            if inference is None:
                print(f"[{ts}]  [WARN] Inference failed — check ADB connection")
            else:
                is_anomaly = inference["anomaly"]
                confidence = inference["confidence"]
                recon_err  = inference["reconstruction_error"]

                if is_anomaly != alert_active:
                    alert_active = is_anomaly
                    set_alert_led(alert_active)

                status = "ANOMALY" if is_anomaly else "OK     "
                detail = f"  !! confidence={confidence}  recon_err={recon_err}" if is_anomaly else ""
                print(f"[{ts}]  [{status}]  temp={temp}°C  humidity={humidity}%{detail}")

                if is_anomaly:
                    snapshot_file = capture_snapshot(ts)
                    anomaly_writer.writerow({
                        "timestamp":            ts,
                        "temperature":          temp,
                        "humidity":             humidity,
                        "pressure":             pressure,
                        "reconstruction_error": recon_err,
                        "confidence":           confidence,
                        "snapshot_file":        snapshot_file,
                    })
                    anomaly_file.flush()

            sensor_writer.writerow({
                "timestamp":   ts,
                "temperature": temp,
                "humidity":    humidity,
                "pressure":    pressure,
            })
            sensor_file.flush()
            count += 1

    except KeyboardInterrupt:
        print(f"\nStopped. {count} reading(s) received.")
        set_alert_led(False)
    finally:
        sensor_file.close()
        anomaly_file.close()
        sock.close()


if __name__ == "__main__":
    main()
