from __future__ import annotations

import base64
import hashlib
import hmac
import json
import unittest

from batman_detector.bal import (
    AccountChanges,
    BlockAccessList,
    SlotChanges,
    StorageChange,
    encode_bal,
)
from batman_detector.harness import (
    EngineClient,
    extract_bal_hex,
    make_engine_jwt,
    run_live_differential,
)
from batman_detector.harness.config import nodes_from_endpoints

A1 = bytes.fromhex("00000000000000000000000000000000000010aa")


def _canonical():
    return BlockAccessList(accounts=[AccountChanges(address=A1, storage_changes=[
        SlotChanges(slot=7, changes=[StorageChange(0, 1), StorageChange(1, 2), StorageChange(2, 3)])])])


def _variant():
    return BlockAccessList(accounts=[AccountChanges(address=A1, storage_changes=[
        SlotChanges(slot=7, changes=[StorageChange(0, 1), StorageChange(1, 3)])])])


def _b64d(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def _fake_transport(bal_hex: str):
    def transport(method, params):
        if method == "engine_forkchoiceUpdatedV3":
            return {"payloadStatus": {"status": "VALID"}, "payloadId": "0x01"}
        if method == "engine_getPayloadV6":
            return {"executionPayload": {"blockNumber": "0x1", "blockAccessList": bal_hex}}
        raise AssertionError(f"unexpected method {method}")
    return transport


class TestJwt(unittest.TestCase):
    def test_hs256_structure_and_signature(self):
        secret = b"\x01" * 32
        token = make_engine_jwt(secret, iat=1000)
        header_seg, payload_seg, sig_seg = token.split(".")
        self.assertEqual(json.loads(_b64d(header_seg))["alg"], "HS256")
        self.assertEqual(json.loads(_b64d(payload_seg))["iat"], 1000)
        expected = hmac.new(secret, f"{header_seg}.{payload_seg}".encode(), hashlib.sha256).digest()
        self.assertEqual(_b64d(sig_seg), expected)


class TestRunner(unittest.TestCase):
    def test_extract_bal_hex(self):
        self.assertEqual(extract_bal_hex({"executionPayload": {"blockAccessList": "0xab"}}), "0xab")
        self.assertEqual(extract_bal_hex({"blockAccessList": "0xcd"}), "0xcd")
        self.assertIsNone(extract_bal_hex({"executionPayload": {}}))

    def test_live_differential_detects_split(self):
        good = "0x" + encode_bal(_canonical()).hex()
        bad = "0x" + encode_bal(_variant()).hex()
        nodes = {
            "geth": EngineClient("http://geth", transport=_fake_transport(good)),
            "reth": EngineClient("http://reth", transport=_fake_transport(bad)),
        }
        result = run_live_differential(nodes, {"headBlockHash": "0x00"}, {"timestamp": "0x0"})
        self.assertFalse(result["agree"])
        self.assertEqual(result["clients_with_bal"], ["geth", "reth"])
        self.assertTrue(result["structural_diff"])

    def test_client_without_bal_noted_not_fatal(self):
        def no_bal(method, params):
            if method == "engine_forkchoiceUpdatedV3":
                return {"payloadId": "0x01"}
            return {"executionPayload": {"blockNumber": "0x1"}}  # no blockAccessList
        nodes = {"besu": EngineClient("http://besu", transport=no_bal)}
        result = run_live_differential(nodes, {"headBlockHash": "0x0"}, {"timestamp": "0x0"})
        self.assertIn("besu", result["notes"])
        self.assertEqual(result["clients_with_bal"], [])

    def test_agreeing_clients(self):
        same = "0x" + encode_bal(_canonical()).hex()
        nodes = {
            "geth": EngineClient("http://geth", transport=_fake_transport(same)),
            "reth": EngineClient("http://reth", transport=_fake_transport(same)),
        }
        result = run_live_differential(nodes, {"headBlockHash": "0x0"}, {"timestamp": "0x0"})
        self.assertTrue(result["agree"])
        self.assertEqual(result["structural_diff"], [])


class TestConfig(unittest.TestCase):
    def test_nodes_from_endpoints_uses_engine_url(self):
        eps = [{"client_id": "geth", "rpc": "http://r:8545", "engine": "http://e:8551"}]
        nodes = nodes_from_endpoints(eps, jwt_secret=b"\x00" * 32)
        self.assertEqual(nodes["geth"].url, "http://e:8551")


if __name__ == "__main__":
    unittest.main()
