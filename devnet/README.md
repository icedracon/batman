# Local Glamsterdam / Gloas devnet (Kurtosis)

A multi-EL devnet for Batman's BAL differential testing. It runs several execution
clients on one Gloas network (EIP-7732 ePBS + **EIP-7928 Block-Level Access Lists**)
so we can compare each EL's independently-computed BAL for the same block.

## Prerequisites

- **Docker** (running).
- **Kurtosis CLI.** Kurtosis has no native Windows build — install it inside **WSL**:
  ```bash
  # In Windows PowerShell, install an Ubuntu distro if you don't have one:
  #   wsl --install -d Ubuntu      (then set up the Linux user, reopen the shell)
  # Inside the Ubuntu WSL shell:
  echo "deb [trusted=yes] https://apt.fury.io/kurtosis-tech/ /" | sudo tee /etc/apt/sources.list.d/kurtosis.list
  sudo apt update && sudo apt install -y kurtosis-cli
  kurtosis version
  ```
  Make sure Docker Desktop has **WSL integration** enabled for that distro
  (Docker Desktop → Settings → Resources → WSL integration).

  Run all the commands below from the WSL shell, in this repo's path
  (e.g. `cd /mnt/c/Users/zevs/Documents/Glamsterdam`).

## Image tags (already pinned)

`glamsterdam-devnet.yaml` pins **real** current images:
`ethpandaops/<client>:glamsterdam-devnet-0` (verified on Docker Hub 2026-04-29).
geth + erigon + reth + nethermind are active (all four EL tags confirmed; geth/
erigon/lighthouse pre-pulled OK). besu is omitted — not built for devnet-0 yet.

- When ethpandaops cut a newer devnet, bump `-devnet-0` everywhere.
- Browse tags: https://hub.docker.com/u/ethpandaops
- EIP-7928 is implemented by geth, besu, reth, nethermind, erigon, nimbus-eth1,
  ethrex — enable whichever ELs you want in `participants`.

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
