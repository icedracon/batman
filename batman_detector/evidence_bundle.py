"""Build a compact, reviewer-friendly public evidence bundle.

Only explicitly listed files are copied. Secret-looking names, symlinks, unsupported
extensions, and oversized files are rejected to reduce accidental disclosure risk.

Example:

    python -m batman_detector.evidence_bundle \
      --output-dir dist/public-evidence \
      --artifact artifacts/live-heads.json \
      --artifact artifacts/live-smoke.json \
      --artifact artifacts/live-4way-diff.txt \
      --artifact artifacts/live-3way-diff.txt \
      --artifact artifacts/subset-live-report.md \
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
        if source.is_symlink():
            raise ValueError(f"refusing symlink artifact: {source}")
        if not source.exists():
            raise ValueError(f"artifact does not exist: {source}")
        if not source.is_file():
            raise ValueError(f"artifact is not a regular file: {source}")

        name = _safe_name(source)
        if name in seen_names:
            raise ValueError(f"duplicate output artifact name: {name}")
        seen_names.add(name)

        data = source.read_bytes()
        if len(data) > MAX_ARTIFACT_BYTES:
            raise ValueError(f"artifact exceeds {MAX_ARTIFACT_BYTES} bytes: {source}")

        target = output_dir / name
        shutil.copyfile(source, target)
        copied.append(
            {
                "name": name,
                "bytes": len(data),
                "sha256": _sha256(data),
            }
        )

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
