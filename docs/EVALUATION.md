# Engineering evaluation

The fixed dataset is `ai-engine/evaluation/scenarios.json`, exercised by `tests/test_evaluation.py`. Cases cover wrong and matching addresses, multiple valid addresses, unresolved macros, non-comparable 8-bit notation, and missing initialization. Assertions inspect expected ranking when justified, contradiction presence, source identity, excerpt traceability, uncertainty, and actionable verification tests. No LLM self-grading is used.

Protocol tests use generated, known digital samples with asserted 7-bit and 10-bit address bytes, ACK/NACK, repeated-start reads, UART framing and all four SPI modes. Ten-bit evaluation includes address assembly across all four values of the two high bits, unresolved read prefixes, truncated address pairs and NACK behavior. Numerical tests check FFT frequency, sample interval, peaks, robust noise estimates and signal comparison. Invalid timestamps, NaNs, undersampling, duplicate channels and empty transactions are tested.

The end-to-end demo uses a fictional sensor model, ideal 0/3.3 V edges, a 2 MHz sample rate, a 100 kHz clock and a deliberate 0x49/0x48 mismatch. No physical measurement, analog rise-time compliance, real sensor register read or temperature result is claimed.

KiCad schematic topology checks include distinct orthogonal wire crossings without junctions, explicit junction joins, rotated-symbol pin coordinates, the simulated sensor's four pin-to-label connections, and firmware SDA/SCL comparison against geometrically extracted ESP32 nets. The extraction intentionally does not cover hierarchy, buses, mirrored symbols or diagonal wires; exported netlists are used for full-project demo connectivity.

Semantic retrieval is evaluated with a paraphrased supply-voltage query versus relevant and irrelevant text. This is a smoke evaluation, not a comprehensive electronics retrieval benchmark. See ROADMAP.md for actual executed results and remaining coverage.
