"""Aplicação demonstrativa que simula falhas apenas em um perfil fictício."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = os.environ.get("CYBER_LAB_HOST", "127.0.0.1")
PORT = 8787
STATIC = Path(__file__).with_name("static")

SCENARIOS = {
    "session": {
        "title": "Sessão insegura",
        "vulnerable": "O laboratório aceita um identificador de sessão previsível.",
        "fixed": "A correção gera identificadores aleatórios, rotaciona a sessão e usa cookies seguros.",
        "event": "Tentativa simulada de reutilização de sessão detectada",
    },
    "reset": {
        "title": "Reset de senha",
        "vulnerable": "O token fictício pode ser reutilizado e não possui expiração.",
        "fixed": "A correção usa token aleatório, de uso único, com expiração curta.",
        "event": "Reutilização simulada de token de recuperação detectada",
    },
    "access": {
        "title": "Controle de acesso",
        "vulnerable": "A versão vulnerável confia apenas no identificador enviado pela interface.",
        "fixed": "A correção verifica no servidor se o recurso pertence ao usuário autenticado.",
        "event": "Acesso simulado a recurso de outro usuário bloqueado",
    },
}


def simulate_scenario(name: str) -> dict[str, str]:
    """Return educational evidence without attacking an account or external service."""
    if name not in SCENARIOS:
        raise KeyError(name)
    scenario = SCENARIOS[name]
    return {
        "scenario": scenario["title"],
        "vulnerable": scenario["vulnerable"],
        "fixed": scenario["fixed"],
        "event": scenario["event"],
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "scope": "localhost / @maysanchess_demo",
    }


class LabHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = "index.html" if self.path == "/" else self.path.removeprefix("/")
        if path not in {"index.html", "style.css", "app.js"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }[Path(path).suffix]
        self._send(HTTPStatus.OK, (STATIC / path).read_bytes(), content_type)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self.path.startswith("/api/scenario/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        name = self.path.rsplit("/", 1)[-1]
        try:
            body = json.dumps(simulate_scenario(name), ensure_ascii=False).encode()
        except KeyError:
            self.send_error(HTTPStatus.NOT_FOUND, "Cenário desconhecido")
            return
        self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[cyber-lab] {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), LabHandler)
    print(f"Laboratório fictício em http://{HOST}:{PORT}")
    print("Perfil de teste: @maysanchess_demo — nenhum serviço externo é acessado.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
