# EF Glamsterdam Grant — ready-to-paste form answers

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
- Repo: https://github.com/icedracon/batman  (MIT, public)
- Architecture: docs/ARCHITECTURE.md · Proposal: docs/grant-proposal.md

## Problem being solved
EIP-7928 makes every block carry a Block-Level Access List whose
`block_access_list_hash` is committed in the header — so a BAL is consensus-critical and
must be byte-identical and canonical across all execution clients. Two concrete risks:
canonicalization divergence (different ordering/dedup → different bytes → different hash
→ a split) and `block_access_index` phase confusion (pre-exec 0 / tx 1..n / post-exec
n+1 merged or misassigned). There is no focused, open, live cross-client BAL conformance
tool, and app developers, indexers, and auditors have no way to see BAL behavior and
impact before mainnet.

## Project structure (milestones / deliverables / outcomes)
8 weeks. (1) Weeks 1–2 Public hardening: public repo + OSI license, README + arch docs,
one-command devnet, green CI, reproducible BAL smoke across 4 ELs. (2) Weeks 3–4 True
differential engine: sync-aware shared-head / same-payload comparison, cross-client
canonicalization checks, richer failure classification. (3) Weeks 5–6 Fuzzing + impact:
BAL mutation corpus, storage/access/index-confusion scenarios, contract/app impact
examples, gas-repricing compatibility hooks where relevant. (4) Weeks 7–8 Reporting +
ecosystem output: Markdown/JSON reports, public datasets, a "Glamsterdam BAL Readiness
Report", and docs for client teams / auditors / indexers.

## Measured impact (current evidence)
Working prototype, not just an idea: spec-anchored EIP-7928 RLP engine (a test asserts the
spec's empty-BAL hash constant), canonical validator, cross-client structural differ, JWT
Engine API harness, one-command Kurtosis 4-EL devnet (geth/erigon/reth/nethermind +
lighthouse), provenance-gated severity, 40 unit tests + CI.

Live-validated on a running 4-client Glamsterdam (Gloas) devnet: all four clients synced on
canonical history, and `bal-diff-live --refresh` built the next block on a shared head and
produced a **byte-identical BAL across geth/reth/nethermind — a repeatable 3-way conformance
pass (8/8 runs, 0 findings)**. erigon ran one block ahead and so did not share the
build-tip. The harness also surfaced a concrete readiness insight: the minimal devnet
**halts at the ePBS/Gloas fork boundary (~block 8) without a builder** — sustained
post-Gloas block production requires a builder component. Both are exactly the kinds of
pre-mainnet signals this tool is built to produce.

## Success metrics
# ELs covered (≥4); # devnet blocks/BALs decoded & diffed; # public fixtures + mutation
scenarios; conformance-dataset size; # cross-client findings/conformance reports to
client teams; # merged PRs / filed issues; cold-clone-to-first-BAL-diff time.

## Ecosystem fit (comparisons)
- execution-spec-tests — spec fixtures for clients; Batman complements it by diffing
  *live* clients' actual BAL bytes on a shared block.
- Hive — broad cross-client integration; Batman is the focused BAL-canonicalization
  conformance + impact layer with a spec-anchored reference RLP engine.
- Client-internal tests — per-client; Batman is the cross-client referee.

## Sustainability plan
MIT license, reproducible one-command devnet, CI, and docs keep maintenance low; the
conformance harness can fold into existing ecosystem CI after the grant.

## Community feedback
[TO FILL — strengthens the application] Plan: share the readiness harness with client
teams and ethpandaops, and present findings/conformance datasets via ACD channels.
Securing one client-team or ethpandaops acknowledgement before submission is recommended.

## Open-source license
MIT.

## Budget
$45,000–$65,000 equivalent in ETH for the 8-week scope. Grants pay on-chain in ETH;
milestones are denominated against a fiat-equivalent assumption to absorb ETH/USD
volatility. (A 12-week variant with a public dashboard + indexer/exporter support +
ongoing devnet monitoring would be $80k–$100k.)
