import unittest
from pathlib import Path

from batman_detector.detectors.bal_system_contract_index_confusion import (
    BalSystemContractIndexConfusionDetector,
)
from batman_detector.reporting import build_markdown_report
from batman_detector.schemas import (
    load_json,
    validate_audit_target,
    validate_fuzz_campaign,
    validate_ruleset,
    validate_trace,
)
from batman_detector.static_scan import scan_audit_target


ROOT = Path(__file__).resolve().parents[1]


class BatmanDetectorTests(unittest.TestCase):
    def test_sample_trace_validates(self):
        trace = load_json(ROOT / "examples" / "traces" / "bal_system_index_confusion.sample.json")
        warnings = validate_trace(trace)
        self.assertTrue(any("provenance" in warning for warning in warnings))

    def test_ruleset_validates(self):
        ruleset = load_json(ROOT / "configs" / "rulesets" / "glamsterdam-alpha.example.json")
        self.assertEqual(validate_ruleset(ruleset), [])

    def test_audit_target_and_fuzz_campaign_validate(self):
        target = load_json(ROOT / "examples" / "audit_targets" / "bal_first_scan.sample.json")
        campaign = load_json(ROOT / "examples" / "fuzz_campaigns" / "bal_index_confusion.sample.json")

        self.assertEqual(validate_audit_target(target), [])
        self.assertEqual(validate_fuzz_campaign(campaign), [])

    def test_static_scan_sample_is_clean(self):
        target_path = ROOT / "examples" / "audit_targets" / "bal_first_scan.sample.json"
        target = load_json(target_path)
        self.assertEqual(scan_audit_target(target, target_path.parent), [])

    def test_bal_detector_reports_overlap_and_mismatch(self):
        trace = load_json(ROOT / "examples" / "traces" / "bal_system_index_confusion.sample.json")
        ruleset = load_json(ROOT / "configs" / "rulesets" / "glamsterdam-alpha.example.json")

        findings = BalSystemContractIndexConfusionDetector().run(trace, ruleset=ruleset)
        titles = {finding.title for finding in findings}

        self.assertIn("Same BAL key is touched across system and transaction phases", titles)
        self.assertIn("Execution clients disagree on BAL output or validity", titles)

    def test_report_contains_private_disclosure_note(self):
        trace = load_json(ROOT / "examples" / "traces" / "bal_system_index_confusion.sample.json")
        ruleset = load_json(ROOT / "configs" / "rulesets" / "glamsterdam-alpha.example.json")

        report = build_markdown_report(trace, ruleset=ruleset)

        self.assertIn("Batman First-Scan Report", report)
        self.assertIn("Keep this report private", report)


if __name__ == "__main__":
    unittest.main()
