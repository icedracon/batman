# Batman - Architecture (authoritative)

> This is the authoritative architecture for Batman. It describes what the current
> tool actually is, what it does, and which roadmap items are still out of scope.

## What Batman is

Batman is a security detector for Ethereum's **Glamsterdam** upgrade. Phase 1
targets **EIP-7928 Block-Level Access Lists (BAL)** via cross-client differential
testing: build the same block on multiple execution clients, compare their
independently computed BALs, and localize divergence to the exact account,
storage slot, and `block_access_index`.

**Scope honesty.** The broader vision, including consensus-layer ePBS checks and
a full CL/EL matrix, is a multi-engineer effort. This repo deliberately ships two
solo-tractable, high-signal decoded-BAL detectors first:
`BAL_SYSTEM_CONTRACT_INDEX_CONFUSION` and `BAL_MIXED_READ_WRITE_ALIAS`.
Everything beyond decoded-BAL EL-side checks remains roadmap, not a commitment.

## Why BAL differential is worth a detector

EIP-7928 makes every block carry a BAL: the complete set of accounts and slots
touched with their post-values, committed via `block_access_list_hash` and
exchanged over the Engine API. A conforming BAL must be canonical and identical
across clients. Three concrete Phase-1 break modes are covered:

1. **Canonicalization** - a client orders or dedupes differently, producing
   different bytes and therefore a different hash.
2. **Index confusion** - the `block_access_index` phases (`0` pre-exec system,
   `1..n` transactions, `n+1` post-exec system) can be merged or misassigned
   when the same account/slot is touched across phases.
3. **Mixed read/write aliasing** - the same account/storage slot appears in both
   `storage_reads` and `storage_changes`, creating ambiguity over read-vs-post-write
   BAL classification across pre-exec, transaction, and post-exec phases.

These are spec-grounded and testable on a single block. Synthetic controls prove
detector behavior, but live/private-devnet outputs are required before any real
client finding is treated as bounty-grade.

## Components

```text
              EIP-7928 spec (pinned in manifests / spec_refs)
                              |
        +---------------------+---------------------+
        v                     v                     v
   bal/ (offline engine)  harness/ (live)      devnet/ (infra)
     model.py    RLP        engine_client.py     glamsterdam-devnet.yaml
     codec.py    hash       (JWT + JSON-RPC)     (Kurtosis, gloas_fork_epoch=0)
     canonical.py order     runner.py            endpoints.sh -> endpoints.json
     differential.py diff   (getPayloadV6 -> BAL)
     fixtures.py  gen       config.py
        |                     |
        +----------+----------+
                   v
   detectors/
     BAL_SYSTEM_CONTRACT_INDEX_CONFUSION
     BAL_MIXED_READ_WRITE_ALIAS
                   v
   findings (severity, localized evidence, spec_refs, rule_refs)
                   v
   cli.py / reporting.py (private first-scan report)
```

## Live data flow

For each EL Engine API endpoint:

1. `engine_forkchoiceUpdatedV3/V4(head, payloadAttributes)` returns a `payloadId`.
2. `engine_getPayloadV6(payloadId)` returns an execution payload carrying `blockAccessList`.
3. Batman decodes BAL bytes, checks canonical form, recomputes `keccak(bytes)`, and
   compares it to any declared/header BAL hash.
4. Cross-client structural diff localizes splits to the account, slot, index, or category.
5. Phase-1 detectors inspect the decoded BAL for index-confusion and mixed read/write
   alias shapes.

The transport is injectable, so the path is unit-tested offline with a mock Engine API.
Against a live devnet it speaks real JWT-authenticated JSON-RPC.

## EIP-7928 ground truth

RLP, not SSZ:

```text
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

| Area | Status |
|---|---|
| `bal/` engine (model, codec, canonical, differential, fixtures) | implemented, tested |
| decoded-BAL Phase-1 detectors | 2 implemented, tested |
| `harness/` (JWT, Engine client, runner, CLI `bal-diff-live`) | implemented, mock-tested |
| `devnet/` Kurtosis config + endpoint extraction | written, YAML validated |
| live smoke on a real Gloas devnet | 4 configured ELs returned BAL bytes |
| live same-head differential | 3-way same-head PASS; full 4-way refused on current devnet split |

Current committed live evidence shows geth, erigon, reth, and nethermind all returning
`blockAccessList` bytes in the smoke path. The stricter 4-way differential is correctly
refused on the current devnet split because all latest heads do not agree. The committed
subset evidence is therefore a scoped 3-way same-head pass with 0 findings, not a full
4-way bounty claim.

## Spec pinning

Gloas / EIP-7928 is a moving draft. Every trace and finding carries `spec_refs`, and a
ruleset manifest pins the rules a run targeted. Pin exact client image digests and the
spec commit in every run so results stay reproducible as the spec changes.

## Safety / disclosure

Local/private devnets only. Do not test mainnet, public RPC providers, or third-party
infrastructure. Suspected client bugs go through private disclosure before any public
mention. Synthetic fixtures are controls: they can prove Batman localizes a bug class,
but they are never bounty-grade evidence until reproduced against live client builds.

## Roadmap

- **Phase 1 (this repo):** `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION`,
  `BAL_MIXED_READ_WRITE_ALIAS`, harness, devnet, compatibility snapshots, and
  offline BAL canonicalization/malformed corpus checks.
- **Next, still solo-tractable (EL-side):** fixture minimization and stable corpus
  IDs for malformed/index/alias cases.
- **Later, multi-person:** ePBS detectors, parent-status drift, absent-vs-negative
  PTC collapse, pending-payment epoch shadow, and broader CL+EL instrumentation.
