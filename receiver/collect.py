"""Collect sensor readings into sensor_log.csv — no inference, no snapshots."""

import csv
import json
import socket
from datetime import datetime
from pathlib import Path

UDP_IP   = "0.0.0.0"
UDP_PORT = 5005

CSV_PATH    = Path(__file__).parent.parent / "data" / "sensor_log.csv"
CSV_HEADERS = ["timestamp", "temperature", "humidity", "pressure"]


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Collecting sensor data → {CSV_PATH}")
    print("Press Ctrl+C to stop.\n")

    f      = open(CSV_PATH, "a", newline="")
    writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
    if CSV_PATH.stat().st_size == 0:
        writer.writeheader()

    count = 0
    try:
        while True:
            data, _ = sock.recvfrom(1024)
            payload  = json.loads(data.decode())
            ts       = datetime.fromtimestamp(payload["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            temp     = float(payload["temperature"])
            humidity = float(payload["humidity"])
            pressure = float(payload["pressure"])

            writer.writerow({"timestamp": ts, "temperature": temp,
                             "humidity": humidity, "pressure": pressure})
            f.flush()
            count += 1
            print(f"[{ts}]  temp={temp}°C  humidity={humidity}%  pressure={pressure}hPa")
    except KeyboardInterrupt:
        print(f"\nStopped. {count} reading(s) collected.")
    finally:
        f.close()
        sock.close()


if __name__ == "__main__":
    main()
