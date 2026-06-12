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
    next_slot_payload_attributes,
    run_live_differential,
    smoke_probe_current_heads,
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
        if method in {"engine_forkchoiceUpdatedV3", "engine_forkchoiceUpdatedV4"}:
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

    def test_uses_forkchoice_v4_for_amsterdam_payload_attributes(self):
        seen = []

        def transport(method, params):
            seen.append((method, params))
            if method == "engine_forkchoiceUpdatedV4":
                return {"payloadStatus": {"status": "VALID"}, "payloadId": "0x01"}
            if method == "engine_getPayloadV6":
                return {"executionPayload": {"blockAccessList": "0x" + encode_bal(_canonical()).hex()}}
            raise AssertionError(f"unexpected method {method}")

        node = EngineClient("http://geth", transport=transport)
        run_live_differential(
            {"geth": node},
            {"headBlockHash": "0x0"},
            {"timestamp": "0x1", "slotNumber": "0x1", "targetGasLimit": "0x1"},
        )

        self.assertEqual(seen[0][0], "engine_forkchoiceUpdatedV4")
        self.assertEqual(len(seen[0][1]), 2)


class TestConfig(unittest.TestCase):
    def test_nodes_from_endpoints_uses_engine_url(self):
        eps = [{"client_id": "geth", "rpc": "http://r:8545", "engine": "http://e:8551"}]
        nodes = nodes_from_endpoints(eps, jwt_secret=b"\x00" * 32)
        self.assertEqual(nodes["geth"].url, "http://e:8551")

    def test_nodes_from_endpoints_adds_http_scheme(self):
        eps = [{"client_id": "geth", "engine": "127.0.0.1:8551"}]
        nodes = nodes_from_endpoints(eps)
        self.assertEqual(nodes["geth"].url, "http://127.0.0.1:8551")


class TestSmokeProbe(unittest.TestCase):
    def test_next_slot_payload_attributes_tracks_current_head(self):
        attrs = next_slot_payload_attributes(
            {"prevRandao": "0x11", "targetGasLimit": "0x1"},
            {"number": "0x9", "slotNumber": "0x20", "timestamp": "0x64", "gasLimit": "0x2"},
        )
        self.assertEqual(attrs["timestamp"], "0x70")
        self.assertEqual(attrs["slotNumber"], "0x21")
        self.assertEqual(attrs["targetGasLimit"], "0x2")
        self.assertEqual(attrs["prevRandao"], "0x11")

    def test_next_slot_payload_attributes_falls_back_to_block_number(self):
        attrs = next_slot_payload_attributes({}, {"number": "0x9", "timestamp": "0x64"})
        self.assertEqual(attrs["slotNumber"], "0xa")

    def test_smoke_probe_current_heads_returns_bal_status(self):
        bal_hex = "0x" + encode_bal(_canonical()).hex()
        endpoints = [{"client_id": "geth", "rpc": "rpc:8545", "engine": "engine:8551"}]
        nodes = {"geth": EngineClient("http://engine:8551", transport=_fake_transport(bal_hex))}

        def rpc(url, method, params):
            self.assertEqual(url, "rpc:8545")
            self.assertEqual(method, "eth_getBlockByNumber")
            self.assertEqual(params, ["latest", False])
            return {
                "number": "0x5",
                "hash": "0xabc",
                "timestamp": "0xa",
                "gasLimit": "0x100",
                "blockAccessList": [],
            }

        results = smoke_probe_current_heads(
            endpoints,
            payload_attributes={"prevRandao": "0x11", "slotNumber": "0x1", "targetGasLimit": "0x1"},
            nodes=nodes,
            rpc=rpc,
        )

        self.assertEqual(results[0]["client_id"], "geth")
        self.assertEqual(results[0]["head_number"], 5)
        self.assertTrue(results[0]["rpc_has_bal"])
        self.assertTrue(results[0]["engine_has_bal"])
        self.assertGreater(results[0]["engine_bal_bytes"], 0)

    def test_build_shared_payload_spec_picks_common_head(self):
        from batman_detector.harness import build_shared_payload_spec

        endpoints = [
            {"client_id": "geth", "rpc": "geth:8545", "engine": "geth:8551"},
            {"client_id": "reth", "rpc": "reth:8545", "engine": "reth:8551"},
        ]
        latest = {
            "geth:8545": {"number": "0x6", "hash": "0xnewgeth", "timestamp": "0x64", "gasLimit": "0x100"},
            "reth:8545": {"number": "0x5", "hash": "0xnewreth", "timestamp": "0x64", "gasLimit": "0x100"},
        }
        block5 = {"number": "0x5", "hash": "0xshared", "timestamp": "0x60", "gasLimit": "0x100"}

        def rpc(url, method, params):
            if params[0] == "latest":
                return latest[url]
            self.assertEqual(params[0], "0x5")  # common head = min(6, 5)
            return block5

        spec = build_shared_payload_spec(endpoints, seed_attrs={"prevRandao": "0x11"}, rpc=rpc)
        self.assertEqual(spec["shared_head"]["number"], 5)
        self.assertEqual(spec["shared_head"]["hash"], "0xshared")
        self.assertTrue(spec["shared_head"]["agree"])
        self.assertEqual(spec["forkchoice_state"]["headBlockHash"], "0xshared")
        self.assertEqual(spec["payload_attributes"]["prevRandao"], "0x11")
        self.assertEqual(spec["payload_attributes"]["slotNumber"], "0x6")  # 5 + 1
        self.assertEqual(spec["payload_attributes"]["timestamp"], "0x6c")  # 0x60 + 12


class TestLiveTrace(unittest.TestCase):
    def test_build_live_trace_is_schema_valid_and_live(self):
        from batman_detector.harness import build_live_trace
        from batman_detector.schemas import validate_trace

        trace = build_live_trace({"geth": encode_bal(_canonical())})
        validate_trace(trace)  # must not raise
        self.assertEqual(trace["provenance"]["kind"], "live_devnet")

    def test_live_divergence_escalates_to_critical(self):
        from batman_detector.detectors import DETECTORS
        from batman_detector.harness import build_live_trace

        trace = build_live_trace({"geth": encode_bal(_canonical()), "reth": encode_bal(_variant())})
        findings = DETECTORS["BAL_SYSTEM_CONTRACT_INDEX_CONFUSION"]().run(trace)
        self.assertTrue(any(f.severity == "critical" for f in findings))


if __name__ == "__main__":
    unittest.main()
