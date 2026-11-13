# Reproducible ESP32 I2C investigation

**Every capture, serial message, and circuit connection here is simulated. No physical device was measured.**
The component is a real TI TMP102. `sensor-datasheet.txt` is a concise, source-attributed excerpt from TI datasheet SBOS397I, Table 6-4 (printed page 10); it is not the complete datasheet. Verify technical details against the [official TMP102 datasheet](https://www.ti.com/lit/ds/symlink/tmp102.pdf) before hardware use. The address facts come from TI; the ADD0-to-GND circuit assumption and all captures are simulated.

1. Install the pinned image-fixture dependency with `python3 -m pip install -r demo/requirements.txt`, then run `python3 demo/generate.py` to regenerate the simulated CSV, PDF and project fixtures.
2. Start BenchTrace, register, and create an ESP32 project.
3. Upload `esp32-i2c/initial-evidence.zip` with automatic category detection.
4. Upload `sensor-symbols.kicad_sch` with category **schematic** to inspect embedded pin metadata and its four drawn pin-to-label connections. Select `SDA` in the net viewer to see U3 pin 1. Use `circuit.net` for the assumed full-project connectivity.
5. Upload `sensor-datasheet.txt` separately with category **datasheet**.
6. Upload `sensor-model-scan.pdf` with category **datasheet** to exercise image-only PDF OCR. It is a generated scan rendition of the cited TI address table, not a scanned page from TI; review OCR output against the uploaded page and the official source.
7. Wait for processing. Inspect `failure.csv`: 2 MHz sampling, 100 kHz clock, unsupported TMP102 target `0x4C`, address-byte NACK. The datasheet's address table lists `0x48` through `0x4B`, selected by ADD0; the simulated netlist ties ADD0 to GND, selecting `0x48`.
8. Create an investigation: “ESP32 sensor returns an address NACK.” Select **Correlate evidence**.
9. The wrong-address hypothesis should rank first, citing firmware, the TI TMP102 address excerpt, simulated ADD0-to-GND net connectivity, and the capture. Power and pull-ups remain alternatives; a simulated netlist does not verify physical wiring.
10. The proposed test is to verify the exact device address and change only that address. Upload `verification.csv`, explicitly noting it is a simulated corrected-address capture (`0x48`, ACK).
11. Record a test: “SIMULATED: generator changed target from unsupported 0x4C to 0x48. Corrected transaction ACKs; original NACKs.” Choose confirms **only for this simulation**.
12. Save the resolution, export the Markdown report, and save a knowledge snapshot.

The `circuit.net` fixture uses KiCad exported S-expression netlist syntax. It describes assumed connections, including ADD0 to GND; it is not evidence of a physically assembled circuit. The `.kicad_sch` fixture shows sensor pin metadata and local signal labels; the assumed ADD0, ESP32 and pull-up connections are in `circuit.net`. The 4.7 kΩ values are illustrative assumptions, not measured or recommended values.

Capture conventions: seconds in `time`, volts in `scl`/`sda`, 10 samples per half-clock, ideal 0/3.3 V transitions. START and STOP transitions occur while SCL is high. The ninth clock carries ACK/NACK. No real sensor register transactions or temperature measurements are claimed.
