"""Report deterministic, source-grounded checks for the fixed I2C scenarios."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.diagnostics import diagnose
from app.evidence import firmware, schematic
from app.signals import analyze_csv


HERE = Path(__file__).resolve().parent
SCENARIOS = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))


def evaluate():
    report = {
        "method": "Deterministic assertions over fixed fixtures; no LLM self-assessment",
        "scenario_count": len(SCENARIOS) + 1,
        "fault_target_scenarios": 0,
        "fault_targets_included": 0,
        "fault_targets_ranked_first": 0,
        "citation_count": 0,
        "grounded_citation_count": 0,
        "unverified_hypothesis_count": 0,
        "complete_uncertainty_count": 0,
        "recommended_test_count": 0,
        "relevant_test_count": 0,
        "checks": [],
    }

    for case in SCENARIOS:
        sources = {"fw": case["firmware"], "doc": case["document"]}
        files = [
            {
                "id": "fw",
                "name": "firmware.ino",
                "category": "firmware",
                "analysis": firmware(case["firmware"]),
            },
            {
                "id": "doc",
                "name": "datasheet.txt",
                "category": "datasheet",
                "analysis": {"chunks": [{"page": 1, "content": case["document"]}]},
            },
        ]
        result = diagnose(files)
        hypotheses = result["hypotheses"]
        by_key = {item["key"]: item for item in hypotheses}
        expected = case["expected_first"]
        check = {"scenario": case["name"], "passed": True, "failures": []}

        if expected:
            report["fault_target_scenarios"] += 1
            included = expected in by_key
            top_ranked = bool(hypotheses) and hypotheses[0]["key"] == expected
            report["fault_targets_included"] += int(included)
            report["fault_targets_ranked_first"] += int(top_ranked)
            if not included:
                check["failures"].append(f"expected hypothesis {expected!r} was absent")
            if not top_ranked:
                check["failures"].append(f"expected hypothesis {expected!r} was not ranked first")

        address = by_key.get("address")
        contradiction_matches = bool(address and address["contradictory_evidence"]) == case["expected_contradiction"]
        if not contradiction_matches:
            check["failures"].append("address contradiction state did not match fixture expectation")

        test_target = by_key.get(expected) if expected else address
        recommendation = (test_target or {}).get("recommended_test", "").lower()
        report["recommended_test_count"] += 1
        relevant = all(term.lower() in recommendation for term in case["expected_test_terms"])
        report["relevant_test_count"] += int(relevant)
        if not relevant:
            missing = [term for term in case["expected_test_terms"] if term.lower() not in recommendation]
            check["failures"].append(f"recommended test omitted expected terms: {missing}")

        for hypothesis in hypotheses:
            report["unverified_hypothesis_count"] += int(hypothesis.get("status") == "unverified")
            complete = all(hypothesis.get(field) for field in ("recommended_test", "confirms_if", "rejects_if", "unknowns", "safety_note"))
            report["complete_uncertainty_count"] += int(complete and hypothesis.get("status") == "unverified")
            if not complete or hypothesis.get("status") != "unverified":
                check["failures"].append(f"{hypothesis.get('key')} lacks unverified status or a complete verification contract")

            for evidence in hypothesis.get("supporting_evidence", []) + hypothesis.get("contradictory_evidence", []):
                report["citation_count"] += 1
                file_id = evidence.get("file_id")
                excerpt = evidence.get("excerpt", "")
                # The missing-init record is a parser finding, not source text;
                # its wording explicitly states the bounded scan's observation.
                grounded = file_id in sources and (excerpt in sources[file_id] or excerpt.startswith("No Wire.begin"))
                report["grounded_citation_count"] += int(grounded)
                if not grounded:
                    check["failures"].append(f"ungrounded or unowned evidence citation: {file_id!r}")

        check["passed"] = not check["failures"]
        report["checks"].append(check)

    # A generated capture adds a deterministic, end-to-end cross-source case:
    # firmware and datasheet disagree, the analyzer capture NACKs, the serial
    # log reports failure, and the schematic corroborates the firmware pins.
    samples = []

    def hold(clock, data, count=10):
        samples.extend([(clock * 3.3, data * 3.3)] * count)

    def send(value, ack):
        for bit in [int(value >> shift & 1) for shift in range(7, -1, -1)] + [int(not ack)]:
            hold(0, bit)
            hold(1, bit)

    hold(1, 1)
    hold(1, 0)  # START
    send(0x92, ack=False)  # 0x49 write address, followed by NACK
    hold(0, 0)
    hold(1, 0)
    hold(1, 1)  # STOP
    capture = "time,scl,sda\n" + "".join(
        f"{index * 0.5e-6:.9f},{scl},{sda}\n" for index, (scl, sda) in enumerate(samples)
    )
    firmware_source = "#define SENSOR_ADDRESS 0x49\nvoid setup(){Wire.begin(21,22);Wire.setClock(100000);}\nvoid loop(){Wire.beginTransmission(SENSOR_ADDRESS);Wire.endTransmission();}"
    document_source = "SIMULATED fixture; 7-bit I2C address: 0x48."
    circuit_source = '''(export (version E)
      (components (comp (ref U1) (value ESP32)) (comp (ref U2) (value SIMULATED_SENSOR)))
      (nets
        (net (code 1) (name SDA) (node (ref U1) (pin 21)) (node (ref U2) (pin SDA)))
        (net (code 2) (name SCL) (node (ref U1) (pin 22)) (node (ref U2) (pin SCL)))))'''
    multi_files = [
        {"id": "fw", "name": "firmware.ino", "category": "firmware", "analysis": firmware(firmware_source)},
        {"id": "doc", "name": "sensor-model.txt", "category": "datasheet", "analysis": {"chunks": [{"page": 1, "content": document_source}]}},
        {"id": "circuit", "name": "board.net", "analysis": schematic(circuit_source)},
        {"id": "capture", "name": "logic-analyzer.csv", "category": "measurement", "analysis": analyze_csv(capture)},
        {"id": "serial", "name": "serial.txt", "category": "log", "analysis": {"chunks": [{"page": 1, "content": "Sensor transaction failed: address NACK"}]}},
    ]
    combined = diagnose(multi_files, problem="ESP32 I2C sensor returns NACK")
    by_key = {item["key"]: item for item in combined["hypotheses"]}
    cross = {"scenario": "firmware_schematic_datasheet_capture_log", "passed": True, "failures": []}
    address = by_key.get("address", {})
    expected_support = {"fw", "doc", "capture", "serial"}
    actual_support = {evidence["file_id"] for evidence in address.get("supporting_evidence", [])}
    if not combined["hypotheses"] or combined["hypotheses"][0]["key"] != "address":
        cross["failures"].append("address mismatch was not ranked first")
    if not expected_support.issubset(actual_support):
        cross["failures"].append(f"address evidence did not include all sources: {sorted(expected_support - actual_support)}")
    pin_hypothesis = by_key.get("pins", {})
    if not any(evidence["file_id"] == "circuit" for evidence in pin_hypothesis.get("contradictory_evidence", [])):
        cross["failures"].append("matching schematic pin topology was not treated as contrary evidence")
    i2c = multi_files[3]["analysis"].get("protocols", {}).get("i2c", {})
    frames = i2c.get("frames", [])
    if not i2c.get("reliable") or not frames or frames[0].get("address") != 0x49 or frames[0].get("bytes", [{}])[0].get("ack") is not False:
        cross["failures"].append("generated capture did not reliably decode the expected 0x49 NACK")
    if any(item.get("status") != "unverified" for item in combined["hypotheses"]):
        cross["failures"].append("cross-source diagnosis promoted an unverified hypothesis")
    report["checks"].append(cross)
    report["cross_source"] = {
        "evidence_sources": sorted(expected_support | {"circuit"}),
        "top_hypothesis": combined["hypotheses"][0]["key"] if combined["hypotheses"] else None,
        "capture_protocol_reliable": bool(i2c.get("reliable")),
        "capture_address": frames[0].get("address") if frames else None,
        "capture_ack": frames[0].get("bytes", [{}])[0].get("ack") if frames else None,
        "hypotheses_remain_unverified": all(item.get("status") == "unverified" for item in combined["hypotheses"]),
    }

    def rate(numerator, denominator):
        return round(numerator / denominator, 4) if denominator else None

    report["metrics"] = {
        "expected_fault_inclusion": rate(report["fault_targets_included"], report["fault_target_scenarios"]),
        "expected_fault_top_rank": rate(report["fault_targets_ranked_first"], report["fault_target_scenarios"]),
        "citation_grounding": rate(report["grounded_citation_count"], report["citation_count"]),
        "complete_unverified_contracts": rate(report["complete_uncertainty_count"], report["unverified_hypothesis_count"]),
        "relevant_verification_tests": rate(report["relevant_test_count"], report["recommended_test_count"]),
    }
    report["passed"] = all(item["passed"] for item in report["checks"])
    return report


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
