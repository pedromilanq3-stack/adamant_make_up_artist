from __future__ import annotations

import atexit
import html
import os
import tempfile
from datetime import date
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .importer import ArchiveError, InstagramArchive
from .search import anonymize, search
from .security import MAX_ARCHIVE_BYTES

HERE = Path(__file__).parent
STATE: dict[str, InstagramArchive | None] = {"archive": None}


def delete_index() -> None:
    archive = STATE.get("archive")
    if archive:
        archive.close()
    STATE["archive"] = None


atexit.register(delete_index)


class Handler(BaseHTTPRequestHandler):
    server_version = "InstagramLocal/1.0"

    def _page(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        template = (HERE / "templates/index.html").read_text(encoding="utf-8")
        body = template.replace("{{CONTENT}}", content).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/static/style.css":
            data = (HERE / "static/style.css").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/css"); self.end_headers(); self.wfile.write(data)
            return
        archive = STATE.get("archive")
        if parsed.path == "/search" and archive:
            query = parse_qs(parsed.query)
            def day(key: str) -> date | None:
                try: return date.fromisoformat(query.get(key, [""])[0])
                except ValueError: return None
            results = search(archive.conversations, query.get("name", [""])[0], query.get("keyword", [""])[0], day("start"), day("end"))
            cards = "".join(
                f'<article><header>{html.escape(r.conversation.title)} · {html.escape(r.message.sender)}</header>'
                f'<time>{r.message.sent_at:%d/%m/%Y %H:%M}</time><p>{html.escape(anonymize(r.message.text) if "anon" in query else r.message.text)}</p>'
                f'<small>{len(r.message.attachments)} anexo(s)</small></article>' for r in results)
            self._page(self._search_form() + f"<h2>{len(results)} resultado(s)</h2>" + (cards or '<p class="empty">Nada encontrado na exportação. Conteúdo ausente não pode ser recuperado dos servidores do Instagram.</p>'))
            return
        self._page(self._home())

    def do_POST(self) -> None:
        if self.path == "/delete":
            delete_index()
            self._page('<div class="success"><h2>Índice local eliminado</h2><p>Os arquivos temporários foram apagados.</p></div>' + self._upload())
            return
        if self.path != "/upload":
            self.send_error(404); return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._page("<p>Envio inválido.</p>", HTTPStatus.BAD_REQUEST); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_ARCHIVE_BYTES + 1024 * 1024:
            self._page('<p class="error">Envio vazio ou acima do limite de 250 MB.</p>' + self._upload(), HTTPStatus.BAD_REQUEST); return
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + self.rfile.read(length)
        )
        field = next((part for part in message.iter_parts() if part.get_param("name", header="content-disposition") == "archive"), None)
        filename = field.get_filename() if field else ""
        if field is None or not filename or not filename.lower().endswith(".zip"):
            self._page('<p class="error">Selecione exclusivamente um arquivo .zip.</p>' + self._upload(), HTTPStatus.BAD_REQUEST); return
        fd, name = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        try:
            with open(name, "wb") as output:
                output.write(field.get_payload(decode=True) or b"")
            candidate = InstagramArchive(name)
            candidate.load()
            delete_index()
            STATE["archive"] = candidate
            self._page('<div class="success"><h2>Exportação carregada localmente</h2><p>Nenhum dado foi transmitido.</p></div>' + self._search_form())
        except (ArchiveError, OSError) as exc:
            self._page(f'<p class="error">{html.escape(str(exc))}</p>' + self._upload(), HTTPStatus.BAD_REQUEST)
        finally:
            Path(name).unlink(missing_ok=True)

    def _home(self) -> str:
        archive = STATE.get("archive")
        return (self._search_form() if archive else self._upload())

    @staticmethod
    def _upload() -> str:
        return '''<section class="hero"><span class="eyebrow">100% local · sem login</span><h1>Encontre mensagens na sua exportação do Instagram</h1>
        <p>Use somente o ZIP obtido em <strong>Instagram → Central de Contas → Suas informações e permissões → Baixar suas informações</strong>.</p>
        <form action="/upload" method="post" enctype="multipart/form-data"><label>Exportação oficial (.zip)<input required type="file" name="archive" accept=".zip,application/zip"></label><button>Importar com segurança</button></form></section>
        <aside><strong>Limite importante</strong><p>Esta ferramenta não recupera mensagens apagadas nem consulta servidores do Instagram. Ela só pesquisa conteúdo já presente no ZIP fornecido pelo próprio titular.</p></aside>
        <section><h2>Privacidade por padrão</h2><ul><li>Sem cookies, credenciais ou acesso à conta.</li><li>Arquivos temporários são apagados ao encerrar.</li><li>Nenhuma integração com GPT ou banco externo.</li></ul></section>'''

    @staticmethod
    def _search_form() -> str:
        return '''<section><span class="eyebrow">Exportação pronta</span><h1>Pesquisar conversas</h1><form class="filters" action="/search" method="get">
        <label>Usuário ou nome exibido<input name="name" placeholder="ex.: maria"></label><label>Palavra-chave<input name="keyword" placeholder="ex.: reunião"></label>
        <label>Data inicial<input type="date" name="start"></label><label>Data final<input type="date" name="end"></label><label class="check"><input type="checkbox" name="anon" value="1" checked> Anonimizar CPF, telefone, e-mail e endereço</label><button>Pesquisar localmente</button></form>
        <p class="notice">Resultados ausentes não podem ser recuperados dos servidores do Instagram.</p><form action="/delete" method="post"><button class="danger">Eliminar índice local e temporários</button></form></section>'''


def main() -> None:
    address = ("127.0.0.1", int(os.environ.get("PORT", "8765")))
    print(f"Abra http://{address[0]}:{address[1]}")
    try:
        ThreadingHTTPServer(address, Handler).serve_forever()
    except KeyboardInterrupt:
        delete_index()


if __name__ == "__main__":
    main()
