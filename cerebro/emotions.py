"""Sistema emocional inspirado na roda de Plutchik.

Oito emoções básicas com níveis de 0 a 1, um humor de fundo (``mood``) que
muda devagar e uma energia que sobe com estímulos e cai com o tempo. Emoções
decaem exponencialmente para uma linha de base definida pela personalidade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .experience import clamp

EMOTIONS: tuple[str, ...] = (
    "alegria",
    "tristeza",
    "raiva",
    "medo",
    "confianca",
    "nojo",
    "surpresa",
    "expectativa",
)

EMOTION_LABELS: dict[str, str] = {
    "alegria": "alegria", "tristeza": "tristeza", "raiva": "raiva", "medo": "medo",
    "confianca": "confiança", "nojo": "nojo", "surpresa": "surpresa", "expectativa": "expectativa",
}

POSITIVE: frozenset[str] = frozenset({"alegria", "confianca", "expectativa"})
NEGATIVE: frozenset[str] = frozenset({"tristeza", "raiva", "medo", "nojo"})

# Meia-vida (segundos) de cada emoção até voltar à linha de base.
HALF_LIFE: dict[str, float] = {
    "alegria": 40 * 60,
    "tristeza": 90 * 60,
    "raiva": 30 * 60,
    "medo": 60 * 60,
    "confianca": 120 * 60,
    "nojo": 45 * 60,
    "surpresa": 5 * 60,
    "expectativa": 50 * 60,
}

ADJECTIVES: dict[str, tuple[str, str, str]] = {
    # (leve, moderado, intenso)
    "alegria": ("contente", "alegre", "eufórico"),
    "tristeza": ("melancólico", "triste", "devastado"),
    "raiva": ("irritado", "com raiva", "furioso"),
    "medo": ("apreensivo", "com medo", "aterrorizado"),
    "confianca": ("tranquilo", "confiante", "em paz"),
    "nojo": ("incomodado", "enojado", "repugnado"),
    "surpresa": ("curioso", "surpreso", "atônito"),
    "expectativa": ("interessado", "ansioso por algo", "vibrando de expectativa"),
}


def _adjective(emotion: str, level: float) -> str:
    light, medium, strong = ADJECTIVES[emotion]
    if level >= 0.75:
        return strong
    if level >= 0.45:
        return medium
    return light


@dataclass
class Emotions:
    levels: dict[str, float] = field(default_factory=lambda: {e: 0.1 for e in EMOTIONS})
    baseline: dict[str, float] = field(default_factory=lambda: {e: 0.1 for e in EMOTIONS})
    mood: float = 0.0
    energy: float = 0.6

    def __post_init__(self) -> None:
        for emotion in EMOTIONS:
            self.levels.setdefault(emotion, 0.1)
            self.baseline.setdefault(emotion, 0.1)

    # ------------------------------------------------------------------ dinâmica
    def apply(self, impact: dict[str, float], gain: float = 1.0) -> None:
        """Aplica um impacto emocional (deltas por emoção) ponderado por ``gain``."""
        for emotion, delta in impact.items():
            if emotion not in self.levels:
                continue
            self.levels[emotion] = clamp(self.levels[emotion] + delta * gain, 0.0, 1.0)
        # Emoções opostas se inibem: alegria x tristeza, confiança x nojo,
        # medo x raiva, surpresa x expectativa.
        for a, b in (("alegria", "tristeza"), ("confianca", "nojo"),
                     ("medo", "raiva"), ("surpresa", "expectativa")):
            overlap = min(self.levels[a], self.levels[b])
            if overlap > 0.5:
                shave = (overlap - 0.5) * 0.5
                self.levels[a] -= shave
                self.levels[b] -= shave
        valence = self.valence()
        self.mood = clamp(self.mood + 0.15 * gain * (valence - self.mood))
        self.energy = clamp(self.energy + 0.1 * gain, 0.0, 1.0)

    def decay(self, seconds: float) -> None:
        """Aproxima cada emoção da linha de base com decaimento exponencial."""
        if seconds <= 0:
            return
        for emotion in EMOTIONS:
            factor = 0.5 ** (seconds / HALF_LIFE[emotion])
            base = self.baseline[emotion]
            self.levels[emotion] = base + (self.levels[emotion] - base) * factor
        self.mood *= 0.5 ** (seconds / (6 * 3600))
        self.energy = 0.6 + (self.energy - 0.6) * 0.5 ** (seconds / (2 * 3600))

    # ------------------------------------------------------------------ leitura
    def valence(self) -> float:
        positive = sum(self.levels[e] for e in POSITIVE) / len(POSITIVE)
        negative = sum(self.levels[e] for e in NEGATIVE) / len(NEGATIVE)
        return clamp(positive - negative)

    def arousal(self) -> float:
        return clamp(sum(self.levels[e] for e in ("raiva", "medo", "surpresa", "expectativa")) / 4
                     + 0.3 * self.energy, 0.0, 1.0)

    def dominant(self, limit: int = 2, floor: float = 0.2) -> list[tuple[str, float]]:
        ranked = sorted(self.levels.items(), key=lambda item: item[1], reverse=True)
        return [(e, round(v, 3)) for e, v in ranked[:limit] if v >= floor]

    def describe(self) -> str:
        dominant = self.dominant()
        if not dominant:
            return "em um estado neutro, quase sem emoção aparente"
        first = _adjective(*dominant[0])
        if len(dominant) > 1 and dominant[1][1] >= 0.3:
            return f"{first}, com um fundo de {ADJECTIVES[dominant[1][0]][0]}"
        return first

    def mood_label(self) -> str:
        if self.mood > 0.35:
            return "humor bom"
        if self.mood > 0.1:
            return "humor levemente positivo"
        if self.mood < -0.35:
            return "humor pesado"
        if self.mood < -0.1:
            return "humor levemente negativo"
        return "humor estável"

    # ------------------------------------------------------------------ persistência
    def to_dict(self) -> dict:
        return {
            "levels": {e: round(v, 4) for e, v in self.levels.items()},
            "baseline": {e: round(v, 4) for e, v in self.baseline.items()},
            "mood": round(self.mood, 4),
            "energy": round(self.energy, 4),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Emotions":
        return cls(
            levels=dict(data.get("levels", {})),
            baseline=dict(data.get("baseline", {})),
            mood=float(data.get("mood", 0.0)),
            energy=float(data.get("energy", 0.6)),
        )


def baseline_from_traits(neuroticism: float, extraversion: float, agreeableness: float) -> dict[str, float]:
    """Linha de base emocional derivada da personalidade."""
    base = {e: 0.1 for e in EMOTIONS}
    base["medo"] = 0.05 + 0.25 * neuroticism
    base["tristeza"] = 0.05 + 0.2 * neuroticism
    base["alegria"] = 0.05 + 0.3 * extraversion
    base["expectativa"] = 0.1 + 0.2 * extraversion
    base["confianca"] = 0.05 + 0.3 * agreeableness
    base["raiva"] = 0.05 + 0.15 * (1 - agreeableness)
    return {e: round(math.fsum([v]), 4) for e, v in base.items()}
