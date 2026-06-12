# Why this matters for Ethereum clients

EIP-7928 makes Block-Level Access Lists consensus-adjacent data: execution clients must agree on the exact canonical BAL bytes and therefore on `block_access_list_hash` for the same block.

A small implementation drift can become a large interoperability problem. Ordering differences, duplicate handling, read/write classification mistakes, or incorrect `block_access_index` assignment can produce different hashes across clients even when the underlying state transition looks similar.

Batman focuses on this narrow but high-signal surface. It gives client teams and protocol researchers a reproducible private-devnet workflow to:

- generate synthetic controls for known BAL failure classes;
- fuzz canonical ordering offline;
- compare Geth, Erigon, Reth, and Nethermind BAL output on the same head;
- refuse misleading comparisons when heads do not align;
- export reviewer-safe evidence bundles with SHA-256 manifests.

The goal is upgrade readiness, not mainnet scanning: catch cross-client disagreement early, localize it precisely, and preserve evidence for responsible private disclosure.
