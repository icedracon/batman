from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from batman_detector.bal.fuzzer import MUTATORS, run_canonicalization_campaign
from batman_detector.evidence_bundle import build_public_evidence_bundle


class CanonicalizationFuzzerTests(unittest.TestCase):
    def test_campaign_detects_and_repairs_every_mutator(self) -> None:
        summary = run_canonicalization_campaign(iterations=len(MUTATORS), seed=7928)
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["missed_mutations"], [])
        self.assertEqual(summary["repair_failures"], [])
        self.assertTrue(all(count == 1 for count in summary["coverage"].values()))

    def test_campaign_is_deterministic(self) -> None:
        first = run_canonicalization_campaign(iterations=32, seed=1234)
        second = run_canonicalization_campaign(iterations=32, seed=1234)
        self.assertEqual(first, second)


class EvidenceBundleTests(unittest.TestCase):
    def test_bundle_copies_explicit_artifacts_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "live-smoke.json"
            source.write_text('{"clients": []}\n', encoding="utf-8")
            out = root / "bundle"

            manifest = build_public_evidence_bundle(
                artifacts=[source],
                output_dir=out,
                metadata={"provenance": "private-devnet"},
            )

            self.assertTrue((out / "live-smoke.json").is_file())
            self.assertTrue((out / "manifest.json").is_file())
            self.assertTrue((out / "README.md").is_file())
            self.assertEqual(manifest["metadata"]["provenance"], "private-devnet")
            self.assertEqual(manifest["artifacts"][0]["name"], "live-smoke.json")

    def test_bundle_rejects_secret_looking_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "jwtsecret.txt"
            source.write_text("do-not-copy", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret-looking"):
                build_public_evidence_bundle([source], root / "bundle")


if __name__ == "__main__":
    unittest.main()
