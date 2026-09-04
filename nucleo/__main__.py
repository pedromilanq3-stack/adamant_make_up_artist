"""Linha de comando do Núcleo: `python -m nucleo <comando>`.

    validar                        confere camadas, travas, versões e dossiês
    estado [S01]                   estado atual e pendências
    aplicar [arquivo]              aplica blocos ```aprendizado``` e ```atlas``` (ou lê da entrada padrão)
    empacotar                      gera upload/ para a sala principal (Harvey e setores)
    atlas [--solicitacao "..."]    gera upload_atlas/ para a sala de ATLAS
    integridade                    status ÍNTEGRO / ATENÇÃO / BLOQUEADO calculado por evidência
    revisar                        o que precisa ser reverificado, revisado ou autorizado
    metricas                       contadores de evolução por setor
    diario [alteracoes|eventos|alertas|recomendacoes|custos]
    travar S01|ATLAS --autorizado-por-milan [--motivo "..."]
    versoes listar S01 | guardar S01 | reverter S01 v002 --autorizado-por-milan
    setor listar | propor | aprovar | piloto | ativar | limitar | liberar | pausar | reativar | encerrar
    setor quarentena S02 --por ATLAS --motivo "..."   (preventiva; só Milan libera)
    dossie listar | autorizar D-001 | recusar D-001
    recomendacao aceitar|recusar R-001 --autorizado-por-milan
    alerta fechar AL-001 --resolucao "..." --autorizado-por-milan
    custo registrar S01 12.5 creditos --descricao "..."

Todas as ações reservadas a Milan exigem --autorizado-por-milan.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .atlas import empacotar_atlas, integridade
from .patch import ErroDePatch, extrair_blocos, parse_bloco, parse_bloco_atlas
from .projeto import ErroDeAutorizacao, ErroDeIsolamento, Projeto
from .setor import ErroDeValidacao

RAIZ_PADRAO = Path(__file__).resolve().parent.parent / "gpt_projeto"
ERROS = (ErroDePatch, ErroDeValidacao, ErroDeIsolamento, ErroDeAutorizacao, ValueError,
         FileExistsError, FileNotFoundError)


def _raiz(args: argparse.Namespace) -> Path:
    return Path(args.pasta or os.environ.get("NUCLEO_DIR") or RAIZ_PADRAO)


def cmd_validar(args: argparse.Namespace) -> int:
    problemas = Projeto.abrir(_raiz(args)).validar()
    if problemas:
        print("Problemas encontrados:")
        for problema in problemas:
            print(f"  - {problema}")
        return 1
    print("Tudo certo: camadas, travas, versões e dossiês válidos.")
    return 0


def cmd_estado(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    ids = [args.setor] if args.setor else projeto.setores()
    for id_setor in ids:
        entrada = projeto.entrada(id_setor)
        print(f"{id_setor} — {entrada['nome']} [{entrada['status']}] {projeto.rotulo_de_versao(id_setor) if entrada['status'] != 'Proposto' else ''}")
        if entrada["status"] == "Proposto":
            print("  (proposto: só a carta existe)")
            continue
        if entrada.get("motivo_do_status"):
            print(f"  motivo do status: {entrada['motivo_do_status']}")
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
    for tipo, trecho in extrair_blocos(texto):
        try:
            if tipo == "atlas":
                bloco = parse_bloco_atlas(trecho)
                relato = projeto.aplicar_atlas(bloco)
                origem = "ATLAS"
            else:
                bloco = parse_bloco(trecho)
                relato = projeto.aplicar(bloco, autorizado_por_milan=args.autorizado_por_milan)
                origem = f"{bloco.setor} (emitido por {bloco.emitido_por})"
        except ERROS as erro:
            print(f"Bloco recusado: {erro}", file=sys.stderr)
            codigo = 1
            continue
        print(f"Aplicado: {origem}")
        for linha in relato:
            print(f"  - {linha}")
    if codigo == 0:
        print("Lembre-se: rode 'empacotar' (Harvey e setores) e 'atlas' (ATLAS) e reenvie os arquivos.")
    return codigo


def cmd_empacotar(args: argparse.Namespace) -> int:
    try:
        gerados = Projeto.abrir(_raiz(args)).empacotar()
    except ErroDeValidacao as erro:
        print(erro, file=sys.stderr)
        return 1
    print("Arquivos prontos para a sala de Harvey e para a sala de cada setor:")
    for caminho in gerados:
        print(f"  {caminho}")
    return 0


def cmd_atlas(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    gerados = empacotar_atlas(projeto, solicitacao=args.solicitacao or "")
    print("Arquivos prontos para a sala de ATLAS:")
    for caminho in gerados:
        print(f"  {caminho}")
    return 0


def cmd_integridade(args: argparse.Namespace) -> int:
    status, evidencias = integridade(Projeto.abrir(_raiz(args)))
    print(f"STATUS: {status}")
    for evidencia in evidencias:
        print(f"  - {evidencia}")
    return 0 if status != "BLOQUEADO" else 1


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


def cmd_diario(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    registros = projeto.diario.ler(args.nome)
    if not registros:
        print(f"Nenhum registro em {args.nome}.")
        return 0
    for registro in registros:
        resumo = registro.get("diferenca") or registro.get("problema") or registro.get("conteudo") \
            or registro.get("evento") or registro.get("descricao") or ""
        extra = f" [{registro.get('status')}]" if registro.get("status") else ""
        print(f"{registro.id}  {registro.get('data')}  {registro.get('componente', '')}{extra}  {resumo}")
    return 0


def cmd_travar(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        trava = projeto.travar(args.setor, args.autorizado_por_milan, motivo=args.motivo or "")
    except ERROS as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"Núcleo de {args.setor} travado: {trava[:12]}")
    return 0


def cmd_versoes(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        if args.acao == "listar":
            for comp in ([args.setor] if args.setor else projeto.setores_com_camadas()):
                versoes = [v.name for v in projeto.diario.versoes(comp)]
                print(f"{comp}  atual {projeto.rotulo_de_versao(comp)}  baselines: {', '.join(versoes) or 'nenhuma'}")
            return 0
        if not args.setor:
            print(f"uso: versoes {args.acao} S01 ...", file=sys.stderr)
            return 2
        if args.acao == "guardar":
            print(f"Baseline guardada em {projeto.guardar_versao(args.setor)}")
            return 0
        if not args.versao:
            print("uso: versoes reverter S01 v002 --autorizado-por-milan", file=sys.stderr)
            return 2
        registro = projeto.reverter(args.setor, args.versao, args.autorizado_por_milan, motivo=args.motivo or "")
        print(f"{args.setor} revertido para {args.versao}; alteração {registro.id} registrada. Rode 'validar'.")
        return 0
    except ERROS as erro:
        print(erro, file=sys.stderr)
        return 1


def cmd_setor(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        if args.acao == "listar":
            for id_setor in projeto.setores():
                entrada = projeto.entrada(id_setor)
                motivo = f"  ({entrada['motivo_do_status']})" if entrada.get("motivo_do_status") else ""
                print(f"{id_setor}  {entrada['status']:<10} {entrada['nome']}{motivo}")
            return 0
        if args.acao == "propor":
            if not args.carta or not args.setor:
                print("uso: setor propor S02 --carta carta.md", file=sys.stderr)
                return 2
            pasta = projeto.propor_setor(args.setor, Path(args.carta).read_text(encoding="utf-8"))
            evento = projeto.entrada(args.setor).get("evento")
            print(f"{args.setor} proposto em {pasta}. Evento {evento} (NOVO_SETOR) registrado para ATLAS. "
                  "Aguarda aprovação de Milan.")
            return 0
        if not args.setor:
            print(f"uso: setor {args.acao} S02 --autorizado-por-milan", file=sys.stderr)
            return 2
        status = projeto.transicionar(args.setor, args.acao, args.autorizado_por_milan,
                                      por=args.por or "Milan", motivo=args.motivo or "")
        print(f"{args.setor} agora está {status}.")
        if args.acao == "quarentena":
            print("Causa registrada no diário. Apresente-a a Milan imediatamente; só Milan libera (reativar).")
        return 0
    except ERROS as erro:
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
    except ERROS as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"{dossie.id} agora está {dossie.get('status')}.")
    return 0


def cmd_recomendacao(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        registro = projeto.decidir_recomendacao(args.recomendacao, args.acao, args.autorizado_por_milan)
    except ERROS as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"{registro.id} agora está {registro.get('status')}.")
    return 0


def cmd_alerta(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        registro = projeto.fechar_alerta(args.alerta, args.autorizado_por_milan, args.resolucao or "")
    except ERROS as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"{registro.id} fechado.")
    return 0


def cmd_custo(args: argparse.Namespace) -> int:
    projeto = Projeto.abrir(_raiz(args))
    try:
        registro = projeto.registrar_custo(args.componente, args.valor, args.unidade, args.descricao or "")
    except ERROS as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"{registro.id} registrado: {args.componente} {args.valor} {args.unidade}.")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nucleo", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pasta", help="pasta do projeto (padrão: gpt_projeto/ do repositório)")
    sub = parser.add_subparsers(dest="comando", required=True)

    def milan(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument("--autorizado-por-milan", action="store_true")
        return p

    sub.add_parser("validar").set_defaults(func=cmd_validar)
    p = sub.add_parser("estado"); p.add_argument("setor", nargs="?"); p.set_defaults(func=cmd_estado)
    p = milan(sub.add_parser("aplicar")); p.add_argument("arquivo", nargs="?"); p.set_defaults(func=cmd_aplicar)
    sub.add_parser("empacotar").set_defaults(func=cmd_empacotar)
    p = sub.add_parser("atlas"); p.add_argument("--solicitacao"); p.set_defaults(func=cmd_atlas)
    sub.add_parser("integridade").set_defaults(func=cmd_integridade)
    sub.add_parser("revisar").set_defaults(func=cmd_revisar)
    sub.add_parser("metricas").set_defaults(func=cmd_metricas)
    p = sub.add_parser("diario")
    p.add_argument("nome", nargs="?", default="alteracoes",
                   choices=["alteracoes", "eventos", "alertas", "recomendacoes", "custos"])
    p.set_defaults(func=cmd_diario)
    p = milan(sub.add_parser("travar")); p.add_argument("setor"); p.add_argument("--motivo"); p.set_defaults(func=cmd_travar)
    p = milan(sub.add_parser("versoes"))
    p.add_argument("acao", choices=["listar", "guardar", "reverter"])
    p.add_argument("setor", nargs="?"); p.add_argument("versao", nargs="?"); p.add_argument("--motivo")
    p.set_defaults(func=cmd_versoes)
    p = milan(sub.add_parser("setor"))
    p.add_argument("acao", choices=["listar", "propor", "aprovar", "piloto", "ativar", "limitar", "liberar",
                                    "quarentena", "pausar", "reativar", "encerrar"])
    p.add_argument("setor", nargs="?"); p.add_argument("--carta"); p.add_argument("--motivo")
    p.add_argument("--por", choices=["Milan", "ATLAS"])
    p.set_defaults(func=cmd_setor)
    p = milan(sub.add_parser("dossie"))
    p.add_argument("acao", choices=["listar", "autorizar", "recusar"]); p.add_argument("dossie", nargs="?")
    p.set_defaults(func=cmd_dossie)
    p = milan(sub.add_parser("recomendacao"))
    p.add_argument("acao", choices=["aceitar", "recusar"]); p.add_argument("recomendacao")
    p.set_defaults(func=cmd_recomendacao)
    p = milan(sub.add_parser("alerta"))
    p.add_argument("acao", choices=["fechar"]); p.add_argument("alerta"); p.add_argument("--resolucao")
    p.set_defaults(func=cmd_alerta)
    p = sub.add_parser("custo")
    p.add_argument("acao", choices=["registrar"]); p.add_argument("componente"); p.add_argument("valor")
    p.add_argument("unidade"); p.add_argument("--descricao")
    p.set_defaults(func=cmd_custo)
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
