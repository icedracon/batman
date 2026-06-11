"""EIP-7928 BAL canonical-form validator and canonicalizer.

This is the core of BAL_SYSTEM_CONTRACT_INDEX_CONFUSION. The spec mandates a
strict ordering + uniqueness; a client that emits a non-canonical BAL produces
different bytes (and therefore a different block_access_list_hash) for the same
state accesses. `check_canonical` reports every violation; `canonicalize` returns
the spec-correct ordering so Batman can compare "what the hash should be" against
a client's actual bytes.

Mandatory ordering (EIP-7928):
  - Accounts: lexicographic by address.
  - storage_changes: slots lexicographic by key; within a slot, changes by
    block_access_index ascending.
  - storage_reads: lexicographic by key.
  - balance_changes / nonce_changes / code_changes: by block_access_index ascending.

Uniqueness:
  - each address exactly once;
  - each storage key at most once per category;
  - no slot in both storage_changes and storage_reads;
  - each block_access_index at most once per change list.
"""

from __future__ import annotations

from .model import AccountChanges, BlockAccessList, SlotChanges


def _ordered(seq: list) -> bool:
    return all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))


def _has_dupes(seq: list) -> bool:
    return len(set(seq)) != len(seq)


def check_canonical(bal: BlockAccessList) -> list[str]:
    """Return a list of human-readable canonical-form violations (empty == valid)."""
    v: list[str] = []

    addrs = [a.address for a in bal.accounts]
    if not _ordered(addrs):
        v.append("accounts not lexicographically ordered by address")
    if _has_dupes(addrs):
        v.append("duplicate account address")

    for a in bal.accounts:
        ah = "0x" + a.address.hex()

        slots = [s.slot for s in a.storage_changes]
        if not _ordered(slots):
            v.append(f"{ah}: storage_changes slots not ordered by key")
        if _has_dupes(slots):
            v.append(f"{ah}: duplicate slot in storage_changes")

        for s in a.storage_changes:
            if not s.changes:
                v.append(f"{ah} slot {s.slot}: SlotChanges must contain at least one StorageChange")
            idxs = [c.block_access_index for c in s.changes]
            if not _ordered(idxs):
                v.append(f"{ah} slot {s.slot}: storage changes not ordered by block_access_index")
            if _has_dupes(idxs):
                v.append(f"{ah} slot {s.slot}: duplicate block_access_index in storage changes")

        reads = list(a.storage_reads)
        if not _ordered(reads):
            v.append(f"{ah}: storage_reads not ordered by key")
        if _has_dupes(reads):
            v.append(f"{ah}: duplicate key in storage_reads")

        overlap = sorted(set(slots) & set(reads))
        if overlap:
            v.append(f"{ah}: slot(s) appear in both storage_changes and storage_reads: {overlap}")

        for label, idxs in (
            ("balance_changes", [b.block_access_index for b in a.balance_changes]),
            ("nonce_changes", [n.block_access_index for n in a.nonce_changes]),
            ("code_changes", [c.block_access_index for c in a.code_changes]),
        ):
            if not _ordered(idxs):
                v.append(f"{ah}: {label} not ordered by block_access_index")
            if _has_dupes(idxs):
                v.append(f"{ah}: duplicate block_access_index in {label}")

    return v


def canonicalize(bal: BlockAccessList) -> BlockAccessList:
    """Return a copy sorted into spec-canonical order.

    Ordering only — it does not drop duplicates, because a duplicate is a spec
    violation to be reported (via check_canonical), not silently repaired.
    """
    accounts = []
    for a in sorted(bal.accounts, key=lambda x: x.address):
        storage_changes = [
            SlotChanges(
                slot=s.slot,
                changes=sorted(s.changes, key=lambda c: c.block_access_index),
            )
            for s in sorted(a.storage_changes, key=lambda x: x.slot)
        ]
        accounts.append(
            AccountChanges(
                address=a.address,
                storage_changes=storage_changes,
                storage_reads=sorted(a.storage_reads),
                balance_changes=sorted(a.balance_changes, key=lambda x: x.block_access_index),
                nonce_changes=sorted(a.nonce_changes, key=lambda x: x.block_access_index),
                code_changes=sorted(a.code_changes, key=lambda x: x.block_access_index),
            )
        )
    return BlockAccessList(accounts=accounts)
