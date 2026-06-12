# Batman — Architecture (authoritative)

> This is the authoritative architecture for Batman. It describes what the current
> tool actually is, what it does, and which roadmap items are still out of scope.

## What Batman is

A security detector for Ethereum's **Glamsterdam** upgrade. Phase 1 targets
**EIP-7928 Block-Level Access Lists (BAL)** via cross-client differential testing:
build the same block on multiple execution clients, compare their independently
computed BALs, and localize any divergence to the exact account / storage slot /
`block_access_index`.

**Scope honesty.** The broader vision (a consensus-layer ePBS + BAL scanner across
a full CL×EL matrix) is a multi-engineer effort. This repo deliberately ships the
one solo-tractable, high-signal wedge first — `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION`,
which the original sketch itself called the "best pure-EL, differential-test-friendly"
detector. Everything beyond that is roadmap, not a commitment.

## Why BAL differential is worth a detector

EIP-7928 makes every block carry a BAL — the complete set of accounts/slots touched
with their post-values — committed via `block_access_list_hash` and exchanged over
`engine_newPayloadV5`. A conforming BAL must be **canonical** (strict ordering +
uniqueness) and **identical** across clients. Two concrete break modes:

1. **Canonicalization** — a client orders or dedupes differently → different bytes →
   different hash → a header/consensus split.
2. **Index confusion** — the `block_access_index` phases (`0` pre-exec system,
   `1..n` transactions, `n+1` post-exec system) can be merged or misassigned when the
   same account/slot is touched across phases.

Both are spec-grounded and testable on a **single block** — no live consensus needed,
which is exactly why a solo researcher can attack them.

## Components

```
              EIP-7928 spec (pinned in manifests / spec_refs)
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   bal/ (offline engine)  harness/ (live)      devnet/ (infra)
     model.py    RLP        engine_client.py     glamsterdam-devnet.yaml
     codec.py    hash       (JWT + JSON-RPC)     (Kurtosis, gloas_fork_epoch=0)
     canonical.py order     runner.py            endpoints.sh → endpoints.json
     differential.py diff   (getPayloadV6→BAL)
     fixtures.py  gen       config.py
        │                     │
        └──────────┬──────────┘
                   ▼
   detectors/BAL_SYSTEM_CONTRACT_INDEX_CONFUSION
                   ▼
   findings (severity, localized evidence, spec_refs, rule_refs)
                   ▼
   cli.py  /  reporting.py (private first-scan report)
```

## Live data flow

For each EL Engine API endpoint:

1. `engine_forkchoiceUpdatedV3(head, payloadAttributes)` → `payloadId`
2. `engine_getPayloadV6(payloadId)` → `ExecutionPayloadV4` (carries `blockAccessList`)
3. decode the BAL bytes → check canonical form → recompute `keccak(bytes)` and compare
   to the header `block_access_list_hash`
4. **cross-client**: a structural diff localizes any split to the exact slot/index

The transport is injectable, so this whole path is unit-tested offline with a mock
Engine API; against a live devnet it speaks real JWT-authed JSON-RPC.

## EIP-7928 ground truth (the pin)

RLP (not SSZ):

```
AccountChanges  = [address, storage_changes, storage_reads,
                   balance_changes, nonce_changes, code_changes]
BlockAccessList = List[AccountChanges]
BlockAccessIndex (uint32): 0 = pre-exec system, 1..n = txs, n+1 = post-exec system
block_access_list_hash = keccak256(rlp(bal))
empty BAL hash = 0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347
```

The empty-BAL hash is asserted in the test suite, so the codec is wired to the real
spec hash rule. Batman also keeps an experimental `WordEncoding` switch around
uint256 byte layout to make encoding drift easy to test, but only the currently
pinned EIP-7928 form should be treated as normative.

## Implemented vs pending

| | Status |
|---|---|
| `bal/` engine (model, codec, canonical, differential, fixtures) | ✅ implemented, tested |
| detector on real decoded bytes | ✅ implemented, tested |
| `harness/` (JWT, Engine client, runner, CLI `bal-diff-live`) | ✅ implemented, mock-tested |
| `devnet/` Kurtosis config + endpoint extraction | ✅ written, YAML validated |
| **live validation on a real devnet** | ⏳ needs Gloas EL images that emit BALs |

**Open empirical question:** which ELs actually emit a `blockAccessList` at the current
Glamsterdam devnet stage. The harness reports per-client whether a BAL came back, so
the first live run answers this directly.

## Spec pinning

Gloas / EIP-7928 is a moving draft. Every trace and finding carries `spec_refs`, and a
ruleset manifest pins the rules a run targeted. Pin exact client **image digests** and
the **spec commit** in every run so results stay reproducible as the spec changes.

## Safety / disclosure

Local/private devnets only — never mainnet, public RPCs, or third-party infra.
Suspected client bugs go through **private disclosure** before any public mention.
Synthetic fixtures are controls: they can prove Batman localizes a bug class, but
they are never bounty-grade evidence until reproduced against live client builds.

## Roadmap

- **Phase 1 (this repo):** `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION` + harness + devnet.
- **Next, still solo-tractable (EL-side):** `BAL_MIXED_READ_WRITE_ALIAS`
  (reads-vs-changes classification), a BAL canonicalization fuzzer (mutate
  orderings/encodings and assert clients converge).
- **Later, multi-person (from the original sketch):** ePBS detectors — parent-status
  drift, absent-vs-negative PTC collapse, pending-payment epoch shadow — and BAL
  post-state contamination. These need a full CL+EL devnet with internal
  instrumentation, and are treated as vision, not commitments.
