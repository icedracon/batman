"""Drive each EL to build a payload, pull its BAL, and diff across clients."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..bal.differential import cross_client
from .engine_client import EngineClient


def extract_bal_hex(payload_result: Any) -> str | None:
    """Pull the RLP-hex blockAccessList from an engine_getPayloadV6 result.

    Tolerant of envelope shape: {executionPayload: {blockAccessList}} or a flat
    payload, and a couple of plausible key spellings.
    """
    if not isinstance(payload_result, dict):
        return None
    ep = payload_result.get("executionPayload", payload_result)
    if not isinstance(ep, dict):
        return None
    for key in ("blockAccessList", "block_access_list", "bal"):
        value = ep.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def build_and_get_bal(
    node: EngineClient, forkchoice_state: dict, payload_attributes: dict | None
) -> tuple[str | None, str | None]:
    if payload_attributes and {"slotNumber", "targetGasLimit"} <= set(payload_attributes):
        fcu = node.forkchoice_updated_v4(forkchoice_state, payload_attributes, None)
    else:
        fcu = node.forkchoice_updated_v3(forkchoice_state, payload_attributes)
    payload_id = (fcu or {}).get("payloadId")
    if not payload_id:
        payload_status = (fcu or {}).get("payloadStatus")
        return None, f"no payloadId (client not building, or forkchoiceUpdated rejected); response={payload_status}"
    result = node.get_payload_v6(payload_id)
    bal_hex = extract_bal_hex(result)
    if not bal_hex:
        return None, "payload has no blockAccessList (client likely does not implement EIP-7928 yet)"
    return bal_hex, None


def collect_bals(
    nodes: dict[str, EngineClient], forkchoice_state: dict, payload_attributes: dict | None
) -> tuple[dict[str, bytes], dict[str, str]]:
    """Returns (raw BAL bytes per client, per-client notes for those without one)."""
    raw_by_client: dict[str, bytes] = {}
    notes: dict[str, str] = {}
    for client_id, node in nodes.items():
        try:
            bal_hex, err = build_and_get_bal(node, forkchoice_state, payload_attributes)
            if err:
                notes[client_id] = err
                continue
            raw_by_client[client_id] = bytes.fromhex(bal_hex[2:] if bal_hex.startswith("0x") else bal_hex)
        except Exception as exc:  # one flaky node must not sink the run
            notes[client_id] = f"error: {exc}"
    return raw_by_client, notes


def run_live_differential(
    nodes: dict[str, EngineClient],
    forkchoice_state: dict,
    payload_attributes: dict | None,
    header_hash: str | None = None,
) -> dict[str, Any]:
    raw_by_client, notes = collect_bals(nodes, forkchoice_state, payload_attributes)
    if raw_by_client:
        result = cross_client(raw_by_client, header_hash)
    else:
        result = {"agree": True, "analyses": {}, "distinct_hashes": [], "structural_diff": []}
    result["notes"] = notes
    result["clients_with_bal"] = sorted(raw_by_client)
    return result


def build_live_trace(
    raw_by_client: dict[str, bytes],
    header_hash: str | None = None,
    notes: dict[str, str] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Wrap live client BAL bytes in a schema-valid Batman trace stamped with
    `provenance.kind = "live_devnet"`, so the detector treats a real divergence as
    bounty-grade (critical) rather than a synthetic control.
    """
    now = datetime.now(timezone.utc)
    observations = [
        {"kind": "bal_output", "client_id": cid, "bal_rlp": "0x" + raw.hex()}
        for cid, raw in raw_by_client.items()
    ]
    block: dict[str, Any] = {"number": 0, "transaction_count": 0}
    if header_hash:
        block["block_access_list_hash"] = header_hash

    return {
        "schema_version": "batman.trace.v1",
        "trace_id": trace_id or "live-" + now.strftime("%Y%m%dT%H%M%SZ"),
        "created_at": now.isoformat(),
        "target": {
            "fork": "Glamsterdam",
            "eips": ["EIP-7928"],
            "spec_refs": [{
                "name": "EIP-7928 Block-Level Access Lists",
                "url": "https://eips.ethereum.org/EIPS/eip-7928",
            }],
        },
        "environment": {
            "topology": "live kurtosis devnet",
            "clients": [{"id": cid, "layer": "EL", "name": cid} for cid in raw_by_client],
        },
        "scenario": {
            "detector_ids": ["BAL_SYSTEM_CONTRACT_INDEX_CONFUSION"],
            "description": "Live Engine API BAL differential across execution clients.",
            "success_condition": "Live clients return comparable blockAccessList bytes for the same payload attributes.",
        },
        "provenance": {"kind": "live_devnet", "bounty_eligible": True, "client_notes": notes or {}},
        "block": block,
        "events": [],
        "observations": observations,
    }
