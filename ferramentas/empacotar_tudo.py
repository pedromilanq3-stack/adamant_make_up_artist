"""Junta tudo de um personagem (ou de todos) em um zip só.

    python ferramentas/empacotar_tudo.py --personagem harvey-specter   # personagens/harvey-specter/harvey-specter-tudo.zip
    python ferramentas/empacotar_tudo.py --todos                       # personagens-tudo.zip na raiz

O zip de um personagem contém: origem, cérebro do motor (JSON), ficha, a skill
(zip para Claude.ai), o pacote para ChatGPT (instruções, conhecimento, prompt
único) e um LEIA-ME. O zip de todos junta cada personagem, o programa em
arquivo único (cerebro.pyz, cerebro_android.py) e a skill genérica.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PERSONAGENS = ROOT / "personagens"

README = """# {nome}: tudo em um lugar

| Onde usar | O que usar |
|---|---|
| Claude.ai (site ou app) | `{slug}-skill.zip`: envie em Configurações > Capacidades > Skills e chame com /{slug} |
| ChatGPT, GPT personalizado | `gpt/instrucoes.md` no campo Instruções e os arquivos de `gpt/conhecimento/` em Conhecimento |
| ChatGPT ou qualquer chat, sem instalar | cole `gpt/prompt-unico.md` como primeira mensagem |
| Programa em código (chat web, Termux, Pydroid) | `{slug}.json` na pasta ~/.cerebro, ou `python cerebro.pyz conversar --arquivo {slug}.json` |
| Skill pura em qualquer lugar | `ficha.md` com `/cerebro carregar` |
| Regenerar tudo | `origem.txt` com `python ferramentas/empacotar_personagem.py --nome "{nome}" --origem origem.txt` |

Comandos dentro da conversa: estado, acaso, viver <acontecimento>, salvar, carregar, parar.
"""


def _add(archive: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(arcname, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data)


def build_one(slug: str, archive: zipfile.ZipFile | None = None, prefix: str = "") -> Path:
    folder = PERSONAGENS / slug
    if not (folder / f"{slug}.json").exists():
        raise SystemExit(f"Personagem não encontrado: {folder}")
    from cerebro import Brain
    name = Brain.load(folder / f"{slug}.json").name
    target = folder / f"{slug}-tudo.zip"
    own = archive is None
    archive = archive or zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED)
    _add(archive, f"{prefix}LEIA-ME.md", README.format(nome=name, slug=slug).encode("utf-8"))
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not path.name.endswith("-tudo.zip"):
            _add(archive, f"{prefix}{path.relative_to(folder).as_posix()}", path.read_bytes())
    if own:
        archive.close()
    return target


def build_all() -> Path:
    target = ROOT / "personagens-tudo.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in sorted(p for p in PERSONAGENS.iterdir() if p.is_dir()):
            build_one(folder.name, archive, prefix=f"personagens/{folder.name}/")
        for name in ("cerebro.pyz", "cerebro_android.py", "cerebro-skill.zip", "Cerebro.bat", "Cerebro.command",
                     "instalar_termux.sh"):
            path = ROOT / name
            if path.exists():
                _add(archive, f"programa/{name}", path.read_bytes())
        _add(archive, "LEIA-ME.md", (
            "# Tudo\n\n- personagens/<nome>/: cada personagem com LEIA-ME próprio (skill, ChatGPT, motor, ficha).\n"
            "- programa/: o motor em arquivo único (cerebro.pyz, cerebro_android.py) e a skill genérica.\n"
        ).encode("utf-8"))
    return target


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Junta tudo de um personagem, ou de todos, em um zip.")
    parser.add_argument("--personagem", help="slug da pasta em personagens/")
    parser.add_argument("--todos", action="store_true")
    args = parser.parse_args(argv)
    if args.personagem:
        target = build_one(args.personagem)
        print(f"Gerado {target} ({target.stat().st_size // 1024} KB)")
    if args.todos:
        target = build_all()
        print(f"Gerado {target} ({target.stat().st_size // 1024} KB)")
    if not args.personagem and not args.todos:
        parser.error("informe --personagem <slug> ou --todos")


if __name__ == "__main__":
    main()
