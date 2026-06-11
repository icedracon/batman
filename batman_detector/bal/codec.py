"""RLP encode / decode / hash for EIP-7928 Block-Level Access Lists.

    block_access_list_hash = keccak256(rlp.encode(block_access_list))

Anchored to the spec's published empty-BAL hash constant in the tests, so the
codec is provably wired to the real spec and not a guess.
"""

from __future__ import annotations

import rlp
from eth_utils import keccak

from .model import (
    AccountChanges,
    BalanceChange,
    BlockAccessList,
    CodeChange,
    NonceChange,
    SlotChanges,
    StorageChange,
    WordEncoding,
)

# keccak256(rlp.encode([])) — EIP-7928 empty-BAL hash. Encoding-independent.
EMPTY_BAL_HASH = bytes.fromhex(
    "1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347"
)


def encode_bal(bal: BlockAccessList, enc: WordEncoding = WordEncoding.MINIMAL) -> bytes:
    return rlp.encode(bal.to_rlp(enc))


def bal_hash(bal: BlockAccessList, enc: WordEncoding = WordEncoding.MINIMAL) -> bytes:
    return keccak(encode_bal(bal, enc))


def _int(value) -> int:
    """Decode an RLP byte string back to a non-negative integer."""
    if isinstance(value, list):
        raise ValueError("expected integer leaf, got list")
    return int.from_bytes(value, "big") if value else 0


def _expect_list(value, length: int | None, label: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an RLP list")
    if length is not None and len(value) != length:
        raise ValueError(f"{label} must be a {length}-element list")
    return value


def decode_bal(data: bytes) -> BlockAccessList:
    """Decode raw RLP BAL bytes (e.g. from a client's engine_getPayloadV6) into the
    model. Word-encoding-agnostic: both MINIMAL and FIXED32 decode to the same ints.

    Raises ValueError on structurally malformed input — itself a useful signal when
    differentially testing clients.
    """
    try:
        decoded = rlp.decode(data)
    except rlp.exceptions.DecodingError as exc:
        raise ValueError(f"invalid RLP: {exc}") from exc
    raw = _expect_list(decoded, None, "BAL")

    accounts: list[AccountChanges] = []
    for acc in raw:
        acc = _expect_list(acc, 6, "AccountChanges")
        address, raw_sc, raw_reads, raw_bal, raw_nonce, raw_code = acc
        raw_sc = _expect_list(raw_sc, None, "storage_changes")
        raw_reads = _expect_list(raw_reads, None, "storage_reads")
        raw_bal = _expect_list(raw_bal, None, "balance_changes")
        raw_nonce = _expect_list(raw_nonce, None, "nonce_changes")
        raw_code = _expect_list(raw_code, None, "code_changes")

        storage_changes = []
        for sc in raw_sc:
            sc = _expect_list(sc, 2, "SlotChanges")
            slot, raw_changes = sc
            raw_changes = _expect_list(raw_changes, None, "SlotChanges.changes")
            changes = []
            for c in raw_changes:
                c = _expect_list(c, 2, "StorageChange")
                changes.append(StorageChange(_int(c[0]), _int(c[1])))
            storage_changes.append(SlotChanges(_int(slot), changes))

        storage_reads = [_int(k) for k in raw_reads]
        balance_changes = []
        for b in raw_bal:
            b = _expect_list(b, 2, "BalanceChange")
            balance_changes.append(BalanceChange(_int(b[0]), _int(b[1])))
        nonce_changes = []
        for n in raw_nonce:
            n = _expect_list(n, 2, "NonceChange")
            nonce_changes.append(NonceChange(_int(n[0]), _int(n[1])))
        code_changes = []
        for c in raw_code:
            c = _expect_list(c, 2, "CodeChange")
            if isinstance(c[1], list):
                raise ValueError("CodeChange.new_code must be bytes")
            code_changes.append(CodeChange(_int(c[0]), bytes(c[1])))

        accounts.append(
            AccountChanges(
                address=bytes(address),
                storage_changes=storage_changes,
                storage_reads=storage_reads,
                balance_changes=balance_changes,
                nonce_changes=nonce_changes,
                code_changes=code_changes,
            )
        )
    return BlockAccessList(accounts=accounts)
