from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when a Batman JSON artifact is structurally invalid."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return data


def _require_object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValidationError(f"`{key}` must be an object")
    return value


def _require_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValidationError(f"`{key}` must be a list")
    return value


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"`{key}` must be a non-empty string")
    return value


def validate_trace(data: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if data.get("schema_version") != "batman.trace.v1":
        raise ValidationError("`schema_version` must be `batman.trace.v1`")

    _require_str(data, "trace_id")
    _require_str(data, "created_at")
    _require_object(data, "target")
    environment = _require_object(data, "environment")
    scenario = _require_object(data, "scenario")
    block = _require_object(data, "block")
    events = _require_list(data, "events")

    detector_ids = scenario.get("detector_ids", [])
    if not isinstance(detector_ids, list) or not all(isinstance(item, str) for item in detector_ids):
        raise ValidationError("`scenario.detector_ids` must be a list of strings")

    transaction_count = block.get("transaction_count")
    if not isinstance(transaction_count, int) or transaction_count < 0:
        raise ValidationError("`block.transaction_count` must be a non-negative integer")

    clients = environment.get("clients", [])
    if not isinstance(clients, list):
        raise ValidationError("`environment.clients` must be a list")

    client_ids = set()
    for client in clients:
        if not isinstance(client, dict):
            raise ValidationError("each client must be an object")
        client_id = _require_str(client, "id")
        if client_id in client_ids:
            raise ValidationError(f"duplicate client id: {client_id}")
        client_ids.add(client_id)

    event_ids = set()
    for event in events:
        if not isinstance(event, dict):
            raise ValidationError("each event must be an object")
        event_id = _require_str(event, "event_id")
        if event_id in event_ids:
            raise ValidationError(f"duplicate event id: {event_id}")
        event_ids.add(event_id)
        _require_str(event, "kind")

    observations = data.get("observations", [])
    if not isinstance(observations, list):
        raise ValidationError("`observations` must be a list when present")
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValidationError("each observation must be an object")
        client_id = observation.get("client_id")
        if client_id and client_ids and client_id not in client_ids:
            warnings.append(f"observation references unknown client id: {client_id}")

    provenance = data.get("provenance")
    if provenance is None:
        warnings.append("trace has no provenance; synthetic/imported data cannot be bounty-grade")
    elif not isinstance(provenance, dict):
        raise ValidationError("`provenance` must be an object when present")
    else:
        kind = provenance.get("kind")
        if kind not in {"synthetic_fixture", "imported_corpus", "live_devnet", "live_client", "private_devnet"}:
            raise ValidationError("`provenance.kind` is not recognized")
        if provenance.get("bounty_eligible") is True and kind not in {"live_devnet", "live_client", "private_devnet"}:
            warnings.append("only live/private-devnet provenance should be marked bounty_eligible")

    if not events:
        warnings.append("trace has no events")
    if not client_ids:
        warnings.append("trace has no client metadata")
    return warnings


def validate_ruleset(data: dict[str, Any] | None) -> list[str]:
    if data is None:
        return []
    warnings: list[str] = []
    if data.get("schema_version") != "batman.ruleset.v1":
        raise ValidationError("`schema_version` must be `batman.ruleset.v1`")

    _require_str(data, "ruleset_id")
    _require_str(data, "target_fork")
    rules = _require_list(data, "rules")
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValidationError("each rule must be an object")
        _require_str(rule, "rule_id")
        _require_str(rule, "detector_id")

    if not rules:
        warnings.append("ruleset has no rules")
    return warnings


def validate_audit_target(data: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if data.get("schema_version") != "batman.audit_target.v1":
        raise ValidationError("`schema_version` must be `batman.audit_target.v1`")

    _require_str(data, "target_id")
    _require_str(data, "name")
    _require_str(data, "target_type")
    _require_object(data, "scope")
    _require_list(data, "spec_refs")

    detector_ids = data.get("detector_ids", [])
    if not isinstance(detector_ids, list) or not all(isinstance(item, str) for item in detector_ids):
        raise ValidationError("`detector_ids` must be a list of strings")

    files = data.get("files", [])
    if not isinstance(files, list):
        raise ValidationError("`files` must be a list when present")
    for file_ref in files:
        if not isinstance(file_ref, dict):
            raise ValidationError("each file reference must be an object")
        _require_str(file_ref, "path")
        _require_str(file_ref, "kind")

    fuzz_campaigns = data.get("fuzz_campaigns", [])
    if not isinstance(fuzz_campaigns, list):
        raise ValidationError("`fuzz_campaigns` must be a list when present")

    if not detector_ids:
        warnings.append("audit target has no detector ids")
    if not data.get("bug_bounty"):
        warnings.append("audit target has no bug bounty disclosure settings")
    return warnings


def validate_fuzz_campaign(data: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if data.get("schema_version") != "batman.fuzz_campaign.v1":
        raise ValidationError("`schema_version` must be `batman.fuzz_campaign.v1`")

    _require_str(data, "campaign_id")
    _require_str(data, "target_id")
    _require_str(data, "detector_id")
    _require_object(data, "input_space")
    mutators = _require_list(data, "mutators")
    invariants = _require_list(data, "invariants")

    for mutator in mutators:
        if not isinstance(mutator, dict):
            raise ValidationError("each mutator must be an object")
        _require_str(mutator, "name")

    for invariant in invariants:
        if not isinstance(invariant, dict):
            raise ValidationError("each invariant must be an object")
        _require_str(invariant, "name")

    if not mutators:
        warnings.append("fuzz campaign has no mutators")
    if not invariants:
        warnings.append("fuzz campaign has no invariants")
    return warnings
