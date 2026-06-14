# Upstream feedback request - ethpandaops/ethereum-package

Filed as: https://github.com/ethpandaops/ethereum-package/issues/1420

This is a public feedback request about local/private Glamsterdam devnet behavior,
not a vulnerability report and not an endorsement.

## Public-safe summary

Batman's committed public evidence currently shows:

- 4-client smoke: all configured execution clients returned BAL bytes.
- 3-way same-head PASS: the committed subset evidence has byte-identical BAL output
  with 0 findings.
- Full 4-way same-head differential: refused on the current devnet split because all
  latest heads did not agree.

The issue asks maintainers whether this Gloas/ePBS same-head split is expected for
`glamsterdam-devnet-0`, whether additional builder/ePBS configuration is needed, and
what setup they recommend for sustained 4-EL EIP-7928 BAL conformance testing.

Keep suspected client-level findings private until reproduced and responsibly disclosed.
