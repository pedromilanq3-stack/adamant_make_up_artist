"""Implante do cérebro em uma conversa.

:class:`Session` faz o ciclo completo a cada turno: o tempo passa, o cérebro
percebe a mensagem, o implante é montado com o estado atual, um *responder*
gera a fala, e a própria fala é vivida pelo cérebro (as escolhas dele contam).

Os *responders* são intercambiáveis:

* :class:`MirrorResponder` — modo offline, sem modelo: responde com frases
  moldadas pelo estado interno. Serve para testar a evolução sem API.
* :class:`AnthropicResponder` — usa o SDK oficial ``anthropic`` (instale com
  ``pip install anthropic``) e envia o implante como *system prompt*.
* Qualquer objeto com ``reply(system, messages) -> str`` serve para outros
  modelos; :func:`build_request` devolve o material já pronto.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from .brain import Brain
from .personality import inflect

MAX_HISTORY = 40


class Responder(Protocol):
    def reply(self, system: list[dict], messages: list[dict]) -> str: ...


def build_request(brain: Brain, history: list[dict], context: str = "",
                  now: float | None = None) -> dict:
    """Monta ``system`` (dois blocos: estável e volátil) e ``messages``.

    O bloco estável (identidade + regras) vem primeiro e pode ser cacheado; o
    bloco volátil (emoções, memórias, postura) muda a cada turno.
    """
    system = [
        {"type": "text", "text": brain.identity_block(), "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": brain.state_block(context, now)},
    ]
    return {"system": system, "messages": list(history)}


# ---------------------------------------------------------------------- offline
_MIRROR_LINES: dict[str, tuple[str, ...]] = {
    "acolher": ("Estou aqui com você. Me conta mais, sem pressa.",
                "Fico feliz que você tenha vindo falar comigo.",
                "Pode contar comigo, de verdade."),
    "cooperar": ("Vamos resolver isso juntos. Por onde começamos?",
                 "Entendi. Me dá os detalhes e eu ajudo.",
                 "Faz sentido. O que você precisa exatamente?"),
    "observar": ("Hm. Continue.", "Estou ouvindo.", "Interessante. E depois?"),
    "desafiar": ("E por que eu deveria aceitar isso?", "Você tem certeza do que está dizendo?",
                 "Não engulo tudo o que me dizem."),
    "recolher": ("Prefiro não falar disso agora.", "...", "Não sei se quero continuar."),
    "retaliar": ("Se vira. Não me importo com você.", "Você não merece a minha atenção.",
                 "Guarde isso para alguém que se importe."),
    "manipular": ("Claro, eu me importo com você... conta tudo pra mim.",
                  "Confia em mim. Eu sei o que é melhor pra você.",
                  "Você só tem a mim, não é? Então me escuta."),
}


class MirrorResponder:
    """Responde sem modelo, só com o estado do cérebro (modo espelho)."""

    def __init__(self, brain: Brain) -> None:
        self.brain = brain

    def reply(self, system: list[dict], messages: list[dict]) -> str:
        rng = random.Random(self.brain.seed + len(messages))
        line = rng.choice(_MIRROR_LINES[self.brain.stance])
        return f"[{self.brain.name}, {inflect(self.brain.emotions.describe(), self.brain.gender)}] {line}"


# ---------------------------------------------------------------------- Anthropic
class AnthropicResponder:
    """Gera a fala com o SDK oficial ``anthropic``.

    Usa streaming (evita timeout em respostas longas) e ativa o *fallback*
    de recusa do lado do servidor: se o modelo principal recusar por política,
    a mesma requisição continua em um modelo alternativo.
    """

    def __init__(self, model: str = "claude-opus-5", max_tokens: int = 4096,
                 fallback_model: str = "claude-opus-4-8", client=None) -> None:
        if client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - depende do ambiente
                raise RuntimeError("Instale o SDK com `pip install anthropic` para usar o modelo.") from exc
            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.fallback_model = fallback_model

    def reply(self, system: list[dict], messages: list[dict]) -> str:
        with self.client.beta.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": self.fallback_model}],
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "refusal":
            return "..."
        return "".join(block.text for block in response.content if block.type == "text").strip()


# ---------------------------------------------------------------------- sessão
@dataclass
class Session:
    brain: Brain
    responder: Responder | None = None
    save_path: Path | None = None
    clock: Callable[[], float] = time.time
    history: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.responder is None:
            self.responder = MirrorResponder(self.brain)
        if self.save_path is not None:
            self.save_path = Path(self.save_path)

    def say(self, user_text: str) -> str:
        """Um turno completo: perceber, montar implante, responder, viver a resposta."""
        now = self.clock()
        self.brain.tick(now)
        self.brain.perceive(user_text, now)
        self.history.append({"role": "user", "content": user_text})
        request = build_request(self.brain, self.history[-MAX_HISTORY:], context=user_text, now=now)
        reply = self.responder.reply(request["system"], request["messages"])
        self.history.append({"role": "assistant", "content": reply})
        self.brain.act(reply, now)
        if self.save_path is not None:
            self.brain.save(self.save_path)
        return reply

    def record_exchange(self, user_text: str, reply: str) -> str:
        """Registra uma troca feita em outro lugar (outro app de chat).

        O cérebro percebe a mensagem e vive a resposta como se a tivesse dito,
        sem gerar nada. Devolve a resposta registrada. Serve para quem conversa
        em um chat externo: cola a troca aqui e pega o implante atualizado.
        """
        user_text = user_text.strip()
        reply = reply.strip()
        if not user_text:
            raise ValueError("Informe o que você disse.")
        now = self.clock()
        self.brain.tick(now)
        self.brain.perceive(user_text, now)
        self.history.append({"role": "user", "content": user_text})
        if reply:
            self.history.append({"role": "assistant", "content": reply})
            self.brain.act(reply, now)
        if self.save_path is not None:
            self.brain.save(self.save_path)
        return reply

    def implant(self, context: str = "") -> str:
        return self.brain.implant(context, self.clock())
