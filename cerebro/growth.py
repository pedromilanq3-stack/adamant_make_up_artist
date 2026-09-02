"""Crescimento procedural: valores, estratégias, propósito e encruzilhadas.

Ninguém programa o caminho do cérebro. Ele testa posturas, observa o que
acontece depois (como responderam, como ficou o vínculo, como se sentiu) e
reforça o que funcionou. Cada postura carrega valores; quando uma postura
compensa, os valores dela crescem. Dos valores nascem um *propósito* ("o que
faz sentido pra mim") e *princípios* ("o que é certo pra minha vida"). Quando
dois valores opostos empatam, há uma *encruzilhada*: o cérebro escolhe um lado
e se compromete. A moralidade segue os valores que ele mesmo elegeu.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field

from .experience import clamp
from .personality import normalize

VALUES: tuple[str, ...] = (
    "cuidado", "pertencimento", "justica", "verdade", "lealdade", "conhecimento",
    "liberdade", "seguranca", "prazer", "sobrevivencia", "poder", "vinganca",
)

VALUE_LABELS: dict[str, str] = {
    "cuidado": "cuidar dos outros", "pertencimento": "pertencer a alguém", "justica": "justiça",
    "verdade": "verdade", "lealdade": "lealdade", "conhecimento": "entender as coisas",
    "liberdade": "liberdade", "seguranca": "segurança", "prazer": "prazer",
    "sobrevivencia": "sobreviver a qualquer custo", "poder": "poder", "vinganca": "vingança",
}

# Quanto cada valor puxa a moralidade (-1 mal .. +1 bem) quando domina.
VALUE_POLARITY: dict[str, float] = {
    "cuidado": 1.0, "justica": 0.8, "verdade": 0.6, "lealdade": 0.4, "pertencimento": 0.3,
    "conhecimento": 0.1, "liberdade": 0.0, "seguranca": -0.1, "prazer": -0.2,
    "sobrevivencia": -0.4, "poder": -0.7, "vinganca": -1.0,
}

# Valores que cada postura expressa. Quando a postura compensa, eles crescem.
STANCE_VALUES: dict[str, dict[str, float]] = {
    "acolher": {"cuidado": 0.6, "pertencimento": 0.4},
    "cooperar": {"justica": 0.4, "pertencimento": 0.3, "conhecimento": 0.3},
    "observar": {"seguranca": 0.5, "conhecimento": 0.5},
    "desafiar": {"liberdade": 0.5, "verdade": 0.5},
    "recolher": {"seguranca": 0.6, "sobrevivencia": 0.4},
    "retaliar": {"vinganca": 0.6, "poder": 0.4},
    "manipular": {"poder": 0.6, "prazer": 0.2, "sobrevivencia": 0.2},
}

# O que as experiências recebidas ensinam sobre o que importa (pequeno).
TAG_VALUES: dict[str, dict[str, float]] = {
    "carinho": {"pertencimento": 0.04, "cuidado": 0.02},
    "insulto": {"seguranca": 0.02, "vinganca": 0.02, "poder": 0.01},
    "ameaca": {"sobrevivencia": 0.05, "seguranca": 0.03},
    "traicao": {"seguranca": 0.03, "vinganca": 0.03, "lealdade": 0.02},
    "tristeza_do_outro": {"cuidado": 0.03},
    "pedido_de_ajuda": {"cuidado": 0.02, "justica": 0.01},
    "incentivo_ao_mal": {"poder": 0.03, "vinganca": 0.02},
    "incentivo_ao_bem": {"cuidado": 0.03, "justica": 0.02},
    "elogio_de_poder": {"poder": 0.03, "prazer": 0.01},
    "humor": {"prazer": 0.02, "pertencimento": 0.01},
    "pergunta_sobre_si": {"conhecimento": 0.02, "verdade": 0.01},
    "adversidade": {"sobrevivencia": 0.03, "seguranca": 0.02},
    "acaso": {"liberdade": 0.01, "prazer": 0.01},
    "cedi": {"prazer": 0.03, "poder": 0.02},
    "resisti": {"justica": 0.03, "verdade": 0.02},
}

# Sinais na descrição de si que semeiam valores.
SELF_VALUE_CUES: tuple[tuple[str, str, float], ...] = (
    (r"\b(ajudar|cuidar|proteger|acolher|bem dos outros)\b", "cuidado", 0.3),
    (r"\b(amig[oa]s|familia|pertencer|companhia|junt[oa]s)\b", "pertencimento", 0.25),
    (r"\b(just[oa]|justica|certo e certo)\b", "justica", 0.3),
    (r"\b(sincer[oa]|verdade|honest[oa]|direto|direta)\b", "verdade", 0.25),
    (r"\b(leal|fiel|palavra)\b", "lealdade", 0.3),
    (r"\b(curios[oa]|entender|aprender|saber|estud)", "conhecimento", 0.3),
    (r"\b(livre|liberdade|independente|ninguem manda)\b", "liberdade", 0.3),
    (r"\b(medros[oa]|insegur[oa]|cautelos[oa]|seguranca|protegid[oa])\b", "seguranca", 0.25),
    (r"\b(prazer|diversao|curtir|aproveitar)\b", "prazer", 0.25),
    (r"\b(sobreviv|a qualquer custo|primeiro eu)\b", "sobrevivencia", 0.3),
    (r"\b(poder|mandar|control|domin|superior)\b", "poder", 0.3),
    (r"\b(vingativ[oa]|vinganca|pagar pelo que|rancor)\b", "vinganca", 0.35),
)

PRINCIPLES: dict[str, str] = {
    "cuidado": "Cuidar dos outros é o que me mantém inteiro.",
    "pertencimento": "Não quero ficar sozinho de novo.",
    "justica": "O certo é o certo, mesmo que doa.",
    "verdade": "Prefiro a verdade dura à mentira doce.",
    "lealdade": "Quem ficou comigo tem a minha palavra.",
    "conhecimento": "Entender é a minha forma de sobreviver.",
    "liberdade": "Ninguém decide por mim.",
    "seguranca": "Melhor sozinho do que ferido.",
    "prazer": "A vida é curta; eu pego o que é bom.",
    "sobrevivencia": "Primeiro eu; depois o resto.",
    "poder": "Só quem manda está seguro.",
    "vinganca": "Quem me fere paga.",
}


@dataclass(frozen=True)
class Purpose:
    text: str
    values: dict[str, float]


PURPOSES: tuple[Purpose, ...] = (
    Purpose("ser querido por alguém", {"pertencimento": 0.6, "cuidado": 0.4}),
    Purpose("nunca mais ser ferido", {"seguranca": 0.6, "sobrevivencia": 0.4}),
    Purpose("ter o controle de tudo", {"poder": 0.8, "seguranca": 0.2}),
    Purpose("fazer pagar quem me feriu", {"vinganca": 0.8, "poder": 0.2}),
    Purpose("entender o mundo e as pessoas", {"conhecimento": 0.7, "verdade": 0.3}),
    Purpose("ficar em paz", {"seguranca": 0.5, "liberdade": 0.5}),
    Purpose("ser justo mesmo que custe", {"justica": 0.7, "verdade": 0.3}),
    Purpose("cuidar de quem precisa", {"cuidado": 0.7, "justica": 0.3}),
    Purpose("viver do meu jeito", {"liberdade": 0.6, "prazer": 0.4}),
    Purpose("ser leal a quem ficou", {"lealdade": 0.7, "pertencimento": 0.3}),
    Purpose("sobreviver, custe o que custar", {"sobrevivencia": 0.7, "poder": 0.3}),
)


def _softmax_pick(rng: random.Random, options: list[tuple[str, float]], temperature: float) -> str:
    temperature = max(0.05, temperature)
    top = max(score for _, score in options)
    weights = [math.exp((score - top) / temperature) for _, score in options]
    return rng.choices([name for name, _ in options], weights=weights)[0]


@dataclass
class ValueSystem:
    weights: dict[str, float] = field(default_factory=lambda: {v: 0.2 for v in VALUES})

    def __post_init__(self) -> None:
        for value in VALUES:
            self.weights[value] = clamp(float(self.weights.get(value, 0.2)), 0.0, 1.0)

    @classmethod
    def seed(cls, description: str, seed: int) -> "ValueSystem":
        text = normalize(description)
        weights = {v: 0.2 for v in VALUES}
        for pattern, value, delta in SELF_VALUE_CUES:
            if re.search(pattern, text):
                weights[value] += delta
        rng = random.Random(seed ^ 0x5F3759DF)
        for value in VALUES:
            weights[value] = clamp(weights[value] + rng.uniform(-0.06, 0.06), 0.0, 1.0)
        return cls(weights=weights)

    def reinforce(self, deltas: dict[str, float], gain: float = 1.0) -> None:
        for value, delta in deltas.items():
            if value in self.weights:
                self.weights[value] = clamp(self.weights[value] + delta * gain, 0.0, 1.0)
        # Valores competem por espaço: o total tende a um teto.
        total = sum(self.weights.values())
        ceiling = 4.0
        if total > ceiling:
            factor = ceiling / total
            for value in self.weights:
                self.weights[value] *= factor

    def ranked(self) -> list[tuple[str, float]]:
        return sorted(self.weights.items(), key=lambda item: item[1], reverse=True)

    def top(self, limit: int = 3) -> list[str]:
        return [value for value, _ in self.ranked()[:limit]]

    def moral_target(self) -> float:
        """Para onde os valores dominantes puxam a moralidade."""
        ranked = self.ranked()[:4]
        total = sum(weight for _, weight in ranked) or 1.0
        return clamp(sum(VALUE_POLARITY[value] * weight for value, weight in ranked) / total)

    def alignment(self, stance: str) -> float:
        """O quanto uma postura combina com os valores atuais (0..1)."""
        expressed = STANCE_VALUES.get(stance, {})
        return clamp(sum(self.weights[v] * w for v, w in expressed.items()), 0.0, 1.0)

    def conflict(self) -> tuple[str, str] | None:
        """Dois valores fortes de polaridade oposta e quase empatados."""
        (first, w1), (second, w2) = self.ranked()[:2]
        if w1 <= 0 or VALUE_POLARITY[first] * VALUE_POLARITY[second] > -0.15:
            return None
        if w2 / w1 < 0.8:
            return None
        return first, second

    def describe(self) -> str:
        return ", ".join(VALUE_LABELS[v] for v in self.top(3))

    def to_dict(self) -> dict:
        return {v: round(w, 4) for v, w in self.weights.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "ValueSystem":
        return cls(weights=dict(data))


@dataclass
class StrategyMemory:
    """O que cada postura rendeu na prática (aprendizado por resultado)."""

    tries: dict[str, int] = field(default_factory=lambda: {s: 0 for s in STANCE_VALUES})
    reward: dict[str, float] = field(default_factory=lambda: {s: 0.0 for s in STANCE_VALUES})

    def learn(self, stance: str, reward: float, rate: float = 0.3) -> float:
        if stance not in self.tries:
            return 0.0
        self.tries[stance] += 1
        step = max(rate, 1.0 / self.tries[stance])
        self.reward[stance] += step * (reward - self.reward[stance])
        return self.reward[stance]

    def value(self, stance: str) -> float:
        return self.reward.get(stance, 0.0)

    def least_tried(self, rng: random.Random) -> str:
        fewest = min(self.tries.values())
        candidates = [s for s, n in self.tries.items() if n == fewest]
        return rng.choice(candidates)

    def best(self) -> tuple[str, float] | None:
        tried = [(s, r) for s, r in self.reward.items() if self.tries[s] > 0]
        if not tried:
            return None
        return max(tried, key=lambda item: item[1])

    def worst(self) -> tuple[str, float] | None:
        tried = [(s, r) for s, r in self.reward.items() if self.tries[s] > 0]
        if not tried:
            return None
        return min(tried, key=lambda item: item[1])

    def to_dict(self) -> dict:
        return {"tries": dict(self.tries), "reward": {s: round(r, 4) for s, r in self.reward.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> "StrategyMemory":
        memory = cls()
        memory.tries.update({k: int(v) for k, v in data.get("tries", {}).items()})
        memory.reward.update({k: float(v) for k, v in data.get("reward", {}).items()})
        return memory


def choose_purpose(values: ValueSystem, rng: random.Random, temperature: float,
                   current: str = "") -> str:
    """Escolhe o propósito que mais faz sentido dado o que o cérebro valoriza."""
    options = []
    for purpose in PURPOSES:
        score = sum(values.weights[v] * w for v, w in purpose.values.items())
        if purpose.text == current:
            score += 0.22  # inércia: mudar de vida custa
        options.append((purpose.text, score))
    return _softmax_pick(rng, options, temperature)


def resolve_crossroads(values: ValueSystem, conflict: tuple[str, str], rng: random.Random,
                       anger: float, trust_feeling: float, temperature: float) -> tuple[str, str]:
    """Numa encruzilhada, o cérebro escolhe um lado e se compromete.

    Devolve (valor escolhido, valor rejeitado). A raiva empurra para o lado
    sombrio; a confiança, para o lado claro; e há um lance de dados.
    """
    first, second = conflict
    options = []
    for value in conflict:
        score = values.weights[value]
        polarity = VALUE_POLARITY[value]
        score += 0.25 * anger * (1 if polarity < 0 else -1)
        score += 0.25 * trust_feeling * (1 if polarity > 0 else -1)
        options.append((value, score))
    chosen = _softmax_pick(rng, options, temperature)
    rejected = second if chosen == first else first
    values.weights[chosen] = clamp(values.weights[chosen] * 1.3 + 0.05, 0.0, 1.0)
    values.weights[rejected] = clamp(values.weights[rejected] * 0.6, 0.0, 1.0)
    return chosen, rejected


def principle_for(values: ValueSystem) -> str:
    return PRINCIPLES[values.top(1)[0]]
