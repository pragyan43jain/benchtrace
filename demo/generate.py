"""Generate a disclosed simulated sensor fixture. No hardware measurements."""
from pathlib import Path
import csv
import json
import zipfile
root=Path(__file__).parent/'esp32-i2c'
root.mkdir(exist_ok=True)

def capture(address,ack,path):
    samples=[]
    def hold(scl,sda):samples.extend([(scl*3.3,sda*3.3)]*10)
    hold(1,1);hold(1,0)
    for bit in [int(x) for x in f'{address<<1:08b}']+[int(not ack)]:
        hold(0,bit);hold(1,bit)
    hold(0,0);hold(1,0);hold(1,1)
    with path.open('w') as f:
        writer=csv.writer(f);writer.writerow(['time','scl','sda'])
        for i,(scl,sda) in enumerate(samples):writer.writerow([f'{i*0.5e-6:.9f}',scl,sda])

capture(0x49,False,root/'failure.csv')
capture(0x48,True,root/'verification.csv')
(root/'firmware.ino').write_text('''// SIMULATED demonstration: intentionally wrong 7-bit address.
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
''')
(root/'sensor-datasheet.txt').write_text('''SIMULATED SENSOR MODEL — NOT A MANUFACTURER DATASHEET
BenchTrace reproducible demonstration model, revision 1.
This fictional I2C peripheral exists only in the fixture generator.
I2C address: 0x48 (7-bit, fixed for this simulation).
Simulation assumptions: 3.3 V logic, ideal transitions, 100 kHz SCL.
SDA and SCL are open-drain in the conceptual model; this digital fixture
cannot establish analog rise times, actual resistance, or supply integrity.
This document is NOT a specification for any physical sensor.
''')
(root/'serial.txt').write_text('SIMULATED serial output\nSensor transaction failed\nWire.endTransmission result: 2 (address NACK in this simulation)\n')
(root/'circuit.net').write_text('''(export (version E)
 (components
  (comp (ref U1) (value ESP32))
  (comp (ref U2) (value SIMULATED_SENSOR))
  (comp (ref R1) (value 4.7k_assumed))
  (comp (ref R2) (value 4.7k_assumed)))
 (nets
  (net (code 1) (name SDA) (node (ref U1) (pin 21)) (node (ref U2) (pin SDA)) (node (ref R1) (pin 1)))
  (net (code 2) (name SCL) (node (ref U1) (pin 22)) (node (ref U2) (pin SCL)) (node (ref R2) (pin 1)))
  (net (code 3) (name 3V3) (node (ref U1) (pin 3V3)) (node (ref U2) (pin VDD)) (node (ref R1) (pin 2)) (node (ref R2) (pin 2)))
  (net (code 4) (name GND) (node (ref U1) (pin GND)) (node (ref U2) (pin GND)))))
''')
(root/'manifest.json').write_text(json.dumps({'simulated':True,'sample_rate_hz':2000000,'clock_hz':100000,'logic_high_v':3.3,'fault':'firmware address 0x49 instead of model address 0x48','known_limits':['ideal edges','no analog noise','no physical sensor','no electrical compliance claim']},indent=2))
with zipfile.ZipFile(root/'initial-evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in ['firmware.ino','failure.csv','circuit.net','serial.txt','manifest.json']:
        archive.write(root/name,name)
print('Generated simulated failure, verification, documentation and circuit fixtures.')
