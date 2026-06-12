from __future__ import annotations

import unittest

from batman_detector.bal import (
    AccountChanges,
    BlockAccessList,
    SlotChanges,
    StorageChange,
    bal_hash,
    encode_bal,
)
from batman_detector.detectors import DETECTORS
from batman_detector.detectors.bal_mixed_read_write_alias import (
    BalMixedReadWriteAliasDetector,
)
from batman_detector.schemas import load_json, validate_trace

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
A1 = bytes.fromhex("00000000000000000000000000000000000010aa")


def _trace_for_bal(bal: BlockAccessList, *, provenance_kind: str = "synthetic_fixture") -> dict:
    raw = encode_bal(bal)
    return {
        "trace_id": "t-bal-mixed-read-write-alias",
        "target": {
            "fork": "Glamsterdam",
            "eips": ["EIP-7928"],
            "spec_refs": [
                {
                    "name": "EIP-7928 Block-Level Access Lists",
                    "url": "https://eips.ethereum.org/EIPS/eip-7928",
                    "commit": "draft-as-of-2026-06-11",
                }
            ],
        },
        "block": {
            "transaction_count": 1,
            "block_access_list_hash": "0x" + bal_hash(bal).hex(),
        },
        "provenance": {"kind": provenance_kind, "bounty_eligible": provenance_kind != "synthetic_fixture"},
        "events": [],
        "observations": [
            {
                "kind": "bal_output",
                "client_id": "geth",
                "bal_hash": "0x" + bal_hash(bal).hex(),
                "bal_rlp": "0x" + raw.hex(),
            }
        ],
    }


def _aliased_bal() -> BlockAccessList:
    return BlockAccessList(
        accounts=[
            AccountChanges(
                address=A1,
                storage_changes=[
                    SlotChanges(
                        slot=7,
                        changes=[
                            StorageChange(0, 1),
                            StorageChange(1, 2),
                            StorageChange(2, 3),
                        ],
                    )
                ],
                storage_reads=[7],
            )
        ]
    )


class MixedReadWriteAliasDetectorTests(unittest.TestCase):
    def test_detector_registered(self) -> None:
        self.assertIn("BAL_MIXED_READ_WRITE_ALIAS", DETECTORS)
        self.assertIs(DETECTORS["BAL_MIXED_READ_WRITE_ALIAS"], BalMixedReadWriteAliasDetector)

    def test_fires_on_decoded_mixed_read_write_alias(self) -> None:
        findings = BalMixedReadWriteAliasDetector().run(_trace_for_bal(_aliased_bal()))

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.detector_id, "BAL_MIXED_READ_WRITE_ALIAS")
        self.assertEqual(finding.severity, "medium")
        self.assertIn("storage_reads and storage_changes", finding.evidence[0])
        self.assertIn("write_indexes=[0, 1, 2]", finding.evidence[0])

    def test_live_alias_can_escalate_but_not_to_critical(self) -> None:
        findings = BalMixedReadWriteAliasDetector().run(
            _trace_for_bal(_aliased_bal(), provenance_kind="live_devnet")
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "high")

    def test_silent_on_clean_read_only_and_write_only_bals(self) -> None:
        read_only = BlockAccessList(accounts=[AccountChanges(address=A1, storage_reads=[7])])
        write_only = BlockAccessList(
            accounts=[
                AccountChanges(
                    address=A1,
                    storage_changes=[SlotChanges(slot=7, changes=[StorageChange(1, 2)])],
                )
            ]
        )

        detector = BalMixedReadWriteAliasDetector()
        self.assertEqual(detector.run(_trace_for_bal(read_only)), [])
        self.assertEqual(detector.run(_trace_for_bal(write_only)), [])

    def test_committed_fixture_validates_and_fires(self) -> None:
        trace = load_json(ROOT / "examples" / "traces" / "bal_mixed_read_write_alias.sample.json")

        validate_trace(trace)
        findings = BalMixedReadWriteAliasDetector().run(trace)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "medium")


if __name__ == "__main__":
    unittest.main()

