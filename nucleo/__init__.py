"""Núcleo Central de Coordenação — o cérebro modular do Projeto de Decisão e Reconstrução.

O pacote não é um modelo de linguagem. Ele guarda, valida e faz evoluir a memória
de cada setor (as cinco camadas), aplica os blocos de aprendizado emitidos pelo GPT,
impede que um setor altere a memória de outro e gera o pacote de arquivos que Milan
envia ao Projeto no ChatGPT.
"""

from .atlas import integridade, registro_global
from .diario import Diario
from .patch import BlocoDeAprendizado, BlocoDoAtlas, ErroDePatch, parse_bloco, parse_bloco_atlas
from .projeto import ESTADOS_DE_SETOR, TRANSICOES, ErroDeAutorizacao, ErroDeIsolamento, Projeto
from .registros import ErroDeFormato, Registro, parse_registros, render_registros
from .setor import CAMADAS, ErroDeValidacao, Setor

__all__ = [
    "BlocoDeAprendizado",
    "BlocoDoAtlas",
    "Diario",
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
    "integridade",
    "parse_bloco_atlas",
    "registro_global",
    "parse_bloco",
    "parse_registros",
    "render_registros",
]
