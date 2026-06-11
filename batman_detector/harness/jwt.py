"""HS256 JWT for Engine API authentication.

Geth/Reth/Nethermind/Erigon gate the Engine API (port 8551) behind a JWT signed
with a shared 32-byte secret. The ethereum-package writes that secret into the
enclave; load it with `load_jwt_secret`. Only an `iat` claim is required.

Hand-rolled with the stdlib (hmac/hashlib/base64) — no third-party dependency.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_engine_jwt(secret: bytes, iat: int | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"iat": int(time.time()) if iat is None else iat}
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64url(json.dumps(payload, separators=(",", ":")).encode())
    )
    sig = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return signing_input + "." + _b64url(sig)


def load_jwt_secret(path: str | Path) -> bytes:
    text = Path(path).read_text(encoding="utf-8").strip()
    if text.startswith("0x"):
        text = text[2:]
    return bytes.fromhex(text)
