"""Cross-client BAL differential analysis on REAL bytes.

This is what makes BAL_SYSTEM_CONTRACT_INDEX_CONFUSION a real detector instead of
a linter over pasted hashes. Given each client's raw RLP BAL bytes (from
engine_getPayloadV6 / a trace observation), it:

  - decodes them (malformed bytes are themselves a signal),
  - checks canonical form (a client emitting non-canonical order => different hash),
  - recomputes keccak(raw) and compares to the client's declared hash and the
    block header's block_access_list_hash,
  - infers the word-encoding the bytes correspond to (minimal vs fixed32),
  - and structurally diffs decoded BALs to localize *where* clients disagree
    (account / slot / block_access_index / category) — not just "hashes differ".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from eth_utils import keccak

from .canonical import canonicalize, check_canonical
from .codec import decode_bal, encode_bal
from .model import AccountChanges, BlockAccessList, WordEncoding


@dataclass
class ClientBalAnalysis:
    client_id: str
    ok: bool
    error: str | None = None
    recomputed_hash: str | None = None          # 0x keccak(raw bytes)
    declared_hash: str | None = None            # client's self-reported BAL hash
    header_hash: str | None = None              # block header block_access_list_hash
    header_matches: bool | None = None
    declared_matches: bool | None = None
    canonical_violations: list[str] = field(default_factory=list)
    encoding: str = "unknown"
    decoded: BlockAccessList | None = None


def _h(b: bytes) -> str:
    return "0x" + keccak(b).hex()


def analyze_client(
    client_id: str,
    raw: bytes,
    declared_hash: str | None = None,
    header_hash: str | None = None,
) -> ClientBalAnalysis:
    try:
        decoded = decode_bal(raw)
    except Exception as exc:  # malformed BAL from a client is a real finding
        return ClientBalAnalysis(
            client_id=client_id,
            ok=False,
            error=str(exc),
            declared_hash=declared_hash,
            header_hash=header_hash,
            encoding="undecodable",
        )

    recomputed = _h(raw)
    violations = check_canonical(decoded)

    # Which (encoding, canonical) combo reproduces the exact bytes the client sent?
    canon = canonicalize(decoded)
    if encode_bal(canon, WordEncoding.MINIMAL) == raw:
        encoding = "minimal/canonical"
    elif encode_bal(canon, WordEncoding.FIXED32) == raw:
        encoding = "fixed32/canonical"
    else:
        encoding = "non-canonical-or-other"

    return ClientBalAnalysis(
        client_id=client_id,
        ok=True,
        recomputed_hash=recomputed,
        declared_hash=declared_hash,
        header_hash=header_hash,
        header_matches=None if not header_hash else recomputed.lower() == header_hash.lower(),
        declared_matches=None if not declared_hash else recomputed.lower() == declared_hash.lower(),
        canonical_violations=violations,
        encoding=encoding,
        decoded=decoded,
    )


def _bnc_pairs(items, value_attr: str) -> list[tuple[int, int]]:
    return sorted((getattr(x, "block_access_index"), getattr(x, value_attr)) for x in items)


def structural_diff(label_a: str, a: BlockAccessList, label_b: str, b: BlockAccessList) -> list[str]:
    """Localize the exact differences between two decoded BALs."""
    diffs: list[str] = []
    map_a = {x.address: x for x in a.accounts}
    map_b = {x.address: x for x in b.accounts}

    for addr in sorted(set(map_a) - set(map_b)):
        diffs.append(f"account 0x{addr.hex()}: present in {label_a}, absent in {label_b}")
    for addr in sorted(set(map_b) - set(map_a)):
        diffs.append(f"account 0x{addr.hex()}: present in {label_b}, absent in {label_a}")

    for addr in sorted(set(map_a) & set(map_b)):
        ah = "0x" + addr.hex()
        ca: AccountChanges = map_a[addr]
        cb: AccountChanges = map_b[addr]

        sca = {s.slot: s for s in ca.storage_changes}
        scb = {s.slot: s for s in cb.storage_changes}
        for slot in sorted(set(sca) - set(scb)):
            diffs.append(f"{ah} slot {hex(slot)}: storage change only in {label_a}")
        for slot in sorted(set(scb) - set(sca)):
            diffs.append(f"{ah} slot {hex(slot)}: storage change only in {label_b}")
        for slot in sorted(set(sca) & set(scb)):
            la = sorted((c.block_access_index, c.new_value) for c in sca[slot].changes)
            lb = sorted((c.block_access_index, c.new_value) for c in scb[slot].changes)
            if la != lb:
                diffs.append(f"{ah} slot {hex(slot)}: change list differs {la} vs {lb}")

        if sorted(ca.storage_reads) != sorted(cb.storage_reads):
            diffs.append(
                f"{ah}: storage_reads differ {sorted(ca.storage_reads)} vs {sorted(cb.storage_reads)}"
            )
        if _bnc_pairs(ca.balance_changes, "post_balance") != _bnc_pairs(cb.balance_changes, "post_balance"):
            diffs.append(f"{ah}: balance_changes differ")
        if _bnc_pairs(ca.nonce_changes, "new_nonce") != _bnc_pairs(cb.nonce_changes, "new_nonce"):
            diffs.append(f"{ah}: nonce_changes differ")
        code_a = sorted((c.block_access_index, c.new_code.hex()) for c in ca.code_changes)
        code_b = sorted((c.block_access_index, c.new_code.hex()) for c in cb.code_changes)
        if code_a != code_b:
            diffs.append(f"{ah}: code_changes differ")

    return diffs


def cross_client(
    raw_by_client: dict[str, bytes],
    header_hash: str | None = None,
    declared_by_client: dict[str, str] | None = None,
) -> dict:
    """Analyze every client's BAL bytes and report agreement + localized diffs."""
    declared_by_client = declared_by_client or {}
    analyses = {
        cid: analyze_client(cid, raw, declared_by_client.get(cid), header_hash)
        for cid, raw in raw_by_client.items()
    }
    decodable = {cid: a for cid, a in analyses.items() if a.ok}
    distinct_hashes = {a.recomputed_hash for a in decodable.values()}

    diffs: list[str] = []
    decoded_ids = sorted(decodable)
    if len(distinct_hashes) > 1 and len(decoded_ids) >= 2:
        # Diff the first decodable client against each other one to localize splits.
        ref = decoded_ids[0]
        for other in decoded_ids[1:]:
            if decodable[ref].recomputed_hash != decodable[other].recomputed_hash:
                diffs.extend(structural_diff(ref, decodable[ref].decoded, other, decodable[other].decoded))

    return {
        "analyses": analyses,
        "agree": len(distinct_hashes) <= 1,
        "distinct_hashes": sorted(distinct_hashes),
        "structural_diff": diffs,
    }
