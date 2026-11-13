// SIMULATED capture: TMP102 ADD0 is tied to GND; target address is intentionally wrong.
#include <Wire.h>
#define SENSOR_ADDRESS 0x4C
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
