# Batman: Open-Source Glamsterdam BAL Differential Testing & Impact Analysis Toolkit

> Draft for the **EF Glamsterdam Grants Round** (ESP wishlist). Framing: open-source
> upgrade-readiness tooling for **EIP-7928 Block-Level Access Lists** — developer
> tooling, impact analysis, and data-driven research. **Not** a bug-bounty play.
>
> Round: https://esp.ethereum.foundation/applicants/wishlist/glamsterdam-round/apply
> Scope EIP: EIP-7928 (Scheduled for Inclusion per EIP-7773).

## Summary

Batman is an open-source toolkit for preparing the Ethereum ecosystem for
Glamsterdam's **Block-Level Access Lists (EIP-7928)**. It stands up multi-client
Glamsterdam/Gloas devnets, extracts each client's BAL through the Engine API,
performs **cross-client differential analysis** with a spec-anchored RLP engine,
and produces reproducible reports that help client teams, auditors, app developers,
block explorers/indexers, and researchers detect BAL inconsistencies **before
deployment**. This grant turns a working prototype into a documented, one-command
readiness tool with fuzzing scenarios, public fixtures, CI, and research reports.

## Problem

EIP-7928 makes every block carry a BAL whose `block_access_list_hash` is committed
in the header — so a BAL is **consensus-critical** and must be byte-identical and
canonical across all execution clients. Two concrete risks: (1) canonicalization
divergence (a client orders/dedupes differently → different bytes → different hash →
a split), and (2) `block_access_index` phase confusion (pre-exec `0` / tx `1..n` /
post-exec `n+1` merged or misassigned), and (3) mixed read/write aliasing where
the same slot appears in both `storage_reads` and `storage_changes`. Today there is no focused, open, live
**cross-client BAL conformance** tool, and app developers / indexers / auditors lack
a way to see BAL behavior and impact before mainnet.

## What already exists (working prototype, this repo)

- **Spec-anchored EIP-7928 RLP engine** (`bal/`): typed model, encode/decode,
  `block_access_list_hash`, with a test asserting the spec's empty-BAL constant
  `0x1dcc4de8…49347`; plus a canonical-form validator and a structural cross-client
  differ that localizes a split to the exact account / slot / `block_access_index`.
- **JWT Engine API harness** (`harness/`): `forkchoiceUpdatedV3/V4` →
  `getPayloadV6` → BAL, a per-client smoke probe, and a **shared-head fresh
  payload-spec generator** so every client builds the *same* block.
- **One-command multi-EL devnet** (`devnet/`): Kurtosis + ethereum-package on real
  `glamsterdam-devnet-0` images (geth/erigon/reth/nethermind), endpoint extraction.
- **Provenance-gated severity**: synthetic fixtures are controls and can never reach
  bounty-grade; only live-devnet provenance escalates a divergence to critical.
- **54 unit tests + GitHub Actions CI.** MIT-licensed.

**Live-validated** against a running 4-EL Kurtosis devnet: the smoke probe returns a
BAL from all four clients. The strict `bal-diff-live --refresh` path currently
blocks a full 4-way differential because the devnet is split at the ePBS/Gloas
boundary: geth/reth/nethermind share block 7 while erigon is one block ahead at
block 8. With the erigon outlier explicitly excluded, Batman produced a **3-way
same-head BAL conformance pass** for geth/reth/nethermind (byte-identical BAL, 0
findings) and wrote reproducible JSON/Markdown evidence under `artifacts/`.

## Project structure (8 weeks)

1. **Weeks 1–2 — Public hardening.** Public repo + OSI license; clean README +
   architecture docs; one-command devnet setup; CI green; reproducible BAL smoke
   test across the four ELs.
2. **Weeks 3–4 — True differential engine.** Shared-head / same-payload comparison
   hardened (sync-aware head selection, devnet-health gating); cross-client BAL
   canonicalization checks; richer failure classification.
3. **Weeks 5–6 — Fuzzing + impact scenarios.** BAL mutation corpus;
   storage/access/index-confusion scenarios; contract/app impact examples; gas
   repricing compatibility hooks where relevant.
4. **Weeks 7–8 — Reporting + ecosystem output.** Markdown/JSON reports; public
   example datasets; a "Glamsterdam BAL Readiness Report"; docs for client teams,
   auditors, and indexers.

## Milestones (proposed, applicant-confirmable dates)

Dates below are proposed planning anchors as of **2026-06-13** and should be
confirmed by the applicant before submission. They assume Glamsterdam mainnet timing
around late August 2026 and will be adjusted if devnet or fork scheduling changes.

| Milestone | Proposed date | Verifiable deliverable |
|---|---:|---|
| **M1: Stable live differential evidence** | **2026-07-07** | A stable 4-way same-head live BAL differential including geth/erigon/reth/nethermind, or a documented infra blocker plus N-block 3-way conformance artifacts, compatibility snapshot, and public-safe evidence bundle. |
| **M2: Second Phase-1 detector complete** | **2026-07-17** | `BAL_MIXED_READ_WRITE_ALIAS` registered, documented, and tested against decoded BAL bytes, with synthetic alias and clean read-only/write-only fixtures proving fire/silent behavior. |
| **M3: Stable fixture corpus** | **2026-08-07** | The existing canonicalization/index fuzzer hardened into a committed fixture corpus with stable IDs, expected validation results, and CI coverage. |
| **M4: Pre-mainnet readiness report** | **2026-08-24** | Public **Glamsterdam BAL Readiness Report** summarizing findings, client responses, or documented clean-conformance results; absence of findings is valid if backed by reproducible artifacts. |

## Success metrics (quantitative)

- # execution clients covered (target ≥4) and # devnet blocks/BALs decoded & diffed.
- # public BAL fixtures + mutation scenarios published; size of the conformance dataset.
- # reproducible cross-client findings or conformance reports issued to client teams.
- # merged PRs / filed issues against clients or ecosystem tooling.
- One-command devnet reproducibility (cold-clone to first BAL diff in < N minutes).

## Ecosystem fit (vs nearest work)

- **execution-spec-tests** — generates spec fixtures for clients; Batman complements
  it by diffing *live* clients' actual BAL bytes on a shared block, not just fixtures.
- **Hive** — broad cross-client integration harness; Batman is the focused
  BAL-canonicalization conformance + impact layer, with a spec-anchored RLP engine.
- **Client-internal tests** — per-client; Batman is the cross-client referee with a
  reference canonicalizer.

## Sustainability

MIT-licensed, reproducible one-command devnet, CI, and docs keep maintenance low and
let the conformance harness fold into existing ecosystem CI after the grant.

## Budget

**$45k–$65k equivalent in ETH** for the 8-week scope above. (A 12-week variant with a
public dashboard, indexer/exporter support, and ongoing devnet monitoring would be
$80k–$100k.) Grants in this round pay on-chain in ETH; milestones are denominated
against a fiat-equivalent assumption to absorb ETH/USD volatility.

## Honest scope & limitations

This is a working prototype, not a finished product; the grant hardens it. A fair
4-way differential requires a **synced** devnet (the live run showed real
ePBS/Gloas boundary split/stall behavior — itself a readiness signal). BAL-over-RPC is currently
geth-only, so the uniform extraction path is the Engine API (`getPayloadV6`).
