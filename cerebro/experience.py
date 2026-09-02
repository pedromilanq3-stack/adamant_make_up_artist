"""Experiências: a unidade básica do que o cérebro vive.

Tudo o que acontece com o cérebro (uma mensagem recebida, uma atitude própria,
um evento do mundo) vira uma :class:`Experience`. Ela carrega valência (bom ou
ruim), intensidade e os impactos que provoca nas emoções e no caráter.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    """Limita ``value`` ao intervalo ``[low, high]``."""
    return max(low, min(high, value))


@dataclass(frozen=True)
class Experience:
    """Um acontecimento vivido pelo cérebro.

    ``valence`` vai de -1 (péssimo) a +1 (ótimo); ``intensity`` de 0 a 1.
    ``source`` indica a origem: ``"interlocutor"`` (quem conversa),
    ``"self"`` (uma atitude do próprio cérebro) ou ``"world"`` (evento externo).
    ``emotion_impact`` e ``character_impact`` são deltas aplicados às emoções
    (chaves de :data:`cerebro.emotions.EMOTIONS`) e ao caráter
    (chaves de :class:`cerebro.personality.Character`).
    """

    text: str
    valence: float = 0.0
    intensity: float = 0.5
    tags: tuple[str, ...] = ()
    source: str = "world"
    emotion_impact: dict[str, float] = field(default_factory=dict)
    character_impact: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "valence", clamp(float(self.valence)))
        object.__setattr__(self, "intensity", clamp(float(self.intensity), 0.0, 1.0))
        object.__setattr__(self, "tags", tuple(dict.fromkeys(self.tags)))
        object.__setattr__(self, "text", " ".join(str(self.text).split()))

    @property
    def weight(self) -> float:
        """Força efetiva da experiência: intensidade ponderada pela valência."""
        return self.intensity * (0.5 + 0.5 * abs(self.valence))

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "valence": self.valence,
            "intensity": self.intensity,
            "tags": list(self.tags),
            "source": self.source,
            "emotion_impact": dict(self.emotion_impact),
            "character_impact": dict(self.character_impact),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Experience":
        return cls(
            text=data.get("text", ""),
            valence=data.get("valence", 0.0),
            intensity=data.get("intensity", 0.5),
            tags=tuple(data.get("tags", ())),
            source=data.get("source", "world"),
            emotion_impact=dict(data.get("emotion_impact", {})),
            character_impact=dict(data.get("character_impact", {})),
        )
