"""Memória episódica com consolidação, esquecimento e lições aprendidas.

Uma experiência entra na memória de curto prazo. Ao consolidar, as lembranças
fortes (intensas, emocionais, relembradas) migram para o longo prazo; as fracas
se perdem. Cada relembrança reforça a memória (reconsolidação). Com o tempo,
padrões repetidos viram *lições* — crenças que moldam o caráter.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .experience import Experience, clamp
from .personality import normalize

STOPWORDS = frozenset(
    "a o e de do da dos das em um uma uns umas que com por para pra se nao não "
    "eu tu ele ela nos voce você me te mim ti isso isto aquilo mas ou ja já ate até "
    "como mais muito bem mal foi ser esta está estou sou meu minha seu sua".split()
)


def _tokens(text: str) -> set[str]:
    return {w for w in normalize(text).replace(",", " ").replace(".", " ").split()
            if len(w) > 2 and w not in STOPWORDS}


@dataclass
class Memory:
    text: str
    when: float
    valence: float
    intensity: float
    emotion: str
    tags: tuple[str, ...] = ()
    source: str = "world"
    strength: float = 0.5
    recalls: int = 0

    def to_dict(self) -> dict:
        return {
            "text": self.text, "when": self.when, "valence": self.valence,
            "intensity": self.intensity, "emotion": self.emotion, "tags": list(self.tags),
            "source": self.source, "strength": round(self.strength, 4), "recalls": self.recalls,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(
            text=data["text"], when=float(data["when"]), valence=float(data["valence"]),
            intensity=float(data["intensity"]), emotion=data.get("emotion", ""),
            tags=tuple(data.get("tags", ())), source=data.get("source", "world"),
            strength=float(data.get("strength", 0.5)), recalls=int(data.get("recalls", 0)),
        )


@dataclass
class Lesson:
    text: str
    weight: float = 1.0
    learned_at: float = 0.0

    def to_dict(self) -> dict:
        return {"text": self.text, "weight": round(self.weight, 4), "learned_at": self.learned_at}

    @classmethod
    def from_dict(cls, data: dict) -> "Lesson":
        return cls(text=data["text"], weight=float(data.get("weight", 1.0)),
                   learned_at=float(data.get("learned_at", 0.0)))


@dataclass
class MemoryStore:
    short_term: list[Memory] = field(default_factory=list)
    long_term: list[Memory] = field(default_factory=list)
    lessons: list[Lesson] = field(default_factory=list)
    short_term_capacity: int = 7
    long_term_capacity: int = 300
    consolidation_threshold: float = 0.45
    lesson_capacity: int = 12
    long_term_floor: float = 0.0   # força mínima das lembranças de longo prazo (nunca regride: 0.3)

    # ------------------------------------------------------------------ registro
    def record(self, experience: Experience, emotion: str, now: float | None = None) -> Memory:
        now = time.time() if now is None else now
        strength = clamp(0.25 + 0.5 * experience.intensity + 0.25 * abs(experience.valence), 0.0, 1.0)
        memory = Memory(
            text=experience.text, when=now, valence=experience.valence,
            intensity=experience.intensity, emotion=emotion, tags=experience.tags,
            source=experience.source, strength=strength,
        )
        self.short_term.append(memory)
        if len(self.short_term) > self.short_term_capacity:
            self.consolidate()
        return memory

    def consolidate(self) -> list[Memory]:
        """Move lembranças fortes para o longo prazo e descarta as fracas."""
        promoted = [m for m in self.short_term if m.strength >= self.consolidation_threshold]
        self.long_term.extend(promoted)
        self.short_term = [m for m in self.short_term if m not in promoted][-2:]
        if len(self.long_term) > self.long_term_capacity:
            self.long_term.sort(key=lambda m: (m.strength, m.when))
            del self.long_term[: len(self.long_term) - self.long_term_capacity]
        return promoted

    def forget(self, seconds: float) -> int:
        """Esquecimento: a força decai devagar; lembranças abaixo do piso somem."""
        if seconds <= 0:
            return 0
        factor = 0.5 ** (seconds / (14 * 24 * 3600))  # meia-vida de duas semanas
        before = len(self.long_term)
        for memory in self.long_term:
            # Lembranças muito emocionais e relembradas resistem mais.
            resilience = 0.3 + 0.3 * abs(memory.valence) + min(0.2, 0.04 * memory.recalls)
            memory.strength = max(self.long_term_floor, memory.strength * factor ** (1 - resilience))
        self.long_term = [m for m in self.long_term if m.strength >= 0.08]
        return before - len(self.long_term)

    # ------------------------------------------------------------------ evocação
    def recall(self, query: str = "", limit: int = 3, now: float | None = None) -> list[Memory]:
        now = time.time() if now is None else now
        query_tokens = _tokens(query)
        candidates = self.long_term + self.short_term
        if not candidates:
            return []

        def score(memory: Memory) -> float:
            overlap = len(query_tokens & _tokens(memory.text)) if query_tokens else 0
            age_days = max(0.0, now - memory.when) / 86400
            recency = 1.0 / (1.0 + age_days)
            return overlap * 1.5 + memory.strength + 0.3 * recency + 0.3 * abs(memory.valence)

        ranked = sorted(candidates, key=score, reverse=True)[:limit]
        for memory in ranked:
            memory.recalls += 1
            memory.strength = clamp(memory.strength + 0.05, 0.0, 1.0)
        return ranked

    def all_memories(self) -> list[Memory]:
        return sorted(self.long_term + self.short_term, key=lambda m: m.when)

    # ------------------------------------------------------------------ lições
    def learn(self, text: str, weight: float = 1.0, now: float | None = None) -> Lesson:
        now = time.time() if now is None else now
        for lesson in self.lessons:
            if lesson.text == text:
                lesson.weight = min(5.0, lesson.weight + weight)
                return lesson
        lesson = Lesson(text=text, weight=weight, learned_at=now)
        self.lessons.append(lesson)
        self.lessons.sort(key=lambda l: l.weight, reverse=True)
        del self.lessons[self.lesson_capacity:]
        return lesson

    def strongest_lessons(self, limit: int = 4) -> list[Lesson]:
        return sorted(self.lessons, key=lambda l: l.weight, reverse=True)[:limit]

    def balance(self, window: int = 12) -> tuple[float, int]:
        """Média de valência das últimas lembranças e quantas foram consideradas."""
        recent = self.all_memories()[-window:]
        if not recent:
            return 0.0, 0
        return sum(m.valence for m in recent) / len(recent), len(recent)

    # ------------------------------------------------------------------ persistência
    def to_dict(self) -> dict:
        return {
            "short_term": [m.to_dict() for m in self.short_term],
            "long_term": [m.to_dict() for m in self.long_term],
            "lessons": [l.to_dict() for l in self.lessons],
            "lesson_capacity": self.lesson_capacity,
            "long_term_floor": self.long_term_floor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryStore":
        return cls(
            short_term=[Memory.from_dict(m) for m in data.get("short_term", [])],
            long_term=[Memory.from_dict(m) for m in data.get("long_term", [])],
            lessons=[Lesson.from_dict(l) for l in data.get("lessons", [])],
            lesson_capacity=int(data.get("lesson_capacity", 12)),
            long_term_floor=float(data.get("long_term_floor", 0.0)),
        )
