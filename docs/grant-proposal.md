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
post-exec `n+1` merged or misassigned). Today there is no focused, open, live
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
- **40 unit tests + GitHub Actions CI.** MIT-licensed.

**Live-validated** against a running 4-EL Kurtosis devnet: the smoke probe returns a
BAL from all four clients; `bal-diff-live --refresh` produced a **3-way BAL
conformance pass** (erigon/reth/nethermind agreed on the BAL for a shared parent),
and the tool correctly surfaced a **cross-client head divergence / under-peered
devnet** — exactly the readiness signal it is meant to produce.

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
sync/peering fragility — itself a readiness signal). BAL-over-RPC is currently
geth-only, so the uniform extraction path is the Engine API (`getPayloadV6`).
