#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "esp_camera.h"
#include "config.h"

static const camera_config_t CAM_CONFIG = {
    .pin_pwdn     = -1,
    .pin_reset    = -1,
    .pin_xclk     = 15,
    .pin_sccb_sda = 4,
    .pin_sccb_scl = 5,
    .pin_d7       = 16,
    .pin_d6       = 17,
    .pin_d5       = 18,
    .pin_d4       = 12,
    .pin_d3       = 10,
    .pin_d2       = 8,
    .pin_d1       = 9,
    .pin_d0       = 11,
    .pin_vsync    = 6,
    .pin_href     = 7,
    .pin_pclk     = 13,
    .xclk_freq_hz = 20000000,
    .ledc_timer   = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,
    .pixel_format = PIXFORMAT_JPEG,
    .frame_size   = FRAMESIZE_VGA,
    .jpeg_quality = 12,
    .fb_count     = 1,
    .fb_location  = CAMERA_FB_IN_DRAM,
    .grab_mode    = CAMERA_GRAB_WHEN_EMPTY,
};

WebServer server(HTTP_PORT);

bool initCamera() {
    return esp_camera_init(&CAM_CONFIG) == ESP_OK;
}

void handleSnapshot() {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("[WARN] Capture failed — reinitializing camera...");
        esp_camera_deinit();
        if (!initCamera()) {
            server.send(500, "text/plain", "Camera reinit failed");
            return;
        }
        fb = esp_camera_fb_get();
        if (!fb) {
            server.send(500, "text/plain", "Capture failed after reinit");
            return;
        }
    }
    size_t len = fb->len;
    server.sendHeader("Content-Disposition", "inline; filename=snapshot.jpg");
    server.send_P(200, "image/jpeg", (const char *)fb->buf, len);
    esp_camera_fb_return(fb);
    Serial.printf("[GET /snapshot] %u bytes\n", len);
}

void handleHealth() {
    String json = "{\"status\":\"ok\",\"ip\":\"" + WiFi.localIP().toString() + "\"}";
    server.send(200, "application/json", json);
}

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
        Serial.println("\nERROR: WiFi failed. Check credentials.");
        while (true) delay(1000);
    }
    Serial.printf("\nWiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
}

void setup() {
    Serial.begin(115200);
    delay(3000);
    Serial.println("Booting ESP32-S3-CAM...");

    if (!initCamera()) {
        Serial.println("ERROR: Camera init failed.");
        while (true) delay(1000);
    }
    Serial.println("Camera OK.");

    connectWiFi();

    server.on("/snapshot", HTTP_GET, handleSnapshot);
    server.on("/health",   HTTP_GET, handleHealth);
    server.begin();

    Serial.printf("\nHTTP server ready on port %d\n", HTTP_PORT);
    Serial.printf("  http://%s/snapshot\n", WiFi.localIP().toString().c_str());
    Serial.printf("  http://%s/health\n\n", WiFi.localIP().toString().c_str());
}

void loop() {
    server.handleClient();
}
