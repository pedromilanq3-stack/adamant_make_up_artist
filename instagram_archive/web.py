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
            try:
                context = int(query.get("context", ["0"])[0])
            except ValueError:
                context = 0
            results = search(archive.conversations, query.get("name", [""])[0], query.get("keyword", [""])[0], day("start"), day("end"), context)
            hide = "anon" in query

            def render_message(message, css_class: str) -> str:
                text = anonymize(message.text) if hide else message.text
                return (f'<div class="{css_class}"><strong>{html.escape(message.sender)}</strong> '
                        f'<time>{message.sent_at:%d/%m/%Y %H:%M}</time><p>{html.escape(text)}</p></div>')

            cards = "".join(
                f'<article><header>{html.escape(r.conversation.title)} · {html.escape(r.message.sender)}</header>'
                f'<p class="evidence"><strong>Correspondência:</strong> {html.escape(", ".join(r.matched_in) or "filtros de data/texto")} · <strong>Origem:</strong> {html.escape(r.conversation.source)}</p>'
                f'{"".join(render_message(message, "context") for message in r.before)}'
                f'{render_message(r.message, "match")}'
                f'{"".join(render_message(message, "context") for message in r.after)}'
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
        <div class="start-here"><strong>Comece agora por aqui</strong><ol><li>No Instagram, abra <strong>Central de Contas → Suas informações e permissões → Baixar suas informações</strong>.</li><li>Solicite as mensagens em formato <strong>JSON</strong> e aguarde o Instagram preparar o arquivo.</li><li>Quando o download terminar, volte a esta página e toque em <strong>Escolher arquivo</strong>.</li><li>Selecione o arquivo <strong>.zip sem descompactá-lo</strong> e toque em <strong>Importar com segurança</strong>.</li></ol><p class="pydroid-note"><strong>Usando Pydroid 3?</strong> Abra e execute o arquivo <code>iniciar.py</code>. O comando <code>python -m ...</code> deve ser usado no Terminal, não digitado no editor Python.</p></div>
        <form action="/upload" method="post" enctype="multipart/form-data"><label>Exportação oficial (.zip)<input required type="file" name="archive" accept=".zip,application/zip"></label><button>Importar com segurança</button></form></section>
        <aside><strong>Sobre os dados do seu celular</strong><p>Este site local não consegue entrar, navegar ou examinar seu celular sozinho. Ele analisa somente o arquivo que você selecionar acima, e esse ZIP contém dados do Instagram — não um inventário completo do aparelho.</p></aside>
        <section class="device-help"><h2>Quer verificar o restante do aparelho?</h2><p>Faça isso pelas ferramentas oficiais do seu próprio celular. Não envie senha, PIN, token, código de verificação ou um backup completo a este programa.</p>
        <div class="platforms"><div><h3>Android</h3><ol><li>Abra <strong>Configurações → Armazenamento</strong> para ver aplicativos e arquivos por categoria.</li><li>Use o app <strong>Files/Meus Arquivos</strong> para revisar Downloads, Imagens, Vídeos, Áudios e Documentos.</li><li>Em <strong>Configurações → Apps</strong>, confira os aplicativos instalados e as permissões concedidas.</li></ol></div>
        <div><h3>iPhone</h3><ol><li>Abra <strong>Ajustes → Geral → Armazenamento do iPhone</strong> para ver aplicativos e uso do espaço.</li><li>Use os apps <strong>Arquivos</strong> e <strong>Fotos → Apagados</strong> para revisar conteúdo acessível.</li><li>Em <strong>Ajustes → Privacidade e Segurança</strong>, confira quais apps acessam fotos, contatos e localização.</li></ol></div></div></section>
        <aside><strong>Limite importante</strong><p>O ZIP ainda sendo preparado não pode ser analisado: aguarde o download terminar. Nem esta ferramenta nem os menus do aparelho recuperam necessariamente dados já apagados. Evite aplicativos que prometem “recuperação total” ou pedem credenciais. Para uma perícia completa, preserve o aparelho e procure um profissional autorizado.</p></aside>
        <section><h2>Privacidade por padrão</h2><ul><li>Sem cookies, credenciais ou acesso à conta.</li><li>Arquivos temporários são apagados ao encerrar.</li><li>Nenhuma integração com GPT ou banco externo.</li></ul></section>'''

    @staticmethod
    def _search_form() -> str:
        return '''<section><span class="eyebrow">Exportação pronta · análise local</span><h1>Pesquisar todos os vestígios da conversa</h1><p class="notice">Informe o @ atual ou antigo. A busca ignora @, acentos, pontos e diferenças entre maiúsculas e minúsculas, e verifica título, participantes, remetentes, texto, anexos e caminho do arquivo.</p><form class="filters" action="/search" method="get">
        <label>@, usuário ou nome exibido<input name="name" placeholder="ex.: @usuario_antigo" autocomplete="off"></label><label>Palavra-chave opcional<input name="keyword" placeholder="ex.: reunião"></label>
        <label>Data inicial<input type="date" name="start"></label><label>Data final<input type="date" name="end"></label>
        <label>Contexto por resultado<select name="context"><option value="0">Somente a mensagem</option><option value="1" selected>1 antes e 1 depois</option><option value="3">3 antes e 3 depois</option><option value="5">5 antes e 5 depois</option></select></label>
        <label class="check"><input type="checkbox" name="anon" value="1" checked> Anonimizar CPF, telefone, e-mail e endereço</label><button>Pesquisar localmente</button></form>
        <p class="notice"><strong>Leitura do resultado:</strong> “Correspondência” indica exatamente em qual campo o vestígio foi localizado, e “Origem” preserva o arquivo da exportação para conferência. Se a Meta substituiu o nome por “Instagram User” e o identificador não aparece em nenhum arquivo, esta ferramenta não consegue atribuir a conversa à conta.</p><form action="/delete" method="post"><button class="danger">Eliminar índice local e temporários</button></form></section>'''


def main() -> None:
    address = ("127.0.0.1", int(os.environ.get("PORT", "8765")))
    print(f"Abra http://{address[0]}:{address[1]}")
    try:
        ThreadingHTTPServer(address, Handler).serve_forever()
    except KeyboardInterrupt:
        delete_index()


if __name__ == "__main__":
    main()
