# Joint LLM feature--rule candidate provider

The new `cipheur.feature_provider.generate_feature_candidate` function extends
candidate transport to the complete typed feature--rule contract. The original
rule-only `cipheur.providers` module remains unchanged.

## Contract and audit artifacts

```python
from pathlib import Path
from cipheur.feature_provider import generate_feature_candidate
from cipheur.graph_features import FeatureRuleProgram

request = {
    "system": "Synthesize graph features and a safe ranking rule using the typed library.",
    "user": "The offline caller inserts certified requirements and structural witnesses here."
}
candidate, metadata = generate_feature_candidate(
    {"type": "replay", "path": str(Path("candidate.json").resolve()),
     "authoring_source": "current_assistant"},
    request,
    Path("runs") / "joint_synthesis" / "round_000",
)
program = FeatureRuleProgram.from_dict(candidate)
```

The candidate contains exactly `name`, `features`, `rule`, and `rationale`.
Each additional feature contains exactly `name` and a nested typed
`expression`. The returned object has already passed the local
`FeatureRuleProgram` type, size, identifier, and rule-safety checks; serialization
uses its canonical AST format.

The request requires `system` and `user` strings. An optional supplied `schema`
must be a dictionary, but the wrapper replaces it with its authoritative joint
schema. This prevents an old rule-only or loose expression schema from being
sent by accident. `feature_program_schema()` returns a fresh copy of the exact
schema used by all transports.

Use a distinct work directory for every candidate-generation round. Every
request saves `request.json`, including the prompts and authoritative schema.
Successful generation saves `feature_provider_metadata.json` with candidate
and schema hashes, transport provenance, stage duration, and
`typed_validation_passed: true`. HTTP bodies are saved to
`transport_response.json` before candidate parsing, including invalid or refused
responses. Command responses remain in `response.json`. Replay metadata records
the exact source file path and raw-byte SHA-256 digest.

`typed_validation_passed` means that the program can be interpreted safely. It
does not mean that certified requirements were satisfied or that schedule
quality improved. The offline synthesis controller must separately evaluate
specification consistency, complete-schedule quality, and measured feature
cost, then freeze the selected program before held-out evaluation.

## Explicit transport choices

| `config.type` | Required configuration | Provenance |
| --- | --- | --- |
| `replay` | `path` to joint candidate JSON | Always `live_llm: false`; optional `authoring_source` is recorded as a declaration |
| `openai_responses` | Explicit `model`; configured API-key environment variable | Responses API and strict recursive JSON Schema |
| `openai_compatible` | Explicit `model`; configured API-key environment variable | Chat Completions-compatible API; optional `json_mode: true` |
| `command` | Nonempty `argv` list; optional `{request}` and `{response}` placeholders | `shell=False`; `live_llm` defaults to false and is true only when explicitly declared |

HTTP configuration accepts `api_key_env` (default `OPENAI_API_KEY`),
`base_url` (default `https://api.openai.com/v1`), and positive finite
`timeout_seconds` (default 90). Responses accepts `max_output_tokens` and
`temperature`; the compatible transport accepts `max_tokens` and
`temperature`. Model choice is explicit; the wrapper does not replace an
unavailable model, switch to another provider, or silently replay a candidate.
Supported parameter values still depend on the selected endpoint and model.

An HTTP configuration example is:

```python
config = {
    "type": "openai_responses",
    "model": "YOUR_EXPLICIT_CONFIGURED_MODEL",
    "api_key_env": "OPENAI_API_KEY",
    "max_output_tokens": 4096,
    "timeout_seconds": 90,
}
```

No secret is included in this configuration or saved request. The shared HTTP
transport loads only the explicitly named environment variable and omits
authentication/request headers from saved response artifacts. If a response
unexpectedly echoes that key, its audit body is redacted by the shared
transport. Error messages omit arbitrary transport text, command output, and
generated expressions. Incomplete generations, refusals, tool calls,
malformed JSON, and candidates rejected by the typed interpreter all fail
explicitly. No failure triggers fallback.

External commands are invoked as argument lists, with no shell. The wrapper
removes a stale `response.json` before invocation, enforces the timeout, and
requires a newly written locally valid candidate. `declares_llm: true` is a
configuration declaration about that external command; it does not prove which
model executed. If used, record the command's own model and generation receipt
as well.

## Strict recursive schema

The transport schema defines `Node`, `NodeSet`, `EdgeSet`, and `Number` in
`$defs`. Numeric feature roots reference `#/$defs/Number`. Operations are grouped
into closed object branches by result type and argument signature; `op` is an
enum, and every operation branch requires `args` with the correct arity and
typed recursive item references. `const` has its own closed branch requiring
`op` and `value`. All object properties are required and every object sets
`additionalProperties: false`.

This uses documented Structured Outputs support for recursive definitions,
`anyOf`, and bounded arrays. The selected standard model must support strict
Structured Outputs; fine-tuned models have additional restrictions on array
and numeric bounds. The authoritative local validator also enforces limits
that are not encoded recursively in JSON Schema, including expression depth,
operation-node count, reserved feature names, and safe ranking-rule syntax.
See the [official OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
for the supported schema subset and explicit refusal/incomplete handling.

## What was actually executed

The present implementation was checked with fictional credentials and mocked
HTTP responses. Tests cover the complete schema, raw-response preservation,
local candidate validation, error handling, key redaction, replay provenance,
compatible transport, and command execution. A temporary Python command tests
the command transport and is explicitly recorded as non-LLM execution.

A candidate authored by the current assistant and read from disk is an
assistant-authored replay. It is not an API model call, regardless of whether
the candidate is useful. No test or replay receipt should be cited as evidence
of a live LLM synthesis experiment.
