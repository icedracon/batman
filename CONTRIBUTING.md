# Contributing

Batman is intentionally small: it should stay easy to audit, reproduce, and explain.

## Development setup

```bash
python -m pip install -e .
python -m unittest discover
```

Useful smoke checks:

```bash
python -m batman_detector validate examples/traces/bal_system_index_confusion.generated.json
python -m batman_detector static-scan examples/audit_targets/bal_first_scan.sample.json --format json
python -m batman_detector run examples/traces/bal_system_index_confusion.generated.json --format json
```

## Contribution rules

- Keep claims tied to reproducible artifacts.
- Preserve provenance labels that distinguish synthetic fixtures from live client output.
- Do not escalate synthetic-control findings into bounty-grade or critical-severity claims.
- Keep devnet secrets, JWT files, and private keys out of commits.
- Prefer narrow tests for narrow changes and broader tests for shared behavior.

## Good first areas

- Add BAL canonicalization edge cases.
- Expand schema validation tests.
- Improve live-devnet compatibility reporting.
- Add fixtures for spec-version transitions as Glamsterdam changes.

