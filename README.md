# Batman - Glamsterdam BAL detector

[![CI](https://github.com/icedracon/batman/actions/workflows/ci.yml/badge.svg)](https://github.com/icedracon/batman/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

![Batman Glamsterdam BAL detector](docs/assets/social-preview.svg)

Batman is a reproducible cross-client detector for Ethereum's **Glamsterdam** upgrade.
Phase 1 targets **EIP-7928 Block-Level Access Lists (BAL)**: it builds the same block on
multiple execution clients, compares their independently computed BALs, and localizes any
divergence to the exact account / storage slot / `block_access_index`.

## Reviewer snapshot

| What to check | Current public status |
|---|---|
| Scope | Defensive EIP-7928 BAL readiness tooling for Glamsterdam |
| Detectors | `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION`, `BAL_MIXED_READ_WRITE_ALIAS` |
| Evidence | Latest devnet-5: 4-client smoke, 4-way same-head PASS, 0 findings |
| Reproducibility | `python -m batman_detector evidence-pack --output-dir dist/public-evidence --verify` |
| Safety | Local/private devnets only; no mainnet, public RPC, or public vulnerability claims |

Key docs: **[Architecture](docs/ARCHITECTURE.md)** / **[Readiness report](docs/GLAMSTERDAM_BAL_READINESS_REPORT.md)** /
**[Compatibility matrix](docs/COMPATIBILITY_MATRIX.md)** / **[Public evidence workflow](docs/PUBLIC_EVIDENCE.md)** /
**[Grant proposal](docs/grant-proposal.md)** · **[Roadmap](ROADMAP.md)**.

## Demo

![Batman private-devnet BAL workflow demo](docs/assets/batman-demo.svg)

The lightweight animated demo shows the intended reviewer workflow: generate a synthetic
control, run the offline canonicalization campaign, compare execution clients only on a
shared private-devnet head, and export an explicitly selected evidence bundle.

## Why this matters for Ethereum clients

EIP-7928 makes BAL output consensus-adjacent data: execution clients must agree on the exact
canonical bytes and therefore on `block_access_list_hash` for the same block. Small differences
in ordering, duplicate handling, read/write classification, or `block_access_index` assignment
can become cross-client interoperability failures.

Batman focuses on that narrow, high-signal surface. It gives client teams and protocol
researchers a reproducible private-devnet workflow that catches disagreement early, refuses
misleading comparisons when heads do not align, and preserves compact evidence for responsible
private disclosure. More detail: **[docs/WHY_THIS_MATTERS.md](docs/WHY_THIS_MATTERS.md)**.

Open roadmap issues:

- [#2 - enrich compatibility snapshots with pinned image digests](https://github.com/icedracon/batman/issues/2)
- [#3 - compact BAL divergence reproducers](https://github.com/icedracon/batman/issues/3)
- [#4 - promote malformed BAL checks into stable fixtures](https://github.com/icedracon/batman/issues/4)

## Current status

- MIT-licensed, installable Python package with a `batman` CLI.
- 59 unit tests and GitHub Actions CI.
- Latest `glamsterdam-devnet-5` smoke evidence shows all four configured ELs returning BAL bytes.
- 4-way same-head PASS on devnet-5: erigon/nethermind/besu/nimbus returned comparable BALs
  with 0 findings.
- Historical devnet-0 evidence is retained separately because the first public run correctly
  refused a split-head 4-way claim.
- A deterministic offline BAL fuzzer exercises seven ordering mutations plus 13 malformed
  or ambiguous BAL corpus cases.
- A machine-readable compatibility snapshot summarizes client/head/BAL status without
  turning a split-devnet run into a 4-way claim.
- A safe public evidence-pack command emits reviewer inventories and SHA-256 manifests.

## What's real

- **`batman_detector/bal/`** - a real EIP-7928 BAL engine: typed RLP model, encode/decode,
  `block_access_list_hash` (anchored to the spec's empty-BAL constant), a canonical-form
  validator, a cross-client structural differ, fixture generators, and an offline fuzzer.
- **`batman_detector/detectors/BAL_SYSTEM_CONTRACT_INDEX_CONFUSION`** - runs on real decoded
  BAL bytes: per-client canonical + header-hash checks and a structural cross-client diff.
- **`batman_detector/detectors/BAL_MIXED_READ_WRITE_ALIAS`** - runs on decoded BAL bytes
  and flags account/storage slots that appear in both `storage_reads` and `storage_changes`.
  Synthetic fixtures stay medium-severity controls; live/private-devnet evidence can rise
  to high, but not critical without a real cross-client divergence.
- **`batman_detector/harness/`** - JWT-authed Engine API client + runner that drives
  `engine_getPayloadV6` on each EL and feeds the returned BAL into the engine. Mock-tested
  offline; talks real JSON-RPC against a devnet.
- **`batman_detector/compatibility.py`** - builds machine-readable compatibility snapshots
  from public-safe live evidence artifacts.
- **`batman_detector/evidence_bundle.py`** - builds compact public-review bundles from explicit
  artifacts only and rejects secret-looking filenames, symlinks, duplicate output names,
  unsupported extensions, and oversized files.
- **`devnet/`** - a Kurtosis config that stands up a multi-EL Gloas devnet, plus endpoint
  extraction for the harness.

59 unit tests, including an assertion that the codec reproduces the spec's empty-BAL hash,
full mutator coverage for the offline canonicalization campaign, malformed BAL corpus checks,
compatibility snapshot validation, and evidence-bundle safety checks.

## Quick Start

```powershell
python -m pip install -e .
batman --help
```

```powershell
# Unit tests
python -m unittest discover

# Generate a real encoded BAL fixture and scan it - no devnet needed.
# This is synthetic control data, not a bounty-grade live-client finding.
python -m batman_detector.bal.fixtures > examples\traces\bal_system_index_confusion.generated.json
python -m batman_detector run examples\traces\bal_system_index_confusion.generated.json
python -m batman_detector run examples\traces\bal_mixed_read_write_alias.sample.json

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

## Offline canonicalization campaign

```bash
python -m batman_detector.bal.fuzzer \
    --iterations 64 \
    --seed 7928 \
    --include-malformed \
    --format json
```

The campaign mutates account ordering, storage-slot ordering, storage-change indexes,
storage-read ordering, balance-change indexes, nonce-change indexes, and code-change indexes.
It also checks duplicate accounts, duplicate slots, duplicate `block_access_index` entries,
read/write overlap, malformed RLP shapes, and uint boundary failures. No RPC endpoint is contacted.

## Compatibility snapshot

```bash
python -m batman_detector compatibility-snapshot \
    --heads artifacts/devnet5-live-heads.json \
    --smoke artifacts/devnet5-live-smoke.json \
    --four-way-output artifacts/devnet5-live-4way-diff.txt \
    --subset-trace artifacts/devnet5-live-trace.json \
    --subset-report artifacts/devnet5-live-report.md \
    --output artifacts/compatibility-snapshot.gloas-devnet5.json \
    --metadata source=devnet5-maintainer-feedback-refresh
```

The snapshot is machine-readable reviewer evidence: client heads, BAL smoke status,
same-head inclusion, artifact hashes, and safety flags.

## Public evidence bundle

```bash
python -m batman_detector evidence-pack --output-dir dist/public-evidence --verify
```

The generated directory contains copied public-safe artifacts, `manifest.json` with SHA-256
digests, and a reviewer-friendly `README.md`. With `--verify`, Batman also checks source
artifacts, copied hashes, JSON readability, the compatibility snapshot, and the public
evidence claim: latest devnet-5 4-client smoke, 4-way same-head PASS, 0 findings.
Review the directory manually before publication.

## Live differential (needs a Gloas devnet)

See **[devnet/README.md](devnet/README.md)** to stand up the devnet (Docker + Kurtosis,
pin current Gloas/EIP-7928 client images). Then:

```bash
./devnet/endpoints.sh batman-gloas-devnet5         # -> devnet/endpoints.json

# Check whether clients are on the same latest head.
python -m batman_detector bal-heads-live \
    --endpoints devnet/endpoints.json

# Smoke test: each EL builds from its own current head and returns BAL bytes.
python -m batman_detector bal-smoke-live \
    --endpoints devnet/endpoints.json \
    --jwt-secret devnet/jwt_file/jwtsecret \
    --payload-spec devnet/payload-spec.latest.json

# Full same-head differential: wait until latest heads agree, then compare one payload spec.
python -m batman_detector bal-diff-live \
    --endpoints devnet/endpoints.json \
    --jwt-secret devnet/jwt_file/jwtsecret \
    --payload-spec devnet/payload-spec.latest.json \
    --refresh \
    --wait-shared-head 60

# Committed devnet-5 evidence:
# erigon/nethermind/besu/nimbus share a head and return 0 findings.
python -m batman_detector bal-diff-live \
    --endpoints devnet/endpoints.json \
    --jwt-secret devnet/jwt_file/jwtsecret \
    --payload-spec devnet/payload-spec.latest.json \
    --refresh \
    --wait-shared-head 20 \
    --poll-interval 2 \
    --output-trace artifacts/devnet5-live-trace.json \
    --output-report artifacts/devnet5-live-report.md
```

The smoke command answers whether each EL can emit `blockAccessList` bytes at all. The
differential command is stricter: with `--refresh`, Batman only runs it when every client's
latest head agrees, because some Engine API implementations reject building on an older
ancestor after forkchoice has advanced.

For diagnosis only, `--client` and `--exclude-client` can run a clearly scoped subset.
Subset results are useful engineering evidence, but a full bounty-grade claim needs the
intended client set to share the same latest head.

Current committed live evidence:

- [devnet5-live-heads.json](artifacts/devnet5-live-heads.json): latest-head agreement check showing all four devnet-5 ELs on the same head.
- [devnet5-live-smoke.json](artifacts/devnet5-live-smoke.json): 4-client smoke result; every configured EL returned BAL bytes.
- [devnet5-live-4way-diff.txt](artifacts/devnet5-live-4way-diff.txt): same-head 4-way differential output with 0 findings.
- [devnet5-live-trace.json](artifacts/devnet5-live-trace.json): 4-way same-head BAL trace for erigon/nethermind/besu/nimbus.
- [devnet5-live-report.md](artifacts/devnet5-live-report.md): detector report for that trace, with 0 findings.
- [compatibility-snapshot.gloas-devnet5.json](artifacts/compatibility-snapshot.gloas-devnet5.json): machine-readable compatibility snapshot and artifact hashes.

Historical devnet-0 artifacts are still committed as earlier evidence of Batman's split-head
refusal behavior, but the reviewer evidence-pack now uses the fresher devnet-5 4-way pass.

## Maintainer notes

- Security and disclosure policy: [SECURITY.md](SECURITY.md)
- Contribution workflow: [CONTRIBUTING.md](CONTRIBUTING.md)
- Release notes: [CHANGELOG.md](CHANGELOG.md)
- Compatibility matrix: [docs/COMPATIBILITY_MATRIX.md](docs/COMPATIBILITY_MATRIX.md)
- Public evidence workflow: [docs/PUBLIC_EVIDENCE.md](docs/PUBLIC_EVIDENCE.md)
- Why this matters: [docs/WHY_THIS_MATTERS.md](docs/WHY_THIS_MATTERS.md)
- Open roadmap work: [docs/ROADMAP_ISSUES.md](docs/ROADMAP_ISSUES.md)
- GitHub presentation checklist: [docs/GITHUB_POLISH.md](docs/GITHUB_POLISH.md)

## Bounty / disclosure safety

Local/private devnets and fixtures only. Do not test against mainnet, public RPCs, or
third-party infrastructure. Do not publish suspected client vulnerabilities before private
disclosure.
