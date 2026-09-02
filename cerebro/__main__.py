"""Linha de comando: ``python -m cerebro``.

Sem argumentos, abre o chat local no navegador (o mesmo que ``web --abrir``).

    python -m cerebro criar --nome Lua --descricao "Sou curiosa e tímida..." --arquivo lua.json
    python -m cerebro estado --arquivo lua.json
    python -m cerebro prompt --arquivo lua.json
    python -m cerebro viver --arquivo lua.json --texto "Perdi meu melhor amigo" --valencia -0.8
    python -m cerebro acaso --arquivo lua.json                # deixa o destino agir uma vez
    python -m cerebro conversar --arquivo lua.json            # modo espelho, sem modelo
    python -m cerebro conversar --arquivo lua.json --modelo   # usa o SDK anthropic
    python -m cerebro web                                     # chat no navegador
    python -m cerebro registrar --arquivo lua.json --voce "..." --resposta "..."
"""

from __future__ import annotations

import argparse
import sys

from .brain import Brain
from .session import AnthropicResponder, Session


def _load(path: str) -> Brain:
    try:
        return Brain.load(path)
    except FileNotFoundError:
        sys.exit(f"Arquivo não encontrado: {path}. Crie o cérebro com `python -m cerebro criar`.")


def cmd_criar(args: argparse.Namespace) -> None:
    brain = Brain.create(args.nome, args.descricao, gender=args.genero)
    brain.save(args.arquivo)
    print(f"Cérebro criado em {args.arquivo}\n")
    print(brain.summary())


def cmd_estado(args: argparse.Namespace) -> None:
    brain = _load(args.arquivo)
    brain.tick()
    print(brain.summary())
    if args.json:
        print()
        print(brain.to_json())


def cmd_prompt(args: argparse.Namespace) -> None:
    brain = _load(args.arquivo)
    brain.tick()
    print(brain.implant(args.contexto or ""))


def cmd_viver(args: argparse.Namespace) -> None:
    brain = _load(args.arquivo)
    brain.tick()
    if args.valencia is None:
        experience = brain.perceive(args.texto)
    else:
        experience = brain.event(args.texto, args.valencia, args.intensidade)
    brain.save(args.arquivo)
    print(f"Experiência vivida: {experience.text} (valência {experience.valence:+.2f}, "
          f"intensidade {experience.intensity:.2f}, tags: {', '.join(experience.tags)})\n")
    print(brain.summary())


def cmd_acaso(args: argparse.Namespace) -> None:
    brain = _load(args.arquivo)
    brain.tick()
    experience = brain.fate.draw(brain.luck, brain.character.morality)
    brain.live(experience)
    brain.save(args.arquivo)
    kind = "adversidade" if "adversidade" in experience.tags else "acaso"
    print(f"O destino agiu ({kind}): {experience.text} (valência {experience.valence:+.2f}, "
          f"intensidade {experience.intensity:.2f})\n")
    print(brain.summary())


def cmd_registrar(args: argparse.Namespace) -> None:
    """Registra uma troca feita em outro chat e imprime o implante atualizado."""
    brain = _load(args.arquivo)
    session = Session(brain, save_path=args.arquivo)
    session.record_exchange(args.voce, args.resposta or "")
    print(session.implant(args.voce))


def cmd_web(args: argparse.Namespace) -> None:
    from pathlib import Path

    from .web import serve

    serve(port=args.porta, directory=Path(args.pasta) if args.pasta else None,
          model=args.modelo_id, force_mirror=args.espelho, open_browser=args.abrir)


def cmd_conversar(args: argparse.Namespace) -> None:
    brain = _load(args.arquivo)
    responder = AnthropicResponder(model=args.modelo_id) if args.modelo else None
    session = Session(brain, responder=responder, save_path=args.arquivo)
    modo = f"modelo {args.modelo_id}" if args.modelo else "modo espelho, sem modelo"
    print(f"Conversando com {brain.name} ({modo}). Digite /estado, /prompt ou /sair.\n")
    while True:
        try:
            text = input("você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text == "/sair":
            break
        if text == "/estado":
            print(brain.summary(), "\n")
            continue
        if text == "/prompt":
            print(session.implant(), "\n")
            continue
        reply = session.say(text)
        print(f"{brain.name}> {reply}\n")
    brain.save(args.arquivo)
    print(f"Cérebro salvo em {args.arquivo}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cerebro", description="Cérebro com sentimentos, memória e caráter em evolução.")
    sub = parser.add_subparsers(dest="comando")

    p = sub.add_parser("criar", help="cria um cérebro a partir da descrição de si")
    p.add_argument("--nome", required=True)
    p.add_argument("--descricao", required=True, help="como o cérebro se descreve (fica para sempre na conversa)")
    p.add_argument("--arquivo", required=True, help="arquivo JSON onde o cérebro vive")
    p.add_argument("--genero", choices=("m", "f"), default="m", help="flexão dos adjetivos (m ou f)")
    p.set_defaults(func=cmd_criar)

    p = sub.add_parser("estado", help="mostra o estado atual")
    p.add_argument("--arquivo", required=True)
    p.add_argument("--json", action="store_true", help="imprime também o JSON completo")
    p.set_defaults(func=cmd_estado)

    p = sub.add_parser("prompt", help="imprime o implante para colar em uma conversa")
    p.add_argument("--arquivo", required=True)
    p.add_argument("--contexto", help="texto da mensagem atual, para evocar lembranças relacionadas")
    p.set_defaults(func=cmd_prompt)

    p = sub.add_parser("viver", help="faz o cérebro viver uma mensagem ou evento")
    p.add_argument("--arquivo", required=True)
    p.add_argument("--texto", required=True)
    p.add_argument("--valencia", type=float, help="de -1 (péssimo) a 1 (ótimo); sem isso o texto é percebido como fala de alguém")
    p.add_argument("--intensidade", type=float, default=0.5)
    p.set_defaults(func=cmd_viver)

    p = sub.add_parser("acaso", help="deixa o destino agir uma vez (adversidade, sorte ou tentação)")
    p.add_argument("--arquivo", required=True)
    p.set_defaults(func=cmd_acaso)

    p = sub.add_parser("registrar", help="registra uma troca feita em outro chat e imprime o implante novo")
    p.add_argument("--arquivo", required=True)
    p.add_argument("--voce", required=True, help="o que você disse")
    p.add_argument("--resposta", help="o que o personagem respondeu no outro chat")
    p.set_defaults(func=cmd_registrar)

    p = sub.add_parser("web", help="chat local no navegador com o estado do cérebro ao lado")
    p.add_argument("--porta", type=int, default=8766)
    p.add_argument("--pasta", help="pasta dos cérebros (padrão: ~/.cerebro ou CEREBRO_DIR)")
    p.add_argument("--modelo-id", default="claude-opus-5")
    p.add_argument("--espelho", action="store_true", help="força o modo espelho mesmo com credencial")
    p.add_argument("--abrir", action="store_true", help="abre o navegador automaticamente")
    p.set_defaults(func=cmd_web)

    p = sub.add_parser("conversar", help="conversa interativa")
    p.add_argument("--arquivo", required=True)
    p.add_argument("--modelo", action="store_true", help="usa o SDK anthropic em vez do modo espelho")
    p.add_argument("--modelo-id", default="claude-opus-5")
    p.set_defaults(func=cmd_conversar)
    return parser


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["web", "--abrir"]
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
