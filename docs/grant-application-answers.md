# EF Glamsterdam Grant - ready-to-paste form answers

> Paste each block into the matching field at
> https://esp.ethereum.foundation/applicants/wishlist/glamsterdam-round/apply
> Review before submitting. Repo must be public first.

## Project name
Batman: Open-Source Glamsterdam BAL Differential Testing & Impact Analysis Toolkit

## Applicant profile
Independent security researcher (EVM smart-contract auditing + systems security; ITMO
student). Prior work: ChainEDR (smart-contract analysis tooling), audit findings via
Cantina/Chainlink programs, and this Batman prototype. Solo applicant; this grant funds
hardening Batman into a reusable public good.

## Public work / links
- Repo: https://github.com/icedracon/batman (MIT, public)
- Architecture: docs/ARCHITECTURE.md
- Proposal: docs/grant-proposal.md
- Readiness report: docs/GLAMSTERDAM_BAL_READINESS_REPORT.md

## Problem being solved
EIP-7928 makes every block carry a Block-Level Access List whose
`block_access_list_hash` is committed in the header, so a BAL is consensus-critical and
must be byte-identical and canonical across all execution clients. Concrete risks include
canonicalization divergence, `block_access_index` phase confusion, and mixed read/write
aliasing where one slot is classified inconsistently across reads and post-write changes.
There is no focused, open, live cross-client BAL conformance tool, and app developers,
indexers, and auditors have no way to see BAL behavior and impact before mainnet.

## Project structure (milestones / deliverables / outcomes)
8 weeks. (1) Weeks 1-2 Public hardening: public repo + OSI license, README + architecture
docs, one-command devnet, green CI, reproducible BAL smoke across 4 ELs. (2) Weeks 3-4
True differential engine: sync-aware shared-head / same-payload comparison, cross-client
canonicalization checks, richer failure classification. (3) Weeks 5-6 Fuzzing + impact:
BAL mutation corpus, storage/access/index-confusion scenarios, contract/app impact
examples, gas-repricing compatibility hooks where relevant. (4) Weeks 7-8 Reporting +
ecosystem output: Markdown/JSON reports, public datasets, a Glamsterdam BAL Readiness
Report, and docs for client teams / auditors / indexers.

## Measured impact (current evidence)
Working prototype, not just an idea: spec-anchored EIP-7928 RLP engine with a test for
the spec's empty-BAL hash constant, canonical validator, cross-client structural differ,
JWT Engine API harness, one-command Kurtosis 4-EL devnet, provenance-gated severity,
54 unit tests, and GitHub Actions CI.

Live-validated on a running 4-client Glamsterdam (Gloas) devnet. Public status:
**4-client smoke, 3-way same-head PASS, full 4-way refused on current devnet split**.
The smoke probe returns BAL bytes from geth, erigon, reth, and nethermind. The strict
`bal-diff-live --refresh` path currently blocks a full 4-way same-head differential
because the devnet latest heads do not all agree. A scoped same-head subset produced
byte-identical BAL output with 0 findings and wrote reproducible JSON/Markdown evidence
under `artifacts/`. The 4-way refusal is intentional: the harness will not produce a
weak claim when latest heads disagree.

Reviewers can verify the public evidence bundle locally:
`python -m batman_detector evidence-pack --output-dir dist/public-evidence --verify`.

## Success metrics
Execution clients covered (target >=4); devnet blocks/BALs decoded and diffed; public
fixtures + mutation scenarios; conformance-dataset size; cross-client findings or
conformance reports to client teams; merged PRs / filed issues; cold-clone-to-first-BAL
diff time; public evidence verifier remains green in CI.

## Ecosystem fit (comparisons)
- execution-spec-tests: spec fixtures for clients; Batman complements it by diffing
  live clients' actual BAL bytes on a shared block.
- Hive: broad cross-client integration; Batman is the focused BAL-canonicalization
  conformance + impact layer with a spec-anchored reference RLP engine.
- Client-internal tests: per-client; Batman is the cross-client referee.

## Sustainability plan
MIT license, reproducible one-command devnet, CI, and docs keep maintenance low; the
conformance harness can fold into existing ecosystem CI after the grant.

## Community feedback
Feedback requested from `ethpandaops/ethereum-package` maintainers on the current
Gloas/ePBS same-head split and recommended sustained 4-EL BAL conformance setup:
https://github.com/ethpandaops/ethereum-package/issues/1420

This is a feedback request, not an endorsement. The grant work will continue sharing
public-safe conformance datasets and route suspected client-level issues through private
responsible disclosure.

## Open-source license
MIT.

## Budget
$45,000-$65,000 equivalent in ETH for the 8-week scope. Grants pay on-chain in ETH;
milestones are denominated against a fiat-equivalent assumption to absorb ETH/USD
volatility. A 12-week variant with a public dashboard + indexer/exporter support +
ongoing devnet monitoring would be $80k-$100k.
