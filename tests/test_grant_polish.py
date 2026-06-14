from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from batman_detector.bal.fuzzer import (
    MALFORMED_CASES,
    MUTATORS,
    run_canonicalization_campaign,
    run_malformed_corpus,
)
from batman_detector.compatibility import build_compatibility_snapshot
from batman_detector.evidence_bundle import build_public_evidence_bundle, verify_public_evidence_bundle
from batman_detector.schemas import validate_compatibility_snapshot


def _write_public_evidence_set(root: Path) -> list[Path]:
    heads = root / "live-heads.json"
    smoke = root / "live-smoke.json"
    refusal = root / "live-4way-diff.txt"
    three_way = root / "live-3way-diff.txt"
    trace = root / "subset-live-trace.json"
    report = root / "subset-live-report.md"
    snapshot = root / "compatibility-snapshot.gloas-devnet0.json"

    heads.write_text(
        """
        {
          "agree": false,
          "client_heads": {
            "geth": {"number": 7, "hash": "0xaaa"},
            "erigon": {"number": 8, "hash": "0xbbb"},
            "reth": {"number": 7, "hash": "0xaaa"},
            "nethermind": {"number": 7, "hash": "0xaaa"}
          }
        }
        """,
        encoding="utf-8",
    )
    smoke.write_text(
        """
        {
          "clients": [
            {"client_id": "geth", "engine_has_bal": true, "engine_bal_bytes": 210, "rpc_has_bal": false},
            {"client_id": "erigon", "engine_has_bal": true, "engine_bal_bytes": 210, "rpc_has_bal": false},
            {"client_id": "reth", "engine_has_bal": true, "engine_bal_bytes": 210, "rpc_has_bal": false},
            {"client_id": "nethermind", "engine_has_bal": true, "engine_bal_bytes": 210, "rpc_has_bal": false}
          ]
        }
        """,
        encoding="utf-8",
    )
    refusal.write_text("not running same-head differential; retry later\n", encoding="utf-8")
    three_way.write_text("findings: 0\n", encoding="utf-8")
    trace.write_text(
        """
        {
          "observations": [
            {"client_id": "geth", "kind": "bal_output"},
            {"client_id": "reth", "kind": "bal_output"},
            {"client_id": "nethermind", "kind": "bal_output"}
          ]
        }
        """,
        encoding="utf-8",
    )
    report.write_text("# Report\n\nFinding count: `0`\n", encoding="utf-8")

    snapshot_data = build_compatibility_snapshot(
        heads_path=heads,
        smoke_path=smoke,
        four_way_output_path=refusal,
        subset_trace_path=trace,
        subset_report_path=report,
        batman_commit="abc123",
    )
    snapshot.write_text(json_dumps(snapshot_data), encoding="utf-8")
    return [heads, smoke, refusal, three_way, trace, report, snapshot]


def json_dumps(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


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

    def test_malformed_corpus_detects_every_case(self) -> None:
        summary = run_malformed_corpus()
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["case_count"], len(MALFORMED_CASES))
        self.assertEqual(summary["missed_cases"], [])


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

    def test_verify_accepts_public_evidence_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = _write_public_evidence_set(root)
            out = root / "bundle"
            build_public_evidence_bundle(artifacts, out)

            summary = verify_public_evidence_bundle(artifacts, out)

            self.assertEqual(summary["artifact_count"], 7)
            self.assertEqual(summary["four_way"], "refused_devnet_split")
            self.assertEqual(summary["finding_count"], 0)

    def test_verify_rejects_missing_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "live-smoke.json"
            with self.assertRaisesRegex(ValueError, "does not exist"):
                verify_public_evidence_bundle([missing], root / "bundle")

    def test_verify_rejects_secret_looking_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "private-key.txt"
            source.write_text("do-not-copy", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret-looking"):
                verify_public_evidence_bundle([source], root / "bundle")

    def test_verify_rejects_broken_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "live-smoke.json"
            source.write_text('{"clients": []}\u0000', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                verify_public_evidence_bundle([source], root / "bundle")

    def test_verify_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = _write_public_evidence_set(root)
            out = root / "bundle"
            build_public_evidence_bundle(artifacts, out)
            (root / "live-smoke.json").write_text('{"clients": []}\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not match source"):
                verify_public_evidence_bundle(artifacts, out)


class CompatibilitySnapshotTests(unittest.TestCase):
    def test_snapshot_summarizes_split_devnet_without_overclaiming(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            heads = root / "heads.json"
            smoke = root / "smoke.json"
            trace = root / "trace.json"
            report = root / "report.md"
            refusal = root / "four-way.txt"

            heads.write_text(
                """
                {
                  "agree": false,
                  "client_heads": {
                    "geth": {"number": 7, "hash": "0xaaa"},
                    "erigon": {"number": 8, "hash": "0xbbb"},
                    "reth": {"number": 7, "hash": "0xaaa"}
                  }
                }
                """,
                encoding="utf-8",
            )
            smoke.write_text(
                """
                {
                  "clients": [
                    {"client_id": "geth", "engine_has_bal": true, "engine_bal_bytes": 210, "rpc_has_bal": false},
                    {"client_id": "erigon", "engine_has_bal": true, "engine_bal_bytes": 210, "rpc_has_bal": false},
                    {"client_id": "reth", "engine_has_bal": true, "engine_bal_bytes": 210, "rpc_has_bal": false}
                  ]
                }
                """,
                encoding="utf-8",
            )
            trace.write_text(
                """
                {
                  "observations": [
                    {"client_id": "geth", "kind": "bal_output"},
                    {"client_id": "reth", "kind": "bal_output"}
                  ]
                }
                """,
                encoding="utf-8",
            )
            report.write_text("# Report\n\nFinding count: `0`\n", encoding="utf-8")
            refusal.write_text("not running same-head differential\n", encoding="utf-8")

            snapshot = build_compatibility_snapshot(
                heads_path=heads,
                smoke_path=smoke,
                four_way_output_path=refusal,
                subset_trace_path=trace,
                subset_report_path=report,
                batman_commit="abc123",
            )

            self.assertEqual(validate_compatibility_snapshot(snapshot), [])
            self.assertEqual(snapshot["results"]["four_way_same_head_differential"], "refused_devnet_split")
            self.assertEqual(snapshot["results"]["subset_same_head_differential"]["finding_count"], 0)
            self.assertFalse(snapshot["safety"]["bounty_claim"])
            included = {
                item["client_id"]: item["included_in_same_head_differential"]
                for item in snapshot["clients"]
            }
            self.assertEqual(included, {"erigon": False, "geth": True, "reth": True})


if __name__ == "__main__":
    unittest.main()
