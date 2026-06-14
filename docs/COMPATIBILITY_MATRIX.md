# Glamsterdam BAL Compatibility Matrix

Batman records execution-client behavior for EIP-7928 Block-Level Access Lists (BAL)
on local/private devnets. This matrix is engineering evidence, not a claim about
mainnet or public infrastructure.

## Latest Committed Gloas Devnet-5 Snapshot

Public status: 4-client smoke, 4-way same-head PASS, 0 findings.

| Execution client | Engine API returned BAL bytes in smoke path | Included in same-head differential | Current note |
|---|---:|---:|---|
| Erigon | Yes | Yes | Shared the devnet-5 head and returned comparable BAL bytes. |
| Nethermind | Yes | Yes | Shared the devnet-5 head and returned comparable BAL bytes. |
| Besu | Yes | Yes | Shared the devnet-5 head and returned comparable BAL bytes. |
| Nimbus EL | Yes | Yes | `el_type: nimbus`, Docker image `ethpandaops/nimbus-eth1:glamsterdam-devnet-5`. |

Committed devnet-5 artifacts:

- [`../artifacts/devnet5-live-heads.json`](../artifacts/devnet5-live-heads.json)
- [`../artifacts/devnet5-live-smoke.json`](../artifacts/devnet5-live-smoke.json)
- [`../artifacts/devnet5-live-4way-diff.txt`](../artifacts/devnet5-live-4way-diff.txt)
- [`../artifacts/devnet5-live-trace.json`](../artifacts/devnet5-live-trace.json)
- [`../artifacts/devnet5-live-report.md`](../artifacts/devnet5-live-report.md)
- [`../artifacts/compatibility-snapshot.gloas-devnet5.json`](../artifacts/compatibility-snapshot.gloas-devnet5.json)

The JSON snapshot is the machine-readable source for reviewer tooling. It records
client heads, same-head inclusion, BAL smoke status, artifact hashes, and explicit
safety flags.

## Historical Devnet-0 Snapshot

The earlier committed devnet-0 evidence is retained for reproducibility. That run
showed 4-client smoke across geth/erigon/reth/nethermind, a 3-way same-head pass
for geth/reth/nethermind, and an honest full 4-way refusal because latest heads did
not agree. The reviewer evidence-pack now uses the newer devnet-5 4-way pass.

## Upstream Feedback

Feedback was requested from `ethpandaops/ethereum-package` maintainers:
https://github.com/ethpandaops/ethereum-package/issues/1420

Maintainer feedback: future issues should be more compact, and the latest
Glamsterdam images are `glamsterdam-devnet-5`. Batman added a dedicated devnet-5
config and refreshed public BAL evidence accordingly. This is useful domain
feedback, not an endorsement.

## Reproducibility Fields For Future Runs

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

## Refresh Procedure

```bash
./devnet/endpoints.sh batman-gloas-devnet5

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
  --wait-shared-head 20 \
  --poll-interval 2 \
  --output-trace artifacts/devnet5-live-trace.json \
  --output-report artifacts/devnet5-live-report.md

python -m batman_detector compatibility-snapshot \
  --heads artifacts/devnet5-live-heads.json \
  --smoke artifacts/devnet5-live-smoke.json \
  --four-way-output artifacts/devnet5-live-4way-diff.txt \
  --subset-trace artifacts/devnet5-live-trace.json \
  --subset-report artifacts/devnet5-live-report.md \
  --output artifacts/compatibility-snapshot.gloas-devnet5.json \
  --metadata source=devnet5-maintainer-feedback-refresh
```

## Safety Boundary

Run Batman only on local/private devnets. Do not test mainnet, public RPC providers,
or third-party systems. Treat suspected client divergences as private-disclosure
material until reproduced and responsibly reported.
