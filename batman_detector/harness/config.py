"""Load devnet/endpoints.json (written by devnet/endpoints.sh) into EngineClients."""

from __future__ import annotations

import json
from pathlib import Path

from .engine_client import EngineClient, Transport


def load_endpoints(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("endpoints file must be a JSON list of {client_id, rpc, engine}")
    return data


def _http_url(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return "http://" + url


def nodes_from_endpoints(
    endpoints: list[dict],
    jwt_secret: bytes | None = None,
    transport: Transport | None = None,
) -> dict[str, EngineClient]:
    nodes: dict[str, EngineClient] = {}
    for entry in endpoints:
        client_id = entry["client_id"]
        url = entry.get("engine") or entry.get("rpc")
        if not url:
            raise ValueError(f"endpoint {client_id} has neither engine nor rpc URL")
        nodes[client_id] = EngineClient(_http_url(url), jwt_secret=jwt_secret, transport=transport)
    return nodes
