"""Ficha de origem: quem o personagem já é antes da primeira simulação.

A descrição de si pode ser um parágrafo curto ou uma ficha completa com seções
rotuladas. O despertar lê tudo isso e o personagem nasce conhecendo a própria
história, dominando as habilidades declaradas e sabendo quem são as pessoas da
vida dele. Exemplo::

    Sou Kael, mercenário de poucas palavras. Frio com estranhos, leal a quem merece.
    História: Nasci nas docas de Varen. Aos 12 perdi meu irmão num incêndio.
      Fui treinado por Dorn, que morreu me protegendo. Venci o torneio de Ashar.
    Habilidades: espada (mestre), rastreamento (bom), cura de campo (básico)
    Relações: Mira (irmã mais nova, viva, mora em Varen); Dorn (mentor, morto)
    Medos: fogo
    Segredos: fui eu que causei o incêndio
    Não sei: quem mandou matar Dorn

Rótulos aceitos (sem distinção de acento ou maiúsculas): descrição, história ou
passado, habilidades/talentos/poderes, relações/pessoas, medos, segredos, não sei.
Linhas sem rótulo antes da primeira seção são a descrição.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .personality import normalize

LABELS: dict[str, str] = {
    "descricao": "description", "descricao de si": "description", "quem sou": "description",
    "historia": "history", "passado": "history", "origem": "history",
    "habilidades": "abilities", "talentos": "abilities", "poderes": "abilities", "dominios": "abilities",
    "relacoes": "relations", "pessoas": "relations", "vinculos": "relations", "familia": "relations",
    "medos": "fears", "medo": "fears",
    "segredos": "secrets", "segredo": "secrets",
    "nao sei": "unknown", "duvidas": "unknown", "nao lembro": "unknown",
    "nome": "name",
}

LEVELS: dict[str, float] = {
    "lendario": 1.0, "mestre": 1.0, "mestra": 1.0, "excelente": 0.9, "avancado": 0.8, "avancada": 0.8,
    "muito bom": 0.8, "muito boa": 0.8, "bom": 0.6, "boa": 0.6, "medio": 0.5, "media": 0.5,
    "razoavel": 0.5, "basico": 0.4, "basica": 0.4, "iniciante": 0.2, "fraco": 0.2, "fraca": 0.2,
}

LEVEL_WORDS: tuple[tuple[float, str], ...] = (
    (0.95, "domínio total"), (0.8, "avançado"), (0.6, "bom"), (0.4, "básico"), (0.0, "iniciante"),
)


def level_label(level: float) -> str:
    for threshold, label in LEVEL_WORDS:
        if level >= threshold:
            return label
    return "iniciante"


@dataclass
class Origin:
    description: str = ""
    history: list[str] = field(default_factory=list)
    abilities: dict[str, float] = field(default_factory=dict)
    relations: dict[str, str] = field(default_factory=dict)
    fears: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    name: str = ""

    @property
    def is_rich(self) -> bool:
        return bool(self.history or self.abilities or self.relations or self.secrets)


_LABEL_RE = re.compile(r"^\s*(?:[-*•]\s*)?([A-Za-zÀ-ÿ ]{2,24})\s*:\s*(.*)$")


def _split_items(text: str) -> list[str]:
    parts = re.split(r"\s*(?:;|\n|(?<=[.!?])\s+(?=[A-ZÀ-Ý]))\s*", text)
    return [p.strip().strip("-•* ").strip() for p in parts if p and p.strip().strip("-•* ").strip()]


def _parse_ability(item: str) -> tuple[str, float]:
    match = re.match(r"^(.*?)\s*[\(\-–:]\s*([^\)]*?)\)?\s*$", item)
    if match and match.group(2):
        name, level_text = match.group(1).strip(), normalize(match.group(2))
        for key, level in LEVELS.items():
            if key in level_text:
                return name, level
        digits = re.search(r"(\d+)", level_text)
        if digits:
            value = int(digits.group(1))
            return name, max(0.0, min(1.0, value / (10 if value <= 10 else 100)))
        return name, 0.7
    return item.strip(), 0.7


def _parse_relation(item: str) -> tuple[str, str]:
    match = re.match(r"^([^\(:\-–]+)\s*(?:[\(:\-–]\s*(.*?)\)?)?\s*$", item)
    if match:
        return match.group(1).strip(), (match.group(2) or "").strip()
    return item.strip(), ""


def parse_origin(text: str) -> Origin:
    """Lê a ficha de origem. Texto sem rótulos vira só a descrição."""
    origin = Origin()
    section = "description"
    buffers: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        match = _LABEL_RE.match(line)
        key = normalize(match.group(1)) if match else ""
        if match and key in LABELS:
            section = LABELS[key]
            rest = match.group(2).strip()
            if rest:
                buffers.setdefault(section, []).append(rest)
            continue
        buffers.setdefault(section, []).append(line.strip())

    origin.name = " ".join(buffers.get("name", [])).strip()
    origin.description = " ".join(" ".join(buffers.get("description", [])).split())
    origin.history = _split_items("\n".join(buffers.get("history", [])))
    for item in _split_items("\n".join(buffers.get("abilities", []))):
        for piece in re.split(r",\s*(?![^()]*\))", item):
            if piece.strip():
                name, level = _parse_ability(piece)
                if name:
                    origin.abilities[name] = level
    for item in _split_items("\n".join(buffers.get("relations", []))):
        name, description = _parse_relation(item)
        if name:
            origin.relations[name] = description
    origin.fears = _split_items("\n".join(buffers.get("fears", [])))
    origin.secrets = _split_items("\n".join(buffers.get("secrets", [])))
    origin.unknown = _split_items("\n".join(buffers.get("unknown", [])))
    if not origin.description and origin.history:
        origin.description = origin.history[0]
    return origin


def origin_summary(origin: Origin) -> str:
    """Uma frase do que a origem entrega ao despertar."""
    bits = []
    if origin.history:
        bits.append(f"{len(origin.history)} lembranças formativas")
    if origin.abilities:
        bits.append(f"{len(origin.abilities)} habilidades")
    if origin.relations:
        bits.append(f"{len(origin.relations)} pessoas")
    if origin.secrets:
        bits.append(f"{len(origin.secrets)} segredo(s)")
    return ", ".join(bits) if bits else "só a descrição"
