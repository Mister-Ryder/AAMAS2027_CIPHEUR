"""Joint-candidate transport tests. HTTP uses mocks and fictional credentials."""
import copy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from cipheur.feature_provider import (
    FEATURE_PROGRAM_RESPONSE_SCHEMA, feature_program_schema, generate_feature_candidate,
)
from cipheur.graph_features import GRAPH_OPERATION_TYPES, NEIGHBOR_EDGE_MIN
from cipheur.providers import ProviderError


CANDIDATE = {
    "name": "joint-test-candidate",
    "features": [{"name": "n_edge_min", "expression": NEIGHBOR_EDGE_MIN}],
    "rule": "weight - conflict_weight + n_edge_min",
    "rationale": "Expose neighbor conflicts; test transport only.",
}
REQUEST = {"system": "Compose typed graph features and a safe ranking rule.",
           "user": "Consider certified structural distinctions."}


class FakeResponse:
    def __init__(self, value):
        self.raw = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.raw


def responses_result(candidate=None):
    return {"id": "resp_mock_joint", "model": "explicit-test-model", "status": "completed",
            "output": [{"type": "reasoning", "summary": []},
                       {"type": "message", "status": "completed", "role": "assistant",
                        "content": [{"type": "output_text", "text": json.dumps(
                            CANDIDATE if candidate is None else candidate)}]}],
            "usage": {"input_tokens": 20, "output_tokens": 50, "total_tokens": 70}}


def compatible_result(candidate=None):
    return {"id": "chat_mock_joint", "model": "explicit-test-model",
            "choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps(CANDIDATE if candidate is None else candidate)}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 50, "total_tokens": 70}}


class FeatureProviderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.workdir = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def call_http(self, config, response, request=REQUEST):
        with patch.dict(os.environ, {"JOINT_TEST_API_KEY": "mock-not-a-real-key"}), \
             patch("cipheur.providers.urlopen", return_value=FakeResponse(response)) as opened:
            candidate, metadata = generate_feature_candidate(
                {"api_key_env": "JOINT_TEST_API_KEY", **config}, request, self.workdir)
        return candidate, metadata, opened

    def test_recursive_schema_is_closed_required_and_covers_the_typed_library(self):
        schema = feature_program_schema()
        self.assertEqual(schema, FEATURE_PROGRAM_RESPONSE_SCHEMA)
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["features"]["maxItems"], 6)
        self.assertEqual(schema["properties"]["features"]["items"]["properties"]["expression"],
                         {"$ref": "#/$defs/Number"})
        seen_ops = set()

        def check(item):
            if isinstance(item, dict):
                if item.get("type") == "object":
                    self.assertIs(item["additionalProperties"], False)
                    self.assertEqual(set(item["required"]), set(item["properties"]))
                    if "op" in item["properties"]:
                        seen_ops.update(item["properties"]["op"]["enum"])
                if "$ref" in item:
                    self.assertTrue(item["$ref"].startswith("#/$defs/"))
                    self.assertIn(item["$ref"].split("/")[-1], schema["$defs"])
                self.assertFalse(set(item).intersection(
                    {"allOf", "not", "if", "then", "else", "dependentRequired", "prefixItems"}))
                for value in item.values():
                    check(value)
            elif isinstance(item, list):
                for value in item:
                    check(value)

        check(schema)
        self.assertEqual(seen_ops, set(GRAPH_OPERATION_TYPES))
        self.assertIn("#/$defs/Number", json.dumps(schema["$defs"]["Number"]))
        self.assertIn("#/$defs/NodeSet", json.dumps(schema["$defs"]["NodeSet"]))
        schema["required"].append("modified")
        self.assertNotIn("modified", feature_program_schema()["required"])

    def test_assistant_authored_replay_is_offline_with_raw_source_hash(self):
        path = self.workdir / "assistant_candidate.json"
        path.write_text(json.dumps(CANDIDATE), encoding="utf-8")
        with patch("cipheur.providers.urlopen") as opened, \
             patch("cipheur.feature_provider.subprocess.run") as command:
            candidate, metadata = generate_feature_candidate(
                {"type": "replay", "path": path.name, "authoring_source": "current_assistant"},
                REQUEST, self.workdir)
        self.assertEqual(candidate, CANDIDATE)
        self.assertIs(metadata["live_llm"], False)
        self.assertEqual(metadata["backend"], "replay")
        self.assertEqual(metadata["declared_authoring_source"], "current_assistant")
        self.assertEqual(metadata["source_sha256"], sha256(path.read_bytes()).hexdigest())
        self.assertTrue(metadata["typed_validation_passed"])
        self.assertEqual(metadata["candidate_kind"], "feature_rule")
        saved = json.loads((self.workdir / "feature_provider_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, metadata)
        opened.assert_not_called()
        command.assert_not_called()

    def test_replay_invalid_code_types_limits_and_contract_are_rejected(self):
        invalid = [dict(CANDIDATE, extra="unused"), dict(CANDIDATE, rule="__import__('os')"),
                   dict(CANDIDATE, features=[{"name": "bad", "expression": {
                       "op": "neighbors", "args": [{"op": "available", "args": []}]}}]),
                   dict(CANDIDATE, features=[{"name": "n" + str(i), "expression": NEIGHBOR_EDGE_MIN}
                                             for i in range(7)]),
                   dict(CANDIDATE, rule="unknown"), {"name": "old", "expression": "weight", "rationale": "old"}]
        path = self.workdir / "candidate.json"
        for value in invalid:
            with self.subTest(value=value):
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(ProviderError):
                    generate_feature_candidate({"type": "replay", "path": path}, REQUEST, self.workdir)

    def test_replay_malformed_or_missing_source_fails_without_fallback(self):
        path = self.workdir / "candidate.json"
        for text in (None, "not JSON", "[]", '{"name": "missing"}'):
            with self.subTest(text=text), patch("cipheur.providers.urlopen") as opened:
                if text is not None:
                    path.write_text(text, encoding="utf-8")
                with self.assertRaises(ProviderError):
                    generate_feature_candidate({"type": "replay", "path": path}, REQUEST, self.workdir)
                opened.assert_not_called()

    def test_mock_responses_uses_authoritative_strict_recursive_schema_and_receipts(self):
        candidate, metadata, opened = self.call_http(
            {"type": "openai_responses", "model": "explicit-test-model", "max_output_tokens": 2048},
            responses_result(), {**REQUEST, "schema": {"type": "object"}})
        self.assertEqual(candidate, CANDIDATE)
        outgoing = opened.call_args.args[0]
        payload = json.loads(outgoing.data)
        self.assertEqual(outgoing.full_url, "https://api.openai.com/v1/responses")
        self.assertIs(payload["store"], False)
        self.assertEqual(payload["max_output_tokens"], 2048)
        self.assertIs(payload["text"]["format"]["strict"], True)
        self.assertEqual(payload["text"]["format"]["schema"], feature_program_schema())
        self.assertEqual(metadata["tokens"]["total_tokens"], 70)
        self.assertEqual(metadata["response_id"], "resp_mock_joint")
        self.assertEqual(json.loads((self.workdir / "transport_response.json").read_text(encoding="utf-8")),
                         responses_result())
        self.assertNotIn("mock-not-a-real-key", json.dumps(metadata))
        self.assertNotIn("Authorization", (self.workdir / "request.json").read_text(encoding="utf-8"))

    def test_raw_response_saved_before_local_validation_and_invalid_candidate_retained(self):
        invalid = dict(CANDIDATE, rule="weight.__class__")
        result = responses_result(invalid)
        with self.assertRaisesRegex(ProviderError, "transport_response.json"):
            self.call_http({"type": "openai_responses", "model": "explicit-test-model"}, result)
        self.assertEqual(json.loads((self.workdir / "transport_response.json").read_text(encoding="utf-8")), result)
        self.assertFalse((self.workdir / "feature_provider_metadata.json").exists())

    def test_responses_refusal_incomplete_tool_output_and_missing_text_fail(self):
        values = []
        value = responses_result()
        value["status"] = "incomplete"
        values.append(value)
        value = responses_result()
        value["incomplete_details"] = {"reason": "max_output_tokens"}
        values.append(value)
        value = responses_result()
        value["output"][1]["content"] = [{"type": "refusal", "refusal": "refused"}]
        values.append(value)
        value = responses_result()
        value["output"].append({"type": "function_call", "name": "unexpected"})
        values.append(value)
        value = responses_result()
        value["output"] = []
        values.append(value)
        value = responses_result()
        value["output"][1]["content"][0]["text"] = "```json\n{}\n```"
        values.append(value)
        for result in values:
            with self.subTest(result=result), self.assertRaisesRegex(ProviderError, "transport_response.json"):
                self.call_http({"type": "openai_responses", "model": "explicit-test-model"}, result)

    def test_http_malformed_body_and_echoed_key_are_preserved_with_redaction(self):
        for raw in (b'{"malformed":', b'\xff\xfe'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ProviderError, "transport_response.json"):
                self.call_http({"type": "openai_responses", "model": "explicit-test-model"}, raw)
            self.assertEqual((self.workdir / "transport_response.json").read_bytes(), raw)
        result = responses_result()
        result["echo"] = "mock-not-a-real-key"
        self.call_http({"type": "openai_responses", "model": "explicit-test-model"}, result)
        saved = (self.workdir / "transport_response.json").read_bytes()
        self.assertNotIn(b"mock-not-a-real-key", saved)
        self.assertIn(b"[REDACTED_API_KEY]", saved)

    def test_http_failure_does_not_echo_secrets_or_trigger_fallback(self):
        errors = [URLError("private-key"), TimeoutError("private-key"),
                  HTTPError("https://example.test", 401, "private-key", {}, io.BytesIO())]
        for error in errors:
            with self.subTest(error=type(error).__name__), \
                 patch.dict(os.environ, {"JOINT_TEST_API_KEY": "private-key"}), \
                 patch("cipheur.providers.urlopen", side_effect=error), \
                 patch("cipheur.feature_provider.subprocess.run") as command:
                with self.assertRaises(ProviderError) as raised:
                    generate_feature_candidate({"type": "openai_responses", "model": "explicit-test-model",
                                                "api_key_env": "JOINT_TEST_API_KEY"}, REQUEST, self.workdir)
                self.assertNotIn("private-key", str(raised.exception))
                command.assert_not_called()

    def test_mock_compatible_json_mode_and_custom_endpoint(self):
        candidate, metadata, opened = self.call_http(
            {"type": "openai_compatible", "model": "explicit-test-model", "json_mode": True,
             "base_url": "https://example.test/v1/", "max_tokens": 2048}, compatible_result())
        self.assertEqual(candidate, CANDIDATE)
        self.assertEqual(metadata["backend"], "openai_compatible")
        outgoing = opened.call_args.args[0]
        self.assertEqual(outgoing.full_url, "https://example.test/v1/chat/completions")
        payload = json.loads(outgoing.data)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertIn('"$defs"', payload["messages"][0]["content"])

    def test_compatible_refusal_tools_and_incomplete_output_fail(self):
        values = []
        for finish in ("length", "content_filter", "tool_calls", None):
            value = compatible_result()
            value["choices"][0]["finish_reason"] = finish
            values.append(value)
        value = compatible_result()
        value["choices"][0]["message"]["refusal"] = "refused"
        values.append(value)
        value = compatible_result()
        value["choices"][0]["message"]["tool_calls"] = [{"type": "function"}]
        values.append(value)
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(ProviderError, "transport_response.json"):
                self.call_http({"type": "openai_compatible", "model": "explicit-test-model"}, value)

    def test_command_real_temporary_python_transport_is_explicitly_offline(self):
        script = ("import json,pathlib,sys; "
                  "request=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); "
                  "assert '$defs' in request['schema']; "
                  "pathlib.Path(sys.argv[2]).write_text(json.dumps(" + repr(CANDIDATE)
                  + "),encoding='utf-8')")
        candidate, metadata = generate_feature_candidate(
            {"type": "command", "argv": [sys.executable, "-c", script, "{request}", "{response}"]},
            REQUEST, self.workdir)
        self.assertEqual(candidate, CANDIDATE)
        self.assertIs(metadata["live_llm"], False)
        self.assertEqual(metadata["transport_response"], "response.json")

    def test_command_no_shell_and_explicit_llm_declaration(self):
        def fake_command(argv, **kwargs):
            self.assertFalse(kwargs["shell"])
            self.assertEqual(argv[1], str((self.workdir / "request.json").resolve()))
            self.assertEqual(argv[2], str((self.workdir / "response.json").resolve()))
            (self.workdir / "response.json").write_text(json.dumps(CANDIDATE), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")
        with patch("cipheur.feature_provider.subprocess.run", side_effect=fake_command):
            _, metadata = generate_feature_candidate(
                {"type": "command", "argv": ["mock-command", "{request}", "{response}"],
                 "declares_llm": True, "model": "explicit-external-test-model"}, REQUEST, self.workdir)
        self.assertIs(metadata["live_llm"], True)
        self.assertEqual(metadata["model"], "explicit-external-test-model")

    def test_stale_command_response_is_never_accepted(self):
        path = self.workdir / "response.json"
        path.write_text(json.dumps(CANDIDATE), encoding="utf-8")
        with patch("cipheur.feature_provider.subprocess.run", return_value=subprocess.CompletedProcess(
                ["mock-command"], 0, "", "")):
            with self.assertRaises(ProviderError):
                generate_feature_candidate({"type": "command", "argv": ["mock-command"]}, REQUEST, self.workdir)
        self.assertFalse(path.exists())

    def test_invalid_requests_config_timeout_and_missing_key_fail_safely(self):
        cases = [([], REQUEST), ({"type": "unknown"}, REQUEST), ({"type": "replay"}, REQUEST),
                 ({"type": "replay", "path": "candidate.json"}, {}),
                 ({"type": "command", "argv": "mock-command"}, REQUEST),
                 ({"type": "command", "argv": ["mock-command"], "declares_llm": "yes"}, REQUEST)]
        for config, request in cases:
            with self.subTest(config=config), self.assertRaises(ProviderError):
                generate_feature_candidate(config, request, self.workdir)
        for timeout in (0, -1, "NaN", True, None):
            with self.subTest(timeout=timeout), patch("cipheur.feature_provider.subprocess.run") as command:
                with self.assertRaises(ProviderError):
                    generate_feature_candidate({"type": "command", "argv": ["mock-command"],
                                                "timeout_seconds": timeout}, REQUEST, self.workdir)
                command.assert_not_called()
        with patch.dict(os.environ, {}, clear=True), patch("cipheur.providers.urlopen") as opened:
            with self.assertRaises(ProviderError):
                generate_feature_candidate({"type": "openai_responses", "model": "explicit-test-model"},
                                           REQUEST, self.workdir)
            opened.assert_not_called()


if __name__ == "__main__":
    unittest.main()
