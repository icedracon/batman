"""Live smoke probes for checking whether each EL can emit BAL bytes."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable

from .config import nodes_from_endpoints
from .engine_client import EngineClient
from .runner import build_and_get_bal

RpcCall = Callable[[str, str, list[Any]], Any]


def _http_url(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return "http://" + url


def rpc_call(url: str, method: str, params: list[Any]) -> Any:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode()
    req = urllib.request.Request(
        _http_url(url),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")


def next_slot_payload_attributes(seed: dict[str, Any], head: dict[str, Any]) -> dict[str, Any]:
    attrs = dict(seed)
    slot_number = head.get("slotNumber", head["number"])
    attrs["timestamp"] = hex(int(head["timestamp"], 16) + 12)
    attrs["slotNumber"] = hex(int(slot_number, 16) + 1)
    if head.get("gasLimit"):
        attrs["targetGasLimit"] = head["gasLimit"]
    return attrs


def build_shared_payload_spec(
    endpoints: list[dict[str, Any]],
    seed_attrs: dict[str, Any] | None = None,
    rpc: RpcCall = rpc_call,
) -> dict[str, Any]:
    """Build a fresh payload spec on a head that ALL clients share.

    This is what turns the smoke probe into a fair (bounty-grade) differential: every
    client is told the same parent head and the same next-slot payload attributes, so
    they all build the *same* block and their BALs are directly comparable. It also
    fixes the "stale fixed spec" problem where a client refuses to build on an old head.

    Returns `shared_head` (number / hash / agree / per-client hashes), plus a
    `forkchoice_state` and `payload_attributes` ready for collect_bals().
    """
    seed = dict(seed_attrs or {})
    heads = {e["client_id"]: rpc(e["rpc"], "eth_getBlockByNumber", ["latest", False]) for e in endpoints}

    # Highest block number every client definitely has (avoids building on a head a
    # lagging client hasn't imported yet).
    common_number = min(int(h["number"], 16) for h in heads.values())
    by_client = {
        e["client_id"]: rpc(e["rpc"], "eth_getBlockByNumber", [hex(common_number), False])
        for e in endpoints
    }
    client_hashes = {cid: b["hash"] for cid, b in by_client.items()}
    shared = by_client[endpoints[0]["client_id"]]

    return {
        "shared_head": {
            "number": common_number,
            "hash": shared["hash"],
            "agree": len(set(client_hashes.values())) == 1,
            "client_hashes": client_hashes,
        },
        "forkchoice_state": {
            "headBlockHash": shared["hash"],
            "safeBlockHash": shared["hash"],
            "finalizedBlockHash": shared["hash"],
        },
        "payload_attributes": next_slot_payload_attributes(seed, shared),
    }


def smoke_probe_current_heads(
    endpoints: list[dict[str, Any]],
    jwt_secret: bytes | None = None,
    payload_attributes: dict[str, Any] | None = None,
    nodes: dict[str, EngineClient] | None = None,
    rpc: RpcCall = rpc_call,
) -> list[dict[str, Any]]:
    """Build one payload from each client's own current head.

    This is intentionally a smoke test, not a cross-client differential: heads may
    differ on an active devnet, so the result only answers whether each client can
    build a payload and return `executionPayload.blockAccessList`.
    """
    seed_attrs = payload_attributes or {}
    engine_nodes = nodes or nodes_from_endpoints(endpoints, jwt_secret=jwt_secret)
    results: list[dict[str, Any]] = []

    for entry in endpoints:
        client_id = entry["client_id"]
        result: dict[str, Any] = {"client_id": client_id}
        try:
            head = rpc(entry["rpc"], "eth_getBlockByNumber", ["latest", False])
            result["head_number"] = int(head["number"], 16)
            result["head_hash"] = head["hash"]
            result["rpc_has_bal"] = "blockAccessList" in head and head["blockAccessList"] is not None

            forkchoice_state = {
                "headBlockHash": head["hash"],
                "safeBlockHash": head["hash"],
                "finalizedBlockHash": head["hash"],
            }
            attrs = next_slot_payload_attributes(seed_attrs, head)
            bal_hex, note = build_and_get_bal(engine_nodes[client_id], forkchoice_state, attrs)
            result["engine_has_bal"] = bal_hex is not None
            if bal_hex:
                hex_body = bal_hex[2:] if bal_hex.startswith("0x") else bal_hex
                result["engine_bal_bytes"] = len(hex_body) // 2
            if note:
                result["note"] = note
        except Exception as exc:
            result["engine_has_bal"] = False
            result["error"] = str(exc)
        results.append(result)

    return results
