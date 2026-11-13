# Deterministic diagnostic evaluation

Run the fixed-scenario evaluation from the repository root:

```sh
docker compose run --rm --no-deps engine python evaluation/run.py
```

The runner evaluates ten checked-in firmware/document pairs and one generated multi-source case with the same parsers and deterministic analyzer used by the diagnostic API. The cross-source case combines firmware, datasheet text, a parsed netlist, a generated logic-analyzer capture and a serial error log. It emits a JSON report and exits nonzero if any fixture expectation fails. The checks measure:

- Whether each declared fault hypothesis is present and ranked first.
- Whether address contradictions match the fixture.
- Whether each recommended test contains the fixture's predefined verification terms.
- Whether each evidence excerpt traces to its uploaded source, or is the explicit bounded static-parser finding for a missing `Wire.begin` call.
- Whether hypotheses remain unverified and include a test, confirming and rejecting outcomes, unknowns, and a safety note.

The checked-in run reports 11/11 scenario passes, 4/4 expected fault targets included and ranked first, 18/18 direct text citations grounded, 10/10 predefined test-relevance checks, and 60/60 hypothesis verification contracts complete. The separate cross-source check verifies that firmware, documentation, capture and serial evidence support the address hypothesis, matching schematic pins count against a pin fault, the capture reliably decodes a `0x49` NACK, and all findings remain unverified. These are fixture results for the supported I2C rules, not a general accuracy estimate, physical validation, or an evaluation of optional external LLM output. The evaluation deliberately does not use an LLM to grade itself.
