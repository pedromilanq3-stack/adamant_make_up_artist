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

    ## correcao
    - substitui: F-003
    - motivo: ...
    - conteudo: ...         (campos do registro novo, do mesmo tipo do substituído)

    ## supera F-002
    - motivo: ...

    ## resultado H-001
    - status: confirmada | refutada | abandonada
    - resultado: ...

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

TIPOS_SIMPLES = {"fato", "hipotese", "licao", "estado", "dossie", "correcao"}
TIPOS_COM_ALVO = {"supera", "resultado"}
CERCA = re.compile(r"^\s*```\s*(aprendizado)?\s*$")
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


def extrair_blocos(texto: str) -> list[str]:
    """Encontra todos os blocos ```aprendizado ... ``` dentro de uma resposta inteira."""
    blocos = re.findall(r"```aprendizado\s*\n(.*?)\n\s*```", texto, flags=re.DOTALL)
    return blocos or [texto]


def parse_bloco(texto: str) -> BlocoDeAprendizado:
    corpo = _sem_cerca(texto)
    try:
        preambulo, registros = parse_registros(corpo)
    except ErroDeFormato as erro:
        raise ErroDePatch(str(erro)) from erro
    cabecalho: dict[str, str] = {}
    for linha in preambulo.splitlines():
        if not linha.strip():
            continue
        encontrado = LINHA_CABECALHO.match(linha.strip())
        if not encontrado:
            raise ErroDePatch(f"cabeçalho inválido: {linha!r} (esperado 'chave: valor')")
        cabecalho[encontrado.group(1)] = encontrado.group(2).strip()
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
