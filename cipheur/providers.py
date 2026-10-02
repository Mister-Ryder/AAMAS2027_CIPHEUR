"""Explicit, replaceable candidate generators; no automatic provider fallback.

Only the candidate's transport contract is checked here. The caller must validate
the expression with its own safe DSL before evaluation. A replay is never labelled
as a live model call, and an external command is only labelled as an LLM when its
configuration explicitly declares that fact.
"""

from __future__ import annotations

import json
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """A provider failed or returned an invalid candidate."""


_CANDIDATE_FIELDS = {"name", "expression", "rationale"}
_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_TRANSPORT_NOTE = " Raw HTTP response saved to transport_response.json."


def _candidate(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != _CANDIDATE_FIELDS:
        raise ProviderError("Candidate must contain exactly name, expression, and rationale.")
    if any(not isinstance(value[key], str) or not value[key].strip()
           for key in _CANDIDATE_FIELDS):
        raise ProviderError("Candidate fields must be nonempty strings.")
    return dict(value)


def _parse_candidate(text: str) -> dict[str, str]:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProviderError("Provider returned invalid JSON.") from exc
    return _candidate(value)


def _read_candidate(path: Path) -> dict[str, str]:
    return _load_candidate(path)[0]


def _load_candidate(path: Path) -> tuple[dict[str, str], bytes]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProviderError("Candidate file could not be read as UTF-8.") from exc
    return _parse_candidate(text), raw


def _positive_timeout(config: dict[str, Any]) -> float:
    value = config.get("timeout_seconds", 90)
    if isinstance(value, bool):
        raise ProviderError("timeout_seconds must be a positive finite number.")
    try:
        timeout = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProviderError("timeout_seconds must be a positive finite number.") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise ProviderError("timeout_seconds must be a positive finite number.")
    return timeout


def _model(config: dict[str, Any]) -> str:
    model = config.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ProviderError("A model must be explicitly configured for an HTTP provider.")
    return model


def _save_transport_response(raw: bytes, workdir: Path, api_key: str) -> None:
    """Save the response body only; never save authentication/request headers.

    The original body is retained even when it is not valid JSON. Defensive
    redaction covers an endpoint unexpectedly echoing its authentication key.
    """
    try:
        workdir.mkdir(parents=True, exist_ok=True)
        redacted = raw.replace(api_key.encode("utf-8"), b"[REDACTED_API_KEY]")
        (workdir / "transport_response.json").write_bytes(redacted)
    except OSError as exc:
        raise ProviderError("HTTP response could not be saved for audit.") from exc


def _http_json(config: dict[str, Any], suffix: str,
               payload: dict[str, Any], workdir: Path) -> dict[str, Any]:
    env_name = config.get("api_key_env", "OPENAI_API_KEY")
    if not isinstance(env_name, str) or not env_name:
        raise ProviderError("api_key_env must be a nonempty environment-variable name.")
    api_key = os.environ.get(env_name)
    if not api_key:
        raise ProviderError("The configured API-key environment variable is not set.")
    base_url = config.get("base_url", _DEFAULT_BASE_URL)
    if not isinstance(base_url, str) or not base_url.startswith(("https://", "http://")):
        raise ProviderError("base_url must be an HTTP or HTTPS URL.")
    try:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        http_request = Request(
            base_url.rstrip("/") + suffix,
            data=body,
            headers={"Authorization": "Bearer " + api_key,
                     "Content-Type": "application/json",
                     "User-Agent": "cipheur/0.1"},
            method="POST",
        )
        with urlopen(http_request, timeout=_positive_timeout(config)) as response:
            raw = response.read()
    except HTTPError as exc:
        # Response bodies and exception strings can echo credentials or prompts.
        try:
            error_body = exc.read()
        except (OSError, ValueError):
            error_body = None
        if error_body:
            _save_transport_response(error_body, workdir, api_key)
        note = _TRANSPORT_NOTE if error_body else ""
        raise ProviderError(f"HTTP provider returned status {exc.code}." + note) from None
    except (URLError, OSError, TimeoutError, ValueError, TypeError) as exc:
        raise ProviderError(f"HTTP provider request failed ({type(exc).__name__}).") from None
    _save_transport_response(raw, workdir, api_key)
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, AttributeError) as exc:
        raise ProviderError("HTTP provider returned invalid UTF-8 JSON." + _TRANSPORT_NOTE) from exc
    if not isinstance(result, dict):
        raise ProviderError("HTTP provider response must be a JSON object." + _TRANSPORT_NOTE)
    if result.get("error") is not None:
        raise ProviderError("HTTP provider reported an API error." + _TRANSPORT_NOTE)
    return result


def _http_metadata(backend: str, model: str,
                   result: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {"backend": backend, "live_llm": True, "model": model,
                               "transport_response": "transport_response.json"}
    if isinstance(result.get("id"), str):
        metadata["response_id"] = result["id"]
    if isinstance(result.get("model"), str):
        metadata["resolved_model"] = result["model"]
    usage = result.get("usage")
    if isinstance(usage, dict):
        fields = ("input_tokens", "output_tokens", "total_tokens",
                  "prompt_tokens", "completion_tokens")
        metadata["tokens"] = {
            key: usage[key] for key in fields
            if isinstance(usage.get(key), int) and not isinstance(usage[key], bool)
        }
    return metadata


def _responses(config: dict[str, Any], request: dict[str, Any], workdir: Path
               ) -> tuple[dict[str, str], dict[str, Any]]:
    model = _model(config)
    payload: dict[str, Any] = {
        "model": model,
        "store": False,
        "input": [{"role": "system", "content": request["system"]},
                  {"role": "user", "content": request["user"]}],
        "text": {"format": {"type": "json_schema", "name": "heuristic_candidate",
                            "strict": True, "schema": request["schema"]}},
    }
    for key in ("max_output_tokens", "temperature"):
        if key in config:
            payload[key] = config[key]
    result = _http_json(config, "/responses", payload, workdir)
    try:
        candidate = _responses_candidate(result)
    except ProviderError as exc:
        raise ProviderError(str(exc) + _TRANSPORT_NOTE) from None
    return candidate, _http_metadata("openai_responses", model, result)


def _responses_candidate(result: dict[str, Any]) -> dict[str, str]:
    if result.get("status") != "completed" or result.get("incomplete_details") is not None:
        raise ProviderError("Responses generation did not complete successfully.")
    output = result.get("output")
    if not isinstance(output, list):
        raise ProviderError("Responses output is missing or invalid.")
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            raise ProviderError("Responses output contains an invalid item.")
        if item.get("type") == "refusal":
            raise ProviderError("Responses generation was refused.")
        if item.get("type") != "message":
            continue
        if item.get("status") not in (None, "completed"):
            raise ProviderError("Responses message did not complete successfully.")
        content = item.get("content")
        if not isinstance(content, list):
            raise ProviderError("Responses message content is invalid.")
        for part in content:
            if not isinstance(part, dict):
                raise ProviderError("Responses message contains invalid content.")
            if part.get("type") == "refusal":
                raise ProviderError("Responses generation was refused.")
            if part.get("type") == "output_text":
                if not isinstance(part.get("text"), str):
                    raise ProviderError("Responses output_text must be a string.")
                chunks.append(part["text"])
    if not chunks:
        raise ProviderError("Responses generation returned no output_text.")
    return _parse_candidate("".join(chunks))


def _compatible(config: dict[str, Any], request: dict[str, Any], workdir: Path
                ) -> tuple[dict[str, str], dict[str, Any]]:
    model = _model(config)
    json_mode = config.get("json_mode", False)
    if not isinstance(json_mode, bool):
        raise ProviderError("json_mode must be a boolean.")
    instructions = (request["system"] + "\n\nReturn exactly one JSON object matching "
                    "this JSON Schema:\n" + json.dumps(request["schema"], ensure_ascii=False))
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": instructions},
                     {"role": "user", "content": request["user"]}],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    for key in ("max_tokens", "temperature"):
        if key in config:
            payload[key] = config[key]
    result = _http_json(config, "/chat/completions", payload, workdir)
    try:
        candidate = _compatible_candidate(result)
    except ProviderError as exc:
        raise ProviderError(str(exc) + _TRANSPORT_NOTE) from None
    return candidate, _http_metadata("openai_compatible", model, result)


def _compatible_candidate(result: dict[str, Any]) -> dict[str, str]:
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
    return _parse_candidate(message["content"])


def _command(config: dict[str, Any], request: dict[str, Any], workdir: Path
             ) -> tuple[dict[str, str], dict[str, Any]]:
    argv = config.get("argv")
    if (not isinstance(argv, list) or not argv
            or any(not isinstance(arg, str) for arg in argv) or not argv[0]):
        raise ProviderError("command argv must be a nonempty list of strings.")
    declares_llm = config.get("declares_llm", False)
    if not isinstance(declares_llm, bool):
        raise ProviderError("declares_llm must be a boolean.")
    workdir = workdir.resolve()
    request_path = workdir / "request.json"
    response_path = workdir / "response.json"
    expanded = [arg.replace("{request}", str(request_path))
                .replace("{response}", str(response_path)) for arg in argv]
    try:
        workdir.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps(request, ensure_ascii=False, allow_nan=False,
                                           indent=2) + "\n", encoding="utf-8")
        # A previous run's output must never satisfy the current request.
        if response_path.exists() or response_path.is_symlink():
            response_path.unlink()
        result = subprocess.run(expanded, cwd=workdir, shell=False, capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                timeout=_positive_timeout(config), check=False)
    except subprocess.TimeoutExpired:
        raise ProviderError("External command exceeded timeout_seconds.") from None
    except (OSError, ValueError, TypeError) as exc:
        raise ProviderError(f"External command failed ({type(exc).__name__}).") from None
    if result.returncode != 0:
        raise ProviderError(f"External command returned exit code {result.returncode}.")
    candidate = _read_candidate(response_path)
    metadata: dict[str, Any] = {"backend": "external_command", "live_llm": declares_llm}
    if isinstance(config.get("model"), str):
        metadata["model"] = config["model"]
    return candidate, metadata


def generate_candidate(config: dict, request: dict, workdir: Path) -> tuple[dict, dict]:
    """Generate one transport-validated candidate and provenance metadata.

    ``request`` contains string ``system``/``user`` prompts and a dict ``schema``.
    ``config.type`` is replay, openai_responses, openai_compatible, or command.
    Replay paths are relative to ``workdir`` unless absolute. Commands receive
    persistent request.json / response.json paths through argv placeholders.
    HTTP response bodies are saved before parsing to transport_response.json;
    that file may contain invalid JSON if the endpoint returned malformed data.
    No provider failure falls back to replay or another model. No secret is logged.
    """
    started = time.monotonic()
    if not isinstance(config, dict) or not isinstance(request, dict):
        raise ProviderError("Provider config and request must be dictionaries.")
    if (not isinstance(request.get("system"), str)
            or not isinstance(request.get("user"), str)
            or not isinstance(request.get("schema"), dict)):
        raise ProviderError("Request requires string system/user and dictionary schema fields.")
    try:
        workdir = Path(workdir)
        provider_type = config.get("type")
        if provider_type == "replay":
            path = config.get("path")
            if not isinstance(path, (str, os.PathLike)) or not str(path):
                raise ProviderError("Replay requires a candidate JSON path.")
            path = Path(path)
            if not path.is_absolute():
                path = workdir / path
            candidate, source_bytes = _load_candidate(path)
            metadata: dict[str, Any] = {"backend": "replay", "live_llm": False,
                                       "source_path": str(path.resolve()),
                                       "source_sha256": sha256(source_bytes).hexdigest()}
        elif provider_type == "openai_responses":
            candidate, metadata = _responses(config, request, workdir)
        elif provider_type == "openai_compatible":
            candidate, metadata = _compatible(config, request, workdir)
        elif provider_type == "command":
            candidate, metadata = _command(config, request, workdir)
        else:
            raise ProviderError("Unsupported provider type.")
    except ProviderError:
        raise
    except Exception as exc:
        # Do not expose arbitrary exception strings, prompts, argv, or credentials.
        raise ProviderError(f"Provider failed ({type(exc).__name__}).") from None
    metadata["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return candidate, metadata
