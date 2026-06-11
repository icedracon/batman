"""EIP-7928 BAL data model (RLP structures).

Mirrors the spec's RLP layout verbatim:

    StorageChange  = [BlockAccessIndex, StorageValue]
    BalanceChange  = [BlockAccessIndex, Balance]
    NonceChange    = [BlockAccessIndex, Nonce]
    CodeChange     = [BlockAccessIndex, Bytecode]
    SlotChanges    = [StorageKey, List[StorageChange]]
    AccountChanges = [Address, List[SlotChanges], List[StorageKey],
                      List[BalanceChange], List[NonceChange], List[CodeChange]]
    BlockAccessList = List[AccountChanges]

Type aliases (EIP-7928):
    Address                              = bytes20
    StorageKey, StorageValue, Balance    = uint256
    Nonce                                = uint64
    BlockAccessIndex                     = uint32
    Bytecode                             = bytes

block_access_index semantics: 0 = pre-execution system calls, 1..n = txs (block
order), n+1 = post-execution system calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WordEncoding(str, Enum):
    """How a uint256 storage key/value is laid into RLP.

    MINIMAL  — RLP big-endian int (no leading zeroes). This is the plain reading
               of "uint256" as an RLP integer sedes.
    FIXED32  — fixed 32-byte big-endian string.

    These produce different bytes (hence different block_access_list_hash) for any
    value with leading zero bytes, so a client that picks the other convention is a
    real cross-client BAL-hash divergence source. Batman keeps it pluggable on
    purpose so the detector can test both.
    """

    MINIMAL = "minimal"
    FIXED32 = "fixed32"


def _int_min(value: int) -> bytes:
    """RLP big-endian-int minimal byte form (0 -> empty string)."""
    if value < 0:
        raise ValueError("BAL integers are unsigned")
    if value == 0:
        return b""
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def _word(value: int, enc: WordEncoding) -> bytes:
    _check_uint(value, 256, "storage key/value")
    if enc is WordEncoding.FIXED32:
        return value.to_bytes(32, "big")
    return _int_min(value)


def _check_uint(value: int, bits: int, label: str) -> None:
    if not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < 0 or value >= 1 << bits:
        raise ValueError(f"{label} out of uint{bits} range")


@dataclass(frozen=True)
class StorageChange:
    block_access_index: int  # uint32
    new_value: int           # uint256

    def __post_init__(self) -> None:
        _check_uint(self.block_access_index, 32, "block_access_index")
        _check_uint(self.new_value, 256, "storage value")

    def to_rlp(self, enc: WordEncoding) -> list:
        return [_int_min(self.block_access_index), _word(self.new_value, enc)]


@dataclass(frozen=True)
class SlotChanges:
    slot: int                       # uint256 storage key
    changes: list[StorageChange] = field(default_factory=list)

    def __post_init__(self) -> None:
        _check_uint(self.slot, 256, "storage slot")
        if not self.changes:
            raise ValueError("SlotChanges must contain at least one StorageChange")

    def to_rlp(self, enc: WordEncoding) -> list:
        return [_word(self.slot, enc), [c.to_rlp(enc) for c in self.changes]]


@dataclass(frozen=True)
class BalanceChange:
    block_access_index: int  # uint32
    post_balance: int        # uint256

    def __post_init__(self) -> None:
        _check_uint(self.block_access_index, 32, "block_access_index")
        _check_uint(self.post_balance, 256, "post_balance")

    def to_rlp(self, enc: WordEncoding) -> list:
        return [_int_min(self.block_access_index), _int_min(self.post_balance)]


@dataclass(frozen=True)
class NonceChange:
    block_access_index: int  # uint32
    new_nonce: int           # uint64

    def __post_init__(self) -> None:
        _check_uint(self.block_access_index, 32, "block_access_index")
        _check_uint(self.new_nonce, 64, "nonce")

    def to_rlp(self, enc: WordEncoding) -> list:
        return [_int_min(self.block_access_index), _int_min(self.new_nonce)]


@dataclass(frozen=True)
class CodeChange:
    block_access_index: int  # uint32
    new_code: bytes          # bytecode

    def __post_init__(self) -> None:
        _check_uint(self.block_access_index, 32, "block_access_index")
        if not isinstance(self.new_code, bytes):
            raise ValueError("new_code must be bytes")

    def to_rlp(self, enc: WordEncoding) -> list:
        return [_int_min(self.block_access_index), self.new_code]


@dataclass(frozen=True)
class AccountChanges:
    address: bytes  # bytes20
    storage_changes: list[SlotChanges] = field(default_factory=list)
    storage_reads: list[int] = field(default_factory=list)  # storage keys
    balance_changes: list[BalanceChange] = field(default_factory=list)
    nonce_changes: list[NonceChange] = field(default_factory=list)
    code_changes: list[CodeChange] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.address, bytes):
            raise ValueError("address must be bytes")
        if len(self.address) != 20:
            raise ValueError(f"address must be 20 bytes, got {len(self.address)}")
        for key in self.storage_reads:
            _check_uint(key, 256, "storage read key")

    def to_rlp(self, enc: WordEncoding) -> list:
        return [
            self.address,
            [s.to_rlp(enc) for s in self.storage_changes],
            [_word(k, enc) for k in self.storage_reads],
            [b.to_rlp(enc) for b in self.balance_changes],
            [n.to_rlp(enc) for n in self.nonce_changes],
            [c.to_rlp(enc) for c in self.code_changes],
        ]


@dataclass(frozen=True)
class BlockAccessList:
    accounts: list[AccountChanges] = field(default_factory=list)

    def to_rlp(self, enc: WordEncoding) -> list:
        return [a.to_rlp(enc) for a in self.accounts]
