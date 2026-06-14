# Glamsterdam BAL Readiness Report

Status as of 2026-06-14. This is public-safe engineering evidence for Batman's
EIP-7928 Block-Level Access List readiness workflow. It is not a mainnet result,
not a public-RPC result, and not a bug-bounty claim.

## Public Status

- 54 unit tests pass locally and in GitHub Actions.
- Two Phase-1 detectors are implemented and registered:
  `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION` and `BAL_MIXED_READ_WRITE_ALIAS`.
- 4-client smoke evidence shows all configured execution clients returning BAL bytes.
- 3-way same-head PASS: the committed subset evidence has byte-identical BAL output
  with 0 findings.
- Full 4-way same-head differential is refused on the current devnet split. Batman
  does not turn split-head data into a weak 4-way claim.
- Public evidence can be regenerated and verified with:

```bash
python -m batman_detector evidence-pack --output-dir dist/public-evidence --verify
```

## Current Public Evidence

- [`../artifacts/live-heads.json`](../artifacts/live-heads.json)
- [`../artifacts/live-smoke.json`](../artifacts/live-smoke.json)
- [`../artifacts/live-4way-diff.txt`](../artifacts/live-4way-diff.txt)
- [`../artifacts/live-3way-diff.txt`](../artifacts/live-3way-diff.txt)
- [`../artifacts/subset-live-trace.json`](../artifacts/subset-live-trace.json)
- [`../artifacts/subset-live-report.md`](../artifacts/subset-live-report.md)
- [`../artifacts/compatibility-snapshot.gloas-devnet0.json`](../artifacts/compatibility-snapshot.gloas-devnet0.json)

The compatibility snapshot is the machine-readable source for the current public
claim: 4-client smoke, 3-way same-head PASS, full 4-way refused on current devnet split.

## External Feedback

Feedback has been requested from the `ethpandaops/ethereum-package` maintainers:

- https://github.com/ethpandaops/ethereum-package/issues/1420

The issue asks whether the observed Gloas/ePBS same-head split is expected for the
current `glamsterdam-devnet-0` images/config, whether additional builder/ePBS
configuration is needed, and what setup maintainers recommend for sustained 4-EL BAL
conformance testing. It should be treated as a feedback request, not an endorsement.

## Limitations

- The current public evidence is local/private-devnet only.
- The current public evidence does not prove a full 4-way same-head BAL conformance
  result because the devnet heads did not agree.
- Synthetic controls remain useful detector tests, but they are not evidence of a
  real client bug.
- Suspected client-level issues must remain private until reproduced and responsibly
  disclosed.

## Next Milestones

- M1: Obtain stable 4-way same-head live evidence, or publish an N-block 3-way
  conformance corpus plus a documented infra blocker.
- M2: Keep both Phase-1 detectors covered by unit tests and public examples.
- M3: Promote the offline fuzzer into a stable fixture corpus with deterministic IDs.
- M4: Publish a pre-mainnet readiness report with findings or documented clean
  conformance.
