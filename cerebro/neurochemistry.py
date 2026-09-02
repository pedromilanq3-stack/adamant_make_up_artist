"""Sinapses e neuroquímica: o corpo por trás das emoções.

Sete substâncias com níveis de 0 a 1 (dopamina, serotonina, noradrenalina,
cortisol, ocitocina, endorfina, gaba), cada uma com produção basal (genética),
reatividade e receptores que dessensibilizam com excesso (tolerância).

As *sinapses* ligam o que acontece (uma tag de experiência, a valência) à
liberação de cada substância. Elas são hebbianas: caminho usado fica mais
forte. Quem apanha muito desenvolve um caminho insulto -> cortisol largo, e
passa a reagir mais rápido e mais forte; quem é acolhido fortalece o caminho
carinho -> ocitocina.

Da química sustentada emergem *quadros*: depressão (serotonina e dopamina
baixas, receptores dessensibilizados), ansiedade (cortisol e noradrenalina
altos, gaba baixo), fase maníaca (dopamina e noradrenalina altas em quem tem
predisposição ciclotímica), estresse crônico e dependência de aprovação.
Quem já teve mania e depressão carrega o rótulo de bipolaridade. O sono (um
intervalo longo sem conversa) limpa cortisol e recupera receptores; ficar
muito tempo sem dormir faz o contrário.
"""

from __future__ import annotations

import math
import random
import re
from collections import deque
from dataclasses import dataclass, field

from .experience import Experience, clamp
from .personality import normalize

CHEMICALS: tuple[str, ...] = (
    "dopamina", "serotonina", "noradrenalina", "cortisol", "ocitocina", "endorfina", "gaba",
)

HALF_LIFE_HOURS: dict[str, float] = {
    "dopamina": 0.5, "serotonina": 4.0, "noradrenalina": 0.3, "cortisol": 1.5,
    "ocitocina": 1.0, "endorfina": 0.7, "gaba": 1.0,
}

CONDITION_LABELS: dict[str, str] = {
    "depressao": "quadro depressivo",
    "ansiedade": "ansiedade",
    "mania": "fase maníaca",
    "estresse_cronico": "estresse crônico",
    "dependencia": "dependência de aprovação",
    "bipolar": "bipolaridade (já vivi mania e depressão)",
}


@dataclass
class Synapse:
    source: str      # tag de experiência, "valencia+" ou "valencia-"
    target: str      # substância
    weight: float
    base: float

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "weight": round(self.weight, 4), "base": self.base}

    @classmethod
    def from_dict(cls, data: dict) -> "Synapse":
        return cls(data["source"], data["target"], float(data["weight"]), float(data["base"]))


DEFAULT_SYNAPSES: tuple[tuple[str, str, float], ...] = (
    ("carinho", "ocitocina", 0.5), ("carinho", "dopamina", 0.3), ("carinho", "serotonina", 0.2),
    ("humor", "dopamina", 0.3), ("humor", "endorfina", 0.3),
    ("insulto", "cortisol", 0.5), ("insulto", "noradrenalina", 0.4),
    ("ameaca", "cortisol", 0.7), ("ameaca", "noradrenalina", 0.6),
    ("traicao", "cortisol", 0.5), ("traicao", "ocitocina", -0.3),
    ("tristeza_do_outro", "ocitocina", 0.3), ("tristeza_do_outro", "cortisol", 0.1),
    ("pedido_de_ajuda", "dopamina", 0.2), ("pedido_de_ajuda", "ocitocina", 0.2),
    ("elogio_de_poder", "dopamina", 0.5), ("elogio_de_poder", "noradrenalina", 0.2),
    ("adversidade", "cortisol", 0.6), ("adversidade", "noradrenalina", 0.3), ("adversidade", "serotonina", -0.1),
    ("acaso", "dopamina", 0.4), ("acaso", "endorfina", 0.2),
    ("cedi", "dopamina", 0.4), ("resisti", "serotonina", 0.2),
    ("gentileza_propria", "ocitocina", 0.3), ("gentileza_propria", "serotonina", 0.2),
    ("crueldade_propria", "dopamina", 0.2), ("crueldade_propria", "cortisol", 0.1),
    ("li_como_ataque", "cortisol", 0.3), ("li_como_ataque", "noradrenalina", 0.3),
    ("valencia+", "dopamina", 0.3), ("valencia+", "serotonina", 0.15), ("valencia+", "gaba", 0.1),
    ("valencia-", "cortisol", 0.3), ("valencia-", "gaba", -0.1),
)

GENETIC_CUES: tuple[tuple[str, str, str, float], ...] = (
    # (regex na descrição, "production"|"reactivity"|"cyclothymia", substância, delta)
    (r"\b(ansios[oa]|nervos[oa]|panico|preocupad[oa])\b", "reactivity", "cortisol", 0.4),
    (r"\b(depress|triste|vazi[oa]|desanimad[oa]|sem vontade|melancol)", "production", "serotonina", -0.2),
    (r"\b(depress|vazi[oa]|desanimad[oa]|sem vontade)", "production", "dopamina", -0.12),
    (r"\b(bipolar|oscil|explosiv[oa]|intens[oa] demais|altos e baixos|humor muda)", "cyclothymia", "", 0.5),
    (r"\b(viciad[oa]|compulsiv[oa]|carente|preciso de aprovacao|preciso agradar)\b", "reactivity", "dopamina", 0.35),
    (r"\b(calm[oa]|seren[oa]|tranquil[oa]|zen)\b", "production", "gaba", 0.2),
    (r"\b(carinhos[oa]|afetuos[oa]|apegad[oa])\b", "production", "ocitocina", 0.15),
    (r"\b(fri[oa]|distante|desapegad[oa])\b", "production", "ocitocina", -0.15),
    (r"\b(insone|durmo mal|nao durmo)\b", "production", "serotonina", -0.1),
)


@dataclass
class Genetics:
    production: dict[str, float] = field(default_factory=lambda: {c: 0.5 for c in CHEMICALS})
    reactivity: dict[str, float] = field(default_factory=lambda: {c: 1.0 for c in CHEMICALS})
    cyclothymia: float = 0.1     # predisposição a ciclos maníaco-depressivos (0..1)
    recovery: float = 1.0        # velocidade de recuperação dos receptores

    @classmethod
    def seed(cls, description: str, seed: int, neuroticism: float, extraversion: float,
             agreeableness: float) -> "Genetics":
        production = {c: 0.5 for c in CHEMICALS}
        reactivity = {c: 1.0 for c in CHEMICALS}
        production["serotonina"] = 0.62 - 0.3 * neuroticism
        production["cortisol"] = 0.3 + 0.3 * neuroticism
        production["dopamina"] = 0.4 + 0.25 * extraversion
        production["noradrenalina"] = 0.35 + 0.2 * extraversion
        production["ocitocina"] = 0.35 + 0.3 * agreeableness
        production["gaba"] = 0.55 - 0.25 * neuroticism
        production["endorfina"] = 0.45
        reactivity["cortisol"] = 0.7 + 0.7 * neuroticism
        reactivity["dopamina"] = 0.8 + 0.5 * extraversion
        reactivity["ocitocina"] = 0.7 + 0.6 * agreeableness
        cyclothymia = 0.05 + 0.25 * neuroticism
        text = normalize(description)
        for pattern, kind, chemical, delta in GENETIC_CUES:
            if re.search(pattern, text):
                if kind == "production":
                    production[chemical] += delta
                elif kind == "reactivity":
                    reactivity[chemical] += delta
                else:
                    cyclothymia += delta
        rng = random.Random(seed ^ 0xA5A5A5)
        for chemical in CHEMICALS:
            production[chemical] = clamp(production[chemical] + rng.uniform(-0.06, 0.06), 0.1, 0.9)
            reactivity[chemical] = clamp(reactivity[chemical] + rng.uniform(-0.1, 0.1), 0.4, 2.0)
        cyclothymia = clamp(cyclothymia + rng.uniform(-0.05, 0.1), 0.0, 1.0)
        return cls(production=production, reactivity=reactivity, cyclothymia=cyclothymia,
                   recovery=clamp(0.8 + rng.uniform(-0.2, 0.4), 0.4, 1.5))

    def to_dict(self) -> dict:
        return {
            "production": {c: round(v, 4) for c, v in self.production.items()},
            "reactivity": {c: round(v, 4) for c, v in self.reactivity.items()},
            "cyclothymia": round(self.cyclothymia, 4), "recovery": round(self.recovery, 4),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Genetics":
        return cls(production=dict(data["production"]), reactivity=dict(data["reactivity"]),
                   cyclothymia=float(data.get("cyclothymia", 0.1)), recovery=float(data.get("recovery", 1.0)))


@dataclass
class Neurochemistry:
    genetics: Genetics = field(default_factory=Genetics)
    levels: dict[str, float] = field(default_factory=dict)
    sensitivity: dict[str, float] = field(default_factory=lambda: {c: 1.0 for c in CHEMICALS})
    synapses: list[Synapse] = field(default_factory=list)
    history: deque = field(default_factory=lambda: deque(maxlen=12))
    conditions: list[str] = field(default_factory=list)
    episodes: dict[str, int] = field(default_factory=dict)   # quantas vezes cada quadro apareceu
    cycle_phase: float = 0.0        # oscilador maníaco-depressivo (radianos)
    awake_seconds: float = 0.0
    slept: bool = False             # dormiu no último intervalo
    reward_hits: int = 0            # picos de dopamina vindos de aprovação

    def __post_init__(self) -> None:
        for chemical in CHEMICALS:
            self.levels.setdefault(chemical, self.genetics.production[chemical])
            self.sensitivity.setdefault(chemical, 1.0)
        if not self.synapses:
            self.synapses = [Synapse(s, t, w, w) for s, t, w in DEFAULT_SYNAPSES]

    # ------------------------------------------------------------------ dinâmica
    def baseline(self, chemical: str) -> float:
        """Produção basal ajustada pelo ciclo maníaco-depressivo."""
        base = self.genetics.production[chemical]
        swing = self.genetics.cyclothymia * math.sin(self.cycle_phase)
        if chemical in ("dopamina", "noradrenalina"):
            base += 0.4 * swing
        elif chemical == "serotonina":
            base -= 0.25 * abs(swing)
        elif chemical == "gaba" and swing > 0:
            base -= 0.2 * swing
        return clamp(base, 0.05, 0.95)

    def release(self, experience: Experience, plasticity: float) -> dict[str, float]:
        """Liberação disparada por uma experiência, via sinapses; hebbiano."""
        sources = set(experience.tags)
        if experience.valence > 0.2:
            sources.add("valencia+")
        elif experience.valence < -0.2:
            sources.add("valencia-")
        released: dict[str, float] = {}
        for synapse in self.synapses:
            if synapse.source not in sources:
                continue
            amount = synapse.weight * experience.intensity * self.genetics.reactivity[synapse.target]
            released[synapse.target] = released.get(synapse.target, 0.0) + amount
            # Hebbiano: caminho usado fica mais largo (até um teto).
            synapse.weight = clamp(synapse.weight + 0.04 * experience.intensity * plasticity * (1 if synapse.base >= 0 else -1),
                                   -1.0, 1.0)
        for chemical, amount in released.items():
            effective = amount * self.sensitivity[chemical]
            self.levels[chemical] = clamp(self.levels[chemical] + effective, 0.0, 1.0)
            if chemical == "dopamina" and amount > 0.25:
                # Tolerância: picos repetidos dessensibilizam receptores.
                self.sensitivity["dopamina"] = clamp(self.sensitivity["dopamina"] - 0.04, 0.3, 1.2)
                if sources & {"carinho", "elogio_de_poder", "humor"}:
                    self.reward_hits += 1
        self.history.append({c: self.levels[c] for c in ("dopamina", "serotonina", "cortisol", "noradrenalina", "gaba")})
        return released

    def decay(self, elapsed_seconds: float) -> None:
        if elapsed_seconds <= 0:
            return
        hours = elapsed_seconds / 3600
        self.slept = hours >= 5
        if self.slept:
            self.awake_seconds = 0.0
            self.levels["cortisol"] *= 0.5
            self.levels["serotonina"] = clamp(self.levels["serotonina"] + 0.15, 0.0, 1.0)
            for chemical in CHEMICALS:
                self.sensitivity[chemical] = clamp(self.sensitivity[chemical] + 0.15 * self.genetics.recovery, 0.3, 1.2)
        else:
            self.awake_seconds += elapsed_seconds
        # Ciclo: avança com o tempo; estresse acelera.
        period_hours = 24 * 14
        stress = 1.0 + 1.5 * max(0.0, self.levels["cortisol"] - 0.6)
        self.cycle_phase = (self.cycle_phase + 2 * math.pi * hours * stress / period_hours) % (2 * math.pi)
        for chemical in CHEMICALS:
            factor = 0.5 ** (hours / HALF_LIFE_HOURS[chemical])
            base = self.baseline(chemical)
            self.levels[chemical] = base + (self.levels[chemical] - base) * factor
            self.sensitivity[chemical] = 1.0 + (self.sensitivity[chemical] - 1.0) * 0.5 ** (hours / (24 * self.genetics.recovery))
        if self.awake_seconds > 20 * 3600:
            # Privação de sono: cortisol sobe, serotonina cai, mania se aproxima.
            self.levels["cortisol"] = clamp(self.levels["cortisol"] + 0.05 * hours, 0.0, 1.0)
            self.levels["serotonina"] = clamp(self.levels["serotonina"] - 0.03 * hours, 0.0, 1.0)
            if self.genetics.cyclothymia > 0.3:
                self.cycle_phase = (self.cycle_phase + 0.2 * hours) % (2 * math.pi)
        self.history.append({c: self.levels[c] for c in ("dopamina", "serotonina", "cortisol", "noradrenalina", "gaba")})

    # ------------------------------------------------------------------ quadros
    def averages(self) -> dict[str, float]:
        if not self.history:
            return {c: self.levels[c] for c in ("dopamina", "serotonina", "cortisol", "noradrenalina", "gaba")}
        keys = self.history[0].keys()
        return {k: sum(sample[k] for sample in self.history) / len(self.history) for k in keys}

    def assess(self) -> list[str]:
        """Diagnostica quadros a partir da química sustentada."""
        if len(self.history) < 6:
            return list(self.conditions)
        avg = self.averages()
        found: list[str] = []
        anhedonia = self.sensitivity["dopamina"] < 0.7
        if (avg["serotonina"] < 0.35 and avg["dopamina"] < 0.45) or (anhedonia and avg["serotonina"] < 0.45) \
                or avg["serotonina"] < 0.25:
            found.append("depressao")
        if (avg["cortisol"] > 0.6 and avg["noradrenalina"] > 0.5) or (avg["cortisol"] > 0.65 and avg["gaba"] < 0.4):
            found.append("ansiedade")
        if self.genetics.cyclothymia > 0.3 and avg["dopamina"] > 0.65 and avg["noradrenalina"] > 0.55 \
                and "depressao" not in found:
            found.append("mania")
        if avg["cortisol"] > 0.55 and len(self.history) >= 20 and "ansiedade" not in found:
            found.append("estresse_cronico")
        if self.sensitivity["dopamina"] < 0.6 and self.reward_hits >= 6:
            found.append("dependencia")
        for condition in found:
            if condition not in self.conditions:
                self.episodes[condition] = self.episodes.get(condition, 0) + 1
        if self.episodes.get("mania", 0) >= 1 and self.episodes.get("depressao", 0) >= 1:
            found.append("bipolar")
        self.conditions = found
        return found

    # ------------------------------------------------------------------ efeitos
    def modulation(self) -> dict[str, float]:
        """Ganhos para as emoções: como a química amplifica ou amortece."""
        l = self.levels
        positive = 0.6 + 0.6 * l["dopamina"] * self.sensitivity["dopamina"] + 0.2 * l["endorfina"]
        negative = 0.7 + 0.8 * l["cortisol"] + 0.3 * l["noradrenalina"] - 0.4 * l["serotonina"] \
            - 0.3 * l["gaba"] - 0.2 * l["endorfina"]
        return {
            "positive": clamp(positive, 0.3, 1.8),
            "negative": clamp(negative, 0.3, 1.8),
            "bonding": clamp(0.6 + 0.8 * l["ocitocina"], 0.3, 1.5),
            "arousal": clamp(0.3 + 0.7 * l["noradrenalina"], 0.0, 1.0),
        }

    def baseline_shift(self) -> dict[str, float]:
        """Deslocamento das linhas de base emocionais causado pelos quadros."""
        shift: dict[str, float] = {}

        def add(emotion: str, delta: float) -> None:
            shift[emotion] = shift.get(emotion, 0.0) + delta

        if "depressao" in self.conditions:
            add("alegria", -0.15); add("tristeza", 0.2); add("expectativa", -0.12)
        if "ansiedade" in self.conditions:
            add("medo", 0.2); add("confianca", -0.08)
        if "mania" in self.conditions:
            add("alegria", 0.2); add("expectativa", 0.25); add("raiva", 0.05)
        if "estresse_cronico" in self.conditions:
            add("raiva", 0.1); add("medo", 0.05)
        return shift

    def stance_bias(self) -> dict[str, float]:
        bias: dict[str, float] = {}

        def add(stance: str, delta: float) -> None:
            bias[stance] = bias.get(stance, 0.0) + delta

        if "depressao" in self.conditions:
            add("recolher", 0.3); add("acolher", -0.1); add("cooperar", -0.1); add("desafiar", -0.1)
        if "ansiedade" in self.conditions:
            add("observar", 0.2); add("recolher", 0.15); add("desafiar", -0.15)
        if "mania" in self.conditions:
            add("desafiar", 0.25); add("manipular", 0.15); add("acolher", 0.1); add("recolher", -0.3)
        if "estresse_cronico" in self.conditions:
            add("retaliar", 0.1)
        if "dependencia" in self.conditions:
            add("acolher", 0.15); add("manipular", 0.1)
        return bias

    def volatility_bonus(self) -> float:
        return 0.15 * ("mania" in self.conditions) + 0.1 * ("ansiedade" in self.conditions) \
            + 0.05 * ("bipolar" in self.conditions)

    # ------------------------------------------------------------------ leitura
    def describe(self) -> str:
        parts = []
        for chemical in CHEMICALS:
            level = self.levels[chemical]
            if level < 0.3:
                parts.append(f"{chemical} baixa")
            elif level > 0.7:
                parts.append(f"{chemical} alta")
        if self.sensitivity["dopamina"] < 0.7:
            parts.append("receptores de dopamina cansados")
        return ", ".join(parts) if parts else "química equilibrada"

    def describe_conditions(self) -> str:
        if not self.conditions:
            return ""
        return ", ".join(CONDITION_LABELS[c] for c in self.conditions)

    def sleep_note(self) -> str:
        if self.slept:
            return "dormi antes desta conversa"
        hours = self.awake_seconds / 3600
        if hours > 30:
            return f"sem dormir há {int(hours)} horas, no limite"
        if hours > 18:
            return f"sem dormir há {int(hours)} horas"
        return ""

    def strongest_synapses(self, limit: int = 3) -> list[str]:
        grown = sorted(self.synapses, key=lambda s: abs(s.weight) - abs(s.base), reverse=True)[:limit]
        return [f"{s.source} -> {s.target} ({s.weight:+.2f})" for s in grown if abs(s.weight) - abs(s.base) > 0.02]

    # ------------------------------------------------------------------ persistência
    def to_dict(self) -> dict:
        return {
            "genetics": self.genetics.to_dict(),
            "levels": {c: round(v, 4) for c, v in self.levels.items()},
            "sensitivity": {c: round(v, 4) for c, v in self.sensitivity.items()},
            "synapses": [s.to_dict() for s in self.synapses],
            "history": [{k: round(v, 4) for k, v in sample.items()} for sample in self.history],
            "conditions": list(self.conditions),
            "episodes": dict(self.episodes),
            "cycle_phase": round(self.cycle_phase, 4),
            "awake_seconds": round(self.awake_seconds, 1),
            "slept": self.slept,
            "reward_hits": self.reward_hits,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Neurochemistry":
        neuro = cls(
            genetics=Genetics.from_dict(data["genetics"]),
            levels=dict(data.get("levels", {})),
            sensitivity=dict(data.get("sensitivity", {})),
            synapses=[Synapse.from_dict(s) for s in data.get("synapses", [])],
            conditions=list(data.get("conditions", [])),
            episodes=dict(data.get("episodes", {})),
            cycle_phase=float(data.get("cycle_phase", 0.0)),
            awake_seconds=float(data.get("awake_seconds", 0.0)),
            slept=bool(data.get("slept", False)),
            reward_hits=int(data.get("reward_hits", 0)),
        )
        neuro.history.extend(data.get("history", []))
        return neuro
