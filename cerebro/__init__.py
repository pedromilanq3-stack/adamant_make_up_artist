"""Cérebro: um personagem com sentimentos, memória e caráter em evolução.

Uso rápido::

    from cerebro import Brain, Session

    brain = Brain.create("Lua", "Sou curiosa, tímida e gosto de ajudar quem sofre.")
    session = Session(brain)                  # sem modelo: modo espelho
    print(session.say("Oi, obrigado por existir!"))
    print(brain.implant())                    # o bloco que vai em toda conversa
"""

from .brain import Brain, STANCES, stage_for
from .experience import Experience
from .fate import ADVERSITIES, FORTUNES, Fate
from .perception import appraise
from .session import AnthropicResponder, MirrorResponder, Session, build_request

__all__ = [
    "Brain", "Experience", "Session", "MirrorResponder", "AnthropicResponder",
    "appraise", "build_request", "STANCES", "stage_for", "Fate", "ADVERSITIES", "FORTUNES",
]
