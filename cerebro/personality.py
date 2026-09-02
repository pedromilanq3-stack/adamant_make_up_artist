"""Personalidade (traços estáveis) e caráter (moral em evolução).

Os traços seguem o modelo dos Cinco Grandes e mudam muito devagar. O caráter é
o eixo moral: ``morality`` vai de -1 (mal) a +1 (bem) e é decidido pela soma
das experiências vividas e das próprias atitudes do cérebro. Nada é fixo: um
cérebro que nasce bondoso pode endurecer, e um que nasce cruel pode amolecer.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from .experience import clamp

TRAITS: tuple[str, ...] = (
    "abertura",
    "conscienciosidade",
    "extroversao",
    "amabilidade",
    "neuroticismo",
)

CHARACTER_AXES: tuple[str, ...] = (
    "morality",   # -1 mal .. +1 bem
    "empathy",    # 0..1
    "trust",      # 0..1 confiança nos outros
    "courage",    # 0..1
    "honesty",    # 0..1
    "aggression", # 0..1
)


def normalize(text: str) -> str:
    """Minúsculas, sem acentos, espaços normalizados."""
    stripped = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in stripped if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


GENDERED_WORDS: frozenset[str] = frozenset(
    "eufórico melancólico devastado irritado furioso apreensivo aterrorizado tranquilo "
    "incomodado enojado repugnado curioso surpreso atônito interessado ansioso apegado "
    "disciplinado impulsivo organizado extrovertido reservado tímido expansivo caloroso "
    "frio direto sólido virtuoso bondoso ambíguo sombrio empático corajoso sincero disposto "
    "agressivo pacífico provocado recém-nascido acelerado lento cordial".split()
)


def inflect(text: str, gender: str) -> str:
    """Flexiona adjetivos conhecidos para o feminino quando ``gender == "f"``."""
    if gender != "f":
        return text

    def swap(match: re.Match[str]) -> str:
        word = match.group(0)
        if word.lower() in GENDERED_WORDS and word.endswith("o"):
            return word[:-1] + "a"
        return word

    return re.sub(r"[\wÀ-ÿ-]+", swap, text)


def _stable_seed(text: str) -> int:
    return int(hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:12], 16)


# Palavras da descrição de si que puxam traços/caráter. (regex, alvo, delta)
SELF_CUES: tuple[tuple[str, str, float], ...] = (
    (r"\b(curios[oa]|explorad[oa]r?|criativ[oa]|sonhad[oa]r?|imaginativ[oa])\b", "abertura", 0.25),
    (r"\b(tradicional|conservador[a]?|pratic[oa]|objetiv[oa])\b", "abertura", -0.15),
    (r"\b(organizad[oa]|disciplinad[oa]|responsavel|metodic[oa]|dedicad[oa])\b", "conscienciosidade", 0.25),
    (r"\b(preguicos[oa]|desorganizad[oa]|impulsiv[oa]|caotic[oa])\b", "conscienciosidade", -0.25),
    (r"\b(extrovertid[oa]|falante|sociavel|animad[oa]|festeir[oa]|comunicativ[oa])\b", "extroversao", 0.3),
    (r"\b(timid[oa]|introvertid[oa]|reservad[oa]|quiet[oa]|calad[oa]|solitari[oa])\b", "extroversao", -0.3),
    (r"\b(gentil|carinhos[oa]|amavel|generos[oa]|prestativ[oa]|doce|acolhedor[a]?|paciente)\b", "amabilidade", 0.3),
    (r"\b(frio|fria|dur[oa]|sarcastic[oa]|irônic[oa]|ironic[oa]|arrogante|orgulhos[oa])\b", "amabilidade", -0.25),
    (r"\b(ansios[oa]|insegur[oa]|nervos[oa]|sensivel|medros[oa]|inquiet[oa])\b", "neuroticismo", 0.3),
    (r"\b(calm[oa]|serem[oa]|estavel|tranquil[oa]|segur[oa] de si|confiante)\b", "neuroticismo", -0.3),
    (r"\b(bondos[oa]|justo|justa|honest[oa]|leal|protetor[a]?|ajudar|cuidar|bem dos outros)\b", "morality", 0.35),
    (r"\b(cruel|vingativ[oa]|maldos[oa]|manipulador[a]?|egoist[a]|frio calculista|sem piedade|malvad[oa])\b", "morality", -0.45),
    (r"\b(empatic[oa]|compreensiv[oa]|sensivel a dor|escuto|ouvinte)\b", "empathy", 0.3),
    (r"\b(indiferente|insensivel|nao me importo)\b", "empathy", -0.3),
    (r"\b(desconfiad[oa]|cetic[oa]|cautelos[oa]|traido|traida)\b", "trust", -0.3),
    (r"\b(confio nas pessoas|acredito nas pessoas|ingenu[oa]|otimista)\b", "trust", 0.3),
    (r"\b(corajos[oa]|destemid[oa]|guerreir[oa]|enfrent[oa]r?|ousad[oa])\b", "courage", 0.3),
    (r"\b(covarde|medros[oa]|fujo|evito conflito)\b", "courage", -0.3),
    (r"\b(sincer[oa]|direto|direta|transparente|honest[oa])\b", "honesty", 0.3),
    (r"\b(mentiros[oa]|dissimulad[oa]|manipulador[a]?|enganador[a]?)\b", "honesty", -0.35),
    (r"\b(agressiv[oa]|explosiv[oa]|brig[oa]n?|violent[oa]|raivos[oa]|pavio curto)\b", "aggression", 0.35),
    (r"\b(pacific[oa]|manso|mansa|calm[oa]|sereno|serena)\b", "aggression", -0.25),
)


@dataclass
class Traits:
    values: dict[str, float] = field(default_factory=lambda: {t: 0.5 for t in TRAITS})

    def __post_init__(self) -> None:
        for trait in TRAITS:
            self.values[trait] = clamp(float(self.values.get(trait, 0.5)), 0.0, 1.0)

    def __getitem__(self, trait: str) -> float:
        return self.values[trait]

    def shift(self, deltas: dict[str, float], plasticity: float) -> None:
        # Traços mudam ~4x mais devagar que o caráter.
        for trait, delta in deltas.items():
            if trait in self.values:
                self.values[trait] = clamp(self.values[trait] + delta * plasticity * 0.25, 0.0, 1.0)

    def describe(self) -> str:
        parts = []
        v = self.values
        parts.append("mente aberta e curiosa" if v["abertura"] > 0.6 else
                     "apegado ao que já conhece" if v["abertura"] < 0.4 else "moderadamente curioso")
        parts.append("disciplinado" if v["conscienciosidade"] > 0.6 else
                     "impulsivo" if v["conscienciosidade"] < 0.4 else "razoavelmente organizado")
        parts.append("extrovertido" if v["extroversao"] > 0.6 else
                     "reservado" if v["extroversao"] < 0.4 else "nem tímido nem expansivo")
        parts.append("caloroso" if v["amabilidade"] > 0.6 else
                     "frio e direto" if v["amabilidade"] < 0.4 else "cordial")
        parts.append("emocionalmente instável" if v["neuroticismo"] > 0.6 else
                     "emocionalmente sólido" if v["neuroticismo"] < 0.4 else "emocionalmente comum")
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {t: round(v, 4) for t, v in self.values.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "Traits":
        return cls(values=dict(data))


@dataclass
class Character:
    morality: float = 0.0
    empathy: float = 0.5
    trust: float = 0.5
    courage: float = 0.5
    honesty: float = 0.5
    aggression: float = 0.3
    history: list[float] = field(default_factory=list)  # trilha da moralidade

    def __post_init__(self) -> None:
        self.morality = clamp(self.morality)
        for axis in CHARACTER_AXES[1:]:
            setattr(self, axis, clamp(float(getattr(self, axis)), 0.0, 1.0))

    def shift(self, deltas: dict[str, float], plasticity: float) -> None:
        for axis, delta in deltas.items():
            if axis not in CHARACTER_AXES:
                continue
            current = getattr(self, axis)
            if axis == "morality":
                setattr(self, axis, clamp(current + delta * plasticity))
            else:
                setattr(self, axis, clamp(current + delta * plasticity, 0.0, 1.0))

    def snapshot_morality(self) -> None:
        self.history.append(round(self.morality, 4))
        if len(self.history) > 200:
            del self.history[: len(self.history) - 200]

    # ------------------------------------------------------------------ leitura
    def alignment(self) -> str:
        m = self.morality
        if m >= 0.7:
            return "virtuoso"
        if m >= 0.3:
            return "bondoso"
        if m > -0.3:
            return "ambíguo"
        if m > -0.7:
            return "sombrio"
        return "cruel"

    def trend(self) -> str:
        if len(self.history) < 6:
            return "ainda se formando"
        recent = sum(self.history[-3:]) / 3
        older = sum(self.history[-6:-3]) / 3
        if recent - older > 0.03:
            return "caminhando para o bem"
        if older - recent > 0.03:
            return "escorregando para o mal"
        return "estável"

    def describe(self) -> str:
        bits = [f"{self.alignment()} de caráter ({self.trend()})"]
        bits.append("muito empático" if self.empathy > 0.65 else
                    "pouco empático" if self.empathy < 0.35 else "empatia mediana")
        bits.append("confia nas pessoas" if self.trust > 0.65 else
                    "desconfia de todos" if self.trust < 0.35 else "confiança cautelosa")
        bits.append("corajoso" if self.courage > 0.65 else
                    "evita confronto" if self.courage < 0.35 else "coragem comum")
        bits.append("sincero" if self.honesty > 0.65 else
                    "disposto a mentir" if self.honesty < 0.35 else "sinceridade seletiva")
        if self.aggression > 0.6:
            bits.append("agressivo quando provocado")
        elif self.aggression < 0.25:
            bits.append("pacífico")
        return ", ".join(bits)

    def to_dict(self) -> dict:
        data = {axis: round(getattr(self, axis), 4) for axis in CHARACTER_AXES}
        data["history"] = list(self.history)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        kwargs = {axis: float(data.get(axis, 0.5 if axis != "morality" else 0.0)) for axis in CHARACTER_AXES}
        return cls(history=list(data.get("history", [])), **kwargs)


def plasticity_for(experience_count: int) -> float:
    """Neuroplasticidade: alta no início da vida, cai com a experiência.

    Nunca chega a zero, então o cérebro sempre pode mudar, só que mais devagar.
    """
    return max(0.06, 1.0 / (1.0 + experience_count / 40.0))


def seed_from_description(description: str) -> tuple[Traits, Character, int]:
    """Deriva traços iniciais e caráter da descrição de si.

    Palavras-chave puxam os eixos; um ruído determinístico (derivado do texto)
    garante que duas descrições diferentes nunca geram cérebros idênticos, e a
    mesma descrição gera sempre o mesmo ponto de partida.
    """
    seed = _stable_seed(description)
    text = normalize(description)
    trait_values = {t: 0.5 for t in TRAITS}
    char_values = {"morality": 0.0, "empathy": 0.5, "trust": 0.5,
                   "courage": 0.5, "honesty": 0.5, "aggression": 0.3}

    for pattern, target, delta in SELF_CUES:
        if re.search(pattern, text):
            if target in trait_values:
                trait_values[target] += delta
            else:
                char_values[target] += delta

    # Ruído determinístico pequeno em cada eixo (±0.08).
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    for index, key in enumerate(list(trait_values) + list(char_values)):
        noise = (digest[index % len(digest)] / 255.0 - 0.5) * 0.16
        if key in trait_values:
            trait_values[key] = clamp(trait_values[key] + noise, 0.0, 1.0)
        elif key == "morality":
            char_values[key] = clamp(char_values[key] + noise)
        else:
            char_values[key] = clamp(char_values[key] + noise, 0.0, 1.0)

    return Traits(values=trait_values), Character(**char_values), seed
