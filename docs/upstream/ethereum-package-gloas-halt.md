# Upstream feedback request - ethpandaops/ethereum-package

Filed as: https://github.com/ethpandaops/ethereum-package/issues/1420

This is a public feedback request about local/private Glamsterdam devnet behavior,
not a vulnerability report and not an endorsement.

Maintainer feedback received:

- keep future issues more compact;
- the latest Glamsterdam images are `glamsterdam-devnet-5`, not `glamsterdam-devnet-0`;
- refresh Batman evidence against the latest images.

## Public-safe summary

Batman's latest committed public evidence now shows:

- latest devnet-5 4-client smoke: all configured execution clients returned BAL bytes;
- 4-way same-head PASS: erigon/nethermind/besu/nimbus shared the same latest head;
- 0 detector findings in the public-safe report.

Historical devnet-0 artifacts are retained because they show Batman correctly refused
to turn split-head data into a weak 4-way claim.

The issue asked maintainers whether this Gloas/ePBS same-head split is expected for
the historical `glamsterdam-devnet-0` evidence run, whether additional builder/ePBS
configuration is needed, and what setup they recommend for sustained 4-EL EIP-7928
BAL conformance testing.

Keep suspected client-level findings private until reproduced and responsibly disclosed.
