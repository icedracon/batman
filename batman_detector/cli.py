from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .detectors import DETECTORS
from .reporting import build_markdown_report
from .schemas import (
    ValidationError,
    load_json,
    validate_audit_target,
    validate_fuzz_campaign,
    validate_ruleset,
    validate_trace,
)
from .static_scan import scan_audit_target


def _cmd_validate(args: argparse.Namespace) -> int:
    data = load_json(Path(args.path))
    try:
        if args.schema == "audit-target":
            warnings = validate_audit_target(data)
        elif args.schema == "fuzz-campaign":
            warnings = validate_fuzz_campaign(data)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batman",
        description="Run Glamsterdam/Gloas detector traces.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a trace or ruleset file")
    validate.add_argument("path")
    validate.add_argument(
        "--schema",
        choices=["trace", "ruleset", "audit-target", "fuzz-campaign"],
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
