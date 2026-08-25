import io
import json
import os
import unittest
import urllib.error
from http.client import HTTPMessage
from unittest.mock import patch

import tinder_ai_server


class FakeResponse:
    def __init__(self, payload):
        self.payload = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.payload.read(size)


class TinderAIServerTests(unittest.TestCase):
    def test_health_identifies_running_server_version(self):
        handler = object.__new__(tinder_ai_server.Handler)
        handler.path = "/health"
        handler.headers = HTTPMessage()
        with patch.object(handler, "_send_json") as send_json:
            handler.do_GET()

        status, payload = send_json.call_args.args
        self.assertEqual(status, 200)
        self.assertEqual(payload["server_version"], tinder_ai_server.SERVER_VERSION)
        self.assertEqual(payload["openai_endpoint"], "/v1/chat/completions")
        self.assertEqual(payload["fallback_endpoint"], "/v1/responses")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("tinder_ai_server.urllib.request.urlopen")
    def test_validates_and_returns_json_decision(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"choices": [{"message": {"content": '{"action":"LIKE","reason":"Critério textual atendido."}'}}]}
        )

        result = tinder_ai_server.request_openai(
            {"text": "Bio textual de teste"}, "LIKE se mencionar teste"
        )

        self.assertEqual(result["action"], "LIKE")
        request = urlopen.call_args.args[0]
        sent = json.loads(request.data)
        transmitted = json.loads(sent["messages"][-1]["content"])
        self.assertEqual(set(transmitted), {"criteria", "profile_text"})
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_requires_api_key(self):
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            tinder_ai_server.request_openai({"text": "teste"}, "critério")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("tinder_ai_server.urllib.request.urlopen")
    def test_generates_text_only_reply_draft(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"choices": [{"message": {"content": '{"reply":"Também gosto de trilhas! Qual foi a última?","reason":"Pergunta aberta."}'}}]}
        )

        result = tinder_ai_server.request_openai_reply(
            "Pessoa: gosto de trilhas", "leve e curta"
        )

        self.assertIn("trilhas", result["reply"])
        sent = json.loads(urlopen.call_args.args[0].data)
        transmitted = json.loads(sent["messages"][-1]["content"])
        self.assertEqual(set(transmitted), {"conversation", "requested_style_and_examples"})

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("tinder_ai_server.urllib.request.urlopen")
    def test_retries_http_400_without_response_format(self, urlopen):
        urlopen.side_effect = [
            urllib.error.HTTPError(
                tinder_ai_server.OPENAI_URL,
                400,
                "Bad Request",
                {},
                io.BytesIO(b""),
            ),
            FakeResponse({"choices": [{"message": {"content": '{"reply":"Tudo bem! E você?","reason":"Pergunta aberta."}'}}]}),
        ]

        result = tinder_ai_server.request_openai_reply("Pessoa: oi", "curta")

        self.assertEqual(result["reply"], "Tudo bem! E você?")
        first = json.loads(urlopen.call_args_list[0].args[0].data)
        second = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertIn("response_format", first)
        self.assertNotIn("response_format", second)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("tinder_ai_server.urllib.request.urlopen")
    def test_falls_back_to_responses_api_after_two_http_400_errors(self, urlopen):
        errors = [
            urllib.error.HTTPError(
                tinder_ai_server.OPENAI_URL,
                400,
                "Bad Request",
                {},
                io.BytesIO(b""),
            )
            for _ in range(2)
        ]
        urlopen.side_effect = [
            *errors,
            FakeResponse({"output_text": '{"reply":"Tudo ótimo! E por aí?","reason":"Pergunta aberta."}'}),
        ]

        result = tinder_ai_server.request_openai_reply("Pessoa: oi", "curta")

        self.assertEqual(result["reply"], "Tudo ótimo! E por aí?")
        third_request = urlopen.call_args_list[2].args[0]
        self.assertEqual(third_request.full_url, tinder_ai_server.OPENAI_RESPONSES_URL)
        third = json.loads(third_request.data)
        self.assertEqual(set(third), {"model", "instructions", "input"})

    def test_extracts_detailed_openai_error(self):
        error = urllib.error.HTTPError(
            tinder_ai_server.OPENAI_URL,
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"error":{"message":"Invalid request payload"}}'),
        )

        try:
            self.assertEqual(
                tinder_ai_server.extract_openai_error(error), "Invalid request payload"
            )
        finally:
            error.close()


if __name__ == "__main__":
    unittest.main()
