"""Drive each EL to build a payload, pull its BAL, and diff across clients."""

from __future__ import annotations

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
    fcu = node.forkchoice_updated_v3(forkchoice_state, payload_attributes)
    payload_id = (fcu or {}).get("payloadId")
    if not payload_id:
        return None, "no payloadId (client not building, or forkchoiceUpdated rejected)"
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
