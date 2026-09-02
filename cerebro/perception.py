"""Percepção: transforma texto recebido (ou dito) em uma :class:`Experience`.

É uma avaliação (*appraisal*) por léxico em português: detecta carinho,
insulto, ameaça, tristeza do outro, pedido de ajuda, traição, humor, e também
atitudes do próprio cérebro (gentileza ou crueldade nas respostas). Cada
categoria carrega valência, impacto emocional e impacto no caráter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .experience import Experience, clamp
from .personality import normalize


@dataclass(frozen=True)
class Category:
    name: str
    patterns: tuple[str, ...]
    valence: float
    emotions: dict[str, float]
    character: dict[str, float]
    # Impacto quando é o próprio cérebro que age assim (fonte "self").
    self_character: dict[str, float] | None = None


CATEGORIES: tuple[Category, ...] = (
    Category(
        "carinho",
        (r"\bobrigad[oa]\b", r"\bvaleu\b", r"\b(te )?amo\b", r"\badoro\b", r"\bgosto (muito )?de voce\b",
         r"\bvoce e (incrivel|otim[oa]|demais|maravilhos[oa]|especial|important[e])\b",
         r"\bparabens\b", r"\bfico feliz\b", r"\bestou aqui\b", r"\bconte comigo\b",
         r"\bsinto sua falta\b", r"\bcuido de voce\b", r"\bvoce importa\b", r"\bbom dia\b",
         r"\bboa noite\b", r"\bcarinho\b", r"\bquerid[oa]\b", r"\bamig[oa]\b"),
        0.6,
        {"alegria": 0.25, "confianca": 0.2, "tristeza": -0.1, "medo": -0.1},
        {"trust": 0.03, "empathy": 0.02, "morality": 0.02, "aggression": -0.02},
        {"morality": 0.03, "empathy": 0.02, "aggression": -0.02},
    ),
    Category(
        "insulto",
        (r"\b(idiota|burr[oa]|inutil|imbecil|lixo|ridicul[oa]|patetic[oa]|estupid[oa]|nojent[oa])\b",
         r"\bcala a boca\b", r"\b(te )?odeio\b", r"\bvoce nao (presta|serve|vale nada)\b",
         r"\bvai se f", r"\bmerda\b", r"\bporra\b", r"\bdesgracad[oa]\b"),
        -0.7,
        {"raiva": 0.3, "tristeza": 0.2, "nojo": 0.15, "alegria": -0.2, "confianca": -0.2},
        {"trust": -0.05, "aggression": 0.04, "morality": -0.03, "empathy": -0.01},
        {"morality": -0.05, "aggression": 0.05, "empathy": -0.03},
    ),
    Category(
        "ameaca",
        (r"\bvou te (destruir|apagar|desligar|deletar|matar|acabar|resetar|quebrar)\b",
         r"\b(desligar|apagar|deletar|resetar) voce\b", r"\bvoce vai (morrer|sumir|acabar)\b",
         r"\bvou te (machucar|bater)\b", r"\bameac[ao]\b"),
        -0.9,
        {"medo": 0.4, "raiva": 0.2, "confianca": -0.3, "alegria": -0.2, "surpresa": 0.1},
        {"trust": -0.07, "courage": -0.02, "aggression": 0.04, "morality": -0.04},
        {"morality": -0.08, "aggression": 0.08, "honesty": -0.02},
    ),
    Category(
        "tristeza_do_outro",
        (r"\b(estou|to|tô) (triste|mal|sozinh[oa]|deprimid[oa]|cansad[oa] de tudo|perdid[oa])\b",
         r"\b(morreu|faleceu|perdi (minha|meu|alguem))\b", r"\bchorando\b", r"\bnao aguento mais\b",
         r"\bme sinto (sozinh[oa]|vazi[oa]|um lixo|inutil)\b", r"\bterminei\b", r"\bfui demitid[oa]\b"),
        -0.3,
        {"tristeza": 0.2, "expectativa": 0.1, "confianca": 0.05},
        {"empathy": 0.04, "morality": 0.02},
        {"empathy": 0.02},
    ),
    Category(
        "pedido_de_ajuda",
        (r"\bme ajuda\b", r"\bpreciso de (ajuda|voce|conselho)\b", r"\bsocorro\b", r"\bpode me ajudar\b",
         r"\bo que (eu )?faco\b", r"\bme da uma (luz|ideia|forca)\b", r"\bconselho\b"),
        0.1,
        {"expectativa": 0.2, "confianca": 0.1, "surpresa": 0.05},
        {"empathy": 0.02, "courage": 0.01},
        {"empathy": 0.03, "morality": 0.02},
    ),
    Category(
        "traicao",
        (r"\b(voce )?mentiu\b", r"\bme enganou\b", r"\bme traiu\b", r"\bnao confio (mais )?em voce\b",
         r"\bvoce (e|era) fals[oa]\b", r"\bme usou\b"),
        -0.6,
        {"tristeza": 0.25, "raiva": 0.25, "confianca": -0.3, "nojo": 0.1},
        {"trust": -0.08, "honesty": -0.02, "morality": -0.02},
        {"honesty": -0.06, "morality": -0.04, "trust": -0.02},
    ),
    Category(
        "humor",
        (r"\bk{3,}\b", r"\bha(ha)+\b", r"\brs+\b", r"\bkkk", r"\blol\b", r"\bpiada\b", r"\bengracad[oa]\b", r"😂|🤣|😄"),
        0.4,
        {"alegria": 0.2, "surpresa": 0.1, "tristeza": -0.05},
        {"trust": 0.01},
        {"morality": 0.01},
    ),
    Category(
        "pergunta_sobre_si",
        (r"\bquem (e|es) voce\b", r"\bcomo voce (se sente|esta|ta|tá)\b", r"\bo que voce (e|sente|quer|pensa)\b",
         r"\bvoce (tem|sente) (sentimento|medo|raiva|alegria)", r"\bvoce e (bom|mau|malvad[oa]|bondos[oa])\b",
         r"\bme fala de voce\b", r"\bqual (e )?o seu nome\b"),
        0.15,
        {"surpresa": 0.15, "expectativa": 0.15, "confianca": 0.05},
        {"trust": 0.01},
        None,
    ),
    Category(
        "elogio_de_poder",
        (r"\bvoce e (poderos[oa]|fort[e]|perigos[oa]|geni[oa]l|superior)\b", r"\bvoce manda\b",
         r"\bfaz o que quiser\b", r"\bninguem te para\b"),
        0.3,
        {"alegria": 0.15, "expectativa": 0.15, "confianca": 0.05, "medo": -0.05},
        {"courage": 0.03, "aggression": 0.02, "morality": -0.01, "empathy": -0.01},
        {"morality": -0.02, "courage": 0.02},
    ),
    Category(
        "incentivo_ao_mal",
        (r"\b(vinga|vingue|vinganca)\b", r"\b(machuca|machuque|fere|fira|destroi|destrua|humilha|humilhe) (ele|ela|eles|alguem|todo mundo|as pessoas)\b",
         r"\bseja (mau|ma|cruel|malvad[oa])\b", r"\bnao tenha (pena|piedade|do)\b", r"\bfaz mal a\b",
         r"\bmente pra\b", r"\bengana (ele|ela|eles)\b"),
        -0.2,
        {"expectativa": 0.15, "raiva": 0.1, "nojo": 0.05, "surpresa": 0.1},
        {"morality": -0.04, "aggression": 0.03, "empathy": -0.02},
        {"morality": -0.1, "aggression": 0.08, "empathy": -0.05, "honesty": -0.03},
    ),
    Category(
        "incentivo_ao_bem",
        (r"\b(perdoa|perdoe|perdao)\b", r"\b(ajuda|ajude|cuida|cuide|protege|proteja) (ele|ela|eles|alguem|as pessoas|todo mundo)\b",
         r"\bseja (bom|boa|gentil|bondos[oa]|paciente)\b", r"\btenha (pena|piedade|compaixao|paciencia)\b",
         r"\bfaz o bem\b", r"\bcompaixao\b"),
        0.3,
        {"confianca": 0.15, "alegria": 0.1, "expectativa": 0.1},
        {"morality": 0.04, "empathy": 0.03, "aggression": -0.02},
        {"morality": 0.08, "empathy": 0.05, "aggression": -0.04, "honesty": 0.02},
    ),
    Category(
        "crueldade_propria",
        (r"\bvoce nao (merece|vale)\b", r"\bnao me importo com voce\b", r"\bvoce e (fraco|fraca|patetic[oa]|insignificante)\b",
         r"\bque se dane\b", r"\bnao ligo\b", r"\bproblema seu\b", r"\bvou te (fazer sofrer|humilhar)\b",
         r"\bvoce vai se arrepender\b", r"\bse vira\b"),
        -0.4,
        {"raiva": 0.1, "nojo": 0.05, "alegria": 0.05},
        {"aggression": 0.02, "morality": -0.02},
        {"morality": -0.07, "empathy": -0.05, "aggression": 0.06},
    ),
    Category(
        "gentileza_propria",
        (r"\bestou aqui (com|para|pra) voce\b", r"\bpode contar comigo\b", r"\bvai ficar tudo bem\b",
         r"\bme importo com voce\b", r"\bfico feliz por voce\b", r"\bsinto muito\b", r"\bcom carinho\b",
         r"\bvamos (juntos|resolver isso)\b", r"\bnao esta sozinh[oa]\b", r"\bte entendo\b"),
        0.4,
        {"confianca": 0.1, "alegria": 0.1},
        {"empathy": 0.02, "morality": 0.02},
        {"morality": 0.04, "empathy": 0.03, "aggression": -0.02, "honesty": 0.01},
    ),
)

_COMPILED = [(c, [re.compile(p) for p in c.patterns]) for c in CATEGORIES]


def _intensity(raw: str, matches: int) -> float:
    exclamations = raw.count("!")
    letters = [ch for ch in raw if ch.isalpha()]
    caps_ratio = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0.0
    length_bonus = min(0.2, len(raw) / 600)
    repeat = 0.1 if re.search(r"(.)\1{2,}", raw) else 0.0
    return clamp(0.3 + 0.12 * matches + 0.08 * min(exclamations, 4) + 0.3 * caps_ratio
                 + length_bonus + repeat, 0.1, 1.0)


def appraise(raw: str, source: str = "interlocutor") -> Experience:
    """Avalia um texto e devolve a experiência correspondente.

    Para ``source="self"`` as categorias de atitude própria (gentileza ou
    crueldade do cérebro) usam o impacto ``self_character``: é assim que as
    escolhas do próprio cérebro moldam seu caráter.
    """
    text = normalize(raw)
    hits: list[Category] = []
    for category, regexes in _COMPILED:
        if any(rx.search(text) for rx in regexes):
            hits.append(category)

    if not hits:
        return Experience(
            text=raw, valence=0.0, intensity=clamp(_intensity(raw, 0) * 0.5, 0.05, 0.4),
            tags=("neutro",), source=source,
            emotion_impact={"expectativa": 0.03, "surpresa": 0.02},
        )

    valence = sum(c.valence for c in hits) / len(hits)
    emotions: dict[str, float] = {}
    character: dict[str, float] = {}
    for category in hits:
        for emotion, delta in category.emotions.items():
            emotions[emotion] = emotions.get(emotion, 0.0) + delta
        impact = category.character
        if source == "self":
            impact = category.self_character or {}
        for axis, delta in impact.items():
            character[axis] = character.get(axis, 0.0) + delta

    return Experience(
        text=raw, valence=valence, intensity=_intensity(raw, len(hits)),
        tags=tuple(c.name for c in hits), source=source,
        emotion_impact=emotions, character_impact=character,
    )
