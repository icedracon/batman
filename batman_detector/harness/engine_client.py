"""Minimal JSON-RPC client for an EL's Engine API.

Transport is injectable: the default does a real JWT-authed HTTP POST (stdlib
urllib), but tests pass a `transport(method, params) -> result` callable so the
whole harness is verified offline without a node.
"""

from __future__ import annotations

import itertools
import json
import urllib.request
from typing import Any, Callable

from .jwt import make_engine_jwt

Transport = Callable[[str, list], Any]


class EngineError(Exception):
    """Raised when the node returns a JSON-RPC error object."""


class EngineClient:
    def __init__(
        self,
        url: str,
        jwt_secret: bytes | None = None,
        transport: Transport | None = None,
        timeout: int = 15,
    ) -> None:
        self.url = url
        self.jwt_secret = jwt_secret
        self._transport = transport
        self.timeout = timeout
        self._ids = itertools.count(1)

    def call(self, method: str, params: list) -> Any:
        if self._transport is not None:
            return self._transport(method, params)
        return self._http(method, params)

    def _http(self, method: str, params: list) -> Any:
        body = json.dumps(
            {"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params}
        ).encode()
        headers = {"Content-Type": "application/json"}
        if self.jwt_secret:
            headers["Authorization"] = "Bearer " + make_engine_jwt(self.jwt_secret)
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode())
        if data.get("error"):
            raise EngineError(data["error"])
        return data.get("result")

    # ── Engine API methods the harness uses ───────────────────────────────
    def forkchoice_updated_v3(self, forkchoice_state: dict, payload_attributes: dict | None = None) -> Any:
        return self.call("engine_forkchoiceUpdatedV3", [forkchoice_state, payload_attributes])

    def get_payload_v6(self, payload_id: str) -> Any:
        return self.call("engine_getPayloadV6", [payload_id])

    def new_payload_v5(self, *params: Any) -> Any:
        return self.call("engine_newPayloadV5", list(params))
