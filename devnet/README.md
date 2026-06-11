# Local Glamsterdam / Gloas devnet (Kurtosis)

A multi-EL devnet for Batman's BAL differential testing. It runs several execution
clients on one Gloas network (EIP-7732 ePBS + **EIP-7928 Block-Level Access Lists**)
so we can compare each EL's independently-computed BAL for the same block.

## Prerequisites

- **Docker** (running).
- **Kurtosis CLI** — https://docs.kurtosis.com/install
  ```bash
  kurtosis version
  ```

## Finding current Gloas / EIP-7928 images (do this first)

`gloas_fork_epoch: 0` only works if the client images actually implement Gloas.
The default `:master` / `:unstable` tags usually **don't** yet. Pin real builds:

- Images: https://hub.docker.com/u/ethpandaops (look for `gloas` / `glamsterdam`
  / current `*-devnet-N` tags per client).
- Which clients are ready + the active devnet: the Glamsterdam devnet specs and
  forkmon under https://github.com/ethpandaops (e.g. `glamsterdam-devnets`).
- EIP-7928 is an **EL** feature — only include ELs whose image emits BALs. Trim
  `participants` in `glamsterdam-devnet.yaml` to those.

Edit `el_image` / `cl_image` in `glamsterdam-devnet.yaml` accordingly.

## Run

```bash
kurtosis run --enclave batman-gloas github.com/ethpandaops/ethereum-package \
  --args-file devnet/glamsterdam-devnet.yaml
```

Inspect it:
```bash
kurtosis enclave inspect batman-gloas
```

## Get endpoints for the harness

```bash
./devnet/endpoints.sh batman-gloas     # writes devnet/endpoints.json
```

`endpoints.json` is a list of `{client_id, rpc, engine}` — the seam the Batman
differential harness will read to call each EL's `engine_getPayloadV6` and collect
its BAL bytes. If the helper's parsing doesn't match your package version, fill
`endpoints.json` by hand from `kurtosis enclave inspect`.

## Teardown

```bash
kurtosis enclave rm -f batman-gloas
```

## Safety

Local/private devnet only. Do not point Batman at mainnet, public RPCs, or
third-party infrastructure. Suspected client bugs go through **private** disclosure
before any public mention.
