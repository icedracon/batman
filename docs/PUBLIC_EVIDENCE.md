# Public evidence bundle workflow

Batman keeps private-devnet evidence reproducible without turning disclosure hygiene into a
paper maze. The bundle builder copies only files explicitly named by the maintainer and writes
a SHA-256 manifest for reviewers.

## Build the compatibility snapshot

```bash
python -m batman_detector compatibility-snapshot \
  --heads artifacts/live-heads.json \
  --smoke artifacts/live-smoke.json \
  --four-way-output artifacts/live-4way-diff.txt \
  --subset-trace artifacts/subset-live-trace.json \
  --subset-report artifacts/subset-live-report.md \
  --output artifacts/compatibility-snapshot.gloas-devnet0.json \
  --metadata source=committed-live-evidence
```

The snapshot records client head state, BAL smoke status, same-head differential inclusion,
artifact hashes, and explicit safety flags.

## Build the committed reviewer bundle

```bash
python -m batman_detector evidence-pack --output-dir dist/public-evidence
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
python -m batman_detector.bal.fuzzer --iterations 64 --seed 7928 --include-malformed --format json
```

The campaign mutates account ordering, storage-slot ordering, storage-change indexes,
storage-read ordering, balance-change indexes, nonce-change indexes, and code-change indexes.
It also checks duplicate accounts, duplicate slots, duplicate indexes, read/write overlap,
malformed RLP shapes, and uint boundary failures. No RPC endpoint is contacted.
