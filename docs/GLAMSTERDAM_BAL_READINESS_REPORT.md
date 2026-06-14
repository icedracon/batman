# Glamsterdam BAL Readiness Report

Status as of 2026-06-14. This is public-safe engineering evidence for Batman's
EIP-7928 Block-Level Access List readiness workflow. It is not a mainnet result,
not a public-RPC result, and not a bug-bounty claim.

## Public Status

- 59 unit tests pass locally and in GitHub Actions.
- Two Phase-1 detectors are implemented and registered:
  `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION` and `BAL_MIXED_READ_WRITE_ALIAS`.
- Latest devnet-5 4-client smoke evidence shows erigon, nethermind, besu, and
  nimbus returning BAL bytes.
- 4-way same-head PASS: all four devnet-5 clients shared the same latest head and
  returned comparable BAL bytes with 0 findings.
- Historical devnet-0 evidence is retained separately because Batman correctly refused
  to turn split-head data into a weak 4-way claim.
- Public evidence can be regenerated and verified with:

```bash
python -m batman_detector evidence-pack --output-dir dist/public-evidence --verify
```

## Current Public Evidence

- [`../artifacts/devnet5-live-heads.json`](../artifacts/devnet5-live-heads.json)
- [`../artifacts/devnet5-live-smoke.json`](../artifacts/devnet5-live-smoke.json)
- [`../artifacts/devnet5-live-4way-diff.txt`](../artifacts/devnet5-live-4way-diff.txt)
- [`../artifacts/devnet5-live-trace.json`](../artifacts/devnet5-live-trace.json)
- [`../artifacts/devnet5-live-report.md`](../artifacts/devnet5-live-report.md)
- [`../artifacts/compatibility-snapshot.gloas-devnet5.json`](../artifacts/compatibility-snapshot.gloas-devnet5.json)

The compatibility snapshot is the machine-readable source for the current public
claim: latest devnet-5 4-client smoke, 4-way same-head PASS, 0 findings.

## External Feedback

Feedback was requested from the `ethpandaops/ethereum-package` maintainers:

- https://github.com/ethpandaops/ethereum-package/issues/1420

A maintainer replied that future issues should be more compact and that the latest
Glamsterdam images are `glamsterdam-devnet-5`, not `glamsterdam-devnet-0`. Batman now
keeps the historical devnet-0 config for committed evidence reproducibility, adds a
separate devnet-5 config, and has refreshed public BAL evidence on devnet-5. This should
be treated as useful domain feedback, not an endorsement.

## Limitations

- The current public evidence is local/private-devnet only.
- The current public evidence proves a clean 4-way same-head BAL comparison on the
  available devnet-5 client set, but it is still local/private-devnet evidence.
- Synthetic controls remain useful detector tests, but they are not evidence of a
  real client bug.
- Suspected client-level issues must remain private until reproduced and responsibly
  disclosed.

## Next Milestones

- M1: Extend the devnet-5 evidence from one clean 4-way same-head block into an N-block
  conformance corpus, or document any new infra blocker if the devnet changes.
- M2: Keep both Phase-1 detectors covered by unit tests and public examples.
- M3: Promote the offline fuzzer into a stable fixture corpus with deterministic IDs.
- M4: Publish a pre-mainnet readiness report with findings or documented clean
  conformance.
