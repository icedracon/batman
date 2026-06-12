from __future__ import annotations

from typing import Any

from .base import Detector, Finding
from .common import (
    evidence_level,
    extract_client_bals,
    rule_refs,
    spec_refs,
)
from ..bal.differential import analyze_client
from ..bal.model import AccountChanges


class BalMixedReadWriteAliasDetector(Detector):
    detector_id = "BAL_MIXED_READ_WRITE_ALIAS"
    title = "BAL mixed read/write alias"

    def run(self, trace: dict[str, Any], ruleset: dict[str, Any] | None = None) -> list[Finding]:
        raw_by_client, declared_by_client, header_hash = extract_client_bals(trace)
        if not raw_by_client:
            return []

        tx_count = int(trace.get("block", {}).get("transaction_count", 0))
        evidence: list[str] = []
        affected_clients: set[str] = set()
        decode_notes: list[str] = []

        for client_id, raw in sorted(raw_by_client.items()):
            analysis = analyze_client(
                client_id,
                raw,
                declared_hash=declared_by_client.get(client_id),
                header_hash=header_hash,
            )
            if not analysis.ok or analysis.decoded is None:
                decode_notes.append(f"{client_id}: skipped undecodable BAL ({analysis.error})")
                continue
            for account in analysis.decoded.accounts:
                overlaps = _account_read_write_aliases(account)
                for slot, indexes in overlaps:
                    affected_clients.add(client_id)
                    phases = sorted({_phase_for_index(index, tx_count) for index in indexes})
                    evidence.append(
                        f"{client_id}: 0x{account.address.hex()} slot {hex(slot)} appears in "
                        f"storage_reads and storage_changes; write_indexes={indexes}; "
                        f"write_phases={phases}"
                    )

        if not evidence:
            return []

        level = evidence_level(trace)
        severity = "high" if level == "live" else "medium"
        if decode_notes:
            evidence.extend(decode_notes)

        return [
            self._finding(
                trace,
                1,
                title="BAL storage slot appears in both reads and writes for the same account",
                severity=severity,
                confidence="high",
                summary=(
                    "Decoded BAL bytes contain at least one account/storage slot that is listed as a "
                    "pure storage read and also as a storage change. This is the mixed read/write alias "
                    "shape that can make clients disagree about whether the read value or post-write "
                    "value belongs in the BAL."
                ),
                evidence=evidence,
                impact=(
                    "On live client output this is a high-signal EIP-7928 conformance issue. "
                    "On synthetic fixtures it is a detector-control signal only and must not be "
                    "treated as a critical bounty finding."
                ),
                recommendation=(
                    "Minimize the account/slot shape, pin client commits, and rerun on a same-head "
                    "private devnet. Escalate through private disclosure only if reproduced on live "
                    "client builds."
                ),
                affected_clients=sorted(affected_clients),
                spec_refs=spec_refs(trace),
                rule_refs=rule_refs(ruleset, self.detector_id),
            )
        ]


def _account_read_write_aliases(account: AccountChanges) -> list[tuple[int, list[int]]]:
    read_slots = set(account.storage_reads)
    aliases = []
    for slot_changes in account.storage_changes:
        if slot_changes.slot not in read_slots:
            continue
        indexes = sorted(change.block_access_index for change in slot_changes.changes)
        aliases.append((slot_changes.slot, indexes))
    return aliases


def _phase_for_index(index: int, tx_count: int) -> str:
    post_index = tx_count + 1
    if index == 0:
        return "pre_execution"
    if 1 <= index <= tx_count:
        return "transaction"
    if index == post_index:
        return "post_execution"
    return "out_of_declared_block_range"

