# Glamsterdam BAL compatibility matrix

Batman records execution-client behavior for EIP-7928 Block-Level Access Lists (BAL) on
local/private devnets. This matrix is an engineering snapshot, not a claim about mainnet or
public infrastructure.

## Current committed Gloas devnet snapshot

Public status: 4-client smoke, 3-way same-head PASS, full 4-way refused on current
devnet split.

| Execution client | Engine API returned BAL bytes in smoke path | Included in committed same-head differential | Current note |
|---|---:|---:|---|
| Geth | Yes | Yes | Shared the committed subset head with Reth and Nethermind. |
| Erigon | Yes | No | Was one block ahead during the committed run, so Batman correctly refused the full 4-way same-head comparison. |
| Reth | Yes | Yes | Shared the committed subset head with Geth and Nethermind. |
| Nethermind | Yes | Yes | Shared the committed subset head with Geth and Reth. |

Committed artifacts:

- [`../artifacts/live-heads.json`](../artifacts/live-heads.json)
- [`../artifacts/live-smoke.json`](../artifacts/live-smoke.json)
- [`../artifacts/live-4way-diff.txt`](../artifacts/live-4way-diff.txt)
- [`../artifacts/live-3way-diff.txt`](../artifacts/live-3way-diff.txt)
- [`../artifacts/subset-live-trace.json`](../artifacts/subset-live-trace.json)
- [`../artifacts/subset-live-report.md`](../artifacts/subset-live-report.md)
- [`../artifacts/compatibility-snapshot.gloas-devnet0.json`](../artifacts/compatibility-snapshot.gloas-devnet0.json)

The JSON snapshot is the machine-readable source for reviewer tooling. It records client
heads, same-head inclusion, BAL smoke status, artifact hashes, and explicit safety flags.

External feedback has been requested from `ethpandaops/ethereum-package` maintainers:
https://github.com/ethpandaops/ethereum-package/issues/1420

## Reproducibility fields for future runs

Every refreshed compatibility entry should record:

| Field | Why it matters |
|---|---|
| Batman commit SHA | Pins detector behavior. |
| EIP-7928 / spec commit | Glamsterdam drafts move over time. |
| Devnet configuration commit | Pins fork epoch and orchestration assumptions. |
| Execution-client image tag and digest | Prevents mutable tags from quietly changing results. |
| Consensus-client image tag and digest | Keeps the CL side reproducible when head behavior changes. |
| Smoke result | Answers whether each client returned BAL bytes at all. |
| Latest-head agreement result | Separates honest gating from actual divergence. |
| Differential trace and report | Preserves localized account / slot / index evidence. |

## Refresh procedure

```bash
./devnet/endpoints.sh batman-gloas

python -m batman_detector bal-heads-live \
  --endpoints devnet/endpoints.json \
  --format json

python -m batman_detector bal-smoke-live \
  --endpoints devnet/endpoints.json \
  --jwt-secret devnet/jwt_file/jwtsecret \
  --payload-spec devnet/payload-spec.latest.json \
  --format json

python -m batman_detector bal-diff-live \
  --endpoints devnet/endpoints.json \
  --jwt-secret devnet/jwt_file/jwtsecret \
  --payload-spec devnet/payload-spec.latest.json \
  --refresh \
  --wait-shared-head 60 \
  --output-trace artifacts/live-trace.json \
  --output-report artifacts/live-report.md

python -m batman_detector compatibility-snapshot \
  --heads artifacts/live-heads.json \
  --smoke artifacts/live-smoke.json \
  --four-way-output artifacts/live-4way-diff.txt \
  --subset-trace artifacts/subset-live-trace.json \
  --subset-report artifacts/subset-live-report.md \
  --output artifacts/compatibility-snapshot.gloas-devnet0.json \
  --metadata source=refreshed-private-devnet
```

## Safety boundary

Run Batman only on local/private devnets. Do not test mainnet, public RPC providers, or
third-party systems. Treat suspected client divergences as private-disclosure material until
reproduced and responsibly reported.
