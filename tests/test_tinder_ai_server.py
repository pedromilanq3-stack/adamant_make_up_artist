import io
import json
import os
import unittest
import urllib.error
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
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("tinder_ai_server.urllib.request.urlopen")
    def test_validates_and_returns_json_decision(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"output_text": '{"action":"LIKE","reason":"Critério textual atendido."}'}
        )

        result = tinder_ai_server.request_openai(
            {"text": "Bio textual de teste"}, "LIKE se mencionar teste"
        )

        self.assertEqual(result["action"], "LIKE")
        request = urlopen.call_args.args[0]
        sent = json.loads(request.data)
        transmitted = json.loads(sent["input"])
        self.assertEqual(set(transmitted), {"criteria", "profile_text"})
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_requires_api_key(self):
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            tinder_ai_server.request_openai({"text": "teste"}, "critério")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("tinder_ai_server.urllib.request.urlopen")
    def test_generates_text_only_reply_draft(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"output_text": '{"reply":"Também gosto de trilhas! Qual foi a última?","reason":"Pergunta aberta."}'}
        )

        result = tinder_ai_server.request_openai_reply(
            "Pessoa: gosto de trilhas", "leve e curta"
        )

        self.assertIn("trilhas", result["reply"])
        sent = json.loads(urlopen.call_args.args[0].data)
        transmitted = json.loads(sent["input"])
        self.assertEqual(set(transmitted), {"conversation", "requested_style_and_examples"})

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
