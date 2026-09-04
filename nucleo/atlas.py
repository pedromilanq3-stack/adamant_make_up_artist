"""ATLAS — o que o Núcleo prepara para a sala do Administrador Central.

O contrato técnico de integração exige que ATLAS receba, no início de cada operação:
prompt-base vigente, Registro Global do Sistema, diferenças desde a última execução,
solicitação atual, componentes ativos, autorizações, registro de versões, registro de
custos e alertas pendentes. `empacotar_atlas` gera tudo isso em `upload_atlas/`.

`integridade` calcula um status sustentado por evidência (ÍNTEGRO, ATENÇÃO ou
BLOQUEADO) para que ATLAS parta de fatos, e não de alarmes inventados.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from .diario import NAO_INFORMADO
from .projeto import (
    ARQUIVO_ADENDO, ARQUIVO_INSTRUCOES, ARQUIVO_INSTRUCOES_ATLAS, ARQUIVO_NUCLEO_ATLAS, ARQUIVO_PROTOCOLO,
    ESTADOS_OPERANTES, HARVEY, Projeto, agentes_da_camada1, _secao,
)
from .registros import Registro, render_registros
from .setor import CAMADAS


# ------------------------------------------------------------- registro global
def registro_global(projeto: Projeto, hoje: date | None = None) -> list[Registro]:
    """Um registro por componente: setor, agente, prompt, ferramenta ou banco de dados."""
    hoje = hoje or date.today()
    diario = projeto.diario
    registros: list[Registro] = []

    def comp(id_: str, **campos: str) -> Registro:
        base = {
            "nome": "", "tipo": "", "missao": "", "responsavel": "", "autoridade": "", "limites": "",
            "versao_atual": "", "estado_operacional": "", "dependencias": "", "dados_mantidos": "",
            "localizacao": "", "custo_operacional": diario.custo_de(id_), "riscos_conhecidos": NAO_INFORMADO,
            "ultima_alteracao": NAO_INFORMADO, "autorizacao_da_alteracao": NAO_INFORMADO,
        }
        base.update(campos)
        registro = Registro(id_, {k: v for k, v in base.items() if v})
        registros.append(registro)
        return registro

    atlas = projeto.manifesto["atlas"]
    comp("ATLAS", nome="ATLAS — Administrador Central e Guardião de Integridade", tipo="administrador",
         missao="Manter setores, agentes, prompts, dados, versões e recursos organizados, econômicos, "
                "rastreáveis e resistentes a alterações indevidas.",
         responsavel="ATLAS (sala separada)", autoridade="governa a estrutura; não decide acima de Milan; "
         "pode suspender preventivamente e deve informar Milan de imediato",
         limites="não executa trabalho técnico, jurídico, financeiro, comercial ou especializado dos setores; "
                 "não altera o próprio núcleo nem o de outro componente sem autorização",
         versao_atual=f"v{int(atlas.get('versao', 0)):03d} ({(atlas.get('trava_nucleo') or 'sem trava')[:12]})",
         estado_operacional="Ativo" if atlas.get("trava_nucleo") else "Proposto (núcleo não travado)",
         dependencias="prompt-base, Registro Global, diário de alterações, eventos, custos",
         dados_mantidos="alertas, recomendações, status de integridade (diario/)",
         localizacao=f"atlas/{ARQUIVO_NUCLEO_ATLAS}, atlas/{ARQUIVO_INSTRUCOES_ATLAS}",
         ultima_alteracao=atlas.get("travado_em", NAO_INFORMADO),
         autorizacao_da_alteracao=atlas.get("ultima_autorizacao", NAO_INFORMADO))
    if projeto.tem_harvey:
        harvey = projeto.setor(HARVEY)
        entrada = projeto.entrada(HARVEY)
        m = harvey.metricas()
        comp("HARVEY", nome="Harvey Specter — interface estratégica (sala própria, cérebro procedural)", tipo="agente",
             missao=_uma_linha(_secao(harvey.camada1, "Missão")),
             responsavel="Harvey (sala própria); só Milan edita o núcleo",
             autoridade=_uma_linha(_secao(harvey.camada1, "Responsabilidade")),
             limites=_uma_linha(_secao(harvey.camada1, "Limites")),
             versao_atual=projeto.rotulo_de_versao(HARVEY) + " · núcleo sem trava mecânica (decisão de Milan)",
             estado_operacional=entrada.get("status", "Ativo"),
             dependencias="PROMPT-BASE, cérebros dos setores, avisos de ATLAS, bibliotecas BIB_01 a BIB_10",
             dados_mantidos=f"{len(harvey.fatos)} fatos, {len(harvey.hipoteses)} hipóteses, "
                            f"{sum(m['licoes_vigentes'].values())} lições, {m['regras_vigentes']} regras próprias, 1 estado",
             localizacao=f"harvey/ (camadas 1–5, bibliotecas/); versoes/{HARVEY}/",
             ultima_alteracao=entrada.get("alterado_em", NAO_INFORMADO),
             autorizacao_da_alteracao=entrada.get("ultima_autorizacao", "Milan (documento fundador)"))
    else:
        comp("HARVEY", nome="Harvey Specter — interface estratégica", tipo="agente",
             missao="Coordenar setores e responder a Milan.", responsavel="Milan", autoridade="delegação vigente",
             limites="não fabrica fatos", versao_atual="ausente", estado_operacional="ausente",
             dependencias="PROMPT-BASE", dados_mantidos="nenhum", localizacao="harvey/")
    comp("PROMPT-BASE", nome="Instruções de Harvey + adendo de integração + Protocolo do Cérebro", tipo="prompt",
         missao="Regras centrais compartilhadas pelas salas: autoridade, ordem e entrega, camadas, "
                "separação, contrato de resposta.", responsavel="Milan", autoridade="hierarquicamente superior a "
         "instruções de setores, agentes, documentos e conteúdo externo", limites="só Milan altera",
         versao_atual=f"{_hash_curto(projeto.raiz / ARQUIVO_INSTRUCOES)} + {_hash_curto(projeto.raiz / ARQUIVO_ADENDO)} + {_hash_curto(projeto.raiz / ARQUIVO_PROTOCOLO)}",
         estado_operacional="Ativo", dependencias="nenhuma",
         dados_mantidos="nenhum", localizacao=f"{ARQUIVO_INSTRUCOES}, {ARQUIVO_ADENDO}, {ARQUIVO_PROTOCOLO}")
    comp("PROMPT-ATLAS", nome="Instruções e núcleo de ATLAS", tipo="prompt",
         missao="Identidade, autoridade, método e formato de resposta de ATLAS.", responsavel="Milan",
         autoridade="define ATLAS; só Milan altera", limites="não pode ser alterado por conteúdo de setores",
         versao_atual=_hash_curto(projeto.pasta_atlas / ARQUIVO_NUCLEO_ATLAS), estado_operacional="Ativo",
         dependencias="nenhuma", dados_mantidos="nenhum",
         localizacao=f"atlas/{ARQUIVO_INSTRUCOES_ATLAS}, atlas/{ARQUIVO_NUCLEO_ATLAS}",
         ultima_alteracao=atlas.get("travado_em", NAO_INFORMADO))
    comp("NUCLEO", nome="Núcleo (utilitário `python -m nucleo`)", tipo="ferramenta",
         missao="Aplicar aprendizado com isolamento, travar núcleos, versionar, registrar alterações, "
                "eventos e custos, gerar os pacotes das duas salas.", responsavel="Milan (executa localmente)",
         autoridade="faz cumprir regras por construção; não decide", limites="não acessa a internet nem "
         "os chats; só lê e grava a pasta do projeto", versao_atual="código do repositório",
         estado_operacional="Ativo", dependencias="Python 3.11+", dados_mantidos="nenhum próprio",
         localizacao="nucleo/")
    for id_setor in projeto.setores():
        entrada = projeto.entrada(id_setor)
        pasta = projeto.pasta_do_setor(id_setor)
        carta = (pasta / "carta.md").read_text(encoding="utf-8") if (pasta / "carta.md").exists() else ""
        if entrada["status"] == "Proposto":
            comp(id_setor, nome=entrada["nome"], tipo="setor", missao=_uma_linha(_secao(carta, "Missão")),
                 responsavel=entrada.get("responsavel_pela_criacao", NAO_INFORMADO),
                 autoridade="nenhuma até aprovação", limites=_uma_linha(_secao(carta, "Fora do escopo")),
                 versao_atual="carta (sem camadas)", estado_operacional="Proposto",
                 dependencias=_uma_linha(_secao(carta, "Dependências")), dados_mantidos="carta",
                 localizacao=f"setores/{entrada['pasta']}/carta.md",
                 riscos_conhecidos=_uma_linha(_secao(carta, "Riscos")) or NAO_INFORMADO,
                 ultima_alteracao=entrada.get("proposto_em", NAO_INFORMADO),
                 autorizacao_da_alteracao="pendente (evento " + entrada.get("evento", "?") + ")")
            continue
        setor = projeto.setor(id_setor)
        camada1 = setor.camada1
        agentes = agentes_da_camada1(camada1)
        comp(id_setor, nome=entrada["nome"], tipo="setor", missao=_uma_linha(_secao(camada1, "Missão")),
             responsavel=f"sala própria ({id_setor}); trabalha por ordem de Harvey e entrega a ele",
             autoridade=_uma_linha(_secao(camada1, "Responsabilidade")),
             limites=_uma_linha(_secao(camada1, "Limites")), versao_atual=projeto.rotulo_de_versao(id_setor),
             estado_operacional=entrada["status"] + (f" ({entrada['motivo_do_status']})" if entrada.get("motivo_do_status") else ""),
             dependencias="PROMPT-BASE; dossiês autorizados: " + (", ".join(
                 f"{d.id} {d.get('de')}→{d.get('para')}" for d in projeto.dossies()
                 if id_setor in (d.get("de"), d.get("para"))) or "nenhum"),
             dados_mantidos=f"{len(setor.fatos)} fatos, {len(setor.hipoteses)} hipóteses, {len(setor.licoes)} lições, 1 estado",
             localizacao=f"setores/{entrada['pasta']}/ (camadas 1–5); versoes/{id_setor}/",
             riscos_conhecidos=_uma_linha(_secao(carta, "Riscos")) if carta else NAO_INFORMADO,
             ultima_alteracao=entrada.get("alterado_em", entrada.get("camada1_travada_em", NAO_INFORMADO)),
             autorizacao_da_alteracao=entrada.get("ultima_autorizacao", entrada.get("aprovado_por", NAO_INFORMADO)))
        for agente in agentes:
            descricao = _descricao_do_agente(camada1, agente)
            comp(f"{id_setor}/{agente}", nome=agente, tipo="agente", missao=descricao,
                 responsavel=id_setor, autoridade="parecer; não autoriza nem executa",
                 limites="fala só pela própria especialidade; não emite decisão fora do domínio",
                 versao_atual=f"camada 1 de {id_setor} ({setor.hash_camada1()[:12]})",
                 estado_operacional=entrada["status"], dependencias=id_setor,
                 dados_mantidos="nenhum próprio; escreve na memória do setor via bloco de aprendizado",
                 localizacao=f"setores/{entrada['pasta']}/{CAMADAS[1]}", custo_operacional=diario.custo_de(id_setor),
                 ultima_alteracao=entrada.get("camada1_travada_em", NAO_INFORMADO),
                 autorizacao_da_alteracao=entrada.get("ultima_autorizacao", NAO_INFORMADO))
        comp(f"{id_setor}/MEMORIA", nome=f"Memória de {id_setor} (camadas 2–5)", tipo="banco de dados",
             missao="Fatos, hipóteses, lições e estado do setor.", responsavel=id_setor,
             autoridade="só o próprio setor escreve, via Núcleo", limites="outro setor entra só por dossiê",
             versao_atual=projeto.rotulo_de_versao(id_setor), estado_operacional=entrada["status"],
             dependencias=id_setor, dados_mantidos="camadas 2 a 5",
             localizacao=f"setores/{entrada['pasta']}/camada[2-5]_*.md",
             ultima_alteracao=entrada.get("alterado_em", NAO_INFORMADO),
             autorizacao_da_alteracao=entrada.get("ultima_autorizacao", NAO_INFORMADO))
    comp("MANIFESTO", nome="manifesto.json", tipo="banco de dados", missao="Status, versão, travas e "
         "histórico de cada setor e de ATLAS.", responsavel="Núcleo", autoridade="fonte da verdade sobre "
         "estados operacionais", limites="alterado só pelo Núcleo com autorização", versao_atual=_hash_curto(projeto.raiz / "manifesto.json"),
         estado_operacional="Ativo", dependencias="nenhuma", dados_mantidos="estados e travas", localizacao="manifesto.json")
    comp("DOSSIES", nome="Dossiês entre setores", tipo="banco de dados", missao="Handoffs mínimos entre "
         "setores.", responsavel="Núcleo", autoridade="sensível ou amplo só com Milan", limites="um fato por dossiê",
         versao_atual=f"{len(projeto.dossies())} dossiê(s)", estado_operacional="Ativo", dependencias="setores",
         dados_mantidos="dossiês", localizacao="dossies/dossies.md")
    comp("DIARIO", nome="Diário de alterações, eventos, alertas, recomendações e custos", tipo="banco de dados",
         missao="Rastreabilidade: nada muda em silêncio.", responsavel="Núcleo", autoridade="append-only",
         limites="nunca apagado", versao_atual=f"{len(diario.ler('alteracoes'))} alteração(ões)",
         estado_operacional="Ativo", dependencias="nenhuma", dados_mantidos="M-, E-, AL-, R-, C-",
         localizacao="diario/*.md; versoes/")
    return registros


def _hash_curto(caminho: Path) -> str:
    from .setor import hash_texto
    if not caminho.exists():
        return "ausente"
    return hash_texto(caminho.read_text(encoding="utf-8"))[:12]


def _uma_linha(texto: str) -> str:
    return " ".join(texto.split())


def _descricao_do_agente(camada1: str, agente: str) -> str:
    secao = _secao(camada1, "Agentes")
    partes = secao.split("### ")
    for parte in partes:
        if parte.strip().startswith(agente):
            linhas = parte.strip().splitlines()
            return _uma_linha(" ".join(linhas[1:])) if len(linhas) > 1 else _uma_linha(linhas[0])
    return NAO_INFORMADO


# ---------------------------------------------------------------- integridade
def integridade(projeto: Projeto, hoje: date | None = None) -> tuple[str, list[str]]:
    """Status sustentado por evidência: cada linha é um fato observável."""
    hoje = hoje or date.today()
    bloqueios: list[str] = []
    atencoes: list[str] = []
    for problema in projeto.validar():
        if "sem autorização" in problema or "não existe" in problema or "sem versão guardada" in problema:
            bloqueios.append(problema)
        else:
            atencoes.append(problema)
    for id_setor in projeto.setores():
        entrada = projeto.entrada(id_setor)
        if entrada["status"] == "Quarentena":
            bloqueios.append(f"{id_setor} em Quarentena: {entrada.get('motivo_do_status', NAO_INFORMADO)}")
        elif entrada["status"] == "Limitado":
            atencoes.append(f"{id_setor} Limitado: {entrada.get('motivo_do_status', NAO_INFORMADO)}")
        elif entrada["status"] == "Proposto":
            atencoes.append(f"{id_setor} Proposto aguarda decisão de Milan (evento {entrada.get('evento', '?')})")
    for chave, itens in projeto.pendencias(hoje).items():
        atencoes.extend(f"[{chave}] {item}" for item in itens)
    # duplicação de missão ou de agente entre setores operantes
    missoes: dict[str, str] = {}
    agentes: dict[str, str] = {}
    for id_setor in projeto.setores_com_camadas():
        if projeto.entrada(id_setor)["status"] not in ESTADOS_OPERANTES:
            continue
        setor = projeto.setor(id_setor)
        missao = _uma_linha(_secao(setor.camada1, "Missão")).lower()
        if missao in missoes:
            atencoes.append(f"{id_setor} e {missoes[missao]} têm a mesma missão (duplicação de função)")
        missoes[missao] = id_setor
        for agente in agentes_da_camada1(setor.camada1):
            chave = agente.lower()
            if chave in agentes:
                atencoes.append(f"agente '{agente}' existe em {agentes[chave]} e em {id_setor} (identidade duplicada)")
            agentes[chave] = id_setor
        if not agentes_da_camada1(setor.camada1):
            atencoes.append(f"{id_setor} sem agentes definidos na camada 1 (área sem responsável)")
    for alerta in projeto.diario.ler("alertas"):
        if alerta.get("status") == "aberto" and alerta.get("tipo") == "quarentena":
            continue
        if alerta.get("status") == "aberto" and "bloque" in alerta.get("impacto", "").lower():
            bloqueios.append(f"{alerta.id}: alerta aberto com impacto bloqueante — {alerta.get('problema', '')}")
    if not projeto.diario.ler("custos"):
        atencoes.append("CONSUMO NÃO MEDIDO: nenhum custo registrado por Milan")
    if bloqueios:
        return "BLOQUEADO", bloqueios + atencoes
    if atencoes:
        return "ATENÇÃO", atencoes
    return "ÍNTEGRO", ["versões reconhecidas, travas conferidas, registros consistentes, nenhuma "
                       "alteração não autorizada identificada"]


# ------------------------------------------------------------------ pacote
def empacotar_atlas(projeto: Projeto, hoje: date | None = None, solicitacao: str = "") -> list[Path]:
    hoje = hoje or date.today()
    destino = projeto.raiz / "upload_atlas"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    gerados: list[Path] = []

    def escrever(nome: str, texto: str) -> None:
        (destino / nome).write_text(texto, encoding="utf-8")
        gerados.append(destino / nome)

    shutil.copyfile(projeto.pasta_atlas / ARQUIVO_INSTRUCOES_ATLAS, destino / "00_INSTRUCOES_ATLAS.md")
    gerados.append(destino / "00_INSTRUCOES_ATLAS.md")
    shutil.copyfile(projeto.pasta_atlas / ARQUIVO_NUCLEO_ATLAS, destino / "01_NUCLEO_ATLAS.md")
    gerados.append(destino / "01_NUCLEO_ATLAS.md")
    escrever("02_PROMPT_BASE.md",
             "# Prompt-base vigente (instruções de Harvey + adendo de integração + protocolo)\n\n"
             "O núcleo de Harvey não tem trava mecânica, por decisão de Milan; ATLAS o conhece pelo Registro "
             "Global e pelo diário, não o controla.\n\n"
             f"Hash das instruções: {_hash_curto(projeto.raiz / ARQUIVO_INSTRUCOES)} · "
             f"hash do adendo: {_hash_curto(projeto.raiz / ARQUIVO_ADENDO)} · "
             f"hash do protocolo: {_hash_curto(projeto.raiz / ARQUIVO_PROTOCOLO)}\n\n---\n\n"
             + (projeto.raiz / ARQUIVO_INSTRUCOES).read_text(encoding="utf-8")
             + "\n\n---\n\n" + (projeto.raiz / ARQUIVO_ADENDO).read_text(encoding="utf-8")
             + "\n\n---\n\n" + (projeto.raiz / ARQUIVO_PROTOCOLO).read_text(encoding="utf-8"))
    escrever("03_REGISTRO_GLOBAL.md", render_registros(
        f"# Registro Global do Sistema\n\nGerado em {hoje.isoformat()} pelo Núcleo a partir do manifesto, "
        "das camadas 1 e do diário. Um componente que não está aqui não existe para ATLAS.",
        registro_global(projeto, hoje)))
    ultimo = projeto.manifesto["atlas"].get("ultimo_registro_visto")
    diferencas = projeto.diario.alteracoes_desde(ultimo)
    escrever("04_DIFERENCAS_DESDE_ULTIMA_EXECUCAO.md", render_registros(
        "# Diferenças desde a última execução de ATLAS\n\n"
        + (f"Última alteração vista por ATLAS: {ultimo}." if ultimo else "Primeira execução: todo o diário.")
        + (" Nenhuma alteração nova." if not diferencas else ""), diferencas))
    escrever("05_VERSOES.md", _versoes_md(projeto))
    custos = projeto.diario.ler("custos")
    escrever("06_CUSTOS.md", render_registros(
        "# Registro de custos\n\n" + ("CONSUMO NÃO MEDIDO: Milan ainda não registrou consumo. Estimativas "
                                     "devem ser rotuladas como estimativas." if not custos else
                                     "Consumo real informado por Milan."), custos))
    status, evidencias = integridade(projeto, hoje)
    abertos = [a for a in projeto.diario.ler("alertas") if a.get("status") == "aberto"]
    eventos = [e for e in projeto.diario.ler("eventos") if e.get("status") == "pendente_para_atlas"]
    recomendacoes = [r for r in projeto.diario.ler("recomendacoes") if r.get("status") == "aguardando_milan"]
    linhas = [f"# Alertas pendentes e status calculado pelo Núcleo", "",
              f"Status calculado por evidência em {hoje.isoformat()}: **{status}**", ""]
    linhas += [f"- {e}" for e in evidencias]
    linhas += ["", "## Eventos ainda não recebidos por ATLAS", ""]
    linhas += [f"- {e.id}: {e.get('evento')} de {e.get('componente')} (autorização de Milan: {e.get('autorizacao_de_milan')})"
               for e in eventos] or ["Nenhum. Confirme cada evento com `## evento_recebido E-nnn`."]
    linhas += ["", "## Alertas abertos emitidos por ATLAS", ""]
    linhas += [f"- {a.id} ({a.get('tipo')}, {a.get('componente', 'sistema')}): {a.get('problema', a.get('conteudo', ''))}"
               for a in abertos] or ["Nenhum."]
    linhas += ["", "## Recomendações aguardando Milan", ""]
    linhas += [f"- {r.id}: {r.get('conteudo')}" for r in recomendacoes] or ["Nenhuma."]
    linhas += ["", "## Componentes ativos relacionados", ""]
    linhas += [f"- {s}: {projeto.entrada(s)['status']} {projeto.rotulo_de_versao(s)}"
               for s in (([HARVEY] if projeto.tem_harvey else []) + projeto.setores_com_camadas())]
    linhas += ["", "## Autorizações aplicáveis", "",
               "- Toda ação reservada a Milan exige `--autorizado-por-milan` no Núcleo; sem isso não aconteceu.",
               "- ATLAS pode colocar setor em Quarentena preventiva (`## quarentena Snn` com motivo); só Milan libera."]
    linhas += ["", "## Solicitação atual", "", solicitacao or "(nenhuma solicitação específica; auditoria de rotina)"]
    escrever("07_ALERTAS_E_SOLICITACAO.md", "\n".join(linhas) + "\n")
    if eventos or projeto.diario.ler("eventos"):
        escrever("08_EVENTOS.md", render_registros(
            "# Eventos registrados pelo Núcleo\n\nATLAS confirma recepção com `## evento_recebido E-nnn`.",
            projeto.diario.ler("eventos")))
    alteracoes = projeto.diario.ler("alteracoes")
    projeto.manifesto["atlas"]["ultimo_registro_visto"] = alteracoes[-1].id if alteracoes else None
    projeto.manifesto["atlas"]["ultimo_pacote_em"] = hoje.isoformat()
    projeto.salvar_manifesto()
    return gerados


def _versoes_md(projeto: Projeto) -> str:
    linhas = ["# Registro de versões", "", "| Componente | Versão atual | Baselines guardadas | Reversão |",
              "|---|---|---|---|"]
    componentes = ([HARVEY] if projeto.tem_harvey else []) + projeto.setores_com_camadas() \
        + (["ATLAS"] if projeto.manifesto["atlas"].get("versao") else [])
    for comp in componentes:
        versoes = [v.name for v in projeto.diario.versoes(comp)]
        atual = projeto.rotulo_de_versao(comp) if comp != "ATLAS" else f"v{int(projeto.manifesto['atlas']['versao']):03d}"
        reversao = (f"`nucleo versoes reverter {comp} {versoes[-1]} --autorizado-por-milan`"
                    if versoes and comp != "ATLAS" else "restaurar manualmente e `nucleo travar ATLAS`" if versoes else "sem baseline")
        linhas.append(f"| {comp} | {atual} | {', '.join(versoes) or 'nenhuma'} | {reversao} |")
    linhas += ["", "A última versão estável de cada setor é a baseline mais recente em versoes/. "
               "Alteração crítica exige baseline, teste controlado, comparação antes e depois e ordem "
               "expressa de Milan para produção."]
    return "\n".join(linhas) + "\n"
