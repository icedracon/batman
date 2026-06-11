"""Real EIP-7928 Block-Level Access List engine.

This subpackage is the part the initial scaffold lacked: a correct RLP model,
codec, hash, and canonical-form validator for BALs. Everything here is offline
and deterministic — no devnet required. The differential harness (which feeds
real client BAL bytes into `decode_bal` / `diff_bals`) plugs in on top.

Grounded in EIP-7928 (Draft, eips.ethereum.org/EIPS/eip-7928). The exact
word-encoding of uint256 storage keys/values (minimal big-endian int vs fixed
32-byte) is a spec-pin point that itself affects `block_access_list_hash`, so it
is modeled explicitly as `WordEncoding` rather than hard-coded.
"""

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
from .codec import EMPTY_BAL_HASH, bal_hash, decode_bal, encode_bal
from .canonical import canonicalize, check_canonical

__all__ = [
    "AccountChanges",
    "BalanceChange",
    "BlockAccessList",
    "CodeChange",
    "NonceChange",
    "SlotChanges",
    "StorageChange",
    "WordEncoding",
    "EMPTY_BAL_HASH",
    "bal_hash",
    "decode_bal",
    "encode_bal",
    "canonicalize",
    "check_canonical",
]
