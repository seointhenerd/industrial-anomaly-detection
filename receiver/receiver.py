"""UDP receiver — listens for ESP32 sensor packets, logs to CSV, and drives Uno Q alert LED via ADB."""

import csv
import json
import socket
import subprocess
from datetime import datetime
from pathlib import Path

UDP_IP   = "0.0.0.0"
UDP_PORT = 5005
CSV_PATH = Path(__file__).parent.parent / "data" / "sensor_log.csv"
CSV_HEADERS = ["timestamp", "temperature", "humidity", "pressure"]

TEMP_HIGH     = 30.0   # °C
HUMIDITY_HIGH = 80.0   # %
PRESSURE_LOW  = 950.0  # hPa

LED_PATH = "/sys/class/leds/red:user/brightness"


def set_alert_led(on: bool) -> None:
    value = "1" if on else "0"
    subprocess.run(["adb", "shell", f"echo {value} > {LED_PATH}"], capture_output=True)


def check_thresholds(temp: float, humidity: float, pressure: float) -> list[str]:
    reasons = []
    if temp > TEMP_HIGH:
        reasons.append(f"temp={temp}°C > {TEMP_HIGH}")
    if humidity > HUMIDITY_HIGH:
        reasons.append(f"humidity={humidity}% > {HUMIDITY_HIGH}")
    if pressure < PRESSURE_LOW:
        reasons.append(f"pressure={pressure}hPa < {PRESSURE_LOW}")
    return reasons


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Listening on UDP port {UDP_PORT} (all interfaces)")
    print(f"Saving readings to: {CSV_PATH}")
    print(f"Thresholds: temp>{TEMP_HIGH}°C  humidity>{HUMIDITY_HIGH}%  pressure<{PRESSURE_LOW}hPa")
    print("Press Ctrl+C to stop.\n")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    csv_file = open(CSV_PATH, "a", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
    if CSV_PATH.stat().st_size == 0:
        writer.writeheader()

    alert_active = False
    set_alert_led(False)  # ensure LED starts off

    count = 0
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            payload = json.loads(data.decode())

            ts       = datetime.fromtimestamp(payload["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            temp     = float(payload["temperature"])
            humidity = float(payload["humidity"])
            pressure = float(payload["pressure"])

            reasons = check_thresholds(temp, humidity, pressure)
            alert   = len(reasons) > 0

            # Only call ADB when state changes to avoid hammering it every 5s
            if alert != alert_active:
                alert_active = alert
                set_alert_led(alert_active)

            status = "ALERT" if alert else "OK   "
            detail = "  !! " + ", ".join(reasons) if reasons else ""
            print(f"[{ts}]  [{status}]  temp={temp}°C  humidity={humidity}%  pressure={pressure}hPa{detail}")

            writer.writerow({
                "timestamp":   ts,
                "temperature": temp,
                "humidity":    humidity,
                "pressure":    pressure,
            })
            csv_file.flush()
            count += 1

    except KeyboardInterrupt:
        print(f"\nStopped. {count} reading(s) saved to {CSV_PATH}")
        set_alert_led(False)
    finally:
        csv_file.close()
        sock.close()


if __name__ == "__main__":
    main()
