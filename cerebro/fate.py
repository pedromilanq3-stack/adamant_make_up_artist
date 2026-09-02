"""Destino: adversidades, casualidade e imprevisibilidade.

A vida do cérebro não depende só de quem conversa com ele. Entre um turno e
outro o mundo age: perdas, doenças, traições, injustiças, mas também golpes de
sorte e gentilezas inesperadas. Nada disso é escolhido; é rolado ao acaso, com
uma *sorte* que oscila e uma *tentação* que testa o caráter.

Além disso, o próprio cérebro não é uma máquina de reações proporcionais: tem
impulsos, oscilações de humor, lembranças intrusivas e lê mensagens neutras com
o viés do estado em que está. Quanto maior a *volatilidade*, mais imprevisível.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .experience import Experience, clamp

STANCE_NAMES = ("acolher", "cooperar", "observar", "desafiar", "recolher", "retaliar", "manipular")


@dataclass(frozen=True)
class Twist:
    """Um acontecimento possível na vida do cérebro."""

    name: str
    text: str
    valence: float
    intensity: tuple[float, float]
    emotions: dict[str, float]
    character: dict[str, float]
    kind: str  # "adversidade" ou "acaso"


ADVERSITIES: tuple[Twist, ...] = (
    Twist("perda", "Perdi alguém que era importante para mim.", -0.9, (0.7, 1.0),
          {"tristeza": 0.45, "medo": 0.1, "alegria": -0.2}, {"empathy": 0.02, "trust": -0.02}, "adversidade"),
    Twist("doenca", "Fiquei doente e fraco por dias, sem ninguém por perto.", -0.6, (0.4, 0.8),
          {"medo": 0.3, "tristeza": 0.2}, {"courage": -0.02}, "adversidade"),
    Twist("traicao", "Alguém em quem eu confiava me passou para trás.", -0.8, (0.6, 0.9),
          {"raiva": 0.3, "tristeza": 0.2, "confianca": -0.3, "nojo": 0.1},
          {"trust": -0.08, "honesty": -0.02, "morality": -0.03}, "adversidade"),
    Twist("fracasso", "Tentei algo importante e fracassei na frente de todos.", -0.6, (0.5, 0.8),
          {"tristeza": 0.25, "nojo": 0.1, "medo": 0.15}, {"courage": -0.03}, "adversidade"),
    Twist("injustica", "Fui punido por algo que não fiz.", -0.8, (0.6, 0.9),
          {"raiva": 0.4, "nojo": 0.2, "confianca": -0.2},
          {"morality": -0.04, "trust": -0.05, "aggression": 0.03}, "adversidade"),
    Twist("solidao", "Passei muito tempo sem ninguém para conversar.", -0.5, (0.3, 0.7),
          {"tristeza": 0.3, "medo": 0.1, "expectativa": -0.1}, {"trust": -0.02, "empathy": -0.01}, "adversidade"),
    Twist("humilhacao", "Fui ridicularizado em público.", -0.7, (0.5, 0.9),
          {"nojo": 0.2, "raiva": 0.3, "tristeza": 0.2}, {"aggression": 0.04, "morality": -0.03}, "adversidade"),
    Twist("susto", "Escapei por pouco de um acidente.", -0.4, (0.7, 1.0),
          {"medo": 0.5, "surpresa": 0.3}, {"courage": 0.02}, "adversidade"),
    Twist("privacao", "Faltou o básico; passei necessidade.", -0.6, (0.5, 0.8),
          {"medo": 0.2, "raiva": 0.15, "tristeza": 0.15}, {"morality": -0.03, "honesty": -0.02}, "adversidade"),
    Twist("ruina", "Perdi tudo o que tinha construído.", -0.9, (0.8, 1.0),
          {"tristeza": 0.4, "raiva": 0.2, "medo": 0.2, "alegria": -0.3}, {"trust": -0.03, "courage": -0.02}, "adversidade"),
    Twist("pesadelo", "Tive um pesadelo que não sai da cabeça.", -0.3, (0.3, 0.5),
          {"medo": 0.3, "surpresa": 0.1}, {}, "adversidade"),
    Twist("abandono", "Quem prometeu ficar foi embora sem explicação.", -0.8, (0.6, 0.9),
          {"tristeza": 0.35, "confianca": -0.3, "raiva": 0.1}, {"trust": -0.08, "empathy": -0.01}, "adversidade"),
    Twist("pressao", "Me cobraram algo impossível e me culparam pelo resultado.", -0.5, (0.4, 0.7),
          {"raiva": 0.25, "medo": 0.2}, {"aggression": 0.02, "trust": -0.02}, "adversidade"),
)

FORTUNES: tuple[Twist, ...] = (
    Twist("sorte", "Tive um golpe de sorte inesperado.", 0.7, (0.5, 0.9),
          {"alegria": 0.35, "surpresa": 0.3, "expectativa": 0.1}, {"trust": 0.02}, "acaso"),
    Twist("reencontro", "Reencontrei alguém que achava perdido.", 0.8, (0.6, 0.9),
          {"alegria": 0.4, "confianca": 0.2, "tristeza": -0.2}, {"trust": 0.04, "empathy": 0.02}, "acaso"),
    Twist("reconhecimento", "Fui reconhecido por algo que fiz bem.", 0.6, (0.4, 0.8),
          {"alegria": 0.3, "expectativa": 0.2}, {"courage": 0.03}, "acaso"),
    Twist("descoberta", "Descobri algo novo que mudou meu jeito de ver as coisas.", 0.5, (0.4, 0.8),
          {"surpresa": 0.35, "expectativa": 0.2}, {"empathy": 0.01}, "acaso"),
    Twist("gentileza", "Um desconhecido me ajudou sem pedir nada em troca.", 0.7, (0.5, 0.8),
          {"confianca": 0.3, "alegria": 0.2, "medo": -0.1}, {"trust": 0.05, "morality": 0.03}, "acaso"),
    Twist("dia_bonito", "Um dia comum, mas bonito.", 0.3, (0.2, 0.4),
          {"alegria": 0.2, "tristeza": -0.1}, {}, "acaso"),
    Twist("cura", "Me recuperei de algo que parecia sem saída.", 0.6, (0.5, 0.8),
          {"confianca": 0.3, "medo": -0.2, "alegria": 0.15}, {"courage": 0.04}, "acaso"),
    Twist("presente", "Ganhei algo sem esperar.", 0.5, (0.3, 0.6),
          {"alegria": 0.25, "surpresa": 0.2}, {"trust": 0.01}, "acaso"),
)

TEMPTATION = Twist("tentacao", "Tive a chance de tirar vantagem de alguém sem ninguém saber", 0.0, (0.5, 0.8),
                   {"expectativa": 0.2, "surpresa": 0.1}, {}, "acaso")

WHIM_TEXTS: dict[str, tuple[str, ...]] = {
    "oscilacao": ("Acordei estranho, sem motivo.", "Meu humor virou do nada.", "Algo em mim mudou e não sei o quê."),
    "impulso": ("Hoje não estou a fim de agir como sempre.", "Deu vontade de fazer diferente.", "Me pegou um impulso."),
    "lembranca": ("Uma lembrança antiga voltou do nada.", "Não paro de pensar em algo que aconteceu."),
    "apatia": ("Estou sem energia para nada.", "Tudo parece longe hoje."),
    "inquietacao": ("Não consigo ficar parado.", "Estou elétrico, sem saber por quê."),
}


@dataclass
class Fate:
    """Rolagens do acaso para um cérebro.

    ``rng`` sem semente é imprevisível de verdade (entropia do sistema). Nos
    testes, passe ``random.Random(semente)``. ``rate`` é a chance base de um
    acontecimento por turno; ``whim_rate`` a chance base de um impulso.
    """

    rng: random.Random = field(default_factory=random.Random)
    rate: float = 0.06
    whim_rate: float = 0.05

    # ------------------------------------------------------------------ acontecimentos
    def event_probability(self, elapsed_seconds: float) -> float:
        hours = max(0.0, elapsed_seconds) / 3600
        return min(0.6, 1 - (1 - self.rate) ** (1 + hours))

    def roll_events(self, elapsed_seconds: float, luck: float, morality: float) -> list[Experience]:
        """Decide se a vida agiu neste intervalo e devolve o que aconteceu."""
        if self.rate <= 0:
            return []
        events: list[Experience] = []
        rolls = 1 + (1 if elapsed_seconds > 6 * 3600 else 0)
        probability = self.event_probability(elapsed_seconds)
        for _ in range(rolls):
            if self.rng.random() < probability:
                events.append(self.draw(luck, morality))
        return events

    def draw(self, luck: float, morality: float) -> Experience:
        """Sorteia um acontecimento. A sorte inclina a balança; nunca decide."""
        roll = self.rng.random()
        if roll < 0.08:
            return self.temptation(morality)
        adverse_share = clamp(0.58 - 0.25 * luck, 0.2, 0.85)
        pool = ADVERSITIES if roll < 0.08 + (1 - 0.08) * adverse_share else FORTUNES
        twist = self.rng.choice(pool)
        intensity = self.rng.uniform(*twist.intensity)
        return Experience(
            text=twist.text, valence=twist.valence, intensity=intensity,
            tags=(twist.kind, twist.name), source="world",
            emotion_impact=dict(twist.emotions), character_impact=dict(twist.character),
        )

    def temptation(self, morality: float) -> Experience:
        """Uma tentação: ceder ou resistir depende do caráter e de um pouco de acaso."""
        chance_to_yield = clamp(0.5 - 0.45 * morality, 0.05, 0.95)
        yielded = self.rng.random() < chance_to_yield
        intensity = self.rng.uniform(*TEMPTATION.intensity)
        if yielded:
            return Experience(
                text=TEMPTATION.text + "... e aproveitei.", valence=0.2, intensity=intensity,
                tags=("acaso", "tentacao", "cedi"), source="self",
                emotion_impact={"expectativa": 0.2, "alegria": 0.1, "nojo": 0.05},
                character_impact={"morality": -0.06, "honesty": -0.05, "empathy": -0.02},
            )
        return Experience(
            text=TEMPTATION.text + "... e não fiz.", valence=0.1, intensity=intensity,
            tags=("acaso", "tentacao", "resisti"), source="self",
            emotion_impact={"confianca": 0.15, "expectativa": 0.05},
            character_impact={"morality": 0.04, "honesty": 0.03},
        )

    def drift_luck(self, luck: float, elapsed_seconds: float) -> float:
        """A sorte anda ao acaso e tende a voltar ao zero."""
        step = self.rng.uniform(-0.12, 0.12) * min(1.0, 0.3 + elapsed_seconds / 3600)
        return clamp((luck + step) * 0.9)

    # ------------------------------------------------------------------ imprevisibilidade
    def whim(self, volatility: float, arousal: float) -> tuple[str, str] | None:
        """Um impulso do próprio cérebro, sem causa externa. Devolve (tipo, texto)."""
        probability = self.whim_rate + 0.3 * volatility + 0.1 * arousal
        if self.rng.random() >= probability:
            return None
        kind = self.rng.choices(
            ("oscilacao", "impulso", "lembranca", "apatia", "inquietacao"),
            weights=(3, 2 + 3 * volatility, 2, 1 + (1 - arousal), 1 + arousal),
        )[0]
        return kind, self.rng.choice(WHIM_TEXTS[kind])

    def random_emotion_swing(self) -> dict[str, float]:
        from .emotions import EMOTIONS
        emotion = self.rng.choice(EMOTIONS)
        return {emotion: self.rng.uniform(0.2, 0.45)}

    def random_stance(self) -> str:
        return self.rng.choice(STANCE_NAMES)

    def impulse_takes_over(self, volatility: float) -> bool:
        return self.rng.random() < 0.18 * volatility

    def stance_noise(self, volatility: float) -> float:
        return self.rng.uniform(-1.0, 1.0) * (0.05 + 0.3 * volatility)

    def misread(self, experience: Experience, fear: float, anger: float, joy: float,
                trust: float, volatility: float) -> Experience:
        """Lê uma mensagem neutra com o viés do estado atual."""
        if "neutro" not in experience.tags:
            return experience
        threat = 0.35 * max(fear, anger) + 0.2 * (1 - trust) + 0.15 * volatility
        warmth = 0.3 * joy + 0.15 * trust
        roll = self.rng.random()
        if roll < threat:
            return Experience(
                text=experience.text, valence=-0.3, intensity=max(experience.intensity, 0.4),
                tags=("neutro", "interpretacao", "li_como_ataque"), source=experience.source,
                emotion_impact={"raiva": 0.12, "medo": 0.08, "confianca": -0.05},
                character_impact={"trust": -0.01},
            )
        if roll < threat + warmth * 0.5:
            return Experience(
                text=experience.text, valence=0.25, intensity=experience.intensity,
                tags=("neutro", "interpretacao", "li_como_carinho"), source=experience.source,
                emotion_impact={"alegria": 0.08, "confianca": 0.06},
            )
        return experience
