"""Registros em markdown: um bloco `## ID` seguido de linhas `- chave: valor`.

O formato é o mesmo nos arquivos de memória, nos blocos de aprendizado que o GPT
emite e nos dossiês entre setores. Ele é legível por Milan, editável à mão e
interpretável pelo GPT quando o arquivo é enviado ao Projeto.

    ## F-001
    - conteudo: Milan perdeu o emprego recentemente.
    - fonte: Milan (documento fundador)
    - data: 2026-09-04
    - confianca: alta

Valores com mais de uma linha continuam em linhas indentadas com dois espaços.
Tudo o que vem antes do primeiro `## ` é preâmbulo e é preservado ao regravar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CABECALHO = re.compile(r"^##\s+(.+?)\s*$")
CAMPO = re.compile(r"^-\s+([a-z][a-z0-9_]*)\s*:\s*(.*)$")
CONTINUACAO = re.compile(r"^\s{2,}(.*)$")


class ErroDeFormato(ValueError):
    """O texto não segue o formato de registros."""


@dataclass
class Registro:
    id: str
    campos: dict[str, str] = field(default_factory=dict)

    def get(self, chave: str, padrao: str = "") -> str:
        return self.campos.get(chave, padrao)

    def set(self, chave: str, valor: str) -> None:
        self.campos[chave] = valor.strip()

    def to_markdown(self) -> str:
        linhas = [f"## {self.id}"]
        for chave, valor in self.campos.items():
            partes = (valor or "").split("\n")
            linhas.append(f"- {chave}: {partes[0]}")
            linhas.extend(f"  {parte}" for parte in partes[1:])
        return "\n".join(linhas) + "\n"


def parse_registros(texto: str) -> tuple[str, list[Registro]]:
    """Separa o preâmbulo dos registros. Levanta ErroDeFormato com a linha do problema."""
    preambulo: list[str] = []
    registros: list[Registro] = []
    atual: Registro | None = None
    ultima_chave: str | None = None
    for numero, linha in enumerate(texto.splitlines(), start=1):
        cabecalho = CABECALHO.match(linha)
        if cabecalho:
            atual = Registro(cabecalho.group(1))
            registros.append(atual)
            ultima_chave = None
            continue
        if atual is None:
            preambulo.append(linha)
            continue
        if not linha.strip():
            ultima_chave = None
            continue
        campo = CAMPO.match(linha)
        if campo:
            chave, valor = campo.group(1), campo.group(2).strip()
            if chave in atual.campos:
                raise ErroDeFormato(f"linha {numero}: campo repetido '{chave}' em {atual.id}")
            atual.campos[chave] = valor
            ultima_chave = chave
            continue
        continuacao = CONTINUACAO.match(linha)
        if continuacao and ultima_chave is not None:
            anterior = atual.campos[ultima_chave]
            atual.campos[ultima_chave] = (anterior + "\n" + continuacao.group(1).rstrip()).strip()
            continue
        raise ErroDeFormato(
            f"linha {numero}: esperado '- chave: valor' dentro de {atual.id}, encontrado: {linha!r}"
        )
    return "\n".join(preambulo).rstrip("\n"), registros


def render_registros(preambulo: str, registros: list[Registro]) -> str:
    partes = [preambulo.rstrip("\n")]
    for registro in registros:
        partes.append(registro.to_markdown().rstrip("\n"))
    return "\n\n".join(parte for parte in partes if parte) + "\n"


def proximo_id(prefixo: str, registros: list[Registro]) -> str:
    maior = 0
    padrao = re.compile(rf"^{re.escape(prefixo)}-(\d+)$")
    for registro in registros:
        encontrado = padrao.match(registro.id)
        if encontrado:
            maior = max(maior, int(encontrado.group(1)))
    return f"{prefixo}-{maior + 1:03d}"
