# Reproducible ESP32 I2C investigation

**Every capture and serial message here is simulated. No physical device was measured.**
The sensor is a fictional fixed-address peripheral, not a branded part. The supplied model document is not a manufacturer datasheet and must never be used to design hardware.

1. Run `python3 demo/generate.py` to regenerate byte-identical CSV fixtures.
2. Start BenchTrace, register, and create an ESP32 project.
3. Upload `esp32-i2c/initial-evidence.zip` with automatic category detection.
4. Upload `sensor-symbols.kicad_sch` with category **schematic** to inspect embedded pin metadata and its four drawn pin-to-label connections. Select `SDA` in the net viewer to see U3 pin 1. Use `circuit.net` for the assumed full-project connectivity.
5. Upload `sensor-datasheet.txt` separately with category **datasheet**.
6. Wait for processing. Inspect `failure.csv`: 2 MHz sampling, 100 kHz clock, address `0x49`, address-byte NACK.
7. Create an investigation: “ESP32 sensor returns an address NACK.” Select **Correlate evidence**.
8. The wrong-address hypothesis should rank first, citing firmware, model documentation and capture. Power, pull-ups and routing remain alternatives.
9. The proposed test is to verify the exact device address and change only that address. Upload `verification.csv`, explicitly noting it is a simulated corrected-address capture (`0x48`, ACK).
10. Record a test: “SIMULATED: generator changed target from 0x49 to 0x48. Corrected transaction ACKs; original NACKs.” Choose confirms **only for this simulation**.
11. Save the resolution, export the Markdown report, and save a knowledge snapshot.

The `circuit.net` fixture uses KiCad exported S-expression netlist syntax. It describes assumed connections; it is not evidence of a physically assembled circuit. The `.kicad_sch` fixture shows only the sensor pins connected to local net labels; the other assumed ESP32 and pull-up connections are in `circuit.net`. The 4.7 kΩ values are illustrative assumptions, not measured or recommended values.

Capture conventions: seconds in `time`, volts in `scl`/`sda`, 10 samples per half-clock, ideal 0/3.3 V transitions. START and STOP transitions occur while SCL is high. The ninth clock carries ACK/NACK. No real sensor register transactions or temperature measurements are claimed.
