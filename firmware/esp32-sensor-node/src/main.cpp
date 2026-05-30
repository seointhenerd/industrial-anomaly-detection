#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include <Adafruit_BME280.h>
#include <time.h>
#include "config.h"

Adafruit_BME280 bme;
WiFiUDP udp;

void connectWiFi() {
    Serial.printf("Connecting to WiFi: %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\nERROR: WiFi connection failed. Check credentials.");
        while (true) delay(1000);
    }

    Serial.println("\nWiFi connected!");
    Serial.printf("IP address: %s\n", WiFi.localIP().toString().c_str());
}

bool initSensor() {
    Wire.begin(I2C_SDA, I2C_SCL);
    delay(50);
    return bme.begin(0x76, &Wire);
}

void setup() {
    Serial.begin(115200);
    delay(3000);  // give USB CDC time to open before any output

    Serial.println("Booting...");

    if (!initSensor()) {
        Serial.println("ERROR: BME280 not found at 0x76. Check wiring.");
        while (true) delay(1000);
    }
    Serial.println("BME280 ready.");

    connectWiFi();

    configTime(0, 0, "pool.ntp.org");
    Serial.print("Syncing time");
    struct tm t;
    while (!getLocalTime(&t)) {
        Serial.print(".");
        delay(500);
    }
    Serial.println(" done.");

    Serial.printf("\nSending UDP to %s:%d every 5s\n\n", UDP_HOST, UDP_PORT);
}

void loop() {
    float temp     = bme.readTemperature();
    float humidity = bme.readHumidity();
    float pressure = bme.readPressure() / 100.0F;

    // Detect corrupted readings and reinitialize I2C
    if (temp > 100.0 || temp < -40.0 || pressure <= 0.0 || humidity > 100.0) {
        Serial.println("[WARN] Bad sensor reading — reinitializing I2C...");
        if (!initSensor()) {
            Serial.println("[ERROR] BME280 not responding.");
        }
        delay(1000);
        return;
    }

    long ts = (long)time(nullptr);

    JsonDocument doc;
    doc["device"]      = "esp32_sensor_node";
    doc["temperature"] = serialized(String(temp, 1));
    doc["humidity"]    = serialized(String(humidity, 1));
    doc["pressure"]    = serialized(String(pressure, 1));
    doc["timestamp"]   = ts;

    String payload;
    serializeJson(doc, payload);

    udp.beginPacket(UDP_HOST, UDP_PORT);
    udp.print(payload);
    udp.endPacket();

    Serial.printf("[TX] %s\n", payload.c_str());

    delay(5000);
}
