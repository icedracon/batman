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
from .runner import collect_bals, extract_bal_hex, run_live_differential

__all__ = [
    "load_jwt_secret",
    "make_engine_jwt",
    "EngineClient",
    "EngineError",
    "load_endpoints",
    "nodes_from_endpoints",
    "collect_bals",
    "extract_bal_hex",
    "run_live_differential",
]
