"""UDP receiver — receives ESP32 sensor packets, runs ML inference on Uno Q, controls alert LED."""

import csv
import json
import socket
import subprocess
from datetime import datetime
from pathlib import Path

UDP_IP   = "0.0.0.0"
UDP_PORT = 5005

CSV_PATH      = Path(__file__).parent.parent / "data" / "sensor_log.csv"
ANOMALY_PATH  = Path(__file__).parent.parent / "data" / "anomaly_log.csv"

CSV_HEADERS     = ["timestamp", "temperature", "humidity", "pressure"]
ANOMALY_HEADERS = ["timestamp", "temperature", "humidity", "pressure", "reconstruction_error", "confidence"]

LED_PATH       = "/sys/class/leds/red:user/brightness"
INFERENCE_SCRIPT = "/home/arduino/inference_uno_q.py"


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


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Listening on UDP port {UDP_PORT}")
    print(f"Sensor log  : {CSV_PATH}")
    print(f"Anomaly log : {ANOMALY_PATH}")
    print("Press Ctrl+C to stop.\n")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

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

            # ── Run inference on Uno Q ────────────────────────────────────────
            inference = run_inference(temp, humidity)

            if inference is None:
                print(f"[{ts}]  [WARN] Inference failed — check ADB connection")
            else:
                is_anomaly  = inference["anomaly"]
                confidence  = inference["confidence"]
                recon_err   = inference["reconstruction_error"]

                # Toggle LED only when state changes
                if is_anomaly != alert_active:
                    alert_active = is_anomaly
                    set_alert_led(alert_active)

                status = "ANOMALY" if is_anomaly else "OK     "
                detail = f"  !! confidence={confidence}  recon_err={recon_err}" if is_anomaly else ""
                print(f"[{ts}]  [{status}]  temp={temp}°C  humidity={humidity}%{detail}")

                if is_anomaly:
                    anomaly_writer.writerow({
                        "timestamp":           ts,
                        "temperature":         temp,
                        "humidity":            humidity,
                        "pressure":            pressure,
                        "reconstruction_error": recon_err,
                        "confidence":          confidence,
                    })
                    anomaly_file.flush()

            # ── Log every reading to sensor CSV ───────────────────────────────
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
