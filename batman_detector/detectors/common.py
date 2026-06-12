from __future__ import annotations

from typing import Any


# Provenance kinds that count as real client evidence. Synthetic/imported traces
# are controls and must not be treated as critical bounty-grade evidence.
LIVE_PROVENANCE_KINDS = {"live_devnet", "live_client", "private_devnet"}


def spec_refs(trace: dict[str, Any]) -> list[str]:
    refs = []
    for ref in trace.get("target", {}).get("spec_refs", []):
        if isinstance(ref, dict):
            name = ref.get("name", "spec")
            url = ref.get("url", "")
            commit = ref.get("commit", "")
            refs.append(" ".join(part for part in [name, url, commit] if part))
    return refs


def evidence_level(trace: dict[str, Any]) -> str:
    provenance = trace.get("provenance", {})
    if not isinstance(provenance, dict):
        return "unknown"
    if provenance.get("kind") in LIVE_PROVENANCE_KINDS:
        return "live"
    return "synthetic"


def rule_refs(ruleset: dict[str, Any] | None, detector_id: str) -> list[str]:
    if not ruleset:
        return []
    refs = []
    for rule in ruleset.get("rules", []):
        if rule.get("detector_id") == detector_id:
            refs.append(rule.get("rule_id", "unknown-rule"))
    return refs


def extract_client_bals(
    trace: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, str], str | None]:
    """Pull raw BAL bytes out of `bal_output` observations that carry `bal_rlp`."""
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

