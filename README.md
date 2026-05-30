# Industrial Anomaly Detection System

ESP32-S3 embedded sensor node that streams BME280 environmental readings (temperature, humidity, pressure) over UDP to a Python receiver for logging and anomaly detection.

## Hardware

| Component | Detail |
|---|---|
| MCU | ESP32-S3 Dev Module |
| Sensor | BME280 (I2C) |
| SDA | GPIO 21 |
| SCL | GPIO 22 |
| BME280 address | 0x76 or 0x77 (scan to confirm) |

## Project Structure

```
firmware/esp32-sensor-node/   ← PlatformIO project (flash to ESP32-S3)
receiver/receiver.py          ← Python UDP listener + CSV logger
data/sensor_log.csv           ← Generated at runtime (gitignored)
```

## Firmware Setup

1. Install [PlatformIO](https://platformio.org/).
2. Copy the credentials template:
   ```
   cp firmware/esp32-sensor-node/include/config.example.h \
      firmware/esp32-sensor-node/include/config.h
   ```
3. Edit `config.h` with your WiFi SSID, password, and laptop IP (`ifconfig` / `ipconfig`).
4. Open `firmware/esp32-sensor-node/` in PlatformIO and flash.

## Receiver Setup

```bash
pip install -r receiver/requirements.txt   # if present
python receiver/receiver.py
```

Listens on UDP port 5005. Saves readings to `data/sensor_log.csv`.

## Milestones

- [x] **Phase 1** — PlatformIO project scaffold
- [ ] **Phase 2** — I2C scanner (confirm BME280 address)
- [ ] **Phase 3** — BME280 read + Serial Monitor output
- [ ] **Phase 4** — WiFi + UDP JSON transmission
- [ ] **Phase 5** — Python UDP receiver + CSV logger
