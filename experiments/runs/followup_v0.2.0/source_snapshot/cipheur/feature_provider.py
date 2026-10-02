"""Explicit transports for joint typed feature--ranking candidates.

The original rule-only provider is unchanged. Shared HTTP helpers preserve raw
responses before parsing and redact authentication keys from the audit body.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

from .graph_features import FeatureRuleProgram, GRAPH_OPERATION_TYPES, MAX_FEATURES
from .providers import (
    ProviderError, _http_json, _http_metadata, _model, _positive_timeout,
    _TRANSPORT_NOTE,
)


def _reference(type_name: str) -> dict:
    alternatives = type_name.split("|")
    if len(alternatives) == 1:
        return {"$ref": "#/$defs/" + type_name}
    return {"anyOf": [{"$ref": "#/$defs/" + name} for name in alternatives]}


def _operation_branch(names: list[str], arguments: tuple[str, ...]) -> dict:
    if arguments and any(argument != arguments[0] for argument in arguments):
        raise RuntimeError("Transport schema needs homogeneous operation arguments")
    return {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": names},
            "args": {"type": "array", "minItems": len(arguments), "maxItems": len(arguments),
                     "items": _reference(arguments[0]) if arguments else {"type": "number"}},
        },
        "required": ["op", "args"], "additionalProperties": False,
    }


def _build_schema() -> dict:
    groups: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    for op, (arguments, result) in GRAPH_OPERATION_TYPES.items():
        if op != "const":
            groups.setdefault((result, arguments), []).append(op)
    definitions: dict[str, dict] = {}
    for result_type in ("Node", "NodeSet", "EdgeSet", "Number"):
        branches = [_operation_branch(names, arguments)
                    for (result, arguments), names in groups.items() if result == result_type]
        if result_type == "Number":
            branches.insert(0, {
                "type": "object", "properties": {
                    "op": {"type": "string", "enum": ["const"]},
                    "value": {"type": "number", "minimum": -1e9, "maximum": 1e9}},
                "required": ["op", "value"], "additionalProperties": False,
            })
        definitions[result_type] = branches[0] if len(branches) == 1 else {"anyOf": branches}
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "features": {"type": "array", "maxItems": MAX_FEATURES, "items": {
                "type": "object", "properties": {
                    "name": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
                    "expression": {"$ref": "#/$defs/Number"}},
                "required": ["name", "expression"], "additionalProperties": False}},
            "rule": {"type": "string"}, "rationale": {"type": "string"},
        },
        "required": ["name", "features", "rule", "rationale"],
        "additionalProperties": False, "$defs": definitions,
    }


FEATURE_PROGRAM_RESPONSE_SCHEMA = _build_schema()


def feature_program_schema() -> dict:
    """Return the complete recursive strict schema, isolated from caller edits."""
    return deepcopy(FEATURE_PROGRAM_RESPONSE_SCHEMA)


def _validated_candidate(value: Any) -> dict:
    try:
        program = FeatureRuleProgram.from_dict(value)
    except (ValueError, TypeError, SyntaxError, RecursionError, OverflowError) as error:
        # A generated expression can contain arbitrary text; do not echo it.
        raise ProviderError("Candidate failed typed feature-rule validation ("
                            + type(error).__name__ + ").") from None
    return program.to_dict()


def _parse_feature_candidate(text: str) -> dict:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError, RecursionError) as error:
        raise ProviderError("Feature provider returned invalid JSON.") from None
    return _validated_candidate(value)


def _load_feature_candidate(path: Path) -> tuple[dict, bytes]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError):
        raise ProviderError("Feature candidate file could not be read as UTF-8.") from None
    return _parse_feature_candidate(text), raw


def _responses_feature_text(result: dict) -> str:
    if result.get("status") != "completed" or result.get("incomplete_details") is not None:
        raise ProviderError("Responses generation did not complete successfully.")
    output = result.get("output")
    if not isinstance(output, list):
        raise ProviderError("Responses output is missing or invalid.")
    chunks = []
    for item in output:
        if not isinstance(item, dict):
            raise ProviderError("Responses output contains an invalid item.")
        if item.get("type") == "reasoning":
            continue
        if item.get("type") == "refusal":
            raise ProviderError("Responses generation was refused.")
        if item.get("type") != "message":
            raise ProviderError("Responses output contains an unexpected non-text action.")
        if item.get("status") not in (None, "completed"):
            raise ProviderError("Responses message did not complete successfully.")
        if item.get("role") not in (None, "assistant"):
            raise ProviderError("Responses message has an invalid role.")
        content = item.get("content")
        if not isinstance(content, list):
            raise ProviderError("Responses message content is invalid.")
        for part in content:
            if not isinstance(part, dict):
                raise ProviderError("Responses message contains invalid content.")
            if part.get("type") == "refusal":
                raise ProviderError("Responses generation was refused.")
            if part.get("type") != "output_text" or not isinstance(part.get("text"), str):
                raise ProviderError("Responses message must contain output_text.")
            chunks.append(part["text"])
    if not chunks:
        raise ProviderError("Responses generation returned no output_text.")
    return "".join(chunks)


def _compatible_feature_text(result: dict) -> str:
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProviderError("Compatible provider returned no valid completion choice.")
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        raise ProviderError("Compatible generation did not finish normally.")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ProviderError("Compatible completion message is invalid.")
    if message.get("refusal"):
        raise ProviderError("Compatible generation was refused.")
    if message.get("tool_calls") or message.get("function_call"):
        raise ProviderError("Compatible provider returned a tool call instead of a candidate.")
    if not isinstance(message.get("content"), str):
        raise ProviderError("Compatible completion content must be a string.")
    return message["content"]


def _http_feature_candidate(config: dict, request: dict, workdir: Path,
                            responses: bool) -> tuple[dict, dict]:
    model = _model(config)
    if responses:
        backend = "openai_responses"
        payload = {
            "model": model, "store": False,
            "input": [{"role": "system", "content": request["system"]},
                      {"role": "user", "content": request["user"]}],
            "text": {"format": {"type": "json_schema", "name": "feature_rule_candidate",
                                "strict": True, "schema": request["schema"]}},
        }
        suffix, optional = "/responses", ("max_output_tokens", "temperature")
    else:
        backend = "openai_compatible"
        json_mode = config.get("json_mode", False)
        if not isinstance(json_mode, bool):
            raise ProviderError("json_mode must be a boolean.")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": request["system"]
                          + "\n\nReturn exactly one JSON object matching this JSON Schema:\n"
                          + json.dumps(request["schema"], ensure_ascii=False)},
                         {"role": "user", "content": request["user"]}],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        suffix, optional = "/chat/completions", ("max_tokens", "temperature")
    for key in optional:
        if key in config:
            payload[key] = config[key]
    result = _http_json(config, suffix, payload, workdir)
    try:
        text = _responses_feature_text(result) if responses else _compatible_feature_text(result)
        candidate = _parse_feature_candidate(text)
    except ProviderError as error:
        raise ProviderError(str(error) + _TRANSPORT_NOTE) from None
    return candidate, _http_metadata(backend, model, result)


def _command_feature_candidate(config: dict, request: dict, workdir: Path) -> tuple[dict, dict]:
    argv = config.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv) or not argv[0]:
        raise ProviderError("command argv must be a nonempty list of strings.")
    declares_llm = config.get("declares_llm", False)
    if not isinstance(declares_llm, bool):
        raise ProviderError("declares_llm must be a boolean.")
    timeout = _positive_timeout(config)
    workdir = workdir.resolve()
    request_path, response_path = workdir / "request.json", workdir / "response.json"
    expanded = [arg.replace("{request}", str(request_path)).replace("{response}", str(response_path))
                for arg in argv]
    try:
        if response_path.exists() or response_path.is_symlink():
            response_path.unlink()
        completed = subprocess.run(expanded, cwd=workdir, shell=False, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace",
                                   timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise ProviderError("External feature command exceeded timeout_seconds.") from None
    except (OSError, ValueError, TypeError) as error:
        raise ProviderError("External feature command failed (" + type(error).__name__ + ").") from None
    if completed.returncode != 0:
        raise ProviderError(f"External feature command returned exit code {completed.returncode}.")
    candidate, raw = _load_feature_candidate(response_path)
    metadata = {"backend": "external_command", "live_llm": declares_llm,
                "transport_response": "response.json", "response_sha256": sha256(raw).hexdigest()}
    if isinstance(config.get("model"), str):
        metadata["model"] = config["model"]
    return candidate, metadata


def generate_feature_candidate(config: dict, request: dict, workdir: Path) -> tuple[dict, dict]:
    """Generate and locally validate one joint feature--rule candidate.

    Accepted explicit transports: replay, openai_responses, openai_compatible,
    command. Requests require system/user strings. The built-in recursive schema
    replaces any supplied transport schema, ensuring every backend uses the
    complete joint contract. A failure never invokes another backend or replay.
    """
    started = time.monotonic()
    if not isinstance(config, dict) or not isinstance(request, dict):
        raise ProviderError("Provider config and request must be dictionaries.")
    if (not isinstance(request.get("system"), str) or not isinstance(request.get("user"), str)
            or ("schema" in request and not isinstance(request["schema"], dict))):
        raise ProviderError("Feature request requires string system/user fields and an optional dictionary schema.")
    normalized_request = {"system": request["system"], "user": request["user"],
                          "schema": feature_program_schema()}
    try:
        workdir = Path(workdir)
        backend = config.get("type")
        if backend not in ("replay", "openai_responses", "openai_compatible", "command"):
            raise ProviderError("Unsupported feature provider type.")
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "request.json").write_text(
            json.dumps(normalized_request, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
            encoding="utf-8")
        if backend == "replay":
            path = config.get("path")
            if not isinstance(path, (str, os.PathLike)) or not str(path):
                raise ProviderError("Feature replay requires a candidate JSON path.")
            path = Path(path)
            if not path.is_absolute():
                path = workdir / path
            candidate, raw = _load_feature_candidate(path)
            metadata = {"backend": "replay", "live_llm": False,
                        "source_path": str(path.resolve()), "source_sha256": sha256(raw).hexdigest()}
            if isinstance(config.get("authoring_source"), str):
                metadata["declared_authoring_source"] = config["authoring_source"]
        elif backend in ("openai_responses", "openai_compatible"):
            candidate, metadata = _http_feature_candidate(
                config, normalized_request, workdir, backend == "openai_responses")
        else:
            candidate, metadata = _command_feature_candidate(config, normalized_request, workdir)
        candidate_text = json.dumps(candidate, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False)
        schema_text = json.dumps(normalized_request["schema"], sort_keys=True, separators=(",", ":"))
        metadata.update({"candidate_kind": "feature_rule", "typed_validation_passed": True,
                         "candidate_sha256": sha256(candidate_text.encode("utf-8")).hexdigest(),
                         "schema_sha256": sha256(schema_text.encode("utf-8")).hexdigest(),
                         "request_artifact": "request.json"})
        metadata["elapsed_seconds"] = round(time.monotonic() - started, 6)
        (workdir / "feature_provider_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    except ProviderError:
        raise
    except Exception as error:
        raise ProviderError("Feature provider failed (" + type(error).__name__ + ").") from None
    return candidate, metadata
