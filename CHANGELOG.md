# Changelog

## 0.1.1 - reviewer-facing grant polish

- Added a deterministic offline BAL canonicalization fuzzer covering account ordering,
  storage-slot ordering, storage-change indexes, storage-read ordering, balance-change
  indexes, nonce-change indexes, and code-change indexes.
- Expanded the offline corpus to duplicate accounts, duplicate slots, duplicate
  `block_access_index` entries, read/write overlap, malformed RLP shapes, and uint
  boundary failures.
- Added a machine-readable compatibility snapshot for committed Gloas devnet evidence.
- Added a safe public evidence bundle builder with explicit artifact selection, SHA-256
  manifests, symlink rejection, size limits, and secret-looking filename rejection.
- Added a reviewer-facing Geth / Erigon / Reth / Nethermind compatibility matrix.
- Added `batman evidence-pack` for one-command public evidence bundles.
- Added unit tests and GitHub Actions smoke checks for the reviewer-facing workflow.

## 0.1.0 - Glamsterdam BAL readiness prototype

- Added EIP-7928 BAL model, RLP codec, canonical validation, hash checks, and
  structural differential comparison.
- Added `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION` detector with synthetic control fixtures.
- Added Engine API live harness and Kurtosis Gloas devnet support.
- Added same-head gating for live BAL differential runs.
- Added committed live evidence:
  - 4-client BAL smoke output.
  - Honest 4-way same-head refusal on the current devnet split.
  - 3-way same-head geth/reth/nethermind pass with 0 findings.
- Added CI dependency fix for clean installs with a keccak backend.
