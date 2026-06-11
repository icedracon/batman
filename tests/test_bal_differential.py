from __future__ import annotations

import unittest

from batman_detector.bal import (
    AccountChanges,
    BlockAccessList,
    SlotChanges,
    StorageChange,
    WordEncoding,
    bal_hash,
    encode_bal,
)
from batman_detector.bal.differential import analyze_client, cross_client, structural_diff
from batman_detector.detectors import DETECTORS

A1 = bytes.fromhex("00000000000000000000000000000000000010aa")
A2 = bytes.fromhex("00000000000000000000000000000000000010bb")


def _canonical_bal() -> BlockAccessList:
    return BlockAccessList(accounts=[
        AccountChanges(address=A1, storage_changes=[
            SlotChanges(slot=7, changes=[StorageChange(0, 1), StorageChange(1, 2), StorageChange(2, 3)]),
        ]),
        AccountChanges(address=A2, storage_reads=[3, 9]),
    ])


def _noncanonical_bal() -> BlockAccessList:
    # Same accesses, wrong account + change order => non-canonical bytes.
    return BlockAccessList(accounts=[
        AccountChanges(address=A2, storage_reads=[9, 3]),
        AccountChanges(address=A1, storage_changes=[
            SlotChanges(slot=7, changes=[StorageChange(2, 3), StorageChange(0, 1), StorageChange(1, 2)]),
        ]),
    ])


class TestDifferential(unittest.TestCase):
    def test_identical_clients_agree(self):
        raw = encode_bal(_canonical_bal())
        result = cross_client({"geth": raw, "reth": raw})
        self.assertTrue(result["agree"])
        self.assertEqual(result["structural_diff"], [])

    def test_noncanonical_order_same_content(self):
        # Same accesses, different byte order: hashes disagree, but content is
        # identical -> structural_diff is empty; the signal is the canonical
        # violation on the offending client.
        good = encode_bal(_canonical_bal())
        bad = encode_bal(_noncanonical_bal())
        result = cross_client({"geth": good, "reth": bad})
        self.assertFalse(result["agree"])
        self.assertEqual(result["structural_diff"], [])
        self.assertTrue(result["analyses"]["reth"].canonical_violations)
        self.assertEqual(result["analyses"]["geth"].canonical_violations, [])

    def test_content_divergence_localized(self):
        # The real index-confusion shape: both BALs canonical, but they disagree
        # on the slot-7 change list (one merged tx+post-exec into one index).
        good = encode_bal(_canonical_bal())
        variant = encode_bal(BlockAccessList(accounts=[
            AccountChanges(address=A1, storage_changes=[
                SlotChanges(slot=7, changes=[StorageChange(0, 1), StorageChange(1, 3)]),
            ]),
            AccountChanges(address=A2, storage_reads=[3, 9]),
        ]))
        result = cross_client({"geth": good, "reth": variant})
        self.assertFalse(result["agree"])
        self.assertTrue(any("slot 0x7: change list differs" in d for d in result["structural_diff"]))
        self.assertEqual(result["analyses"]["geth"].canonical_violations, [])
        self.assertEqual(result["analyses"]["reth"].canonical_violations, [])

    def test_encoding_inference(self):
        raw_min = encode_bal(_canonical_bal(), WordEncoding.MINIMAL)
        raw_fix = encode_bal(_canonical_bal(), WordEncoding.FIXED32)
        self.assertEqual(analyze_client("c", raw_min).encoding, "minimal/canonical")
        self.assertEqual(analyze_client("c", raw_fix).encoding, "fixed32/canonical")

    def test_header_mismatch_detected(self):
        raw = encode_bal(_canonical_bal())
        a = analyze_client("geth", raw, header_hash="0x" + "00" * 32)
        self.assertFalse(a.header_matches)
        good_header = "0x" + bal_hash(_canonical_bal()).hex()
        self.assertTrue(analyze_client("geth", raw, header_hash=good_header).header_matches)

    def test_undecodable_bytes(self):
        a = analyze_client("geth", b"\xff\xff\xff not rlp")
        self.assertFalse(a.ok)
        self.assertEqual(a.encoding, "undecodable")

    def test_structural_diff_localizes_account(self):
        diffs = structural_diff("a", _canonical_bal(), "b",
                                BlockAccessList(accounts=[AccountChanges(address=A1)]))
        self.assertTrue(any("0x" + A2.hex() in d for d in diffs))


class TestDetectorRealPath(unittest.TestCase):
    def _trace(self, good: bytes, bad: bytes) -> dict:
        return {
            "trace_id": "t-real-001",
            "block": {"transaction_count": 1,
                      "block_access_list_hash": "0x" + bal_hash(_canonical_bal()).hex()},
            "events": [],
            "observations": [
                {"kind": "bal_output", "client_id": "geth", "bal_rlp": "0x" + good.hex()},
                {"kind": "bal_output", "client_id": "reth", "bal_rlp": "0x" + bad.hex()},
            ],
        }

    def test_detector_reports_real_divergence(self):
        detector = DETECTORS["BAL_SYSTEM_CONTRACT_INDEX_CONFUSION"]()
        findings = detector.run(self._trace(encode_bal(_canonical_bal()), encode_bal(_noncanonical_bal())))
        titles = [f.title for f in findings]
        self.assertTrue(any("non-canonical BAL" in t for t in titles))
        self.assertTrue(any("different BAL bytes for the same block" in t for t in titles))
        self.assertTrue(any(f.severity == "critical" for f in findings))


if __name__ == "__main__":
    unittest.main()
