"""Chat local no navegador com o cérebro vivo ao lado.

    python -m cerebro web            # abre http://127.0.0.1:8766

Servidor apenas local (127.0.0.1), sem dependências externas. Os cérebros
ficam em ``~/.cerebro`` (ou no diretório de ``CEREBRO_DIR``). Se o SDK
``anthropic`` estiver instalado e houver credencial, a fala vem do modelo;
caso contrário o chat roda em modo espelho (só o estado interno fala).
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .brain import Brain
from .emotions import EMOTION_LABELS
from .session import AnthropicResponder, MirrorResponder, Session

DEFAULT_PORT = 8766


def brains_dir() -> Path:
    return Path(os.environ.get("CEREBRO_DIR") or Path.home() / ".cerebro")


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "cerebro"


def has_model_credentials() -> bool:
    if os.environ.get("CEREBRO_MODO", "").lower() == "espelho":
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return (Path.home() / ".config" / "anthropic").exists()


def snapshot(brain: Brain, now: float | None = None) -> dict:
    """Estado estruturado para a interface."""
    now = time.time() if now is None else now
    return {
        "nome": brain.name,
        "genero": brain.gender,
        "descricao": brain.self_description,
        "estagio": brain._g(brain.stage),
        "idade": brain.age(now),
        "experiencias": brain.experience_count,
        "emocoes": {EMOTION_LABELS[e]: round(v, 3) for e, v in brain.emotions.levels.items()},
        "emocao_texto": brain._g(brain.emotions.describe()),
        "humor": brain.emotions.mood_label(),
        "energia": round(brain.emotions.energy, 3),
        "quimica": {c: round(v, 3) for c, v in brain.neuro.levels.items()},
        "quimica_texto": brain.neuro.describe(),
        "quadros": brain.neuro.describe_conditions(),
        "sono": brain.neuro.sleep_note(),
        "carater": brain._g(brain.character.describe()),
        "moralidade": round(brain.character.morality, 3),
        "alinhamento": brain._g(brain.character.alignment()),
        "temperamento": brain._g(brain.traits.describe()),
        "vinculo": round(brain.bond, 3),
        "postura": brain.stance,
        "proposito": brain.purpose,
        "valores": brain.values.describe(),
        "principios": list(brain.principles),
        "decisoes": list(brain.decisions[-4:]),
        "vida": [brain._g(entry) for entry in brain.world_log[-4:]],
        "impulso": brain._g(brain.whim) if brain.whim else "",
        "destino": brain._g(f"{brain.volatility_label()}; {brain.luck_label()}; {brain.resilience_label()}"),
        "licoes": [lesson.text for lesson in brain.memory.strongest_lessons()],
        "estrategias": {s: {"vezes": n, "resultado": round(brain.strategies.reward[s], 2)}
                        for s, n in brain.strategies.tries.items() if n},
        "resumo": brain.summary(now),
        "implante": brain.implant(now=now),
    }


class Hub:
    """Guarda as sessões abertas (uma por arquivo de cérebro)."""

    def __init__(self, directory: Path, model: str | None = None, force_mirror: bool = False) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, Session] = {}
        self.model = model or "claude-opus-5"
        self.use_model = (not force_mirror) and has_model_credentials()
        self._responder = None

    def responder(self, brain: Brain):
        if not self.use_model:
            return MirrorResponder(brain)
        if self._responder is None:
            try:
                self._responder = AnthropicResponder(model=self.model)
            except RuntimeError:
                self.use_model = False
                return MirrorResponder(brain)
        return self._responder

    def path_for(self, file: str) -> Path:
        name = Path(file).name
        if not name.endswith(".json") or name.startswith("."):
            raise ValueError("Arquivo inválido.")
        return self.directory / name

    def list(self) -> list[dict]:
        entries = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                brain = Brain.load(path)
            except (OSError, ValueError, KeyError):
                continue
            entries.append({"arquivo": path.name, "nome": brain.name, "estagio": brain._g(brain.stage),
                            "proposito": brain.purpose, "experiencias": brain.experience_count})
        return entries

    def create(self, name: str, description: str, gender: str) -> tuple[str, Brain]:
        brain = Brain.create(name, description, gender=gender)
        file = f"{slugify(name)}.json"
        path = self.directory / file
        counter = 2
        while path.exists():
            file = f"{slugify(name)}-{counter}.json"
            path = self.directory / file
            counter += 1
        brain.save(path)
        return file, brain

    def session(self, file: str) -> Session:
        path = self.path_for(file)
        if file not in self.sessions:
            brain = Brain.load(path)
            self.sessions[file] = Session(brain, responder=self.responder(brain), save_path=path)
        return self.sessions[file]

    def mode(self) -> str:
        return f"modelo {self.model}" if self.use_model else "modo espelho (sem modelo)"


def make_handler(hub: Hub):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CerebroLocal/1.0"

        def log_message(self, format: str, *args) -> None:  # silencioso
            pass

        # ------------------------------------------------------------ util
        def _send(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send(json.dumps(data, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8", status)

        def _error(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
            self._json({"erro": message}, status)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 200_000:
                raise ValueError("Mensagem grande demais.")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(data, dict):
                raise ValueError("Corpo inválido.")
            return data

        # ------------------------------------------------------------ GET
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif parsed.path == "/static/app.css":
                self._send(STYLE.encode("utf-8"), "text/css; charset=utf-8")
            elif parsed.path == "/static/app.js":
                self._send(SCRIPT.encode("utf-8"), "application/javascript; charset=utf-8")
            elif parsed.path == "/api/cerebros":
                self._json({"cerebros": hub.list(), "modo": hub.mode()})
            elif parsed.path == "/api/estado":
                file = parse_qs(parsed.query).get("arquivo", [""])[0]
                try:
                    session = hub.session(file)
                except (ValueError, FileNotFoundError):
                    return self._error("Cérebro não encontrado.", HTTPStatus.NOT_FOUND)
                session.brain.tick()
                self._json({"estado": snapshot(session.brain), "historico": session.history[-40:]})
            else:
                self._error("Não encontrado.", HTTPStatus.NOT_FOUND)

        # ------------------------------------------------------------ POST
        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                data = self._body()
            except (ValueError, json.JSONDecodeError):
                return self._error("Corpo inválido.")
            try:
                if parsed.path == "/api/criar":
                    file, brain = hub.create(str(data.get("nome", "")), str(data.get("descricao", "")),
                                             str(data.get("genero", "m")))
                    return self._json({"arquivo": file, "estado": snapshot(brain)})
                session = hub.session(str(data.get("arquivo", "")))
                brain = session.brain
                if parsed.path == "/api/dizer":
                    text = str(data.get("texto", "")).strip()
                    if not text:
                        return self._error("Escreva alguma coisa.")
                    reply = session.say(text)
                    return self._json({"resposta": reply, "estado": snapshot(brain)})
                if parsed.path == "/api/registrar":
                    reply = session.record_exchange(str(data.get("voce", "")), str(data.get("resposta", "")))
                    return self._json({"resposta": reply, "estado": snapshot(brain)})
                if parsed.path == "/api/acaso":
                    brain.tick()
                    experience = brain.fate.draw(brain.luck, brain.character.morality)
                    brain.live(experience)
                    brain.save(session.save_path)
                    return self._json({"acontecimento": experience.text, "estado": snapshot(brain)})
                if parsed.path == "/api/viver":
                    brain.tick()
                    experience = brain.event(str(data.get("texto", "")), float(data.get("valencia", 0.0)),
                                             float(data.get("intensidade", 0.5)))
                    brain.save(session.save_path)
                    return self._json({"acontecimento": experience.text, "estado": snapshot(brain)})
                return self._error("Não encontrado.", HTTPStatus.NOT_FOUND)
            except FileNotFoundError:
                return self._error("Cérebro não encontrado.", HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                return self._error(str(exc))

    return Handler


def serve(port: int = DEFAULT_PORT, directory: Path | None = None, model: str | None = None,
          force_mirror: bool = False) -> None:
    hub = Hub(directory or brains_dir(), model=model, force_mirror=force_mirror)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(hub))
    print(f"Cérebro local em http://127.0.0.1:{port} ({hub.mode()}). Cérebros em {hub.directory}. Ctrl+C encerra.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cérebro</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
<header>
  <h1>Cérebro</h1>
  <span id="modo"></span>
  <select id="lista"></select>
  <button id="novo">Novo cérebro</button>
  <button id="acaso" title="Deixa a vida acontecer com o cérebro">Deixar o destino agir</button>
  <button id="ver-implante">Ver implante</button>
</header>
<main>
  <section id="chat">
    <div id="mensagens"></div>
    <form id="form">
      <textarea id="texto" rows="2" placeholder="Fale com o cérebro..."></textarea>
      <button type="submit">Enviar</button>
    </form>
  </section>
  <aside id="estado">
    <p class="vazio">Crie ou escolha um cérebro.</p>
  </aside>
</main>
<dialog id="dialogo-novo">
  <form method="dialog" id="form-novo">
    <h2>Novo cérebro</h2>
    <label>Nome <input id="novo-nome" required></label>
    <label>Gênero dos adjetivos
      <select id="novo-genero"><option value="m">masculino</option><option value="f">feminino</option></select>
    </label>
    <label>Descrição de si (fica para sempre na conversa)
      <textarea id="novo-descricao" rows="4" required placeholder="Sou curiosa, tímida e gosto de ajudar quem sofre..."></textarea>
    </label>
    <menu><button value="cancel" type="button" id="cancelar-novo">Cancelar</button><button value="ok">Nascer</button></menu>
  </form>
</dialog>
<dialog id="dialogo-implante">
  <h2>Implante (cole como system prompt em qualquer chat)</h2>
  <textarea id="implante" rows="24" readonly></textarea>
  <menu><button id="copiar">Copiar</button><button id="fechar-implante">Fechar</button></menu>
</dialog>
<script src="/static/app.js"></script>
</body>
</html>
"""

STYLE = """
:root { --bg:#f4f1ea; --card:#fffdf8; --ink:#2a2622; --muted:#7a7268; --line:#e2dccf; --accent:#7a4b2a; --me:#e6dccb; --brain:#d9e4d3; }
* { box-sizing:border-box; }
body { margin:0; font:15px/1.45 system-ui, sans-serif; background:var(--bg); color:var(--ink); height:100vh; display:flex; flex-direction:column; }
header { display:flex; gap:.6rem; align-items:center; padding:.6rem 1rem; border-bottom:1px solid var(--line); background:var(--card); flex-wrap:wrap; }
header h1 { font-size:1.1rem; margin:0 .4rem 0 0; }
#modo { color:var(--muted); font-size:.85rem; margin-right:auto; }
button { background:var(--accent); color:#fff; border:0; border-radius:6px; padding:.45rem .8rem; cursor:pointer; font:inherit; }
button:disabled { opacity:.5; cursor:default; }
select, input, textarea { font:inherit; border:1px solid var(--line); border-radius:6px; padding:.4rem .5rem; background:#fff; color:var(--ink); }
main { flex:1; display:grid; grid-template-columns: 1fr 380px; min-height:0; }
#chat { display:flex; flex-direction:column; min-height:0; }
#mensagens { flex:1; overflow:auto; padding:1rem; display:flex; flex-direction:column; gap:.6rem; }
.msg { max-width:75%; padding:.55rem .8rem; border-radius:12px; white-space:pre-wrap; }
.msg.voce { align-self:flex-end; background:var(--me); }
.msg.cerebro { align-self:flex-start; background:var(--brain); }
.msg.sistema { align-self:center; background:transparent; color:var(--muted); font-size:.85rem; font-style:italic; }
#form { display:flex; gap:.5rem; padding:.7rem 1rem; border-top:1px solid var(--line); background:var(--card); }
#form textarea { flex:1; resize:vertical; }
#estado { border-left:1px solid var(--line); background:var(--card); overflow:auto; padding:1rem; font-size:.9rem; }
#estado h2 { font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:1rem 0 .3rem; }
#estado h2:first-child { margin-top:0; }
#estado p, #estado li { margin:.15rem 0; }
#estado ul { padding-left:1.1rem; margin:0; }
.barra { display:grid; grid-template-columns: 95px 1fr 34px; gap:.4rem; align-items:center; font-size:.8rem; }
.barra i { display:block; height:7px; background:var(--line); border-radius:4px; overflow:hidden; }
.barra i b { display:block; height:100%; background:var(--accent); }
.tag { display:inline-block; background:var(--me); border-radius:4px; padding:.05rem .4rem; margin:.1rem .2rem 0 0; font-size:.8rem; }
.tag.alerta { background:#f2d0c8; }
.vazio { color:var(--muted); }
dialog { border:1px solid var(--line); border-radius:10px; padding:1.2rem; max-width:640px; width:92vw; }
dialog label { display:block; margin:.6rem 0; }
dialog input, dialog textarea, dialog select { width:100%; }
dialog menu { display:flex; gap:.5rem; justify-content:flex-end; padding:0; margin:.8rem 0 0; }
#implante { width:100%; font:12px/1.4 ui-monospace, monospace; }
@media (max-width: 900px) { main { grid-template-columns:1fr; grid-template-rows: 1fr auto; } #estado { border-left:0; border-top:1px solid var(--line); max-height:40vh; } }
"""

SCRIPT = r"""
(() => {
  const $ = (id) => document.getElementById(id);
  let arquivo = null;

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

  async function api(path, body) {
    const res = await fetch(path, body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : undefined);
    const data = await res.json();
    if (!res.ok) throw new Error(data.erro || "Erro");
    return data;
  }

  function addMsg(kind, text) {
    const div = document.createElement("div");
    div.className = "msg " + kind;
    div.textContent = text;
    $("mensagens").appendChild(div);
    $("mensagens").scrollTop = $("mensagens").scrollHeight;
  }

  function barras(obj, max) {
    return Object.entries(obj).map(([k, v]) => {
      const pct = Math.round(v * 100);
      return `<div class="barra"><span>${esc(k)}</span><i><b style="width:${pct}%"></b></i><span>${pct}</span></div>`;
    }).join("");
  }

  function render(e) {
    $("estado").innerHTML = `
      <h2>${esc(e.nome)} · ${esc(e.estagio)}</h2>
      <p>${esc(e.idade)} de vida · ${e.experiencias} experiências</p>
      <p class="vazio">"${esc(e.descricao)}"</p>
      <h2>Agora</h2>
      <p>Sinto-me ${esc(e.emocao_texto)}; ${esc(e.humor)}.</p>
      ${e.impulso ? `<p>Impulso: ${esc(e.impulso)}</p>` : ""}
      <p>Postura: <span class="tag">${esc(e.postura)}</span></p>
      ${barras(e.emocoes)}
      <h2>Corpo e química</h2>
      <p>${esc(e.quimica_texto)}${e.quadros ? ` · <span class="tag alerta">${esc(e.quadros)}</span>` : ""}</p>
      ${e.sono ? `<p>${esc(e.sono)}</p>` : ""}
      ${barras(e.quimica)}
      <h2>Caráter</h2>
      <p>${esc(e.carater)}</p>
      <p>Moralidade ${e.moralidade > 0 ? "+" : ""}${e.moralidade.toFixed(2)} (${esc(e.alinhamento)}) · vínculo ${e.vinculo > 0 ? "+" : ""}${e.vinculo.toFixed(2)}</p>
      <p>${esc(e.temperamento)}</p>
      <h2>O que faz sentido pra mim</h2>
      <p>Quero: <strong>${esc(e.proposito)}</strong></p>
      <p>Importa: ${esc(e.valores)}</p>
      <ul>${e.principios.map(p => `<li>${esc(p)}</li>`).join("")}</ul>
      ${e.decisoes.length ? `<h2>Decisões</h2><ul>${e.decisoes.map(d => `<li>${esc(d)}</li>`).join("")}</ul>` : ""}
      ${e.vida.length ? `<h2>O que a vida fez</h2><ul>${e.vida.map(d => `<li>${esc(d)}</li>`).join("")}</ul>` : ""}
      ${e.licoes.length ? `<h2>Lições</h2><ul>${e.licoes.map(d => `<li>${esc(d)}</li>`).join("")}</ul>` : ""}
      <h2>Destino</h2><p>${esc(e.destino)}</p>
      ${Object.keys(e.estrategias).length ? `<h2>Estratégias</h2><p>${Object.entries(e.estrategias).map(([s, r]) => `<span class="tag">${esc(s)} ${r.vezes}x ${r.resultado >= 0 ? "+" : ""}${r.resultado}</span>`).join(" ")}</p>` : ""}
    `;
    $("implante").value = e.implante;
  }

  async function carregarLista(selecionar) {
    const data = await api("/api/cerebros");
    $("modo").textContent = data.modo;
    const lista = $("lista");
    lista.innerHTML = '<option value="">— escolha um cérebro —</option>' +
      data.cerebros.map(c => `<option value="${esc(c.arquivo)}">${esc(c.nome)} (${esc(c.estagio)}, ${c.experiencias} exp.)</option>`).join("");
    if (selecionar) { lista.value = selecionar; await abrir(selecionar); }
  }

  async function abrir(file) {
    arquivo = file || null;
    $("mensagens").innerHTML = "";
    if (!arquivo) { $("estado").innerHTML = '<p class="vazio">Crie ou escolha um cérebro.</p>'; return; }
    const data = await api("/api/estado?arquivo=" + encodeURIComponent(arquivo));
    for (const m of data.historico) addMsg(m.role === "user" ? "voce" : "cerebro", m.content);
    render(data.estado);
  }

  $("lista").addEventListener("change", (ev) => abrir(ev.target.value));
  $("novo").addEventListener("click", () => $("dialogo-novo").showModal());
  $("cancelar-novo").addEventListener("click", () => $("dialogo-novo").close());
  $("form-novo").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      const data = await api("/api/criar", {nome: $("novo-nome").value, descricao: $("novo-descricao").value, genero: $("novo-genero").value});
      $("dialogo-novo").close();
      await carregarLista(data.arquivo);
      addMsg("sistema", `${data.estado.nome} acabou de nascer.`);
    } catch (e) { alert(e.message); }
  });

  $("form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const texto = $("texto").value.trim();
    if (!texto || !arquivo) return;
    $("texto").value = "";
    addMsg("voce", texto);
    const btn = ev.target.querySelector("button"); btn.disabled = true;
    try {
      const data = await api("/api/dizer", {arquivo, texto});
      addMsg("cerebro", data.resposta);
      render(data.estado);
    } catch (e) { addMsg("sistema", "Erro: " + e.message); }
    finally { btn.disabled = false; $("texto").focus(); }
  });
  $("texto").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); $("form").requestSubmit(); }
  });

  $("acaso").addEventListener("click", async () => {
    if (!arquivo) return;
    try {
      const data = await api("/api/acaso", {arquivo});
      addMsg("sistema", "A vida agiu: " + data.acontecimento);
      render(data.estado);
    } catch (e) { alert(e.message); }
  });

  $("ver-implante").addEventListener("click", () => { if (arquivo) $("dialogo-implante").showModal(); });
  $("fechar-implante").addEventListener("click", () => $("dialogo-implante").close());
  $("copiar").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("implante").value); $("copiar").textContent = "Copiado"; setTimeout(() => $("copiar").textContent = "Copiar", 1500); }
    catch (e) { $("implante").select(); }
  });

  carregarLista();
})();
"""
