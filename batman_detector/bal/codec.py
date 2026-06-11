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


def decode_bal(data: bytes) -> BlockAccessList:
    """Decode raw RLP BAL bytes (e.g. from a client's engine_getPayloadV6) into the
    model. Word-encoding-agnostic: both MINIMAL and FIXED32 decode to the same ints.

    Raises ValueError on structurally malformed input — itself a useful signal when
    differentially testing clients.
    """
    raw = rlp.decode(data)
    if not isinstance(raw, list):
        raise ValueError("BAL must be an RLP list")

    accounts: list[AccountChanges] = []
    for acc in raw:
        if not isinstance(acc, list) or len(acc) != 6:
            raise ValueError("AccountChanges must be a 6-element list")
        address, raw_sc, raw_reads, raw_bal, raw_nonce, raw_code = acc

        storage_changes = []
        for sc in raw_sc:
            slot, raw_changes = sc
            changes = [StorageChange(_int(c[0]), _int(c[1])) for c in raw_changes]
            storage_changes.append(SlotChanges(_int(slot), changes))

        storage_reads = [_int(k) for k in raw_reads]
        balance_changes = [BalanceChange(_int(b[0]), _int(b[1])) for b in raw_bal]
        nonce_changes = [NonceChange(_int(n[0]), _int(n[1])) for n in raw_nonce]
        code_changes = [CodeChange(_int(c[0]), bytes(c[1])) for c in raw_code]

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
