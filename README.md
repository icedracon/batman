# Batman Detector for Glamsterdam

Batman is a small, reproducible detector harness for Glamsterdam/Gloas security research.
The first target is EIP-7928 Block-Level Access List behavior, especially system-contract
index canonicalization around `block_access_index = 0`, transaction indices, and `n + 1`.

This repository starts deliberately small:

- JSON schemas for traces, rulesets, and findings.
- JSON schemas for audit targets and fuzz campaigns.
- A version-aware ruleset manifest.
- A CLI that validates inputs, runs detectors, performs static pre-scans, and writes reports.
- A first detector: `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION`.
- A synthetic sample trace to prove the pipeline works.

## Quick Start

```powershell
python -m batman_detector validate examples\traces\bal_system_index_confusion.sample.json
python -m batman_detector validate examples\audit_targets\bal_first_scan.sample.json --schema audit-target
python -m batman_detector validate examples\fuzz_campaigns\bal_index_confusion.sample.json --schema fuzz-campaign
python -m batman_detector static-scan examples\audit_targets\bal_first_scan.sample.json
python -m batman_detector run examples\traces\bal_system_index_confusion.sample.json --ruleset configs\rulesets\glamsterdam-alpha.example.json
python -m batman_detector report examples\traces\bal_system_index_confusion.sample.json --ruleset configs\rulesets\glamsterdam-alpha.example.json --output first-scan-report.md
python -m unittest discover
```

## Current Detector

## Architecture Source

The project goal and detector roadmap are captured in
`docs/Batman Detector Architecture for Glamsterdam.pdf`.

### `BAL_SYSTEM_CONTRACT_INDEX_CONFUSION`

Looks for BAL entries where the same account/storage key is touched across system phases and
normal transactions, then checks whether client observations disagree on BAL hash or validity.

The detector is meant to support this bug-hunting path:

1. Generate or record an adversarial EIP-7928 fixture.
2. Run the fixture against several execution clients.
3. Record each client's BAL hash/status in a Batman trace.
4. Run the detector.
5. If a real mismatch appears, prepare a private disclosure package.

## Bounty Safety

Use this only on local/private devnets or fixtures. Do not test against mainnet, public RPCs,
or third-party infrastructure. Do not publish suspected vulnerabilities before private disclosure.
