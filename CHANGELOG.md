# Changelog

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

