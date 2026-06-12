# Public evidence bundle workflow

Batman keeps private-devnet evidence reproducible without turning disclosure hygiene into a
paper maze. The bundle builder copies only files explicitly named by the maintainer and writes
a SHA-256 manifest for reviewers.

## Build the committed reviewer bundle

```bash
python -m batman_detector.evidence_bundle \
  --output-dir dist/public-evidence \
  --artifact artifacts/live-heads.json \
  --artifact artifacts/live-smoke.json \
  --artifact artifacts/live-4way-diff.txt \
  --artifact artifacts/live-3way-diff.txt \
  --artifact artifacts/subset-live-report.md \
  --metadata spec=eip-7928 \
  --metadata provenance=private-devnet
```

The output directory contains:

- copied public-safe artifacts,
- `manifest.json` with SHA-256 digests and metadata,
- a generated `README.md` inventory for reviewers.

## Guardrails

The builder refuses:

- paths that were not explicitly supplied,
- secret-looking filenames such as JWT, token, password, mnemonic, keystore, or private-key files,
- symbolic links,
- unsupported file types,
- individual artifacts larger than 2 MiB,
- duplicate output filenames.

These guardrails reduce accidental leakage. They are not a substitute for manually reviewing
the generated folder before publication.

## Offline canonicalization campaign

Batman also ships a deterministic offline fuzzer for canonical BAL ordering:

```bash
python -m batman_detector.bal.fuzzer --iterations 64 --seed 7928 --format json
```

The campaign mutates account ordering, storage-slot ordering, storage-change indexes,
storage-read ordering, balance-change indexes, nonce-change indexes, and code-change indexes.
It verifies that the validator detects each mutation and that canonicalization repairs ordering.
No RPC endpoint is contacted.
