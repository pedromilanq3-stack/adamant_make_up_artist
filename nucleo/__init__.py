"""Núcleo Central de Coordenação — o cérebro modular do Projeto de Decisão e Reconstrução.

O pacote não é um modelo de linguagem. Ele guarda, valida e faz evoluir a memória
de cada setor (as cinco camadas), aplica os blocos de aprendizado emitidos pelo GPT,
impede que um setor altere a memória de outro e gera o pacote de arquivos que Milan
envia ao Projeto no ChatGPT.
"""

from .patch import BlocoDeAprendizado, ErroDePatch, parse_bloco
from .projeto import ESTADOS_DE_SETOR, TRANSICOES, ErroDeAutorizacao, ErroDeIsolamento, Projeto
from .registros import ErroDeFormato, Registro, parse_registros, render_registros
from .setor import CAMADAS, ErroDeValidacao, Setor

__all__ = [
    "BlocoDeAprendizado",
    "CAMADAS",
    "ESTADOS_DE_SETOR",
    "ErroDeAutorizacao",
    "ErroDeFormato",
    "ErroDeIsolamento",
    "ErroDePatch",
    "ErroDeValidacao",
    "Projeto",
    "Registro",
    "Setor",
    "TRANSICOES",
    "parse_bloco",
    "parse_registros",
    "render_registros",
]
