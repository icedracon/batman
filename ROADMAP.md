# Roadmap

Batman focuses on one useful wedge first: EIP-7928 Block-Level Access List readiness.
The project is not a full Ethereum client fuzzer and does not claim to replace
client-team testing.

## Completed grant-polish milestones

- Added a deterministic offline BAL canonicalization fuzzer for account, slot, and
  `block_access_index` ordering.
- Added a compatibility matrix for Geth, Erigon, Reth, and Nethermind devnet behavior.
- Added a reusable safe command for producing a compact public evidence bundle with
  SHA-256 manifests and secret-looking filename rejection.
- Added a machine-readable compatibility snapshot with artifact hashes and explicit
  split-devnet safety flags.
- Expanded the offline BAL corpus beyond ordering mutations to duplicates, read/write
  overlap, malformed RLP shapes, and uint boundary failures.
- Added unit tests and CI smoke checks for the new reviewer-facing workflow.

## Near term

- Keep the BAL codec pinned to the current Glamsterdam/EIP-7928 draft behavior.
- Refresh live devnet evidence as new Gloas/Glamsterdam devnets become available.
- Track which clients return `blockAccessList` over the Engine API and under which
  fork/head conditions.
- Record exact execution-client and consensus-client image digests for refreshed runs.

## Next

- Expand `static-scan` checks for audit-target manifests before live runs.
- Add fixture minimization for BAL divergences so reports contain the smallest useful
  reproducer.
- Expand malformed-encoding coverage into a committed fixture corpus with stable ids.

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
