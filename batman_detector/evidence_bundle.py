"""Build a compact, reviewer-friendly public evidence bundle.

Only explicitly listed files are copied. Secret-looking names, symlinks, unsupported
extensions, and oversized files are rejected to reduce accidental disclosure risk.

Example:

    python -m batman_detector.evidence_bundle \
      --output-dir dist/public-evidence \
      --artifact artifacts/devnet5-live-heads.json \
      --artifact artifacts/devnet5-live-smoke.json \
      --artifact artifacts/devnet5-live-4way-diff.txt \
      --artifact artifacts/devnet5-live-trace.json \
      --artifact artifacts/devnet5-live-report.md \
      --metadata spec=eip-7928 \
      --metadata provenance=private-devnet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import ValidationError, validate_compatibility_snapshot

ALLOWED_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml"}
BLOCKED_NAME_FRAGMENTS = (
    "jwt",
    "secret",
    "private",
    "privkey",
    "password",
    "passwd",
    "token",
    "keystore",
    "mnemonic",
    ".env",
)
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
GLAMSTERDAM_BAL_PRESET_ARTIFACTS = [
    Path("artifacts/devnet5-live-heads.json"),
    Path("artifacts/devnet5-live-smoke.json"),
    Path("artifacts/devnet5-live-4way-diff.txt"),
    Path("artifacts/devnet5-live-trace.json"),
    Path("artifacts/devnet5-live-report.md"),
    Path("artifacts/compatibility-snapshot.gloas-devnet5.json"),
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_name(path: Path) -> str:
    name = path.name
    lower = name.lower()
    if not name or name in {".", ".."}:
        raise ValueError(f"invalid artifact name: {path}")
    if any(fragment in lower for fragment in BLOCKED_NAME_FRAGMENTS):
        raise ValueError(f"refusing secret-looking artifact name: {name}")
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_SUFFIXES))
        raise ValueError(f"unsupported artifact extension for {name}; allowed: {allowed}")
    return name


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _finding_count_from_report(path: Path) -> int | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Finding count:"):
            parts = line.split("`")
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def _source_artifact_info(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"refusing symlink artifact: {path}")
    if not path.exists():
        raise ValueError(f"artifact does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"artifact is not a regular file: {path}")
    name = _safe_name(path)
    data = path.read_bytes()
    if len(data) > MAX_ARTIFACT_BYTES:
        raise ValueError(f"artifact exceeds {MAX_ARTIFACT_BYTES} bytes: {path}")
    if path.suffix.lower() == ".json":
        _load_json_object(path)
    return {"name": name, "bytes": len(data), "sha256": _sha256(data)}


def build_public_evidence_bundle(
    artifacts: list[Path],
    output_dir: Path,
    metadata: dict[str, str] | None = None,
) -> dict:
    """Copy explicit public artifacts and write a reproducibility manifest."""
    if not artifacts:
        raise ValueError("at least one --artifact is required")

    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict] = []
    seen_names: set[str] = set()

    for source in artifacts:
        info = _source_artifact_info(source)
        name = info["name"]
        if name in seen_names:
            raise ValueError(f"duplicate output artifact name: {name}")
        seen_names.add(name)

        target = output_dir / name
        shutil.copyfile(source, target)
        copied.append(info)

    manifest = {
        "bundle_format": "batman-public-evidence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "explicit_artifacts_only": True,
            "secret_looking_names_rejected": True,
            "symlinks_rejected": True,
            "max_artifact_bytes": MAX_ARTIFACT_BYTES,
        },
        "metadata": dict(sorted((metadata or {}).items())),
        "artifacts": sorted(copied, key=lambda item: item["name"]),
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    readme_lines = [
        "# Batman public evidence bundle",
        "",
        "This directory was generated from explicitly selected public-safe artifacts.",
        "It is intended for reviewer inspection and reproducibility checks.",
        "",
        "## Included artifacts",
        "",
    ]
    for item in manifest["artifacts"]:
        readme_lines.append(f"- `{item['name']}` — {item['bytes']} bytes — SHA-256 `{item['sha256']}`")
    readme_lines.extend(
        [
            "",
            "## Safety note",
            "",
            "The builder rejects secret-looking filenames, symlinks, and unsupported file types.",
            "Review the copied files before publishing any bundle.",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    return manifest


def verify_public_evidence_bundle(artifacts: list[Path], output_dir: Path) -> dict[str, Any]:
    """Verify source artifacts, copied bundle files, and the compatibility story."""
    if not artifacts:
        raise ValueError("at least one artifact is required")

    source_info: dict[str, dict[str, Any]] = {}
    for path in artifacts:
        info = _source_artifact_info(path)
        source_info[info["name"]] = info
    expected_names = {path.name for path in artifacts}
    if len(expected_names) != len(artifacts):
        raise ValueError("duplicate artifact filenames are not allowed")

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"bundle manifest does not exist: {manifest_path}")
    manifest = _load_json_object(manifest_path)
    if manifest.get("bundle_format") != "batman-public-evidence-v1":
        raise ValueError("manifest bundle_format is not batman-public-evidence-v1")
    manifest_items = manifest.get("artifacts")
    if not isinstance(manifest_items, list):
        raise ValueError("manifest artifacts must be a list")

    manifest_by_name: dict[str, dict[str, Any]] = {}
    for item in manifest_items:
        if not isinstance(item, dict):
            raise ValueError("manifest artifact entries must be objects")
        name = item.get("name")
        if not isinstance(name, str):
            raise ValueError("manifest artifact name must be a string")
        if Path(name).name != name:
            raise ValueError(f"manifest artifact name must not contain directories: {name}")
        _safe_name(Path(name))
        if name in manifest_by_name:
            raise ValueError(f"duplicate manifest artifact: {name}")
        manifest_by_name[name] = item

    missing = sorted(expected_names - set(manifest_by_name))
    extra = sorted(set(manifest_by_name) - expected_names)
    if missing:
        raise ValueError(f"bundle manifest is missing artifact(s): {', '.join(missing)}")
    if extra:
        raise ValueError(f"bundle manifest contains unexpected artifact(s): {', '.join(extra)}")

    for name, expected in source_info.items():
        copied_path = output_dir / name
        if copied_path.is_symlink():
            raise ValueError(f"refusing symlink copied artifact: {copied_path}")
        if not copied_path.exists():
            raise ValueError(f"copied artifact does not exist: {copied_path}")
        data = copied_path.read_bytes()
        actual = {"bytes": len(data), "sha256": _sha256(data)}
        manifest_item = manifest_by_name[name]
        if actual["bytes"] != manifest_item.get("bytes") or actual["sha256"] != manifest_item.get("sha256"):
            raise ValueError(f"manifest hash/size mismatch for copied artifact: {name}")
        if actual != {"bytes": expected["bytes"], "sha256": expected["sha256"]}:
            raise ValueError(f"copied artifact does not match source artifact: {name}")
        if copied_path.suffix.lower() == ".json":
            _load_json_object(copied_path)

    snapshot_path = next(
        (
            path for path in artifacts
            if path.name.startswith("compatibility-snapshot.") and path.suffix.lower() == ".json"
        ),
        None,
    )
    if snapshot_path is None:
        raise ValueError("compatibility snapshot is required for --verify")
    snapshot = _load_json_object(snapshot_path)
    try:
        validate_compatibility_snapshot(snapshot)
    except ValidationError as exc:
        raise ValueError(f"invalid compatibility snapshot: {exc}") from exc

    safety = snapshot.get("safety", {})
    if safety.get("mainnet") or safety.get("public_rpc") or safety.get("bounty_claim"):
        raise ValueError("compatibility snapshot safety flags must stay public-devnet only")

    results = snapshot.get("results", {})
    if results.get("smoke_clients") != 4 or results.get("smoke_clients_with_bal") != 4:
        raise ValueError("public evidence must show BAL smoke coverage for four clients")
    four_way = results.get("four_way_same_head_differential")
    if four_way not in {"refused_devnet_split", "available"}:
        raise ValueError("four-way differential status is not recognized")
    subset = results.get("subset_same_head_differential", {})
    if not isinstance(subset, dict) or subset.get("finding_count") != 0:
        raise ValueError("public same-head subset report must have 0 findings")

    source_by_posix = {path.as_posix(): path for path in artifacts}
    for snapshot_artifact in snapshot.get("artifacts", []):
        artifact_path = snapshot_artifact.get("path")
        if not isinstance(artifact_path, str):
            raise ValueError("snapshot artifact path must be a string")
        source_path = source_by_posix.get(Path(artifact_path).as_posix())
        if source_path is None:
            raise ValueError(f"snapshot references artifact outside bundle preset: {artifact_path}")
        if _sha256(source_path.read_bytes()) != snapshot_artifact.get("sha256"):
            raise ValueError(f"snapshot hash mismatch for {artifact_path}")

    report_path = next((path for path in artifacts if "report" in path.name and path.suffix.lower() == ".md"), None)
    if report_path is None:
        raise ValueError("subset live report is required for --verify")
    if _finding_count_from_report(report_path) != 0:
        raise ValueError("subset live report must state Finding count: `0`")

    if four_way == "refused_devnet_split":
        refusal_path = next((path for path in artifacts if "4way" in path.name and path.suffix.lower() == ".txt"), None)
        if refusal_path is None:
            raise ValueError("4-way refusal output is required for split-devnet evidence")
        refusal = refusal_path.read_text(encoding="utf-8", errors="replace")
        if "not running same-head differential" not in refusal:
            raise ValueError("4-way output must show Batman refused the split-devnet comparison")

    return {
        "artifact_count": len(expected_names),
        "detector_count": 2,
        "four_way": four_way,
        "smoke": "4-client smoke",
        "subset": "4-way same-head PASS" if four_way == "available" else "3-way same-head PASS",
        "finding_count": 0,
    }


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
    parser = argparse.ArgumentParser(description="Build a safe Batman public evidence bundle")
    parser.add_argument("--artifact", action="append", default=[], help="Public-safe artifact file; repeatable")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--metadata", action="append", default=[], help="Manifest key=value metadata; repeatable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        metadata = _parse_metadata(args.metadata)
        manifest = build_public_evidence_bundle(
            artifacts=[Path(item) for item in args.artifact],
            output_dir=Path(args.output_dir),
            metadata=metadata,
        )
    except (OSError, ValueError) as exc:
        print(f"BUNDLE ERROR: {exc}")
        return 2

    print(f"WROTE: {Path(args.output_dir) / 'manifest.json'}")
    print(f"artifacts: {len(manifest['artifacts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
