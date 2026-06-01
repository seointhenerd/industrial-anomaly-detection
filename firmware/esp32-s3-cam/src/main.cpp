#include <Arduino.h>
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
    .frame_size   = FRAMESIZE_QVGA,   // 320x240 — fits in DRAM
    .jpeg_quality = 12,
    .fb_count     = 1,
    .fb_location  = CAMERA_FB_IN_DRAM,
    .grab_mode    = CAMERA_GRAB_WHEN_EMPTY,
};

void setup() {
    Serial.begin(115200);
    delay(3000);
    Serial.println("Booting camera test...");

    esp_err_t err = esp_camera_init(&CAM_CONFIG);
    if (err != ESP_OK) {
        Serial.printf("ERROR: Camera init failed — 0x%x\n", err);
        while (true) delay(1000);
    }
    Serial.println("Camera OK — resolution: 320x240 (QVGA)");

    Serial.println("Taking test photo...");
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("ERROR: Capture failed — fb is null");
        while (true) delay(1000);
    }
    Serial.printf("Test photo OK — JPEG size: %u bytes\n", fb->len);
    esp_camera_fb_return(fb);
}

void loop() {}
