from __future__ import annotations

from collections import defaultdict
from typing import Any

from .base import Detector, Finding


class BalSystemContractIndexConfusionDetector(Detector):
    detector_id = "BAL_SYSTEM_CONTRACT_INDEX_CONFUSION"
    title = "BAL system-contract index confusion"

    def run(self, trace: dict[str, Any], ruleset: dict[str, Any] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        tx_count = int(trace.get("block", {}).get("transaction_count", 0))
        spec_refs = _spec_refs(trace)
        rule_refs = _rule_refs(ruleset, self.detector_id)

        phase_errors = _find_phase_index_errors(trace.get("events", []), tx_count)
        if phase_errors:
            findings.append(
                self._finding(
                    trace,
                    len(findings) + 1,
                    title="BAL entries use phase-inconsistent block_access_index values",
                    severity="medium",
                    confidence="high",
                    summary=(
                        "One or more BAL access events use an index that does not match "
                        "the declared phase. This can hide fixture bugs or expose client "
                        "canonicalization ambiguity."
                    ),
                    evidence=phase_errors,
                    impact=(
                        "A malformed or ambiguously encoded BAL fixture can produce noisy "
                        "results unless phase/index invariants are enforced first."
                    ),
                    recommendation=(
                        "Normalize fixture generation so pre-execution uses index 0, "
                        "transactions use 1..n, and post-execution or withdrawals use n+1."
                    ),
                    spec_refs=spec_refs,
                    rule_refs=rule_refs,
                )
            )

        overlap_evidence = _find_cross_phase_overlaps(trace.get("events", []))
        if overlap_evidence:
            findings.append(
                self._finding(
                    trace,
                    len(findings) + 1,
                    title="Same BAL key is touched across system and transaction phases",
                    severity="medium",
                    confidence="medium",
                    summary=(
                        "The trace stresses the same account/storage key across pre/post "
                        "system phases and transaction phases, which is the intended surface "
                        "for index canonicalization bugs."
                    ),
                    evidence=overlap_evidence,
                    impact=(
                        "This is a high-value fixture shape. By itself it is not a vulnerability; "
                        "it becomes bounty-relevant if clients disagree on BAL bytes, hash, "
                        "validity, or resulting block validity."
                    ),
                    recommendation=(
                        "Run this exact fixture across execution clients and record each "
                        "client's BAL hash, payload status, and state/block hash."
                    ),
                    spec_refs=spec_refs,
                    rule_refs=rule_refs,
                )
            )

        mismatch = _find_client_bal_mismatch(trace.get("observations", []))
        if mismatch:
            findings.append(
                self._finding(
                    trace,
                    len(findings) + 1,
                    title="Execution clients disagree on BAL output or validity",
                    severity="high",
                    confidence="high",
                    summary=(
                        "Client observations contain different BAL hashes or validity statuses "
                        "for the same fixture. If reproduced on current fork code, this is the "
                        "core signal for a consensus-split-class report."
                    ),
                    evidence=mismatch["evidence"],
                    impact=(
                        "A block accepted by one execution client and rejected or canonicalized "
                        "differently by another can create consensus risk once the fork rules "
                        "are live or accepted for a public testnet."
                    ),
                    recommendation=(
                        "Minimize the fixture, pin exact client commits, rerun on clean local "
                        "devnets, then submit privately if the mismatch is real."
                    ),
                    affected_clients=mismatch["affected_clients"],
                    spec_refs=spec_refs,
                    rule_refs=rule_refs,
                )
            )

        return findings


def _spec_refs(trace: dict[str, Any]) -> list[str]:
    refs = []
    for ref in trace.get("target", {}).get("spec_refs", []):
        if isinstance(ref, dict):
            name = ref.get("name", "spec")
            url = ref.get("url", "")
            commit = ref.get("commit", "")
            refs.append(" ".join(part for part in [name, url, commit] if part))
    return refs


def _rule_refs(ruleset: dict[str, Any] | None, detector_id: str) -> list[str]:
    if not ruleset:
        return []
    refs = []
    for rule in ruleset.get("rules", []):
        if rule.get("detector_id") == detector_id:
            refs.append(rule.get("rule_id", "unknown-rule"))
    return refs


def _find_phase_index_errors(events: list[dict[str, Any]], tx_count: int) -> list[str]:
    evidence = []
    post_index = tx_count + 1
    for event in events:
        if event.get("kind") != "bal_access":
            continue
        phase = event.get("phase")
        index = event.get("block_access_index")
        event_id = event.get("event_id", "<unknown>")
        if not isinstance(index, int):
            evidence.append(f"{event_id}: block_access_index is not an integer")
            continue
        if phase == "pre_execution" and index != 0:
            evidence.append(f"{event_id}: pre_execution must use index 0, got {index}")
        elif phase == "transaction" and not (1 <= index <= tx_count):
            evidence.append(f"{event_id}: transaction must use index 1..{tx_count}, got {index}")
        elif phase in {"post_execution", "withdrawal"} and index != post_index:
            evidence.append(f"{event_id}: {phase} must use index {post_index}, got {index}")
        elif phase not in {"pre_execution", "transaction", "post_execution", "withdrawal"}:
            evidence.append(f"{event_id}: unknown BAL phase {phase!r}")
    return evidence


def _find_cross_phase_overlaps(events: list[dict[str, Any]]) -> list[str]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("kind") != "bal_access":
            continue
        account = event.get("account")
        slot = event.get("storage_slot", "<account>")
        if account:
            grouped[(account.lower(), str(slot).lower())].append(event)

    evidence = []
    for (account, slot), accesses in grouped.items():
        phases = {access.get("phase") for access in accesses}
        has_system = bool(phases & {"pre_execution", "post_execution", "withdrawal"})
        has_tx = "transaction" in phases
        if has_system and has_tx:
            ids = ", ".join(str(access.get("event_id", "<unknown>")) for access in accesses)
            phase_list = ", ".join(sorted(str(phase) for phase in phases))
            evidence.append(f"{account}/{slot}: phases={phase_list}; events={ids}")
    return evidence


def _find_client_bal_mismatch(observations: list[dict[str, Any]]) -> dict[str, Any] | None:
    bal_outputs = [item for item in observations if item.get("kind") == "bal_output"]
    if len(bal_outputs) < 2:
        return None

    status_by_client = {
        item.get("client_id", "<unknown>"): item.get("status", "<missing>") for item in bal_outputs
    }
    hash_by_client = {
        item.get("client_id", "<unknown>"): item.get("bal_hash", "<missing>") for item in bal_outputs
    }

    statuses = set(status_by_client.values())
    hashes = set(hash_by_client.values())
    if len(statuses) <= 1 and len(hashes) <= 1:
        return None

    evidence = []
    for client_id in sorted(status_by_client):
        evidence.append(
            f"{client_id}: status={status_by_client[client_id]}, bal_hash={hash_by_client[client_id]}"
        )

    return {
        "affected_clients": sorted(status_by_client),
        "evidence": evidence,
    }

