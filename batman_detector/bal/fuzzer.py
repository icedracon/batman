"""Deterministic offline BAL canonicalization fuzz campaign.

This module deliberately mutates canonical EIP-7928 BAL ordering and checks that
Batman's validator catches each mutation. It never contacts a network endpoint.

Run directly:

    python -m batman_detector.bal.fuzzer --iterations 64 --format json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from random import Random
from typing import Callable

from .canonical import canonicalize, check_canonical
from .model import (
    AccountChanges,
    BalanceChange,
    BlockAccessList,
    CodeChange,
    NonceChange,
    SlotChanges,
    StorageChange,
)

Mutator = Callable[[BlockAccessList], BlockAccessList]


def _base_bal() -> BlockAccessList:
    """Return a small canonical BAL exercising every sortable category."""
    account_a = AccountChanges(
        address=bytes.fromhex("11" * 20),
        storage_changes=[
            SlotChanges(1, [StorageChange(0, 10), StorageChange(2, 12)]),
            SlotChanges(7, [StorageChange(1, 70), StorageChange(3, 73)]),
        ],
        storage_reads=[3, 9],
        balance_changes=[BalanceChange(0, 100), BalanceChange(2, 120)],
        nonce_changes=[NonceChange(0, 1), NonceChange(2, 2)],
        code_changes=[CodeChange(0, b"\x60\x00"), CodeChange(2, b"\x60\x01")],
    )
    account_b = AccountChanges(
        address=bytes.fromhex("22" * 20),
        storage_changes=[SlotChanges(5, [StorageChange(1, 50)])],
        storage_reads=[8],
    )
    return BlockAccessList(accounts=[account_a, account_b])


def _replace_first_account(bal: BlockAccessList, **changes) -> BlockAccessList:
    accounts = list(bal.accounts)
    accounts[0] = replace(accounts[0], **changes)
    return BlockAccessList(accounts=accounts)


def _reverse_accounts(bal: BlockAccessList) -> BlockAccessList:
    return BlockAccessList(accounts=list(reversed(bal.accounts)))


def _reverse_storage_slots(bal: BlockAccessList) -> BlockAccessList:
    account = bal.accounts[0]
    return _replace_first_account(bal, storage_changes=list(reversed(account.storage_changes)))


def _reverse_storage_change_indexes(bal: BlockAccessList) -> BlockAccessList:
    account = bal.accounts[0]
    slots = list(account.storage_changes)
    slots[0] = replace(slots[0], changes=list(reversed(slots[0].changes)))
    return _replace_first_account(bal, storage_changes=slots)


def _reverse_storage_reads(bal: BlockAccessList) -> BlockAccessList:
    account = bal.accounts[0]
    return _replace_first_account(bal, storage_reads=list(reversed(account.storage_reads)))


def _reverse_balance_indexes(bal: BlockAccessList) -> BlockAccessList:
    account = bal.accounts[0]
    return _replace_first_account(bal, balance_changes=list(reversed(account.balance_changes)))


def _reverse_nonce_indexes(bal: BlockAccessList) -> BlockAccessList:
    account = bal.accounts[0]
    return _replace_first_account(bal, nonce_changes=list(reversed(account.nonce_changes)))


def _reverse_code_indexes(bal: BlockAccessList) -> BlockAccessList:
    account = bal.accounts[0]
    return _replace_first_account(bal, code_changes=list(reversed(account.code_changes)))


MUTATORS: tuple[tuple[str, Mutator], ...] = (
    ("account_order", _reverse_accounts),
    ("storage_slot_order", _reverse_storage_slots),
    ("storage_change_index_order", _reverse_storage_change_indexes),
    ("storage_read_order", _reverse_storage_reads),
    ("balance_change_index_order", _reverse_balance_indexes),
    ("nonce_change_index_order", _reverse_nonce_indexes),
    ("code_change_index_order", _reverse_code_indexes),
)


def run_canonicalization_campaign(iterations: int = 64, seed: int = 7928) -> dict:
    """Run deterministic ordering mutations and return a JSON-friendly summary."""
    if iterations < 1:
        raise ValueError("iterations must be at least 1")

    canonical = _base_bal()
    baseline_violations = check_canonical(canonical)
    if baseline_violations:
        raise AssertionError(f"fuzzer baseline is not canonical: {baseline_violations}")

    rng = Random(seed)
    missed: list[dict] = []
    repair_failures: list[dict] = []
    samples: list[dict] = []
    coverage: dict[str, int] = {name: 0 for name, _ in MUTATORS}

    for iteration in range(iterations):
        # Exercise every mutation at least once before switching to seeded sampling.
        name, mutate = MUTATORS[iteration] if iteration < len(MUTATORS) else rng.choice(MUTATORS)
        coverage[name] += 1
        mutated = mutate(canonical)
        violations = check_canonical(mutated)
        repaired_violations = check_canonical(canonicalize(mutated))

        if not violations:
            missed.append({"iteration": iteration, "mutation": name})
        if repaired_violations:
            repair_failures.append(
                {
                    "iteration": iteration,
                    "mutation": name,
                    "violations": repaired_violations,
                }
            )
        if len(samples) < 8:
            samples.append(
                {
                    "iteration": iteration,
                    "mutation": name,
                    "detected_violations": violations,
                    "canonicalize_repaired": not repaired_violations,
                }
            )

    return {
        "campaign": "BAL_CANONICALIZATION_ORDERING",
        "offline_only": True,
        "seed": seed,
        "iterations": iterations,
        "mutator_count": len(MUTATORS),
        "coverage": coverage,
        "missed_mutations": missed,
        "repair_failures": repair_failures,
        "ok": not missed and not repair_failures,
        "samples": samples,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Batman's offline BAL canonicalization campaign")
    parser.add_argument("--iterations", type=int, default=64)
    parser.add_argument("--seed", type=int, default=7928)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = run_canonicalization_campaign(iterations=args.iterations, seed=args.seed)
    except (AssertionError, ValueError) as exc:
        print(f"INVALID CAMPAIGN: {exc}")
        return 2

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"campaign: {summary['campaign']}")
        print(f"offline only: {summary['offline_only']}")
        print(f"seed: {summary['seed']}")
        print(f"iterations: {summary['iterations']}")
        print(f"coverage: {summary['coverage']}")
        print(f"missed mutations: {len(summary['missed_mutations'])}")
        print(f"repair failures: {len(summary['repair_failures'])}")
        print(f"result: {'PASS' if summary['ok'] else 'FAIL'}")
    return 0 if summary["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
