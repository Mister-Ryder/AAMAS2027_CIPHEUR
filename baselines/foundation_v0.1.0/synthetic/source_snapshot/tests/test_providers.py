"""Transport contract tests. HTTP is mocked; no actual model/harness is contacted."""

import io
import json
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from cipheur.providers import ProviderError, generate_candidate


CANDIDATE = {"name": "bounded-risk", "expression": "risk + delay", "rationale": "风险优先"}
SCHEMA = {
    "type": "object",
    "properties": {key: {"type": "string"} for key in CANDIDATE},
    "required": list(CANDIDATE),
    "additionalProperties": False,
}
REQUEST = {"system": "Generate a safe scheduling expression.",
           "user": "Consider latency and failure risk.", "schema": SCHEMA}


class FakeResponse:
    def __init__(self, value):
        self.raw = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.raw


def responses_result():
    return {
        "id": "resp_test", "model": "explicit-model", "status": "completed",
        "output": [{"type": "message", "status": "completed", "role": "assistant",
                    "content": [{"type": "output_text", "text": json.dumps(CANDIDATE)}]}],
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
    }


def compatible_result():
    return {
        "id": "chat_test", "model": "explicit-model",
        "choices": [{"finish_reason": "stop", "message": {
            "role": "assistant", "content": json.dumps(CANDIDATE)}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 20, "total_tokens": 32},
    }


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def http_call(self, config, result):
        with patch.dict(os.environ, {"TEST_PROVIDER_KEY": "test-not-a-real-key"}), \
                patch("cipheur.providers.urlopen", return_value=FakeResponse(result)) as opened:
            candidate, metadata = generate_candidate(
                {"api_key_env": "TEST_PROVIDER_KEY", **config}, REQUEST, self.workdir)
        return candidate, metadata, opened

    def test_replay_is_explicitly_offline(self):
        path = self.workdir / "candidate.json"
        path.write_text(json.dumps(CANDIDATE), encoding="utf-8")
        with patch("cipheur.providers.urlopen") as opened, \
                patch("cipheur.providers.subprocess.run") as run:
            candidate, metadata = generate_candidate(
                {"type": "replay", "path": "candidate.json"}, REQUEST, self.workdir)
        self.assertEqual(candidate, CANDIDATE)
        self.assertEqual(metadata["backend"], "replay")
        self.assertIs(metadata["live_llm"], False)
        self.assertEqual(metadata["source_path"], str(path.resolve()))
        self.assertEqual(metadata["source_sha256"], sha256(path.read_bytes()).hexdigest())
        self.assertGreaterEqual(metadata["elapsed_seconds"], 0)
        opened.assert_not_called()
        run.assert_not_called()

    def test_replay_missing_and_malformed_files_fail(self):
        path = self.workdir / "candidate.json"
        for text in (None, "not JSON", "[]", '{"name": "x"}'):
            with self.subTest(text=text):
                if text is not None:
                    path.write_text(text, encoding="utf-8")
                with self.assertRaises(ProviderError):
                    generate_candidate({"type": "replay", "path": path}, REQUEST, self.workdir)

    def test_strict_candidate_contract(self):
        path = self.workdir / "candidate.json"
        invalid = [dict(CANDIDATE, extra="unused"), dict(CANDIDATE, expression=10),
                   dict(CANDIDATE, name="  "), dict(CANDIDATE, rationale="")]
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.assertRaises(ProviderError):
                    generate_candidate({"type": "replay", "path": path}, REQUEST, self.workdir)

    def test_invalid_config_and_request_fail(self):
        for config, request in (({}, REQUEST), ({"type": "unknown"}, REQUEST),
                                ({"type": "replay"}, REQUEST), ([], REQUEST),
                                ({"type": "replay"}, {}), ({"type": "replay"}, [])):
            with self.subTest(config=config, request=request), self.assertRaises(ProviderError):
                generate_candidate(config, request, self.workdir)

    def test_responses_payload_and_provenance(self):
        candidate, metadata, opened = self.http_call(
            {"type": "openai_responses", "model": "explicit-model",
             "max_output_tokens": 512}, responses_result())
        self.assertEqual(candidate, CANDIDATE)
        self.assertEqual(metadata["backend"], "openai_responses")
        self.assertIs(metadata["live_llm"], True)
        self.assertEqual(metadata["response_id"], "resp_test")
        self.assertEqual(metadata["tokens"]["total_tokens"], 30)
        self.assertEqual(metadata["transport_response"], "transport_response.json")
        saved = json.loads((self.workdir / "transport_response.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, responses_result())
        self.assertNotIn("Authorization", json.dumps(saved))
        self.assertNotIn("api_key_env", json.dumps(saved))
        self.assertNotIn("test-not-a-real-key", json.dumps(saved))
        outgoing = opened.call_args.args[0]
        self.assertEqual(outgoing.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(outgoing.method, "POST")
        payload = json.loads(outgoing.data)
        self.assertEqual(payload["model"], "explicit-model")
        self.assertEqual(payload["input"][0]["content"], REQUEST["system"])
        self.assertEqual(payload["text"]["format"]["schema"], SCHEMA)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertIs(payload["text"]["format"]["strict"], True)
        self.assertIs(payload["store"], False)
        self.assertEqual(payload["max_output_tokens"], 512)
        self.assertNotIn("test-not-a-real-key", json.dumps(metadata))

    def test_responses_reject_refusal_incomplete_error_and_missing_text(self):
        cases = []
        value = responses_result()
        value["status"] = "incomplete"
        cases.append(value)
        value = responses_result()
        value["incomplete_details"] = {"reason": "max_output_tokens"}
        cases.append(value)
        value = responses_result()
        value["error"] = {"code": "server_error", "message": "private prompt"}
        cases.append(value)
        value = responses_result()
        value["output"][0]["content"] = [{"type": "refusal", "refusal": "refused"}]
        cases.append(value)
        value = responses_result()
        value["output"] = []
        cases.append(value)
        value = responses_result()
        value["output"][0]["content"][0]["text"] = "```json\n{}\n```"
        cases.append(value)
        for result in cases:
            with self.subTest(result=result):
                with self.assertRaisesRegex(ProviderError, "transport_response.json"):
                    self.http_call({"type": "openai_responses", "model": "explicit-model"}, result)
                saved = json.loads((self.workdir / "transport_response.json").read_text(encoding="utf-8"))
                self.assertEqual(saved, result)

    def test_http_malformed_json_and_utf8_are_preserved_before_failure(self):
        for raw in (b'{"id":"resp_malformed",not JSON}', b'\xff\xfe invalid UTF-8'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ProviderError, "transport_response.json"):
                    self.http_call({"type": "openai_responses", "model": "explicit-model"}, raw)
                self.assertEqual((self.workdir / "transport_response.json").read_bytes(), raw)

    def test_http_response_is_saved_before_candidate_contract_parsing(self):
        result = responses_result()
        def inspect_before_parse(text):
            saved = json.loads((self.workdir / "transport_response.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, result)
            return json.loads(text)
        with patch("cipheur.providers._parse_candidate", side_effect=inspect_before_parse):
            candidate, _, _ = self.http_call(
                {"type": "openai_responses", "model": "explicit-model"}, result)
        self.assertEqual(candidate, CANDIDATE)

    def test_http_response_storage_failure_is_explicit(self):
        with patch("cipheur.providers.Path.write_bytes", side_effect=PermissionError("secret-value")):
            with self.assertRaisesRegex(ProviderError, "could not be saved") as raised:
                self.http_call({"type": "openai_responses", "model": "explicit-model"}, responses_result())
        self.assertNotIn("secret-value", str(raised.exception))

    def test_http_providers_require_model_and_key(self):
        for provider in ("openai_responses", "openai_compatible"):
            with self.subTest(provider=provider):
                with patch("cipheur.providers.urlopen") as opened:
                    with self.assertRaises(ProviderError):
                        generate_candidate({"type": provider}, REQUEST, self.workdir)
                    opened.assert_not_called()
                with patch.dict(os.environ, {}, clear=True), \
                        patch("cipheur.providers.urlopen") as opened:
                    with self.assertRaises(ProviderError):
                        generate_candidate({"type": provider, "model": "explicit-model"},
                                           REQUEST, self.workdir)
                    opened.assert_not_called()

    def test_http_failures_are_explicit_and_do_not_echo_secrets(self):
        failures = [HTTPError("https://example.test", 401, "secret-value", {}, io.BytesIO()),
                    URLError("secret-value"), TimeoutError("secret-value")]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), \
                    patch.dict(os.environ, {"TEST_PROVIDER_KEY": "secret-value"}), \
                    patch("cipheur.providers.urlopen", side_effect=failure), \
                    patch("cipheur.providers.subprocess.run") as run:
                with self.assertRaises(ProviderError) as raised:
                    generate_candidate({"type": "openai_responses", "model": "explicit-model",
                                        "api_key_env": "TEST_PROVIDER_KEY"}, REQUEST, self.workdir)
                self.assertNotIn("secret-value", str(raised.exception))
                run.assert_not_called()
                self.assertFalse((self.workdir / "transport_response.json").exists())

    def test_http_error_response_is_preserved_and_echoed_api_key_redacted(self):
        body = b'{"error":{"code":"bad_request","message":"echo: secret-value"}}'
        failure = HTTPError("https://example.test", 400, "secret-value", {}, io.BytesIO(body))
        with patch.dict(os.environ, {"TEST_PROVIDER_KEY": "secret-value"}), \
                patch("cipheur.providers.urlopen", side_effect=failure):
            with self.assertRaisesRegex(ProviderError, "transport_response.json") as raised:
                generate_candidate({"type": "openai_responses", "model": "explicit-model",
                                    "api_key_env": "TEST_PROVIDER_KEY"}, REQUEST, self.workdir)
        saved = (self.workdir / "transport_response.json").read_bytes()
        self.assertEqual(saved, body.replace(b"secret-value", b"[REDACTED_API_KEY]"))
        self.assertNotIn(b"secret-value", saved)
        self.assertNotIn("secret-value", str(raised.exception))

    def test_success_response_redacts_unexpected_key_echo_from_audit_file(self):
        result = responses_result()
        result["unexpected_echo"] = "test-not-a-real-key"
        candidate, _, _ = self.http_call(
            {"type": "openai_responses", "model": "explicit-model"}, result)
        saved = (self.workdir / "transport_response.json").read_bytes()
        self.assertNotIn(b"test-not-a-real-key", saved)
        self.assertIn(b"[REDACTED_API_KEY]", saved)
        self.assertEqual(candidate, CANDIDATE)

    def test_compatible_json_mode_custom_endpoint(self):
        candidate, metadata, opened = self.http_call(
            {"type": "openai_compatible", "model": "explicit-model", "json_mode": True,
             "base_url": "https://example.test/v1/"}, compatible_result())
        self.assertEqual(candidate, CANDIDATE)
        self.assertEqual(metadata["backend"], "openai_compatible")
        self.assertEqual(metadata["tokens"]["prompt_tokens"], 12)
        self.assertEqual(json.loads((self.workdir / "transport_response.json").read_text(encoding="utf-8")),
                         compatible_result())
        outgoing = opened.call_args.args[0]
        self.assertEqual(outgoing.full_url, "https://example.test/v1/chat/completions")
        payload = json.loads(outgoing.data)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertIn('"additionalProperties": false', payload["messages"][0]["content"])

    def test_compatible_non_json_mode_omits_response_format(self):
        _, _, opened = self.http_call(
            {"type": "openai_compatible", "model": "explicit-model", "json_mode": False},
            compatible_result())
        self.assertNotIn("response_format", json.loads(opened.call_args.args[0].data))

    def test_compatible_rejects_incomplete_refused_and_tool_output(self):
        cases = []
        for finish in ("length", "content_filter", "tool_calls", None):
            value = compatible_result()
            value["choices"][0]["finish_reason"] = finish
            cases.append(value)
        value = compatible_result()
        value["choices"][0]["message"]["refusal"] = "refused"
        cases.append(value)
        value = compatible_result()
        value["choices"][0]["message"]["tool_calls"] = [{"type": "function"}]
        cases.append(value)
        value = compatible_result()
        value["choices"] = []
        cases.append(value)
        for result in cases:
            with self.subTest(result=result):
                with self.assertRaisesRegex(ProviderError, "transport_response.json"):
                    self.http_call({"type": "openai_compatible", "model": "explicit-model"}, result)
                self.assertEqual(json.loads((self.workdir / "transport_response.json").read_text(encoding="utf-8")),
                                 result)

    def test_command_real_temporary_python_transport(self):
        script = (
            "import json,pathlib,sys; "
            "request=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); "
            "assert 'schema' in request; "
            "pathlib.Path(sys.argv[2]).write_text(json.dumps("
            + repr(CANDIDATE) + "),encoding='utf-8')"
        )
        candidate, metadata = generate_candidate(
            {"type": "command", "argv": [sys.executable, "-c", script, "{request}", "{response}"]},
            REQUEST, self.workdir)
        self.assertEqual(candidate, CANDIDATE)
        self.assertEqual(metadata["backend"], "external_command")
        self.assertIs(metadata["live_llm"], False)
        self.assertEqual(json.loads((self.workdir / "request.json").read_text(encoding="utf-8")),
                         REQUEST)

    def test_command_uses_argv_without_shell_and_explicit_llm_declaration(self):
        def successful_command(argv, **kwargs):
            self.assertFalse(kwargs["shell"])
            self.assertEqual(argv[0], "test-executable")
            self.assertEqual(argv[1], str((self.workdir / "request.json").resolve()))
            self.assertEqual(argv[2], str((self.workdir / "response.json").resolve()))
            (self.workdir / "response.json").write_text(json.dumps(CANDIDATE), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")
        with patch("cipheur.providers.subprocess.run", side_effect=successful_command):
            _, metadata = generate_candidate(
                {"type": "command", "declares_llm": True, "model": "external-model",
                 "argv": ["test-executable", "{request}", "{response}"]}, REQUEST, self.workdir)
        self.assertEqual(metadata["backend"], "external_command")
        self.assertIs(metadata["live_llm"], True)
        self.assertEqual(metadata["model"], "external-model")

    def test_command_stale_response_never_counts_as_success(self):
        (self.workdir / "response.json").write_text(json.dumps(CANDIDATE), encoding="utf-8")
        with patch("cipheur.providers.subprocess.run", return_value=subprocess.CompletedProcess(
                ["dummy"], 0, "", "")):
            with self.assertRaises(ProviderError):
                generate_candidate({"type": "command", "argv": ["dummy"]}, REQUEST, self.workdir)
        self.assertFalse((self.workdir / "response.json").exists())

    def test_command_timeout_nonzero_and_launch_failure(self):
        failures = [subprocess.TimeoutExpired(["dummy"], 1), OSError("secret-value")]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), \
                    patch("cipheur.providers.subprocess.run", side_effect=failure):
                with self.assertRaises(ProviderError) as raised:
                    generate_candidate({"type": "command", "argv": ["dummy"]}, REQUEST, self.workdir)
                self.assertNotIn("secret-value", str(raised.exception))
        with patch("cipheur.providers.subprocess.run", return_value=subprocess.CompletedProcess(
                ["dummy"], 3, "secret-value", "secret-value")):
            with self.assertRaisesRegex(ProviderError, "exit code 3"):
                generate_candidate({"type": "command", "argv": ["dummy"]}, REQUEST, self.workdir)

    def test_command_requires_list_argv_and_boolean_llm_flag(self):
        for config in ({"type": "command", "argv": "echo dummy"},
                       {"type": "command", "argv": []},
                       {"type": "command", "argv": [1]},
                       {"type": "command", "argv": ["dummy"], "declares_llm": "true"}):
            with self.subTest(config=config), patch("cipheur.providers.subprocess.run") as run:
                with self.assertRaises(ProviderError):
                    generate_candidate(config, REQUEST, self.workdir)
                run.assert_not_called()

    def test_invalid_timeout_is_rejected_without_running(self):
        for value in (0, -1, "NaN", True, None):
            with self.subTest(value=value), patch("cipheur.providers.subprocess.run") as run:
                with self.assertRaises(ProviderError):
                    generate_candidate({"type": "command", "argv": ["dummy"],
                                        "timeout_seconds": value}, REQUEST, self.workdir)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
