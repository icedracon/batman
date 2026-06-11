from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schemas import ValidationError, load_json, validate_fuzz_campaign


@dataclass
class StaticIssue:
    issue_id: str
    title: str
    severity: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "title": self.title,
            "severity": self.severity,
            "summary": self.summary,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


def scan_audit_target(target: dict[str, Any], base_dir: Path) -> list[StaticIssue]:
    issues: list[StaticIssue] = []

    issues.extend(_scan_spec_pinning(target))
    issues.extend(_scan_disclosure_gate(target))
    issues.extend(_scan_client_matrix(target))
    issues.extend(_scan_fuzz_campaigns(target, base_dir))

    return issues


def _scan_spec_pinning(target: dict[str, Any]) -> list[StaticIssue]:
    evidence = []
    for ref in target.get("spec_refs", []):
        if not isinstance(ref, dict):
            evidence.append("spec ref is not an object")
            continue
        name = ref.get("name", "<unnamed>")
        if not ref.get("commit"):
            evidence.append(f"{name}: missing commit/date pin")
        if ref.get("status") in {"draft", "unstable"} and not ref.get("review_date"):
            evidence.append(f"{name}: draft/unstable ref has no review_date")

    if not evidence:
        return []

    return [
        StaticIssue(
            issue_id="STATIC-SPEC-PINNING",
            title="Spec references are not fully pinned",
            severity="medium",
            summary="Glamsterdam/Gloas rules are moving, so every scan needs exact source pins.",
            evidence=evidence,
            recommendation="Add commit hashes or date pins and a review date for each draft/unstable source.",
        )
    ]


def _scan_disclosure_gate(target: dict[str, Any]) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    disclosure = target.get("bug_bounty", {})
    gate = target.get("deployment_gate", {})

    if not disclosure.get("private_disclosure_required", False):
        issues.append(
            StaticIssue(
                issue_id="STATIC-DISCLOSURE-PRIVATE",
                title="Private disclosure is not enforced",
                severity="high",
                summary="Bug-bounty findings can become ineligible if they are published too early.",
                evidence=["bug_bounty.private_disclosure_required is not true"],
                recommendation="Set private_disclosure_required=true and keep suspected findings out of public issues.",
            )
        )

    allowed = set(disclosure.get("allowed_test_environments", []))
    if "local_devnet" not in allowed and "private_devnet" not in allowed:
        issues.append(
            StaticIssue(
                issue_id="STATIC-DISCLOSURE-TESTNET",
                title="Safe test environment is not explicit",
                severity="high",
                summary="Protocol bug hunting should be constrained to local or private networks.",
                evidence=[f"allowed_test_environments={sorted(allowed)}"],
                recommendation="Add local_devnet or private_devnet to allowed test environments.",
            )
        )

    if gate.get("blocks_real_world_deployment") is not True:
        issues.append(
            StaticIssue(
                issue_id="STATIC-DEPLOYMENT-GATE",
                title="Deployment gate is not blocking",
                severity="medium",
                summary="The audit target does not clearly block deployment when high-severity issues exist.",
                evidence=["deployment_gate.blocks_real_world_deployment is not true"],
                recommendation="Require a clean high-severity scan before public deployment or public testnet use.",
            )
        )

    return issues


def _scan_client_matrix(target: dict[str, Any]) -> list[StaticIssue]:
    clients = target.get("client_matrix", [])
    if not isinstance(clients, list):
        return [
            StaticIssue(
                issue_id="STATIC-CLIENT-MATRIX-SHAPE",
                title="Client matrix is malformed",
                severity="medium",
                summary="client_matrix must be a list of client descriptors.",
                evidence=["client_matrix is not a list"],
                recommendation="Define client_matrix as a list with layer/name/version/commit fields.",
            )
        ]

    el_clients = {client.get("name") for client in clients if isinstance(client, dict) and client.get("layer") == "EL"}
    if len(el_clients) < 3:
        return [
            StaticIssue(
                issue_id="STATIC-CLIENT-MATRIX-WEAK",
                title="Execution client matrix is too small",
                severity="medium",
                summary="BAL bugs become bounty-relevant when differential behavior spans real clients.",
                evidence=[f"EL clients configured: {', '.join(sorted(el_clients)) or '<none>'}"],
                recommendation="Use at least three EL clients for first scan, ideally Geth, Reth, Nethermind, Erigon, and Besu.",
            )
        ]
    return []


def _scan_fuzz_campaigns(target: dict[str, Any], base_dir: Path) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    required_invariants = {
        "bal_phase_index_invariant",
        "cross_client_bal_hash_equivalence",
        "cross_client_payload_status_equivalence",
    }

    campaign_paths = target.get("fuzz_campaigns", [])
    if not campaign_paths:
        return [
            StaticIssue(
                issue_id="STATIC-FUZZ-MISSING",
                title="No fuzz campaign is attached",
                severity="medium",
                summary="A first scan should define what behavior will be fuzzed before running clients.",
                evidence=["fuzz_campaigns is empty"],
                recommendation="Attach at least one fuzz campaign file with mutators and invariants.",
            )
        ]

    for raw_path in campaign_paths:
        path = base_dir / raw_path
        try:
            campaign = load_json(path)
            validate_fuzz_campaign(campaign)
        except ValidationError as exc:
            issues.append(
                StaticIssue(
                    issue_id="STATIC-FUZZ-INVALID",
                    title="Fuzz campaign cannot be loaded",
                    severity="high",
                    summary="A configured fuzz campaign is missing or invalid.",
                    evidence=[f"{raw_path}: {exc}"],
                    recommendation="Fix the campaign file before running behavioral fuzzing.",
                )
            )
            continue

        names = {
            invariant.get("name")
            for invariant in campaign.get("invariants", [])
            if isinstance(invariant, dict)
        }
        missing = sorted(required_invariants - names)
        if missing:
            issues.append(
                StaticIssue(
                    issue_id="STATIC-FUZZ-INVARIANTS",
                    title="Fuzz campaign lacks key invariants",
                    severity="medium",
                    summary="The campaign may generate inputs without checking the properties needed for bounty-grade evidence.",
                    evidence=[f"{raw_path}: missing {', '.join(missing)}"],
                    recommendation="Add BAL phase/index and cross-client equivalence invariants.",
                )
            )

    return issues

