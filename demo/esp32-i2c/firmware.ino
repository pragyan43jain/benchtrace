// SIMULATED demonstration: intentionally wrong 7-bit address.
#include <Wire.h>
#define SENSOR_ADDRESS 0x49
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  Wire.setClock(100000);
}
void loop() {
  Wire.beginTransmission(SENSOR_ADDRESS);
  uint8_t result = Wire.endTransmission();
  if (result != 0) Serial.println("Sensor transaction failed");
  delay(1000);
}
