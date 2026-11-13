# Deterministic diagnostic evaluation

Run the fixed-scenario evaluation from the repository root:

```sh
docker compose run --rm --no-deps engine python evaluation/run.py
```

The runner evaluates the ten checked-in firmware/document pairs with the same deterministic analyzer used by the diagnostic API. It emits a JSON report and exits nonzero if any fixture expectation fails. The checks measure:

- Whether each declared fault hypothesis is present and ranked first.
- Whether address contradictions match the fixture.
- Whether each recommended test contains the fixture's predefined verification terms.
- Whether each evidence excerpt traces to its uploaded source, or is the explicit bounded static-parser finding for a missing `Wire.begin` call.
- Whether hypotheses remain unverified and include a test, confirming and rejecting outcomes, unknowns, and a safety note.

The checked-in run reports 10/10 scenario passes, 4/4 expected fault targets included and ranked first, 18/18 evidence citations grounded, 10/10 relevant test recommendations, and 60/60 hypothesis verification contracts complete. These are fixture results for the supported I2C rules, not a general accuracy estimate, physical validation, or an evaluation of optional external LLM output. The evaluation deliberately does not use an LLM to grade itself.
