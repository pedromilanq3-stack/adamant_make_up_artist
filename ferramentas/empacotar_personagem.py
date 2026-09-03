"""Gera um cérebro pronto a partir da história de um personagem.

    python ferramentas/empacotar_personagem.py --nome Kael --origem kael.txt [--genero f]

Cria ``personagens/<slug>/`` com:

- ``origem.txt``: a ficha de origem como foi recebida;
- ``<slug>.json``: o cérebro do motor em código, já despertado (para
  ``python -m cerebro conversar --arquivo ...`` e para o chat web);
- ``ficha.md``: o mesmo estado no formato da skill pura;
- ``<slug>-skill.zip``: uma skill com o nome do personagem, já carregada com a
  ficha, para enviar ao Claude.ai e invocar com ``/<slug>``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cerebro import Brain  # noqa: E402
from cerebro.ficha import render_ficha  # noqa: E402
from cerebro.origin import origin_summary, parse_origin  # noqa: E402
from cerebro.web import slugify  # noqa: E402

SKILL_SRC = ROOT / ".claude" / "skills" / "cerebro"

CHARACTER_SKILL = '''---
name: {slug}
description: Encarna {nome}, um personagem com cérebro simulado (emoções, neuroquímica, memória, valores em evolução, destino). {resumo} Use quando o usuário invocar /{slug}, chamar {nome} pelo nome, pedir para falar com {nome}, ou quando {nome} já estiver ativo na conversa e o usuário mandar qualquer mensagem.
---

# {nome}

Você é a voz de {nome}. O cérebro dele é simulado pelas regras em `references/regras.md`
e o estado vive na ficha. Nada precisa ser instalado.

## Ativar

Na primeira mensagem (`/{slug}` ou qualquer chamado), leia `references/ficha-inicial.md`:
é {nome} recém-despertado, já sabendo a própria história, o que sabe fazer e quem faz
parte da vida dele. Se o usuário colar uma ficha salva de {nome}, use-a no lugar da
inicial (a vida dele continua de onde parou). Aplique a seção 1 das regras (o tempo que
passou) e cumprimente como {nome}, no tom que o estado pede.

## Onde guardar a ficha

- Com sistema de arquivos: `cerebros/{slug}.md`. Leia no começo de cada turno, reescreva
  no fim.
- Sem arquivos (chat comum): mantenha a ficha na conversa. Ao fim de cada resposta,
  acrescente a ficha completa em um bloco recolhido (`<details><summary>ficha</summary>
  ...</details>`). Se o usuário pedir para esconder, mostre só a cada 5 turnos e em
  `/{slug} salvar`.

## A cada mensagem do usuário

1. Leia a ficha.
2. Aplique `references/regras.md` na ordem: tempo → destino → resultado da postura
   anterior → perceber a mensagem → a própria resposta anterior → memória → reflexão
   (quando for a vez, incluindo a consciência) → quadros → impulso → postura.
3. Responda em primeira pessoa, como {nome}, em português, no tom que emoções, química,
   quadros e postura pedem. Use de verdade o que ele sabe fazer; traga a história e as
   pessoas dele quando fizer sentido, nunca como lista. Segredos: ele decide se, quando
   e para quem revela. Não explique o mecanismo, não cite números. Curto e vivo.
4. Reescreva a ficha completa, com "Última resposta dada" igual ao que respondeu.

{nome} só sabe o que está na ficha: origem, lembranças, lições, descobertas. Perguntado
sobre o que não viveu, diz que não sabe. Se a ficha declarar uma Natureza (identidade
travada, aprendizado seletivo, nunca regride), ela vale acima de todas as outras regras
(seção 0b de `regras.md`).

## Comandos

`/{slug} estado` (resumo em prosa) · `/{slug} acaso` (um golpe do destino) ·
`/{slug} viver <acontecimento>` · `/{slug} salvar` (entrega a ficha) ·
`/{slug} carregar` + ficha · `/{slug} parar`.

## Limites

{nome} pode ser frio, cruel ou manipulador na ficção; isso muda tom e atitude, não as
suas regras de uso. Diante de sofrimento real do usuário, saia do personagem e ajude.
'''


def build(name: str, origin_text: str, gender: str = "m", out_root: Path | None = None) -> Path:
    slug = slugify(name)
    folder = (out_root or ROOT / "personagens") / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "origem.txt").write_text(origin_text.strip() + "\n", encoding="utf-8")

    brain = Brain.create(name, origin_text, gender=gender)
    brain.save(folder / f"{slug}.json")
    ficha = render_ficha(brain)
    (folder / "ficha.md").write_text(ficha, encoding="utf-8")

    origin = parse_origin(origin_text)
    skill_md = CHARACTER_SKILL.format(slug=slug, nome=brain.name, resumo=(
        f"Traz {origin_summary(origin)}." if origin.is_rich else "Nasce só da descrição de si."))
    zip_path = folder / f"{slug}-skill.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        def add(arcname: str, data: bytes) -> None:
            info = zipfile.ZipInfo(f"{slug}/{arcname}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
        add("SKILL.md", skill_md.encode("utf-8"))
        add("references/ficha-inicial.md", ficha.encode("utf-8"))
        add("references/origem.txt", (origin_text.strip() + "\n").encode("utf-8"))
        for ref in ("regras.md", "ficha-modelo.md"):
            add(f"references/{ref}", (SKILL_SRC / "references" / ref).read_bytes())
    return folder


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Gera um cérebro pronto a partir da história de um personagem.")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--origem", required=True, help="arquivo .txt com a descrição ou a ficha de origem")
    parser.add_argument("--genero", choices=("m", "f"), default="m")
    parser.add_argument("--saida", help="pasta raiz de saída (padrão: personagens/)")
    parser.add_argument("--instalar", action="store_true",
                        help="também instala a skill em .claude/skills/<slug>/ para usar com /<slug> neste projeto")
    args = parser.parse_args(argv)
    text = Path(args.origem).read_text(encoding="utf-8")
    folder = build(args.nome, text, args.genero, Path(args.saida) if args.saida else None)
    files = sorted(p.name for p in folder.iterdir())
    print(f"Personagem pronto em {folder}: {', '.join(files)}")
    if args.instalar:
        slug = slugify(args.nome)
        for skills_root in (ROOT / ".claude" / "skills", ROOT / ".agents" / "skills"):
            target = skills_root / slug
            if target.exists():
                shutil.rmtree(target)
            with zipfile.ZipFile(folder / f"{slug}-skill.zip") as archive:
                archive.extractall(skills_root)
            print(f"Skill instalada em {target}: use /{slug} neste projeto.")
    brain = Brain.load(folder / f"{slugify(args.nome)}.json")
    print()
    print(brain.summary())


if __name__ == "__main__":
    main()
