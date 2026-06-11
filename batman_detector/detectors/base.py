from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Finding:
    finding_id: str
    detector_id: str
    title: str
    severity: str
    confidence: str
    trace_id: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    impact: str = ""
    recommendation: str = ""
    affected_clients: list[str] = field(default_factory=list)
    spec_refs: list[str] = field(default_factory=list)
    rule_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "detector_id": self.detector_id,
            "title": self.title,
            "severity": self.severity,
            "confidence": self.confidence,
            "trace_id": self.trace_id,
            "summary": self.summary,
            "evidence": self.evidence,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "affected_clients": self.affected_clients,
            "spec_refs": self.spec_refs,
            "rule_refs": self.rule_refs,
        }


class Detector:
    detector_id = "BASE"
    title = "Base detector"

    def run(self, trace: dict[str, Any], ruleset: dict[str, Any] | None = None) -> list[Finding]:
        raise NotImplementedError

    def _finding(
        self,
        trace: dict[str, Any],
        ordinal: int,
        *,
        title: str,
        severity: str,
        confidence: str,
        summary: str,
        evidence: list[str],
        impact: str,
        recommendation: str,
        affected_clients: list[str] | None = None,
        spec_refs: list[str] | None = None,
        rule_refs: list[str] | None = None,
    ) -> Finding:
        trace_id = trace.get("trace_id", "unknown-trace")
        return Finding(
            finding_id=f"{trace_id}:{self.detector_id}:{ordinal:03d}",
            detector_id=self.detector_id,
            title=title,
            severity=severity,
            confidence=confidence,
            trace_id=trace_id,
            summary=summary,
            evidence=evidence,
            impact=impact,
            recommendation=recommendation,
            affected_clients=affected_clients or [],
            spec_refs=spec_refs or [],
            rule_refs=rule_refs or [],
        )

