"""UDP receiver — listens for ESP32 sensor packets and logs to CSV."""

import csv
import json
import socket
from datetime import datetime
from pathlib import Path

UDP_IP   = "0.0.0.0"   # listen on all network interfaces
UDP_PORT = 5005
CSV_PATH = Path(__file__).parent.parent / "data" / "sensor_log.csv"
CSV_HEADERS = ["timestamp", "temperature", "humidity", "pressure"]


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Listening on UDP port {UDP_PORT} (all interfaces)")
    print(f"Saving readings to: {CSV_PATH}")
    print("Press Ctrl+C to stop.\n")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    csv_file = open(CSV_PATH, "a", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
    if CSV_PATH.stat().st_size == 0:
        writer.writeheader()

    count = 0
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            payload = json.loads(data.decode())

            ts       = datetime.fromtimestamp(payload["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            temp     = payload["temperature"]
            humidity = payload["humidity"]
            pressure = payload["pressure"]

            print(f"[{ts}]  temp={temp}°C  humidity={humidity}%  pressure={pressure}hPa")

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
    finally:
        csv_file.close()
        sock.close()


if __name__ == "__main__":
    main()
