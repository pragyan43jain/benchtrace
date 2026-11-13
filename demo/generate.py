"""Generate a disclosed simulated sensor fixture. No hardware measurements."""
from pathlib import Path
import csv
import json
import zipfile
from io import BytesIO

def pdf_bytes(text):
    escaped=text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
    stream=f'BT /F1 12 Tf 50 700 Td ({escaped}) Tj ET'.encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    out=b'%PDF-1.4\n';offsets=[]
    for i,obj in enumerate(objects,1):offsets.append(len(out));out+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    offset=len(out);out+=b'xref\n0 6\n0000000000 65535 f \n'
    for x in offsets:out+=f'{x:010d} 00000 n \n'.encode()
    return out+f'trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n{offset}\n%%EOF'.encode()

def scanned_pdf_bytes(lines):
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(1800,500),'white')
    draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=58)
    for index,line in enumerate(lines):draw.text((55,30+index*115),line,fill='black',font=font)
    encoded=BytesIO();image.save(encoded,format='JPEG',quality=95);image.close()
    jpeg=encoded.getvalue();stream=b'q 900 0 0 250 0 0 cm /Im0 Do Q'
    objects=[
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 900 250] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /XObject /Subtype /Image /Width 1800 /Height 500 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '+str(len(jpeg)).encode()+b' >>\nstream\n'+jpeg+b'\nendstream',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream',
    ]
    out=b'%PDF-1.4\n';offsets=[]
    for i,obj in enumerate(objects,1):offsets.append(len(out));out+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    offset=len(out);out+=b'xref\n0 6\n0000000000 65535 f \n'
    for value in offsets:out+=f'{value:010d} 00000 n \n'.encode()
    return out+f'trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n{offset}\n%%EOF'.encode()

root=Path(__file__).parent/'esp32-i2c'
root.mkdir(exist_ok=True)

def capture(address,ack,path):
    samples=[]
    def hold(scl,sda):samples.extend([(scl*3.3,sda*3.3)]*10)
    hold(1,1);hold(1,0)
    for bit in [int(x) for x in f'{address<<1:08b}']+[int(not ack)]:
        hold(0,bit);hold(1,bit)
    hold(0,0);hold(1,0);hold(1,1)
    with path.open('w', newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['time','scl','sda'])
        for i,(scl,sda) in enumerate(samples):writer.writerow([f'{i*0.5e-6:.9f}',scl,sda])

(root/'sensor-model.pdf').write_bytes(pdf_bytes('TMP102 address excerpt. TI SBOS397I, Table 6-4, printed page 10.'))
(root/'sensor-model-scan.pdf').write_bytes(scanned_pdf_bytes([
    'TI TMP102 address table, SBOS397I, page 10',
    'ADD0 grounded: seven-bit address 0x48',
    'ADD0 connected to V+: seven-bit address 0x49',
    'Source: Table 6-4; OCR test rendition, not the full datasheet',
]))

capture(0x4c,False,root/'failure.csv')
capture(0x48,True,root/'verification.csv')
(root/'firmware.ino').write_text('''// SIMULATED capture: TMP102 ADD0 is tied to GND; target address is intentionally wrong.
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
''')
(root/'sensor-datasheet.txt').write_text('''SOURCE-GROUNDED EXCERPT — Texas Instruments TMP102 datasheet, SBOS397I, revised June 2024

This is a short BenchTrace-created text excerpt of the manufacturer's address table, not the complete datasheet. Verify against the linked source before hardware use.

Table 6-4, printed page 10. 7-bit I2C address: 0x48 (ADD0=GND); 0x49 (ADD0=V+); 0x4A (ADD0=SDA); 0x4B (ADD0=SCL).
The attempted firmware target is not listed in the TMP102 address table.

Official source PDF: https://www.ti.com/lit/ds/symlink/tmp102.pdf
The address values above are manufacturer data. All BenchTrace waveforms, serial output, and the simulated ADD0-to-GND netlist are generated assumptions, not measured hardware evidence.
''')
(root/'serial.txt').write_text('SIMULATED serial output\nSensor transaction failed\nWire.endTransmission result: 2 (address NACK in this simulation; target 0x4C is outside the TMP102 address table)\n')
(root/'circuit.net').write_text('''(export (version E)
 (components
  (comp (ref U1) (value ESP32))
  (comp (ref U2) (value TMP102))
  (comp (ref R1) (value 4.7k_assumed))
  (comp (ref R2) (value 4.7k_assumed)))
 (nets
  (net (code 1) (name SDA) (node (ref U1) (pin 21)) (node (ref U2) (pin SDA)) (node (ref R1) (pin 1)))
  (net (code 2) (name SCL) (node (ref U1) (pin 22)) (node (ref U2) (pin SCL)) (node (ref R2) (pin 1)))
  (net (code 3) (name 3V3) (node (ref U1) (pin 3V3)) (node (ref U2) (pin VDD)) (node (ref R1) (pin 2)) (node (ref R2) (pin 2)))
  (net (code 4) (name GND) (node (ref U1) (pin GND)) (node (ref U2) (pin GND)) (node (ref U2) (pin ADD0)))))
''')
(root/'manifest.json').write_text(json.dumps({'simulated':True,'component':'Texas Instruments TMP102','datasheet_source':'https://www.ti.com/lit/ds/symlink/tmp102.pdf','datasheet_citation':'SBOS397I, Table 6-4, printed page 10','assumed_add0_net':'GND','expected_target_address':'0x48','sample_rate_hz':2000000,'clock_hz':100000,'logic_high_v':3.3,'fault':'firmware targets unsupported address 0x4C; the simulated TMP102 ADD0-to-GND connection selects 0x48','known_limits':['ideal edges','no analog noise','simulated circuit netlist','no physical sensor','no electrical compliance claim']},indent=2))
with zipfile.ZipFile(root/'initial-evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in ['firmware.ino','failure.csv','circuit.net','serial.txt','manifest.json']:
        info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,(root/name).read_bytes())
print('Generated simulated failure, verification, documentation and circuit fixtures.')
