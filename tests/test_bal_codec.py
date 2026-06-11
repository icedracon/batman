from __future__ import annotations

import unittest

from batman_detector.bal import (
    AccountChanges,
    BalanceChange,
    BlockAccessList,
    EMPTY_BAL_HASH,
    NonceChange,
    SlotChanges,
    StorageChange,
    WordEncoding,
    bal_hash,
    canonicalize,
    check_canonical,
    decode_bal,
    encode_bal,
)

A1 = bytes.fromhex("00000000000000000000000000000000000010aa")
A2 = bytes.fromhex("00000000000000000000000000000000000010bb")


def _sample_bal() -> BlockAccessList:
    return BlockAccessList(
        accounts=[
            AccountChanges(
                address=A1,
                storage_changes=[
                    SlotChanges(slot=7, changes=[
                        StorageChange(0, 1),   # pre-exec system write
                        StorageChange(1, 2),   # tx write
                        StorageChange(2, 3),   # post-exec write (n+1, n=1)
                    ]),
                ],
                balance_changes=[BalanceChange(1, 10**18)],
                nonce_changes=[NonceChange(1, 5)],
            ),
            AccountChanges(address=A2, storage_reads=[3, 9]),
        ]
    )


class TestBalCodec(unittest.TestCase):
    def test_empty_bal_hash_matches_spec_constant(self):
        # The keystone: proves codec is wired to the real EIP-7928 hash rule.
        self.assertEqual(bal_hash(BlockAccessList()), EMPTY_BAL_HASH)

    def test_round_trip(self):
        bal = _sample_bal()
        self.assertEqual(decode_bal(encode_bal(bal)), bal)

    def test_word_encoding_changes_hash(self):
        # Same accesses, different uint256 lay-out -> different bytes/hash.
        # This is itself a cross-client divergence class, not just an internal knob.
        bal = _sample_bal()
        self.assertNotEqual(
            bal_hash(bal, WordEncoding.MINIMAL),
            bal_hash(bal, WordEncoding.FIXED32),
        )

    def test_canonical_sample_is_valid(self):
        self.assertEqual(check_canonical(_sample_bal()), [])

    def test_detects_unordered_accounts(self):
        bal = BlockAccessList(accounts=[
            AccountChanges(address=A2),
            AccountChanges(address=A1),  # out of order
        ])
        violations = check_canonical(bal)
        self.assertTrue(any("not lexicographically ordered" in x for x in violations))

    def test_detects_slot_in_both_reads_and_changes(self):
        bal = BlockAccessList(accounts=[
            AccountChanges(
                address=A1,
                storage_changes=[SlotChanges(slot=7, changes=[StorageChange(1, 2)])],
                storage_reads=[7],  # same slot also declared as a pure read
            )
        ])
        violations = check_canonical(bal)
        self.assertTrue(any("both storage_changes and storage_reads" in x for x in violations))

    def test_canonicalize_repairs_ordering(self):
        # A clearly-unordered two-account list: wrong account order, wrong slot
        # change order, wrong storage_reads order.
        shuffled = BlockAccessList(accounts=[
            AccountChanges(address=A2, storage_reads=[9, 3]),
            AccountChanges(address=A1, storage_changes=[SlotChanges(
                slot=7, changes=[StorageChange(2, 3), StorageChange(0, 1)])]),
        ])
        self.assertNotEqual(check_canonical(shuffled), [])
        self.assertEqual(check_canonical(canonicalize(shuffled)), [])


if __name__ == "__main__":
    unittest.main()
