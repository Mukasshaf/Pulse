/*
 * Pulse ESP32 Firmware — Fixed 66.67 Hz Biosignal Acquisition
 *
 * Sensors:
 * - Analog Pulse Sensor: GPIO 35
 * - Grove GSR: GPIO 34 (ADC1_CHANNEL_6)
 * - MPU-6050 (I2C): SDA GPIO 21, SCL GPIO 22
 *
 * Output format (CSV via Serial @ 115200 baud):
 * sample_idx,timestamp_ms,pulse_raw,gsr_raw,acc_x,acc_y,acc_z
 */

#include <Wire.h>

#define PULSE_PIN 35
#define GSR_PIN 34
#define MPU_ADDR 0x68

const unsigned long SAMPLE_INTERVAL_US = 15000; // 15 ms = 66.67 Hz
unsigned long last_sample_us = 0;
unsigned long sample_idx = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000);

  Wire.begin(21, 22);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // Wake up MPU-6050
  Wire.endTransmission(true);

  pinMode(PULSE_PIN, INPUT);
  pinMode(GSR_PIN, INPUT);

  last_sample_us = micros();
}

void loop() {
  unsigned long current_us = micros();
  if (current_us - last_sample_us >= SAMPLE_INTERVAL_US) {
    last_sample_us += SAMPLE_INTERVAL_US;

    int pulse_raw = analogRead(PULSE_PIN);
    int gsr_raw = analogRead(GSR_PIN);

    int16_t ax = 0, ay = 0, az = 0;
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom((uint16_t)MPU_ADDR, (uint8_t)6, true);

    if (Wire.available() >= 6) {
      ax = (Wire.read() << 8) | Wire.read();
      ay = (Wire.read() << 8) | Wire.read();
      az = (Wire.read() << 8) | Wire.read();
    }

    unsigned long timestamp_ms = millis();
    Serial.printf("%lu,%lu,%d,%d,%d,%d,%d\n",
                  sample_idx++, timestamp_ms, pulse_raw, gsr_raw, ax, ay, az);
  }
}
