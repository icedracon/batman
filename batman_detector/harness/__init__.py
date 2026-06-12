"""Live differential harness: drive real EL clients over the Engine API and feed
their Block Access Lists into the offline BAL engine.

Flow per client:
    engine_forkchoiceUpdatedV3(head, payload_attributes)  -> payloadId
    engine_getPayloadV6(payloadId)                         -> ExecutionPayloadV4
    extract executionPayload.blockAccessList (RLP hex)     -> bal/differential

The transport is injectable, so the whole path is unit-tested offline with a mock
Engine API; against a live Kurtosis devnet (see devnet/) it talks real JSON-RPC.
"""

from .jwt import load_jwt_secret, make_engine_jwt
from .engine_client import EngineClient, EngineError
from .config import load_endpoints, nodes_from_endpoints
from .runner import build_live_trace, collect_bals, extract_bal_hex, run_live_differential
from .smoke import (
    build_shared_payload_spec,
    latest_head_agreement,
    next_slot_payload_attributes,
    smoke_probe_current_heads,
    wait_for_shared_payload_spec,
)

__all__ = [
    "load_jwt_secret",
    "make_engine_jwt",
    "EngineClient",
    "EngineError",
    "load_endpoints",
    "nodes_from_endpoints",
    "build_live_trace",
    "collect_bals",
    "extract_bal_hex",
    "run_live_differential",
    "latest_head_agreement",
    "next_slot_payload_attributes",
    "smoke_probe_current_heads",
    "build_shared_payload_spec",
    "wait_for_shared_payload_spec",
]
