from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .detectors import DETECTORS
from .reporting import build_markdown_report
from .schemas import (
    ValidationError,
    load_json,
    validate_audit_target,
    validate_compatibility_snapshot,
    validate_fuzz_campaign,
    validate_ruleset,
    validate_trace,
)
from .static_scan import scan_audit_target


def _package_version() -> str:
    try:
        return version("batman-detector")
    except PackageNotFoundError:
        return "0+unknown"


def _print_findings(findings) -> None:
    for finding in findings:
        print()
        print(f"[{finding.severity.upper()}] {finding.title}")
        print(f"detector: {finding.detector_id}")
        print(f"confidence: {finding.confidence}")
        print(f"summary: {finding.summary}")
        if finding.affected_clients:
            print(f"affected clients: {', '.join(finding.affected_clients)}")
        if finding.evidence:
            print("evidence:")
            for item in finding.evidence:
                print(f"  - {item}")
        print(f"recommendation: {finding.recommendation}")


def _cmd_validate(args: argparse.Namespace) -> int:
    data = load_json(Path(args.path))
    try:
        if args.schema == "audit-target":
            warnings = validate_audit_target(data)
        elif args.schema == "fuzz-campaign":
            warnings = validate_fuzz_campaign(data)
        elif args.schema == "compatibility-snapshot":
            warnings = validate_compatibility_snapshot(data)
        elif args.schema == "ruleset":
            warnings = validate_ruleset(data)
        else:
            warnings = validate_trace(data)
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    print(f"VALID: {args.path}")
    for warning in warnings:
        print(f"warning: {warning}")
    return 0


def _cmd_list_detectors(_: argparse.Namespace) -> int:
    for detector_id, detector_cls in sorted(DETECTORS.items()):
        detector = detector_cls()
        print(f"{detector_id}\t{detector.title}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    trace = load_json(Path(args.trace))
    ruleset = load_json(Path(args.ruleset)) if args.ruleset else None

    try:
        trace_warnings = validate_trace(trace)
        ruleset_warnings = validate_ruleset(ruleset) if ruleset is not None else []
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    selected = args.detector or trace.get("scenario", {}).get("detector_ids", [])
    if not selected:
        selected = sorted(DETECTORS)

    unknown = [detector_id for detector_id in selected if detector_id not in DETECTORS]
    if unknown:
        print(f"UNKNOWN DETECTOR: {', '.join(unknown)}", file=sys.stderr)
        return 2

    findings = []
    for detector_id in selected:
        detector = DETECTORS[detector_id]()
        findings.extend(detector.run(trace, ruleset=ruleset))

    if args.format == "json":
        payload = {
            "trace_id": trace.get("trace_id"),
            "finding_count": len(findings),
            "warnings": trace_warnings + ruleset_warnings,
            "findings": [finding.to_dict() for finding in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"Trace: {trace.get('trace_id', '<unknown>')}")
    print(f"Findings: {len(findings)}")
    for warning in trace_warnings + ruleset_warnings:
        print(f"warning: {warning}")

    _print_findings(findings)
    return 0


def _cmd_static_scan(args: argparse.Namespace) -> int:
    path = Path(args.audit_target)
    target = load_json(path)
    try:
        warnings = validate_audit_target(target)
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    issues = scan_audit_target(target, path.parent)
    if args.format == "json":
        payload = {
            "target_id": target.get("target_id"),
            "issue_count": len(issues),
            "warnings": warnings,
            "issues": [issue.to_dict() for issue in issues],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"Audit target: {target.get('target_id', '<unknown>')}")
    print(f"Static issues: {len(issues)}")
    for warning in warnings:
        print(f"warning: {warning}")
    for issue in issues:
        print()
        print(f"[{issue.severity.upper()}] {issue.title}")
        print(f"id: {issue.issue_id}")
        print(f"summary: {issue.summary}")
        if issue.evidence:
            print("evidence:")
            for item in issue.evidence:
                print(f"  - {item}")
        print(f"recommendation: {issue.recommendation}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    trace = load_json(Path(args.trace))
    ruleset = load_json(Path(args.ruleset)) if args.ruleset else None
    try:
        validate_trace(trace)
        if ruleset:
            validate_ruleset(ruleset)
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    selected = args.detector or trace.get("scenario", {}).get("detector_ids", [])
    unknown = [detector_id for detector_id in selected if detector_id not in DETECTORS]
    if unknown:
        print(f"UNKNOWN DETECTOR: {', '.join(unknown)}", file=sys.stderr)
        return 2

    report = build_markdown_report(trace, ruleset=ruleset, detector_ids=selected)
    if args.output:
        output = Path(args.output)
        output.write_text(report, encoding="utf-8")
        print(f"WROTE: {output}")
    else:
        print(report, end="")
    return 0


def _select_endpoints(endpoints: list[dict], include: list[str] | None, exclude: list[str] | None) -> list[dict]:
    known = {entry["client_id"] for entry in endpoints}
    include_set = set(include or [])
    exclude_set = set(exclude or [])
    unknown = sorted((include_set | exclude_set) - known)
    if unknown:
        raise ValueError(f"unknown client id(s): {', '.join(unknown)}")
    selected = [
        entry for entry in endpoints
        if (not include_set or entry["client_id"] in include_set)
        and entry["client_id"] not in exclude_set
    ]
    if not selected:
        raise ValueError("client selection is empty")
    return selected


def _cmd_bal_diff_live(args: argparse.Namespace) -> int:
    from .harness import (
        build_live_trace,
        collect_bals,
        load_endpoints,
        load_jwt_secret,
        nodes_from_endpoints,
        wait_for_shared_payload_spec,
    )

    try:
        endpoints = _select_endpoints(
            load_endpoints(Path(args.endpoints)),
            args.client,
            args.exclude_client,
        )
    except ValueError as exc:
        print(f"INVALID ENDPOINTS: {exc}", file=sys.stderr)
        return 2
    jwt_secret = load_jwt_secret(Path(args.jwt_secret)) if args.jwt_secret else None
    spec = load_json(Path(args.payload_spec))
    nodes = nodes_from_endpoints(endpoints, jwt_secret=jwt_secret)

    # --refresh: rebuild the spec only when all clients share the latest head, so every
    # client builds the SAME next block. Historical common ancestors are not enough:
    # some clients reject building on an older parent after forkchoice has advanced.
    if args.refresh:
        fresh = wait_for_shared_payload_spec(
            endpoints,
            seed_attrs=spec.get("payload_attributes", {}),
            timeout_seconds=args.wait_shared_head,
            poll_seconds=args.poll_interval,
        )
        head = fresh["shared_head"]
        print(f"shared head: #{head['number']} {head['hash']} (all clients agree: {head['agree']})")
        if not head["agree"]:
            print(f"  current heads: {head['client_heads']}")
            print("  not running same-head differential; retry or use --wait-shared-head SECONDS")
            return 1
        spec = {**spec, "forkchoice_state": fresh["forkchoice_state"], "payload_attributes": fresh["payload_attributes"]}

    # Collect each EL's BAL, wrap it in a live-provenance trace, and run it through
    # the detector so a real cross-client divergence escalates to critical.
    raw_by_client, notes = collect_bals(
        nodes, spec.get("forkchoice_state", {}), spec.get("payload_attributes")
    )
    trace = build_live_trace(raw_by_client, header_hash=spec.get("block_access_list_hash"), notes=notes)
    findings = DETECTORS["BAL_SYSTEM_CONTRACT_INDEX_CONFUSION"]().run(trace)
    if args.output_trace:
        output = Path(args.output_trace)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(trace, indent=2, sort_keys=True), encoding="utf-8")
        print(f"WROTE trace: {output}")
    if args.output_report:
        report = build_markdown_report(
            trace,
            detector_ids=["BAL_SYSTEM_CONTRACT_INDEX_CONFUSION"],
        )
        output = Path(args.output_report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"WROTE report: {output}")

    print(f"clients queried: {sorted(nodes)}")
    print(f"clients returning a BAL: {sorted(raw_by_client)}")
    for client_id, note in sorted(notes.items()):
        print(f"  note[{client_id}]: {note}")
    print(f"findings: {len(findings)}")
    _print_findings(findings)
    return 3 if any(finding.severity in ("critical", "high") for finding in findings) else 0


def _cmd_bal_smoke_live(args: argparse.Namespace) -> int:
    from .harness import load_endpoints, load_jwt_secret, smoke_probe_current_heads

    try:
        endpoints = _select_endpoints(
            load_endpoints(Path(args.endpoints)),
            args.client,
            args.exclude_client,
        )
    except ValueError as exc:
        print(f"INVALID ENDPOINTS: {exc}", file=sys.stderr)
        return 2
    jwt_secret = load_jwt_secret(Path(args.jwt_secret)) if args.jwt_secret else None
    spec = load_json(Path(args.payload_spec))
    results = smoke_probe_current_heads(
        endpoints,
        jwt_secret=jwt_secret,
        payload_attributes=spec.get("payload_attributes", {}),
    )

    if args.format == "json":
        print(json.dumps({"clients": results}, indent=2, sort_keys=True))
    else:
        print(f"clients queried: {[item['client_id'] for item in results]}")
        for item in results:
            status = "BAL" if item.get("engine_has_bal") else "no BAL"
            detail = item.get("engine_bal_bytes")
            suffix = f" ({detail} bytes)" if detail is not None else ""
            head = item.get("head_number", "<unknown>")
            print(f"  {item['client_id']}: {status}{suffix}; head={head}; rpc_bal={item.get('rpc_has_bal')}")
            if item.get("note"):
                print(f"    note: {item['note']}")
            if item.get("error"):
                print(f"    error: {item['error']}")

    return 0 if all(item.get("engine_has_bal") for item in results) else 1


def _cmd_bal_heads_live(args: argparse.Namespace) -> int:
    from .harness import latest_head_agreement, load_endpoints

    try:
        endpoints = _select_endpoints(
            load_endpoints(Path(args.endpoints)),
            args.client,
            args.exclude_client,
        )
    except ValueError as exc:
        print(f"INVALID ENDPOINTS: {exc}", file=sys.stderr)
        return 2
    status = latest_head_agreement(endpoints)
    payload = {"agree": status["agree"], "client_heads": status["client_heads"]}
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"latest heads agree: {status['agree']}")
        for client_id, head in sorted(status["client_heads"].items()):
            print(f"  {client_id}: #{head['number']} {head['hash']}")
    return 0 if status["agree"] else 1


def _cmd_compatibility_snapshot(args: argparse.Namespace) -> int:
    from .compatibility import build_compatibility_snapshot

    try:
        metadata = {}
        for item in args.metadata or []:
            if "=" not in item:
                raise ValueError(f"metadata must use key=value form: {item}")
            key, value = item.split("=", 1)
            if not key.strip():
                raise ValueError("metadata key cannot be empty")
            metadata[key.strip()] = value.strip()
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
            metadata=metadata,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"SNAPSHOT ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE: {output}")
    print(f"clients: {len(snapshot['clients'])}")
    print(f"four-way: {snapshot['results']['four_way_same_head_differential']}")
    return 0


def _cmd_evidence_pack(args: argparse.Namespace) -> int:
    from .evidence_bundle import (
        GLAMSTERDAM_BAL_PRESET_ARTIFACTS,
        build_public_evidence_bundle,
        verify_public_evidence_bundle,
    )

    if args.preset != "glamsterdam-bal":
        print(f"UNKNOWN PRESET: {args.preset}", file=sys.stderr)
        return 2

    artifacts = list(GLAMSTERDAM_BAL_PRESET_ARTIFACTS)
    try:
        manifest = build_public_evidence_bundle(
            artifacts=artifacts,
            output_dir=Path(args.output_dir),
            metadata={
                "preset": args.preset,
                "spec": "eip-7928",
                "provenance": "private-devnet",
            },
        )
        verification = verify_public_evidence_bundle(artifacts, Path(args.output_dir)) if args.verify else None
    except (OSError, ValueError) as exc:
        prefix = "VERIFY ERROR" if args.verify else "BUNDLE ERROR"
        print(f"{prefix}: {exc}", file=sys.stderr)
        return 2
    print(f"WROTE: {Path(args.output_dir) / 'manifest.json'}")
    print(f"artifacts: {len(manifest['artifacts'])}")
    if verification:
        detector_names = ", ".join(sorted(DETECTORS))
        four_way_label = {
            "refused_devnet_split": "refused on current devnet split",
            "available": "available",
        }.get(verification["four_way"], verification["four_way"])
        print("VERIFY OK: public Glamsterdam BAL evidence bundle")
        print(f"detectors: {detector_names}")
        print(f"public evidence: {verification['smoke']}; {verification['subset']}; full 4-way {four_way_label}")
        print(f"3-way findings: {verification['finding_count']}")
        print("safety: local/private-devnet evidence only; no mainnet/public-RPC/bounty claim")
    return 0


def _add_client_selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--client", action="append", help="Only include this client id; can be repeated")
    parser.add_argument("--exclude-client", action="append", help="Exclude this client id; can be repeated")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batman",
        description="Run Glamsterdam/Gloas detector traces.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a trace or ruleset file")
    validate.add_argument("path")
    validate.add_argument(
        "--schema",
        choices=["trace", "ruleset", "audit-target", "fuzz-campaign", "compatibility-snapshot"],
        default="trace",
    )
    validate.set_defaults(func=_cmd_validate)

    run = subparsers.add_parser("run", help="Run detectors against a trace")
    run.add_argument("trace")
    run.add_argument("--ruleset")
    run.add_argument("--detector", action="append", help="Detector id to run. Can be repeated.")
    run.add_argument("--format", choices=["text", "json"], default="text")
    run.set_defaults(func=_cmd_run)

    list_detectors = subparsers.add_parser("list-detectors", help="Show available detectors")
    list_detectors.set_defaults(func=_cmd_list_detectors)

    static_scan = subparsers.add_parser("static-scan", help="Run pre-behavior audit checks")
    static_scan.add_argument("audit_target")
    static_scan.add_argument("--format", choices=["text", "json"], default="text")
    static_scan.set_defaults(func=_cmd_static_scan)

    report = subparsers.add_parser("report", help="Generate a private first-scan Markdown report")
    report.add_argument("trace")
    report.add_argument("--ruleset")
    report.add_argument("--detector", action="append", help="Detector id to include. Can be repeated.")
    report.add_argument("--output")
    report.set_defaults(func=_cmd_report)

    heads = subparsers.add_parser(
        "bal-heads-live",
        help="Show latest-head agreement across live EL RPC endpoints",
    )
    heads.add_argument("--endpoints", required=True, help="endpoints.json from devnet/endpoints.sh")
    heads.add_argument("--format", choices=["text", "json"], default="text")
    _add_client_selection_args(heads)
    heads.set_defaults(func=_cmd_bal_heads_live)

    live = subparsers.add_parser(
        "bal-diff-live",
        help="Build a payload on each EL Engine API endpoint and diff their BALs",
    )
    live.add_argument("--endpoints", required=True, help="endpoints.json from devnet/endpoints.sh")
    live.add_argument("--jwt-secret", help="path to the Engine API JWT secret (hex)")
    live.add_argument("--payload-spec", required=True,
                      help="JSON with forkchoice_state and payload_attributes")
    live.add_argument("--refresh", action="store_true",
                      help="Rebuild the spec on a shared current head so all clients build the same block")
    live.add_argument("--wait-shared-head", type=float, default=0,
                      help="With --refresh, wait up to this many seconds for all latest heads to agree")
    live.add_argument("--poll-interval", type=float, default=2,
                      help="Seconds between shared-head checks")
    live.add_argument("--output-trace", help="Write the live trace JSON artifact")
    live.add_argument("--output-report", help="Write a Markdown detector report")
    _add_client_selection_args(live)
    live.set_defaults(func=_cmd_bal_diff_live)

    smoke = subparsers.add_parser(
        "bal-smoke-live",
        help="Check whether each EL can build from its own head and return a BAL",
    )
    smoke.add_argument("--endpoints", required=True, help="endpoints.json from devnet/endpoints.sh")
    smoke.add_argument("--jwt-secret", help="path to the Engine API JWT secret (hex)")
    smoke.add_argument("--payload-spec", required=True,
                       help="JSON with payload_attributes used as a seed")
    smoke.add_argument("--format", choices=["text", "json"], default="text")
    _add_client_selection_args(smoke)
    smoke.set_defaults(func=_cmd_bal_smoke_live)

    snapshot = subparsers.add_parser(
        "compatibility-snapshot",
        help="Build a machine-readable compatibility snapshot from public live artifacts",
    )
    snapshot.add_argument("--heads", required=True, help="bal-heads-live JSON artifact")
    snapshot.add_argument("--smoke", required=True, help="bal-smoke-live JSON artifact")
    snapshot.add_argument("--four-way-output", help="4-way differential command output artifact")
    snapshot.add_argument("--subset-trace", help="subset live trace artifact")
    snapshot.add_argument("--subset-report", help="subset live report artifact")
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--snapshot-id", default="gloas-devnet-bal-snapshot")
    snapshot.add_argument("--batman-commit", default="unknown")
    snapshot.add_argument("--spec", default="eip-7928")
    snapshot.add_argument("--devnet", default="gloas-private-devnet")
    snapshot.add_argument("--metadata", action="append", help="key=value metadata; repeatable")
    snapshot.set_defaults(func=_cmd_compatibility_snapshot)

    evidence_pack = subparsers.add_parser(
        "evidence-pack",
        help="Build a preset public evidence bundle from committed artifacts",
    )
    evidence_pack.add_argument("--preset", choices=["glamsterdam-bal"], default="glamsterdam-bal")
    evidence_pack.add_argument("--output-dir", default="dist/public-evidence")
    evidence_pack.add_argument("--verify", action="store_true",
                               help="Verify source artifacts, copied files, hashes, and public evidence claims")
    evidence_pack.set_defaults(func=_cmd_evidence_pack)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
