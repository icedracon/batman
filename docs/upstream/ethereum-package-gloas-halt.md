# Upstream issue draft → ethpandaops/ethereum-package

Paste into https://github.com/ethpandaops/ethereum-package/issues/new
(You file it — it posts under your GitHub identity. Review first.)

---

**Title:** `glamsterdam-devnet-0: block production stalls at the Gloas/ePBS fork boundary (no finality past slot 8)`

---

## Summary

Running a 4-EL Glamsterdam (Gloas) devnet via `ethereum-package`, the chain produces
the pre-fork blocks and then **stops producing and finalizing at the Gloas fork
boundary**. With `gloas_fork_epoch: 1` and the `minimal` preset (8 slots/epoch), that
boundary is slot 8. The beacon head freezes at slot 8 while the slot clock keeps
advancing, `finalized_epoch` stays at `0`, and post-fork slots are empty. One execution
client (erigon) ends up one block ahead and then deadlocks with its **own** consensus
client (`wrong head block`).

I'm filing to ask whether this is **expected** for `glamsterdam-devnet-0` at this stage
(ePBS still early), a **config gap on my side** (e.g. a builder component required for
ePBS block production), or an **interop issue** worth tracking.

## Environment

- `ethereum-package` via Kurtosis: `kurtosis run --enclave gloas github.com/ethpandaops/ethereum-package --args-file args.yaml`
- Images (Docker Hub, pulled ~2026-04-29): `ethpandaops/{geth,erigon,reth,nethermind,lighthouse}:glamsterdam-devnet-0`
- `args.yaml` (essentials):

```yaml
participants:
  - {el_type: geth,       cl_type: lighthouse}
  - {el_type: erigon,     cl_type: lighthouse}
  - {el_type: reth,       cl_type: lighthouse}
  - {el_type: nethermind, cl_type: lighthouse}
  # each el_image/cl_image pinned to :glamsterdam-devnet-0
network_params:
  preset: "minimal"
  electra_fork_epoch: 0
  fulu_fork_epoch: 0
  gloas_fork_epoch: 1     # Gloas at slot 8 (minimal preset)
  seconds_per_slot: 6
```

## Observed

- Pre-fork blocks are produced (up to ~block 7–8), then production halts.
- EL heads diverge and freeze: geth / reth / nethermind at block **#7** (`0xa4be…2e14b`),
  erigon one ahead at block **#8** (`0x4f4a…d49e9`). All report `eth_syncing == false`.
- Lighthouse CL: head frozen at **slot 8**, slot clock running (e.g. `slot 372 / epoch 46`),
  `finalized_epoch: 0`, post-fork slots `empty`.
- erigon's EL is one block ahead of its **own** CL, so the CL keeps asking it to build on
  block #7 while erigon is at #8 → `wrong head block`.

### Lighthouse (`cl-1-lighthouse-geth`)
```
WARN Skipping more than an epoch    head_slot: 8, request_slot: 256
INFO Synced    peers: "3", finalized_epoch: 0, epoch: 46, block: "  …  empty", slot: 372
```

### Erigon (`el-2-erigon-lighthouse`)
```
WARN Failed to build a block   err="wrong head block: 4f4a2477d43b…d49e9 (current) vs a4beb74578fa…2e14b (requested)"
WARN [rpc] served  method=engine_getPayloadV6  err="wrong head block: 4f4a2477d43b…d49e9 (current) vs a4beb74578fa…2e14b (requested)"
```

## Expected

Sustained block production and finalization past the Gloas fork — or, if that isn't
expected on `glamsterdam-devnet-0` yet, a documented note that ePBS block production does
not yet advance on this devnet config.

## Questions for maintainers

1. Is a stall at the ePBS/Gloas fork expected for `glamsterdam-devnet-0` at this stage?
2. Does ePBS block production on this devnet need a builder component that the default
   args don't include?
3. Is "erigon EL one block ahead of its own CL → `wrong head block`" a known interop quirk
   at the transition, or worth a separate report?

Happy to share the full args file and complete service logs.
