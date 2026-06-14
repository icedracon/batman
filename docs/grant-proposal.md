# Batman: Open-Source Glamsterdam BAL Differential Testing & Impact Analysis Toolkit

> Draft for the EF Glamsterdam Grants Round (ESP wishlist). Framing: open-source
> upgrade-readiness tooling for EIP-7928 Block-Level Access Lists: developer
> tooling, impact analysis, and data-driven research. Not a bug-bounty play.
>
> Round: https://esp.ethereum.foundation/applicants/wishlist/glamsterdam-round/apply
> Scope EIP: EIP-7928 (Scheduled for Inclusion per EIP-7773).

## Summary

Batman is an open-source toolkit for preparing the Ethereum ecosystem for
Glamsterdam's Block-Level Access Lists (EIP-7928). It stands up multi-client
Glamsterdam/Gloas devnets, extracts each client's BAL through the Engine API,
performs cross-client differential analysis with a spec-anchored RLP engine,
and produces reproducible reports that help client teams, auditors, app developers,
block explorers/indexers, and researchers detect BAL inconsistencies before
deployment. This grant turns a working prototype into a documented, one-command
readiness tool with fuzzing scenarios, public fixtures, CI, and research reports.

## Applicant

The project is led by an independent security researcher and university student
focused on systems security, incident response, threat hunting, and Web3 auditing.
The applicant has about 1.5 years of professional cybersecurity experience, currently
works in incident response / threat hunting, holds Hack The Box CDSA and OffSec OSCC
credentials, is preparing for CPTS, and is actively studying Ethereum/Web3 auditing.
Relevant project work includes ChainEDR, smart-contract analysis tooling, audit findings
via Cantina/Chainlink programs, and this Batman prototype.

## Problem

EIP-7928 makes every block carry a BAL whose `block_access_list_hash` is committed
in the header, so a BAL is consensus-critical and must be byte-identical and
canonical across all execution clients. Concrete risks include canonicalization
divergence, `block_access_index` phase confusion, and mixed read/write aliasing where
the same slot appears in both `storage_reads` and `storage_changes`. Today there is
no focused, open, live cross-client BAL conformance tool, and app developers,
indexers, and auditors lack a way to see BAL behavior and impact before mainnet.

## What Already Exists

- Spec-anchored EIP-7928 RLP engine: typed model, encode/decode,
  `block_access_list_hash`, empty-BAL hash test, canonical-form validator, and
  structural cross-client differ.
- JWT Engine API harness: `forkchoiceUpdatedV3/V4` to `getPayloadV6` to BAL, plus
  a shared-head fresh payload-spec generator so every client builds the same block.
- One-command multi-EL devnet configs: historical devnet-0 evidence and the latest
  maintainer-recommended devnet-5 line.
- Provenance-gated severity: synthetic fixtures are controls and can never reach
  bounty-grade; only live-devnet provenance escalates a divergence.
- 59 unit tests + GitHub Actions CI. MIT-licensed.

Live-validated against a running 4-EL Kurtosis devnet. Public status: latest devnet-5
4-client smoke, 4-way same-head PASS, 0 findings. After maintainer feedback that the
latest Glamsterdam images are `glamsterdam-devnet-5`, Batman added a dedicated
devnet-5 config and refreshed evidence using erigon, nethermind, besu, and nimbus.
The strict `bal-diff-live --refresh` path ran only after all latest heads agreed,
then produced a reproducible same-head 4-way BAL comparison with 0 findings under
`artifacts/`.

## Project Structure

1. Weeks 1-2 - Public hardening: public repo + OSI license, README + architecture
   docs, one-command devnet setup, CI green, reproducible BAL smoke across 4 ELs.
2. Weeks 3-4 - True differential engine: sync-aware shared-head / same-payload
   comparison, cross-client canonicalization checks, richer failure classification.
3. Weeks 5-6 - Fuzzing + impact scenarios: BAL mutation corpus,
   storage/access/index-confusion scenarios, contract/app impact examples, and
   gas repricing compatibility hooks where relevant.
4. Weeks 7-8 - Reporting + ecosystem output: Markdown/JSON reports, public example
   datasets, a Glamsterdam BAL Readiness Report, and docs for client teams, auditors,
   and indexers.

## Milestones

Dates below are proposed planning anchors as of 2026-06-13 and should be confirmed
by the applicant before submission. They assume Glamsterdam mainnet timing around
late August 2026 and will be adjusted if devnet or fork scheduling changes.

| Milestone | Proposed date | Verifiable deliverable |
|---|---:|---|
| M1: Stable live differential evidence | 2026-07-07 | Extend the current clean devnet-5 4-way same-head evidence into an N-block conformance corpus, or document any new infra blocker plus public-safe compatibility artifacts. |
| M2: Second Phase-1 detector complete | 2026-07-17 | `BAL_MIXED_READ_WRITE_ALIAS` registered, documented, and tested against decoded BAL bytes, with synthetic alias and clean read-only/write-only fixtures proving fire/silent behavior. |
| M3: Stable fixture corpus | 2026-08-07 | The existing canonicalization/index fuzzer hardened into a committed fixture corpus with stable IDs, expected validation results, and CI coverage. |
| M4: Pre-mainnet readiness report | 2026-08-24 | Public Glamsterdam BAL Readiness Report summarizing findings, client responses, or documented clean-conformance results; absence of findings is valid if backed by reproducible artifacts. |

## Success Metrics

- Execution clients covered (target >=4) and number of devnet blocks/BALs decoded and diffed.
- Public BAL fixtures + mutation scenarios published; size of the conformance dataset.
- Reproducible cross-client findings or conformance reports issued to client teams.
- Merged PRs / filed issues against clients or ecosystem tooling.
- One-command devnet reproducibility.
- Public evidence verifier stays green:
  `python -m batman_detector evidence-pack --output-dir dist/public-evidence --verify`.

## Ecosystem Fit

- execution-spec-tests generates spec fixtures for clients; Batman complements it by
  diffing live clients' actual BAL bytes on a shared block.
- Hive is a broad cross-client integration harness; Batman is the focused
  BAL-canonicalization conformance + impact layer, with a spec-anchored RLP engine.
- Client-internal tests are per-client; Batman is the cross-client referee with a
  reference canonicalizer and public-safe evidence bundles.

## Sustainability

MIT license, reproducible one-command devnet, CI, and docs keep maintenance low and
let the conformance harness fold into existing ecosystem CI after the grant.

## Community Feedback

Feedback has been requested from `ethpandaops/ethereum-package` maintainers about the
Gloas/ePBS same-head behavior and recommended sustained 4-EL BAL conformance setup:
https://github.com/ethpandaops/ethereum-package/issues/1420

A maintainer responded that future issues should be more compact and that the latest
Glamsterdam images are `glamsterdam-devnet-5`, not `glamsterdam-devnet-0`. Batman now
keeps devnet-0 for historical evidence reproducibility, adds a devnet-5 config, and
has refreshed public BAL evidence on the latest available devnet images. This is useful
domain feedback, not an endorsement.

## Budget

$45k-$65k equivalent in ETH for the 8-week scope above. A 12-week variant with a
public dashboard, indexer/exporter support, and ongoing devnet monitoring would be
$80k-$100k. Grants in this round pay on-chain in ETH; milestones are denominated
against a fiat-equivalent assumption to absorb ETH/USD volatility.

## Honest Scope & Limitations

This is a working prototype, not a finished product; the grant hardens it. A fair
4-way differential requires a synced devnet. The latest devnet-5 run produced a clean
same-head window across erigon/nethermind/besu/nimbus; future runs may still be affected
by devnet churn as images change. BAL-over-RPC remains uneven across clients, so the
uniform extraction path is the Engine API (`getPayloadV6`).
