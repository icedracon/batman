# Public evidence bundle workflow

Batman keeps private-devnet evidence reproducible without turning disclosure hygiene into a
paper maze. The bundle builder copies only files explicitly named by the maintainer and writes
a SHA-256 manifest for reviewers.

## Build the compatibility snapshot

```bash
python -m batman_detector compatibility-snapshot \
  --heads artifacts/devnet5-live-heads.json \
  --smoke artifacts/devnet5-live-smoke.json \
  --four-way-output artifacts/devnet5-live-4way-diff.txt \
  --subset-trace artifacts/devnet5-live-trace.json \
  --subset-report artifacts/devnet5-live-report.md \
  --output artifacts/compatibility-snapshot.gloas-devnet5.json \
  --metadata source=devnet5-maintainer-feedback-refresh
```

The snapshot records client head state, BAL smoke status, same-head differential inclusion,
artifact hashes, and explicit safety flags.

## Build the committed reviewer bundle

```bash
python -m batman_detector evidence-pack --output-dir dist/public-evidence --verify
```

The output directory contains:

- copied public-safe artifacts,
- `manifest.json` with SHA-256 digests and metadata,
- a generated `README.md` inventory for reviewers.
- a verification summary confirming: latest devnet-5 4-client smoke, 4-way
  same-head PASS, and 0 findings.

## Guardrails

The builder refuses:

- paths that were not explicitly supplied,
- secret-looking filenames such as JWT, token, password, mnemonic, keystore, or private-key files,
- symbolic links,
- unsupported file types,
- individual artifacts larger than 2 MiB,
- duplicate output filenames.

With `--verify`, Batman also checks that source artifacts exist, JSON artifacts parse,
copied files match the manifest hashes, compatibility snapshot hashes match the source
files, and the public subset report records zero findings.

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
