"""Report deterministic, source-grounded checks for the fixed I2C scenarios."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.diagnostics import diagnose
from app.evidence import firmware


HERE = Path(__file__).resolve().parent
SCENARIOS = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))


def evaluate():
    report = {
        "method": "Deterministic assertions over fixed fixtures; no LLM self-assessment",
        "scenario_count": len(SCENARIOS),
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
