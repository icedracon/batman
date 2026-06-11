from __future__ import annotations

from collections import defaultdict
from typing import Any

from .base import Detector, Finding
from ..bal.differential import cross_client


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

        # When real BAL bytes are attached, the real-bytes path below supersedes
        # the legacy hash-only mismatch check (avoid double-reporting one split).
        raw_by_client, declared_by_client, header_hash = _extract_client_bals(trace)

        mismatch = None if raw_by_client else _find_client_bal_mismatch(trace.get("observations", []))
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

        # ── Real path: decode actual client BAL bytes and diff them ──────────
        if raw_by_client:
            findings.extend(
                self._real_bal_findings(
                    trace,
                    cross_client(raw_by_client, header_hash, declared_by_client),
                    start_ordinal=len(findings) + 1,
                    spec_refs=spec_refs,
                    rule_refs=rule_refs,
                )
            )

        return findings

    def _real_bal_findings(
        self,
        trace: dict[str, Any],
        result: dict[str, Any],
        *,
        start_ordinal: int,
        spec_refs: list[str],
        rule_refs: list[str],
    ) -> list[Finding]:
        findings: list[Finding] = []
        ordinal = start_ordinal

        for client_id, analysis in sorted(result["analyses"].items()):
            if not analysis.ok:
                findings.append(self._finding(
                    trace, ordinal,
                    title=f"Client {client_id} emitted an undecodable BAL",
                    severity="high", confidence="high",
                    summary=f"Raw BAL bytes from {client_id} failed EIP-7928 RLP decoding.",
                    evidence=[f"{client_id}: {analysis.error}"],
                    impact="A client producing malformed BAL bytes is rejected by conforming peers — a consensus-relevant split.",
                    recommendation="Capture the exact engine_getPayloadV6 bytes, minimize, and confirm the decode failure.",
                    affected_clients=[client_id], spec_refs=spec_refs, rule_refs=rule_refs,
                ))
                ordinal += 1
                continue

            if analysis.canonical_violations:
                findings.append(self._finding(
                    trace, ordinal,
                    title=f"Client {client_id} emitted a non-canonical BAL",
                    severity="high", confidence="high",
                    summary=f"{client_id}'s BAL violates EIP-7928 canonical ordering/uniqueness, which changes block_access_list_hash for identical accesses.",
                    evidence=[f"{client_id}: {item}" for item in analysis.canonical_violations],
                    impact="Non-canonical ordering yields a different BAL hash than a canonical client — a cross-client hash split.",
                    recommendation="Pin the client commit; confirm whether it canonicalizes per spec; disclose privately if reproduced.",
                    affected_clients=[client_id], spec_refs=spec_refs, rule_refs=rule_refs,
                ))
                ordinal += 1

            if analysis.header_matches is False:
                findings.append(self._finding(
                    trace, ordinal,
                    title=f"Client {client_id}: BAL body does not match header block_access_list_hash",
                    severity="high", confidence="high",
                    summary=f"keccak(BAL bytes) for {client_id} differs from the declared block header hash.",
                    evidence=[f"{client_id}: keccak(bal)={analysis.recomputed_hash} header={analysis.header_hash}"],
                    impact="A header committing to a different BAL than the body is invalid — a direct consensus signal.",
                    recommendation="Re-capture the BAL bytes and header from the same payload; check for serialization drift.",
                    affected_clients=[client_id], spec_refs=spec_refs, rule_refs=rule_refs,
                ))
                ordinal += 1

        if not result["agree"]:
            findings.append(self._finding(
                trace, ordinal,
                title="Execution clients produced different BAL bytes for the same block",
                severity="critical", confidence="high",
                summary="Decoded BALs from the client set do not all hash-agree; the structural diff localizes the split.",
                evidence=result["structural_diff"] or [f"distinct BAL hashes: {result['distinct_hashes']}"],
                impact="A real cross-client BAL divergence on live fork code is a consensus-split-class bug.",
                recommendation="Minimize to the smallest diverging access, pin client commits, rerun on a clean local devnet, disclose privately.",
                affected_clients=sorted(result["analyses"]), spec_refs=spec_refs, rule_refs=rule_refs,
            ))

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


def _extract_client_bals(
    trace: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, str], str | None]:
    """Pull real BAL bytes out of `bal_output` observations that carry `bal_rlp`."""
    raw_by_client: dict[str, bytes] = {}
    declared_by_client: dict[str, str] = {}
    for obs in trace.get("observations", []):
        if not isinstance(obs, dict) or obs.get("kind") != "bal_output":
            continue
        rlp_hex = obs.get("bal_rlp")
        client_id = obs.get("client_id", "<unknown>")
        if not isinstance(rlp_hex, str) or not rlp_hex:
            continue
        try:
            raw_by_client[client_id] = bytes.fromhex(rlp_hex[2:] if rlp_hex.startswith("0x") else rlp_hex)
        except ValueError:
            continue
        if obs.get("bal_hash"):
            declared_by_client[client_id] = obs["bal_hash"]
    header_hash = trace.get("block", {}).get("block_access_list_hash")
    return raw_by_client, declared_by_client, header_hash

