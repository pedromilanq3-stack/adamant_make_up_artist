"""Proxy local mínimo entre o userscript e a OpenAI Responses API.

Mantém OPENAI_API_KEY fora do navegador e transmite somente texto explicitamente
enviado pelo userscript. Fotos, cookies e credenciais do Tinder nunca são recebidos.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8767
OPENAI_URL = "https://api.openai.com/v1/responses"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
MAX_BODY = 32_000

SYSTEM_PROMPT = """Você sugere uma decisão para um perfil de namoro usando SOMENTE o
texto fornecido e os critérios do usuário. Nunca infira gênero, raça, saúde, religião,
orientação sexual ou qualquer característica pela aparência, nome ou pistas ambíguas.
Não há imagens. Se os critérios não puderem ser aplicados com segurança, escolha SKIP.
Responda apenas JSON: {"action":"LIKE|REJECT|SKIP","reason":"frase curta"}."""

REPLY_SYSTEM_PROMPT = """Você sugere um rascunho de resposta para uma conversa de
namoro usando SOMENTE o texto fornecido. Seja respeitoso, não pressione, não manipule,
não invente fatos e não infira características sensíveis. Se não houver contexto
suficiente ou houver pedido abusivo, retorne uma resposta vazia. Responda apenas JSON:
{"reply":"rascunho curto","reason":"frase curta"}. Nunca afirme que enviou a mensagem."""


def extract_output_text(result: dict) -> str:
    if result.get("output_text"):
        return str(result["output_text"])
    chunks = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                chunks.append(content.get("text", ""))
    return "".join(chunks)


def extract_openai_error(error: urllib.error.HTTPError) -> str:
    fallback = f"OpenAI API respondeu HTTP {error.code}"
    raw = error.read()
    if not raw:
        return fallback
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
        detail = payload.get("error", fallback)
        if isinstance(detail, dict):
            return str(detail.get("message") or detail.get("code") or fallback)[:1000]
        return str(detail)[:1000]
    except json.JSONDecodeError:
        # A resposta nunca deve conter a chave enviada no cabeçalho. Limita o corpo
        # para evitar despejar páginas inteiras ou dados inesperados no navegador.
        return f"{fallback}: {text.strip()[:500]}"


def request_openai(profile: dict, criteria: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada")
    prompt = json.dumps(
        {"criteria": criteria, "profile_text": profile.get("text", "")[:4000]},
        ensure_ascii=False,
    )
    payload = json.dumps(
        {"model": MODEL, "instructions": SYSTEM_PROMPT, "input": prompt},
        ensure_ascii=False,
    ).encode()
    request = urllib.request.Request(
        OPENAI_URL,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    output = extract_output_text(result)
    decision = json.loads(output)
    if decision.get("action") not in {"LIKE", "REJECT", "SKIP"}:
        raise ValueError("A API retornou uma ação inválida")
    return {"action": decision["action"], "reason": str(decision.get("reason", ""))[:500]}


def request_openai_reply(conversation: str, style: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada")
    prompt = json.dumps(
        {"conversation": conversation[-6000:], "requested_style_and_examples": style[:2000]},
        ensure_ascii=False,
    )
    payload = json.dumps(
        {"model": MODEL, "instructions": REPLY_SYSTEM_PROMPT, "input": prompt},
        ensure_ascii=False,
    ).encode()
    request = urllib.request.Request(
        OPENAI_URL,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    output = extract_output_text(result)
    suggestion = json.loads(output)
    return {
        "reply": str(suggestion.get("reply", ""))[:1000],
        "reason": str(suggestion.get("reason", ""))[:500],
    }


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        origin = self.headers.get("Origin", "")
        if origin in {"https://tinder.com", "https://www.tinder.com"}:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _send_json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_error(404)
            return
        self._send_json(200, {"ok": True, "model": MODEL, "api_key_configured": bool(os.environ.get("OPENAI_API_KEY"))})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/decision", "/reply"}:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise ValueError("Corpo vazio ou grande demais")
            body = json.loads(self.rfile.read(length))
            if self.path == "/decision":
                profile = body.get("profile") or {}
                if not isinstance(profile, dict) or not isinstance(profile.get("text", ""), str):
                    raise ValueError("Perfil inválido")
                result = request_openai(profile, str(body.get("criteria", ""))[:1000])
            else:
                conversation = body.get("conversation", "")
                if not isinstance(conversation, str) or not conversation.strip():
                    raise ValueError("Conversa inválida")
                result = request_openai_reply(conversation, str(body.get("style", "")))
            self._send_json(200, result)
        except (ValueError, RuntimeError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
        except urllib.error.HTTPError as error:
            self._send_json(502, {"error": extract_openai_error(error)})
        except (urllib.error.URLError, TimeoutError) as error:
            self._send_json(502, {"error": f"Falha na API: {error}"})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[TinderAI] {format % args}")


def main() -> None:
    print(f"TinderAI local em http://{HOST}:{PORT} usando {MODEL}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
