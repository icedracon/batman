"""Machine-readable compatibility snapshots for Batman live evidence.

The snapshot is intentionally conservative: it summarizes committed public-safe
artifacts and records the same honesty gates as the README. It does not turn a
split-devnet run into a 4-way differential claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "batman.compatibility_snapshot.v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _artifact(path: Path, kind: str) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"artifact does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"artifact is not a regular file: {path}")
    return {
        "kind": kind,
        "path": path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _head_groups(client_heads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str], list[str]] = {}
    for client_id, head in client_heads.items():
        key = (int(head.get("number", -1)), str(head.get("hash", "")))
        grouped.setdefault(key, []).append(client_id)
    groups = []
    for (number, block_hash), clients in grouped.items():
        groups.append(
            {
                "number": number,
                "hash": block_hash,
                "clients": sorted(clients),
            }
        )
    return sorted(groups, key=lambda item: (-len(item["clients"]), item["number"], item["hash"]))


def _finding_count_from_report(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Finding count:"):
            raw = line.split("`", 2)
            if len(raw) >= 2 and raw[1].isdigit():
                return int(raw[1])
    return None


def build_compatibility_snapshot(
    *,
    heads_path: Path,
    smoke_path: Path,
    four_way_output_path: Path | None = None,
    subset_trace_path: Path | None = None,
    subset_report_path: Path | None = None,
    snapshot_id: str = "gloas-devnet-bal-snapshot",
    batman_commit: str = "unknown",
    spec: str = "eip-7928",
    devnet: str = "gloas-private-devnet",
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a compact JSON summary from public-safe live evidence artifacts."""
    heads = _read_json(heads_path)
    smoke = _read_json(smoke_path)
    client_heads = heads.get("client_heads")
    smoke_clients = smoke.get("clients")
    if not isinstance(client_heads, dict):
        raise ValueError("heads artifact must contain object `client_heads`")
    if not isinstance(smoke_clients, list):
        raise ValueError("smoke artifact must contain list `clients`")

    smoke_by_client = {
        item.get("client_id"): item
        for item in smoke_clients
        if isinstance(item, dict) and isinstance(item.get("client_id"), str)
    }
    subset_clients: list[str] = []
    if subset_trace_path and subset_trace_path.exists():
        subset_trace = _read_json(subset_trace_path)
        observations = subset_trace.get("observations", [])
        if isinstance(observations, list):
            subset_clients = sorted(
                {
                    item.get("client_id")
                    for item in observations
                    if isinstance(item, dict) and isinstance(item.get("client_id"), str)
                }
            )

    clients = []
    for client_id in sorted(set(client_heads) | set(smoke_by_client)):
        head = client_heads.get(client_id, {})
        smoke_item = smoke_by_client.get(client_id, {})
        clients.append(
            {
                "client_id": client_id,
                "head_number": head.get("number"),
                "head_hash": head.get("hash"),
                "engine_has_bal": bool(smoke_item.get("engine_has_bal")),
                "engine_bal_bytes": smoke_item.get("engine_bal_bytes"),
                "rpc_has_bal": bool(smoke_item.get("rpc_has_bal")),
                "included_in_same_head_differential": client_id in subset_clients,
            }
        )

    artifacts = [
        _artifact(heads_path, "head-agreement"),
        _artifact(smoke_path, "bal-smoke"),
    ]
    if four_way_output_path:
        artifacts.append(_artifact(four_way_output_path, "four-way-differential-output"))
    if subset_trace_path:
        artifacts.append(_artifact(subset_trace_path, "subset-trace"))
    if subset_report_path:
        artifacts.append(_artifact(subset_report_path, "subset-report"))

    same_head_agree = bool(heads.get("agree"))
    subset_finding_count = _finding_count_from_report(subset_report_path)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": {
            "fork": "Glamsterdam",
            "spec": spec,
            "eips": ["EIP-7928"],
        },
        "batman": {
            "commit": batman_commit,
        },
        "devnet": {
            "name": devnet,
            "provenance": "private-devnet",
        },
        "head_agreement": {
            "agree": same_head_agree,
            "groups": _head_groups(client_heads),
        },
        "clients": clients,
        "results": {
            "smoke_clients": len(clients),
            "smoke_clients_with_bal": sum(1 for item in clients if item["engine_has_bal"]),
            "four_way_same_head_differential": "available" if same_head_agree else "refused_devnet_split",
            "subset_same_head_differential": {
                "clients": subset_clients,
                "finding_count": subset_finding_count,
            },
        },
        "artifacts": sorted(artifacts, key=lambda item: item["path"]),
        "safety": {
            "mainnet": False,
            "public_rpc": False,
            "bounty_claim": False,
            "note": "Engineering compatibility snapshot only; suspected client issues require private disclosure.",
        },
        "metadata": dict(sorted((metadata or {}).items())),
    }
    return snapshot


def _parse_metadata(values: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"metadata must use key=value form: {value}")
        key, item_value = value.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("metadata key cannot be empty")
        metadata[key] = item_value.strip()
    return metadata


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Batman compatibility snapshot")
    parser.add_argument("--heads", required=True, help="bal-heads-live JSON artifact")
    parser.add_argument("--smoke", required=True, help="bal-smoke-live JSON artifact")
    parser.add_argument("--four-way-output", help="4-way differential command output artifact")
    parser.add_argument("--subset-trace", help="subset live trace artifact")
    parser.add_argument("--subset-report", help="subset live report artifact")
    parser.add_argument("--output", required=True)
    parser.add_argument("--snapshot-id", default="gloas-devnet-bal-snapshot")
    parser.add_argument("--batman-commit", default="unknown")
    parser.add_argument("--spec", default="eip-7928")
    parser.add_argument("--devnet", default="gloas-private-devnet")
    parser.add_argument("--metadata", action="append", default=[], help="key=value metadata; repeatable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        snapshot = build_compatibility_snapshot(
            heads_path=Path(args.heads),
            smoke_path=Path(args.smoke),
            four_way_output_path=Path(args.four_way_output) if args.four_way_output else None,
            subset_trace_path=Path(args.subset_trace) if args.subset_trace else None,
            subset_report_path=Path(args.subset_report) if args.subset_report else None,
            snapshot_id=args.snapshot_id,
            batman_commit=args.batman_commit,
            spec=args.spec,
            devnet=args.devnet,
            metadata=_parse_metadata(args.metadata),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"SNAPSHOT ERROR: {exc}")
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE: {output}")
    print(f"clients: {len(snapshot['clients'])}")
    print(f"four-way: {snapshot['results']['four_way_same_head_differential']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

