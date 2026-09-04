"""Linha de comando do Núcleo: `python -m nucleo <comando>`.

    validar                        confere as cinco camadas, travas e dossiês
    estado [S01]                   mostra o estado atual e as pendências
    aplicar [arquivo]              aplica um bloco de aprendizado (ou lê da entrada padrão)
    empacotar                      gera gpt_projeto/upload/ para reenviar ao Projeto
    revisar                        lista o que precisa ser reverificado, revisado ou autorizado
    metricas                       contadores de evolução por setor
    travar S01 --autorizado-por-milan
    setor listar | propor | aprovar | piloto | ativar | pausar | reativar | encerrar
    dossie listar | autorizar D-001 | recusar D-001

Todas as ações reservadas a Milan exigem --autorizado-por-milan.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from .patch import ErroDePatch, extrair_blocos, parse_bloco
from .projeto import ErroDeAutorizacao, ErroDeIsolamento, Projeto
from .setor import ErroDeValidacao

RAIZ_PADRAO = Path(__file__).resolve().parent.parent / "gpt_projeto"


def _raiz(args: argparse.Namespace) -> Path:
    return Path(args.pasta or os.environ.get("NUCLEO_DIR") or RAIZ_PADRAO)


def cmd_validar(args: argparse.Namespace) -> int:
    problemas = Projeto.abrir(_raiz(args)).validar()
    if problemas:
        print("Problemas encontrados:")
        for problema in problemas:
            print(f"  - {problema}")
        return 1
    print("Tudo certo: camadas, travas e dossiês válidos.")
    return 0


def cmd_estado(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    ids = [args.setor] if args.setor else projeto.setores()
    for id_setor in ids:
        entrada = projeto.entrada(id_setor)
        print(f"{id_setor} — {entrada['nome']} [{entrada['status']}]")
        if entrada["status"] == "Proposto":
            print("  (proposto: só a carta existe)")
            continue
        estado = projeto.setor(id_setor).estado
        for chave in ("tarefa_ativa", "prazo", "proxima_acao", "bloqueios", "autorizacoes_pendentes",
                      "atualizado_em"):
            print(f"  {chave}: {estado.get(chave)}")
    pendencias = projeto.pendencias()
    if pendencias:
        print("\nPendências:")
        for chave, itens in pendencias.items():
            for item in itens:
                print(f"  [{chave}] {item}")
    return 0


def cmd_aplicar(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    texto = Path(args.arquivo).read_text(encoding="utf-8") if args.arquivo else sys.stdin.read()
    codigo = 0
    for trecho in extrair_blocos(texto):
        try:
            bloco = parse_bloco(trecho)
            relato = projeto.aplicar(bloco, autorizado_por_milan=args.autorizado_por_milan)
        except (ErroDePatch, ErroDeValidacao, ErroDeIsolamento, ErroDeAutorizacao) as erro:
            print(f"Bloco recusado: {erro}", file=sys.stderr)
            codigo = 1
            continue
        print(f"Aplicado em {bloco.setor} (emitido por {bloco.emitido_por}):")
        for linha in relato:
            print(f"  - {linha}")
    if codigo == 0:
        print("Lembre-se: rode 'empacotar' e reenvie os arquivos de upload/ ao Projeto.")
    return codigo


def cmd_empacotar(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        gerados = projeto.empacotar()
    except ErroDeValidacao as erro:
        print(erro, file=sys.stderr)
        return 1
    print("Arquivos prontos para enviar ao Projeto:")
    for caminho in gerados:
        print(f"  {caminho}")
    return 0


def cmd_revisar(args: argparse.Namespace) -> int:
    pendencias = Projeto.abrir(_raiz(args)).pendencias()
    if not pendencias:
        print("Nada a revisar hoje.")
        return 0
    for chave, itens in pendencias.items():
        print(chave)
        for item in itens:
            print(f"  - {item}")
    return 0


def cmd_metricas(args: argparse.Namespace) -> int:
    print(json.dumps(Projeto.abrir(_raiz(args)).metricas(), ensure_ascii=False, indent=2))
    return 0


def cmd_travar(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        trava = projeto.travar(args.setor, args.autorizado_por_milan)
    except (ErroDeAutorizacao, ErroDeValidacao) as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"Camada 1 de {args.setor} travada: {trava[:12]}")
    return 0


def cmd_setor(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        if args.acao == "listar":
            for id_setor in projeto.setores():
                entrada = projeto.entrada(id_setor)
                print(f"{id_setor}  {entrada['status']:<9}  {entrada['nome']}")
            return 0
        if args.acao == "propor":
            if not args.carta or not args.setor:
                print("uso: setor propor S02 --carta carta.md", file=sys.stderr)
                return 2
            pasta = projeto.propor_setor(args.setor, Path(args.carta).read_text(encoding="utf-8"))
            print(f"{args.setor} proposto em {pasta}. Aguarda aprovação de Milan.")
            return 0
        if not args.setor:
            print(f"uso: setor {args.acao} S02 --autorizado-por-milan", file=sys.stderr)
            return 2
        status = projeto.transicionar(args.setor, args.acao, args.autorizado_por_milan)
        print(f"{args.setor} agora está {status}.")
        return 0
    except (ErroDeAutorizacao, ErroDeValidacao, ValueError, FileExistsError) as erro:
        print(erro, file=sys.stderr)
        return 1


def cmd_dossie(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    if args.acao == "listar":
        dossies = projeto.dossies()
        if not dossies:
            print("Nenhum dossiê.")
        for dossie in dossies:
            print(f"{dossie.id}  {dossie.get('de')} → {dossie.get('para')}  [{dossie.get('status')}]  {dossie.get('fato')}")
        return 0
    if not args.dossie:
        print(f"uso: dossie {args.acao} D-001 --autorizado-por-milan", file=sys.stderr)
        return 2
    try:
        dossie = projeto.decidir_dossie(args.dossie, args.acao, args.autorizado_por_milan)
    except (ErroDeAutorizacao, ErroDeValidacao, ValueError) as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"{dossie.id} agora está {dossie.get('status')}.")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nucleo", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pasta", help="pasta do projeto (padrão: gpt_projeto/ do repositório)")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("validar").set_defaults(func=cmd_validar)
    p = sub.add_parser("estado")
    p.add_argument("setor", nargs="?")
    p.set_defaults(func=cmd_estado)
    p = sub.add_parser("aplicar")
    p.add_argument("arquivo", nargs="?")
    p.add_argument("--autorizado-por-milan", action="store_true")
    p.set_defaults(func=cmd_aplicar)
    sub.add_parser("empacotar").set_defaults(func=cmd_empacotar)
    sub.add_parser("revisar").set_defaults(func=cmd_revisar)
    sub.add_parser("metricas").set_defaults(func=cmd_metricas)
    p = sub.add_parser("travar")
    p.add_argument("setor")
    p.add_argument("--autorizado-por-milan", action="store_true")
    p.set_defaults(func=cmd_travar)
    p = sub.add_parser("setor")
    p.add_argument("acao", choices=["listar", "propor", "aprovar", "piloto", "ativar", "pausar",
                                    "reativar", "encerrar"])
    p.add_argument("setor", nargs="?")
    p.add_argument("--carta")
    p.add_argument("--autorizado-por-milan", action="store_true")
    p.set_defaults(func=cmd_setor)
    p = sub.add_parser("dossie")
    p.add_argument("acao", choices=["listar", "autorizar", "recusar"])
    p.add_argument("dossie", nargs="?")
    p.add_argument("--autorizado-por-milan", action="store_true")
    p.set_defaults(func=cmd_dossie)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as erro:
        print(erro, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
