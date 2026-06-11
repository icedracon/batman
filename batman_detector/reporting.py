from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .detectors import DETECTORS


def build_markdown_report(
    trace: dict[str, Any],
    ruleset: dict[str, Any] | None = None,
    detector_ids: list[str] | None = None,
) -> str:
    selected = detector_ids or trace.get("scenario", {}).get("detector_ids", []) or sorted(DETECTORS)
    findings = []
    for detector_id in selected:
        detector = DETECTORS[detector_id]()
        findings.extend(detector.run(trace, ruleset=ruleset))

    lines = [
        "# Batman First-Scan Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Trace: `{trace.get('trace_id', '<unknown>')}`",
        f"Target fork: `{trace.get('target', {}).get('fork', '<unknown>')}`",
        f"Finding count: `{len(findings)}`",
        "",
        "## Disclosure Handling",
        "",
        "Keep this report private if any finding may affect live clients, public testnets, or upcoming fork code.",
        "Use only local/private devnets until maintainers or the bug bounty process authorize disclosure.",
        "",
        "## Findings",
        "",
    ]

    if not findings:
        lines.append("No findings were produced by the selected detectors.")
        return "\n".join(lines) + "\n"

    for finding in findings:
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"- Detector: `{finding.detector_id}`",
                f"- Severity: `{finding.severity}`",
                f"- Confidence: `{finding.confidence}`",
                f"- Finding ID: `{finding.finding_id}`",
                "",
                finding.summary,
                "",
                "**Evidence**",
                "",
            ]
        )
        for item in finding.evidence:
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "**Impact**",
                "",
                finding.impact or "Impact not specified.",
                "",
                "**Recommendation**",
                "",
                finding.recommendation or "Recommendation not specified.",
                "",
            ]
        )

    return "\n".join(lines) + "\n"
