# Batman - Glamsterdam BAL detector

Batman is a reproducible cross-client detector for Ethereum's **Glamsterdam** upgrade.
Phase 1 targets **EIP-7928 Block-Level Access Lists (BAL)**: it builds the same block on
multiple execution clients, compares their independently computed BALs, and localizes any
divergence to the exact account / storage slot / `block_access_index`.

Architecture and scope: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** (authoritative).
The PDF in `docs/` is an early ChatGPT brainstorm and is **superseded** by that document.

## What's real

- **`batman_detector/bal/`** - a real EIP-7928 BAL engine: typed RLP model, encode/decode,
  `block_access_list_hash` (anchored to the spec's empty-BAL constant), a canonical-form
  validator, a cross-client structural differ, and fixture generators.
- **`batman_detector/detectors/BAL_SYSTEM_CONTRACT_INDEX_CONFUSION`** - runs on real decoded
  BAL bytes: per-client canonical + header-hash checks and a structural cross-client diff.
- **`batman_detector/harness/`** - JWT-authed Engine API client + runner that drives
  `engine_getPayloadV6` on each EL and feeds the returned BAL into the engine. Mock-tested
  offline; talks real JSON-RPC against a devnet.
- **`devnet/`** - a Kurtosis config that stands up a multi-EL Gloas devnet, plus endpoint
  extraction for the harness.

39 unit tests, including an assertion that the codec reproduces the spec's empty-BAL hash.

## Quick Start

```powershell
# Unit tests
python -m unittest discover

# Generate a real encoded BAL fixture and scan it - no devnet needed.
# This is synthetic control data, not a bounty-grade live-client finding.
python -m batman_detector.bal.fixtures > examples\traces\bal_system_index_confusion.generated.json
python -m batman_detector run examples\traces\bal_system_index_confusion.generated.json

# Schema validation / detector listing / pre-scan
python -m batman_detector validate examples\traces\bal_system_index_confusion.generated.json
python -m batman_detector list-detectors
python -m batman_detector static-scan examples\audit_targets\bal_first_scan.sample.json
```

The generated scan yields a high-confidence synthetic-control finding localizing an
index-confusion split, e.g.:

```
slot 0x7: change list differs [(0, 1), (1, 2), (2, 3)] vs [(0, 1), (1, 3)]
```

Only traces with live/private-devnet provenance are allowed to escalate cross-client
BAL divergence to critical severity.

## Live differential (needs a Gloas devnet)

See **[devnet/README.md](devnet/README.md)** to stand up the devnet (Docker + Kurtosis,
pin current Gloas/EIP-7928 client images). Then:

```bash
./devnet/endpoints.sh batman-gloas                 # -> devnet/endpoints.json

# Smoke test: each EL builds from its own current head and returns BAL bytes.
python -m batman_detector bal-smoke-live \
    --endpoints devnet/endpoints.json \
    --jwt-secret devnet/jwt_file/jwtsecret \
    --payload-spec devnet/payload-spec.latest.json

# Differential test: compare clients on one forkchoice/payload spec.
python -m batman_detector bal-diff-live \
    --endpoints devnet/endpoints.json \
    --jwt-secret devnet/jwt_file/jwtsecret \
    --payload-spec <forkchoice+attributes.json>
```

The smoke command answers whether each EL can emit `blockAccessList` bytes at all. The
differential command is stricter: it only becomes bounty-grade when every client builds from
the same forkchoice and payload attributes.

## Bounty / disclosure safety

Local/private devnets and fixtures only. Do not test against mainnet, public RPCs, or
third-party infrastructure. Do not publish suspected client vulnerabilities before private
disclosure.
