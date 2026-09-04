"""Bloco de aprendizado: o que o GPT emite ao fim de uma resposta para o cérebro evoluir.

    ```aprendizado
    setor: S01
    emitido_por: RAIO-X
    data: 2026-09-04

    ## fato
    - conteudo: ...
    - fonte: ...
    - confianca: alta
    - volatil: nao

    ## hipotese
    - conteudo: ...
    - evidencia_favoravel: ...
    - evidencia_contraria: ...
    - teste: ...
    - revisao: 2026-09-11
    - abandono: ...

    ## licao
    - conteudo: ...
    - origem: correcao_milan

    ## regra
    - conteudo: ...            (regra operacional derivada do próprio conhecimento)
    - base: L-002; F-007       (padrão de evidências ou correção de Milan)
    - quando_aplicar: ...

    ## correcao
    - substitui: F-003
    - motivo: ...
    - conteudo: ...         (campos do registro novo, do mesmo tipo do substituído)

    ## supera F-002
    - motivo: ...

    ## resultado H-001
    - status: confirmada | refutada | abandonada
    - resultado: ...

    ## mente                      (só personagens com Camada 6, como BATMAN)
    - evento: exposicao_ao_caos   (catálogo em nucleo/mente.py)
    - intensidade: normal         (leve | normal | forte)
    - descricao: ...

    ## tempo
    - dias: 3

    ## estado
    - tarefa_ativa: ...
    - prazo: 2026-09-11
    - proxima_acao: ...
    - bloqueios: ...
    - autorizacoes_pendentes: nenhuma

    ## dossie
    - para: S02
    - fato: ...
    - fonte: ...
    - confianca: media
    - restricao: ...
    - pergunta: ...
    - sensivel: nao
    ```

Os ids (F-, H-, L-) são atribuídos pelo Núcleo ao aplicar; o GPT não os inventa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .registros import ErroDeFormato, Registro, parse_registros

TIPOS_SIMPLES = {"fato", "hipotese", "licao", "regra", "estado", "dossie", "correcao", "mente", "tempo"}
TIPOS_COM_ALVO = {"supera", "resultado"}
TIPOS_ATLAS_SIMPLES = {"status", "alerta", "auditoria", "recomendacao"}
TIPOS_ATLAS_COM_ALVO = {"quarentena", "evento_recebido"}
CERCA = re.compile(r"^\s*```\s*(aprendizado|atlas)?\s*$")
LINHA_CABECALHO = re.compile(r"^([a-z_]+)\s*:\s*(.*)$")


class ErroDePatch(ValueError):
    pass


@dataclass
class Secao:
    tipo: str
    alvo: str | None
    campos: dict[str, str] = field(default_factory=dict)


@dataclass
class BlocoDeAprendizado:
    setor: str
    emitido_por: str
    data: str
    secoes: list[Secao] = field(default_factory=list)


def _sem_cerca(texto: str) -> str:
    linhas = texto.splitlines()
    while linhas and not linhas[0].strip():
        linhas.pop(0)
    while linhas and not linhas[-1].strip():
        linhas.pop()
    if linhas and CERCA.match(linhas[0]):
        linhas.pop(0)
    if linhas and CERCA.match(linhas[-1]):
        linhas.pop()
    return "\n".join(linhas)


@dataclass
class BlocoDoAtlas:
    """O que ATLAS devolve à sala principal: status, alertas, recomendações, quarentenas.

        ```atlas
        emitido_por: ATLAS
        data: 2026-09-05

        ## status
        - status: ATENÇÃO
        - observado: ...
        - problema: ...
        - impacto: ...
        - recomendacao: ...
        - custo: baixo
        - autorizacao: ...
        - proximo_movimento: ...

        ## alerta
        - componente: S01
        - problema: ...
        - impacto: ...
        - recomendacao: ...
        - evidencia: ...

        ## recomendacao
        - conteudo: ...
        - impacto: alto | medio | baixo
        - urgencia: alta | media | baixa
        - confianca: alta | media | baixa
        - esforco: alto | medio | baixo
        - custo: baixo | medio | alto | nao_medido
        - risco: ...
        - reversibilidade: ...

        ## quarentena S02
        - motivo: ...

        ## evento_recebido E-001
        - parecer: recomenda ativação | ajustes | rejeição
        ```
    """
    emitido_por: str
    data: str
    secoes: list[Secao] = field(default_factory=list)


def extrair_blocos(texto: str) -> list[tuple[str, str]]:
    """Encontra os blocos ```aprendizado``` e ```atlas``` de uma resposta inteira.

    Retorna pares (tipo, corpo). Sem cerca, o texto inteiro é tratado como um bloco
    de aprendizado, ou como bloco atlas se o cabeçalho disser `emitido_por: ATLAS`.
    """
    blocos = re.findall(r"```(aprendizado|atlas)\s*\n(.*?)\n\s*```", texto, flags=re.DOTALL)
    if blocos:
        return [(tipo, corpo) for tipo, corpo in blocos]
    tipo = "atlas" if re.search(r"^emitido_por\s*:\s*ATLAS\s*$", texto, re.MULTILINE) else "aprendizado"
    return [(tipo, texto)]


def parse_bloco_atlas(texto: str) -> BlocoDoAtlas:
    corpo = _sem_cerca(texto)
    try:
        preambulo, registros = parse_registros(corpo)
    except ErroDeFormato as erro:
        raise ErroDePatch(str(erro)) from erro
    cabecalho = _cabecalho(preambulo)
    if cabecalho.get("emitido_por", "").upper() != "ATLAS":
        raise ErroDePatch("o bloco atlas precisa de 'emitido_por: ATLAS'")
    if not cabecalho.get("data"):
        raise ErroDePatch("o bloco atlas precisa da linha 'data:'")
    bloco = BlocoDoAtlas("ATLAS", cabecalho["data"])
    for registro in registros:
        partes = registro.id.split()
        tipo = partes[0].lower()
        if tipo in TIPOS_ATLAS_SIMPLES and len(partes) == 1:
            bloco.secoes.append(Secao(tipo, None, dict(registro.campos)))
        elif tipo in TIPOS_ATLAS_COM_ALVO and len(partes) == 2:
            bloco.secoes.append(Secao(tipo, partes[1], dict(registro.campos)))
        else:
            raise ErroDePatch(
                f"seção desconhecida no bloco atlas '## {registro.id}'. Use: "
                f"{sorted(TIPOS_ATLAS_SIMPLES)} ou {sorted(TIPOS_ATLAS_COM_ALVO)} com alvo"
            )
    if not bloco.secoes:
        raise ErroDePatch("o bloco atlas não tem nenhuma seção")
    return bloco


def _cabecalho(preambulo: str) -> dict[str, str]:
    cabecalho: dict[str, str] = {}
    for linha in preambulo.splitlines():
        if not linha.strip():
            continue
        encontrado = LINHA_CABECALHO.match(linha.strip())
        if not encontrado:
            raise ErroDePatch(f"cabeçalho inválido: {linha!r} (esperado 'chave: valor')")
        cabecalho[encontrado.group(1)] = encontrado.group(2).strip()
    return cabecalho


def parse_bloco(texto: str) -> BlocoDeAprendizado:
    corpo = _sem_cerca(texto)
    try:
        preambulo, registros = parse_registros(corpo)
    except ErroDeFormato as erro:
        raise ErroDePatch(str(erro)) from erro
    cabecalho = _cabecalho(preambulo)
    for chave in ("setor", "emitido_por", "data"):
        if not cabecalho.get(chave):
            raise ErroDePatch(f"o bloco precisa da linha '{chave}:' antes das seções")
    bloco = BlocoDeAprendizado(cabecalho["setor"], cabecalho["emitido_por"], cabecalho["data"])
    for registro in registros:
        bloco.secoes.append(_secao(registro))
    if not bloco.secoes:
        raise ErroDePatch("o bloco não tem nenhuma seção '## fato', '## hipotese', ...")
    return bloco


def _secao(registro: Registro) -> Secao:
    partes = registro.id.split()
    tipo = partes[0].lower()
    if tipo in TIPOS_SIMPLES:
        if len(partes) != 1:
            raise ErroDePatch(f"'## {tipo}' não leva alvo (recebido: {registro.id!r})")
        return Secao(tipo, None, dict(registro.campos))
    if tipo in TIPOS_COM_ALVO:
        if len(partes) != 2:
            raise ErroDePatch(f"'## {tipo}' precisa de um alvo, por exemplo '## {tipo} F-001'")
        return Secao(tipo, partes[1], dict(registro.campos))
    raise ErroDePatch(
        f"seção desconhecida '## {registro.id}'. Use: {sorted(TIPOS_SIMPLES | TIPOS_COM_ALVO)}"
    )
