# Roadmap

Batman focuses on one useful wedge first: EIP-7928 Block-Level Access List readiness.
The project is not a full Ethereum client fuzzer and does not claim to replace
client-team testing.

## Near term

- Keep the BAL codec pinned to the current Glamsterdam/EIP-7928 draft behavior.
- Expand canonicalization and malformed-encoding test coverage.
- Refresh live devnet evidence as new Gloas/Glamsterdam devnets become available.
- Track which clients return `blockAccessList` over the Engine API and under which
  fork/head conditions.

## Next

- Add a BAL canonicalization fuzzer for account, slot, and `block_access_index`
  ordering.
- Add a compatibility matrix for Geth, Erigon, Reth, and Nethermind devnet images.
- Add a reusable command for producing a compact public evidence bundle.
- Expand `static-scan` checks for audit-target manifests before live runs.

## Later

- Investigate BAL read/write aliasing detectors.
- Add broader CL+EL orchestration only when the devnet layer is stable enough to make
  same-head 4-way differential runs repeatable.
- Explore ePBS-adjacent checks as separate modules, not as unverified claims in the
  BAL detector.

## Non-goals

- Mainnet scanning.
- Public-RPC testing.
- Publishing suspected client vulnerabilities before private disclosure.
- Treating synthetic fixtures as proof of real client bugs.

