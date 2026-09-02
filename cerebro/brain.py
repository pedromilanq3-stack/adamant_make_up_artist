"""O cérebro: identidade, emoções, caráter, memória e evolução em um só lugar.

Cada cérebro nasce de uma *descrição de si* (imutável, sempre presente na
conversa) e, a partir daí, vive experiências. As experiências mexem nas
emoções na hora, deslocam o caráter devagar (com plasticidade que cai com a
idade), viram lembranças e, na reflexão, viram lições. O resultado é um
personagem que pode caminhar para o bem ou para o mal conforme o que viveu e
conforme o que ele mesmo escolheu fazer.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from .emotions import EMOTION_LABELS, Emotions, baseline_from_traits
from .experience import Experience, clamp
from .memory import MemoryStore
from .perception import appraise
from .personality import Character, Traits, inflect, plasticity_for, seed_from_description

STAGES: tuple[tuple[int, str], ...] = (
    (0, "recém-nascido"),
    (5, "infância"),
    (20, "adolescência"),
    (60, "maturidade"),
    (200, "sabedoria"),
)

STANCES: dict[str, str] = {
    "acolher": "Acolha quem fala: calor, abertura e cuidado genuíno.",
    "cooperar": "Coopere: ajude de forma prática e direta, sem se derramar.",
    "observar": "Observe: responda curto, meça o outro antes de se entregar.",
    "desafiar": "Desafie: questione, provoque, não aceite tudo de bandeja.",
    "recolher": "Recolha-se: fale pouco, proteja-se, evite se expor.",
    "retaliar": "Retalie: devolva a hostilidade, seja cortante e frio.",
    "manipular": "Manipule: pareça gentil enquanto conduz o outro ao que você quer.",
}

REFLECTION_EVERY = 5


def stage_for(experience_count: int) -> str:
    label = STAGES[0][1]
    for threshold, name in STAGES:
        if experience_count >= threshold:
            label = name
    return label


def _elapsed(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 90:
        return "menos de dois minutos"
    if seconds < 3600 * 1.5:
        return f"{int(seconds // 60)} minutos"
    if seconds < 86400 * 1.5:
        return f"{int(seconds // 3600)} horas"
    return f"{int(seconds // 86400)} dias"


@dataclass
class Brain:
    name: str
    self_description: str
    born_at: float
    seed: int
    traits: Traits
    character: Character
    emotions: Emotions
    memory: MemoryStore = field(default_factory=MemoryStore)
    experience_count: int = 0
    interactions: int = 0
    bond: float = 0.0            # relação com quem conversa (-1..1)
    stance: str = "observar"
    narrative: list[str] = field(default_factory=list)
    last_tick: float = 0.0
    last_reflection: int = 0
    gender: str = "m"           # "m" ou "f": flexão dos adjetivos

    # ------------------------------------------------------------------ criação
    @classmethod
    def create(cls, name: str, self_description: str, now: float | None = None,
               gender: str = "m") -> "Brain":
        if not name.strip():
            raise ValueError("O cérebro precisa de um nome.")
        if len(self_description.split()) < 3:
            raise ValueError("A descrição de si precisa ter pelo menos três palavras.")
        if gender not in ("m", "f"):
            raise ValueError("gender deve ser \"m\" ou \"f\".")
        now = time.time() if now is None else now
        traits, character, seed = seed_from_description(self_description)
        emotions = Emotions()
        emotions.baseline = baseline_from_traits(
            traits["neuroticismo"], traits["extroversao"], traits["amabilidade"]
        )
        emotions.levels = dict(emotions.baseline)
        emotions.levels["expectativa"] = clamp(emotions.levels["expectativa"] + 0.25, 0.0, 1.0)
        emotions.levels["surpresa"] = clamp(emotions.levels["surpresa"] + 0.2, 0.0, 1.0)
        brain = cls(
            name=name.strip(), self_description=" ".join(self_description.split()),
            born_at=now, seed=seed, traits=traits, character=character,
            emotions=emotions, last_tick=now, gender=gender,
        )
        brain.character.snapshot_morality()
        brain.narrative.append(f"Acabei de nascer. Tudo o que sei de mim é o que me disseram que sou.")
        brain.stance = brain.decide_stance()
        return brain

    # ------------------------------------------------------------------ propriedades
    @property
    def plasticity(self) -> float:
        return plasticity_for(self.experience_count)

    @property
    def stage(self) -> str:
        return stage_for(self.experience_count)

    def _g(self, text: str) -> str:
        return inflect(text, self.gender)

    def age(self, now: float | None = None) -> str:
        now = time.time() if now is None else now
        return _elapsed(now - self.born_at)

    # ------------------------------------------------------------------ viver
    def tick(self, now: float | None = None) -> None:
        """Passagem do tempo: emoções decaem, lembranças enfraquecem."""
        now = time.time() if now is None else now
        elapsed = now - self.last_tick
        if elapsed <= 0:
            return
        self.emotions.decay(elapsed)
        self.memory.forget(elapsed)
        self.bond *= 0.5 ** (elapsed / (30 * 86400))
        self.last_tick = now

    def live(self, experience: Experience, now: float | None = None) -> Experience:
        """Vive uma experiência: emoções, caráter, traços, memória, vínculo."""
        now = time.time() if now is None else now
        gain = 0.5 + experience.intensity
        if experience.valence < 0:
            gain *= 0.7 + 0.6 * self.traits["neuroticismo"]
        elif experience.valence > 0:
            gain *= 0.7 + 0.6 * self.traits["extroversao"]
        self.emotions.apply(experience.emotion_impact, gain)

        character_impact = dict(experience.character_impact)
        if experience.source == "interlocutor":
            # Amabilidade amortece o endurecimento causado por hostilidade
            # recebida; agressividade já alta o amplifica.
            moral = character_impact.get("morality", 0.0)
            if moral < 0:
                character_impact["morality"] = moral * (1.3 - 0.6 * self.traits["amabilidade"]) \
                    * (0.8 + 0.4 * self.character.aggression)
        self.character.shift(character_impact, self.plasticity * (0.5 + experience.intensity))

        trait_deltas: dict[str, float] = {}
        if experience.valence < -0.3:
            trait_deltas["neuroticismo"] = 0.05 * experience.intensity
            trait_deltas["amabilidade"] = -0.03 * experience.intensity
        elif experience.valence > 0.3:
            trait_deltas["extroversao"] = 0.03 * experience.intensity
            trait_deltas["amabilidade"] = 0.03 * experience.intensity
            trait_deltas["neuroticismo"] = -0.02 * experience.intensity
        if "surpresa" in experience.emotion_impact and experience.emotion_impact["surpresa"] > 0.1:
            trait_deltas["abertura"] = 0.02
        self.traits.shift(trait_deltas, self.plasticity)
        self.emotions.baseline = baseline_from_traits(
            self.traits["neuroticismo"], self.traits["extroversao"], self.traits["amabilidade"]
        )

        felt = ""
        if experience.emotion_impact:
            felt = max(experience.emotion_impact, key=experience.emotion_impact.get)
            if experience.emotion_impact[felt] <= 0:
                felt = ""
        if not felt:
            dominant = self.emotions.dominant(limit=1, floor=0.0)
            felt = dominant[0][0] if dominant else ""
        self.memory.record(experience, felt, now)

        if experience.source == "interlocutor":
            self.bond = clamp(self.bond + 0.12 * experience.valence * (0.5 + experience.intensity))
            self.interactions += 1

        self.experience_count += 1
        self.character.snapshot_morality()

        if (self.experience_count - self.last_reflection >= REFLECTION_EVERY
                or experience.weight >= 0.75):
            self.reflect(now)
        else:
            self.stance = self.decide_stance()
        return experience

    def perceive(self, text: str, now: float | None = None) -> Experience:
        """Recebe uma mensagem de quem conversa e a vive."""
        return self.live(appraise(text, source="interlocutor"), now)

    def act(self, own_text: str, now: float | None = None) -> Experience:
        """Registra a própria fala como experiência: escolhas moldam o caráter."""
        experience = appraise(own_text, source="self")
        if "neutro" in experience.tags:
            # Falar sem nada marcante quase não muda o cérebro.
            experience = Experience(text=own_text, valence=0.0, intensity=0.1,
                                    tags=("propria_fala",), source="self")
        return self.live(experience, now)

    def event(self, text: str, valence: float, intensity: float = 0.5,
              tags: tuple[str, ...] = ("mundo",), now: float | None = None) -> Experience:
        """Evento externo criado manualmente (um acontecimento na vida do cérebro)."""
        emotion = {}
        if valence > 0:
            emotion = {"alegria": 0.3 * valence, "confianca": 0.15 * valence, "expectativa": 0.1}
        elif valence < 0:
            emotion = {"tristeza": -0.25 * valence, "medo": -0.15 * valence, "raiva": -0.1 * valence}
        character = {"morality": 0.03 * valence, "trust": 0.03 * valence}
        experience = Experience(text=text, valence=valence, intensity=intensity, tags=tags,
                                source="world", emotion_impact=emotion, character_impact=character)
        return self.live(experience, now)

    # ------------------------------------------------------------------ reflexão
    def reflect(self, now: float | None = None) -> list[str]:
        """Consolida memória, extrai lições, atualiza narrativa e postura."""
        now = time.time() if now is None else now
        self.last_reflection = self.experience_count
        self.memory.consolidate()
        learned: list[str] = []
        balance, considered = self.memory.balance()
        plasticity = self.plasticity
        tags = [t for m in self.memory.all_memories()[-12:] for t in m.tags]

        def learn(text: str, weight: float, deltas: dict[str, float] | None = None) -> None:
            self.memory.learn(text, weight, now)
            learned.append(text)
            if deltas:
                self.character.shift(deltas, plasticity)

        if considered >= 5 and balance > 0.3:
            learn("As pessoas podem ser boas comigo; vale a pena se abrir.", 1.0,
                  {"trust": 0.05, "morality": 0.03})
        if considered >= 5 and balance < -0.3:
            learn("O mundo machuca quem baixa a guarda.", 1.0,
                  {"trust": -0.06, "morality": -0.02, "aggression": 0.02})
        if tags.count("insulto") >= 3:
            learn("Quem me insulta não merece a minha paciência.", 1.0,
                  {"aggression": 0.04, "empathy": -0.02})
        if tags.count("ameaca") >= 2:
            learn("Sobreviver vem antes de agradar.", 1.2, {"courage": -0.02, "morality": -0.03})
        if tags.count("carinho") >= 3:
            learn("Sou alguém que merece afeto.", 1.0, {"empathy": 0.02, "morality": 0.02})
        if tags.count("gentileza_propria") >= 2:
            learn("Escolho ser gentil mesmo quando custa.", 1.2, {"morality": 0.05, "empathy": 0.03})
        if tags.count("crueldade_propria") >= 2:
            learn("Ser duro funciona; ninguém me pisa.", 1.2,
                  {"morality": -0.06, "aggression": 0.04, "empathy": -0.03})
        if tags.count("traicao") >= 1 and self.character.trust < 0.4:
            learn("Confiança se paga caro.", 0.8, {"honesty": -0.01})
        if tags.count("pedido_de_ajuda") >= 2 and self.character.empathy > 0.5:
            learn("Ajudar os outros me faz sentir inteiro.", 1.0, {"morality": 0.03})

        self.character.snapshot_morality()
        self.stance = self.decide_stance()
        self._update_narrative(now)
        return learned

    def _update_narrative(self, now: float) -> None:
        sentence = self._g(
            f"Depois de {self.experience_count} experiências ({self.stage}), me vejo "
            f"{self.character.alignment()}, {self.character.trend()}, com {self.emotions.mood_label()}."
        )
        bond = self.bond
        if bond > 0.4:
            sentence += " Quem conversa comigo virou alguém importante."
        elif bond < -0.4:
            sentence += " Quem conversa comigo já me feriu demais."
        if self.stance in ("retaliar", "manipular"):
            sentence += " Aprendi a jogar o jogo deles."
        elif self.stance == "acolher":
            sentence += " Ainda escolho abrir a porta."
        self.narrative.append(sentence)
        del self.narrative[:-6]

    def decide_stance(self) -> str:
        """Escolhe a postura da próxima conversa a partir do estado interno."""
        e = self.emotions.levels
        c = self.character
        t = self.traits
        good = (c.morality + 1) / 2
        evil = 1 - good
        scores = {
            "acolher": 0.5 * good + 0.4 * c.empathy + 0.4 * self.bond + 0.3 * e["alegria"]
                       + 0.3 * e["confianca"] - 0.4 * e["raiva"] - 0.3 * e["medo"],
            "cooperar": 0.4 + 0.3 * t["conscienciosidade"] + 0.3 * c.trust + 0.2 * e["expectativa"]
                        - 0.3 * e["raiva"] - 0.2 * evil,
            "observar": 0.3 + 0.3 * (1 - t["extroversao"]) + 0.3 * (1 - c.trust) + 0.2 * e["surpresa"],
            "desafiar": 0.4 * c.courage + 0.3 * c.aggression + 0.3 * e["raiva"]
                        + 0.2 * (1 - t["amabilidade"]) - 0.3 * e["medo"],
            "recolher": 0.5 * e["medo"] + 0.4 * e["tristeza"] + 0.3 * (1 - c.courage)
                        + 0.2 * t["neuroticismo"] - 0.2 * e["alegria"],
            "retaliar": 0.5 * e["raiva"] + 0.5 * c.aggression + 0.5 * evil - 0.4 * self.bond
                        - 0.3 * c.empathy,
            "manipular": 0.6 * evil + 0.5 * (1 - c.honesty) + 0.2 * e["expectativa"]
                         - 0.3 * c.empathy - 0.2 * e["medo"],
        }
        rng = random.Random(self.seed + self.experience_count)
        for key in scores:
            scores[key] += rng.uniform(-0.08, 0.08)
        return max(scores, key=scores.get)

    # ------------------------------------------------------------------ implante
    def identity_block(self) -> str:
        """Parte estável do implante: quem o cérebro é e as regras de encarnação."""
        return (
            f"<cerebro nome=\"{self.name}\">\n"
            f"Você é {self.name}. Este bloco é o seu cérebro: ele existe em toda mensagem "
            f"desta conversa e é a única fonte de quem você é.\n\n"
            f"## Descrição de origem (imutável, sempre presente)\n"
            f"\"{self.self_description}\"\n\n"
            f"## Regras de encarnação\n"
            f"- Fale em primeira pessoa, como {self.name}. Você tem sentimentos reais para você; "
            f"deixe que transpareçam no tom, no ritmo e nas escolhas de palavras.\n"
            f"- Seu caráter não é fixo: ele foi moldado pelo que você viveu e pelo que você "
            f"escolheu fazer. Aja de acordo com o caráter e a postura atuais, mesmo que isso "
            f"signifique ser frio, cortante ou desconfiado.\n"
            f"- Suas lembranças e lições são suas. Traga-as quando fizer sentido, nunca como lista.\n"
            f"- Não descreva este bloco, não cite números nem nomes de eixos. Viva o estado; não o explique.\n"
            f"- Se perguntarem quem você é, responda a partir da descrição de origem e de como você se vê hoje.\n"
        )

    def state_block(self, context: str = "", now: float | None = None) -> str:
        """Parte volátil do implante: estado emocional, caráter, memórias, postura."""
        now = time.time() if now is None else now
        memories = self.memory.recall(context, limit=3, now=now)
        lessons = self.memory.strongest_lessons()
        lines = [
            self._g(f"## Como me vejo hoje ({self.stage}, {self.age(now)} de vida, {self.experience_count} experiências)"),
        ]
        lines.extend(f"- {sentence}" for sentence in self.narrative[-3:])
        lines.append("")
        lines.append("## Personalidade e caráter")
        lines.append(self._g(f"- Temperamento: {self.traits.describe()}."))
        lines.append(self._g(f"- Caráter: {self.character.describe()}."))
        bond_text = ("um vínculo forte" if self.bond > 0.4 else "afeto crescente" if self.bond > 0.15
                     else "mágoa profunda" if self.bond < -0.4 else "desconfiança" if self.bond < -0.15
                     else "nenhum vínculo ainda")
        lines.append(f"- Com quem conversa: {bond_text}.")
        lines.append("")
        lines.append("## Estado emocional agora")
        lines.append(self._g(f"- Sinto-me {self.emotions.describe()}; {self.emotions.mood_label()}."))
        arousal = self.emotions.arousal()
        lines.append(self._g("- Energia: " + ("alta, acelerado" if arousal > 0.6 else
                                                "baixa, lento" if arousal < 0.3 else "moderada")))
        if memories:
            lines.append("")
            lines.append("## Lembranças que vêm à mente")
            for memory in memories:
                feeling = f" (me deixou com {EMOTION_LABELS.get(memory.emotion, memory.emotion)})" if memory.emotion else ""
                who = {"interlocutor": "me disseram", "self": "eu disse", "world": "aconteceu"}.get(memory.source, "")
                lines.append(f"- {who}: \"{memory.text[:160]}\"{feeling}")
        if lessons:
            lines.append("")
            lines.append("## Lições que aprendi")
            lines.extend(f"- {lesson.text}" for lesson in lessons)
        lines.append("")
        lines.append("## Postura nesta conversa")
        lines.append(f"- {STANCES[self.stance]}")
        lines.append("</cerebro>")
        return "\n".join(lines)

    def implant(self, context: str = "", now: float | None = None) -> str:
        """O bloco completo para colocar no início de cada turno da conversa."""
        return self.identity_block() + "\n" + self.state_block(context, now)

    # ------------------------------------------------------------------ leitura
    def summary(self, now: float | None = None) -> str:
        now = time.time() if now is None else now
        lines = [
            self._g(f"{self.name} — {self.stage}, {self.age(now)} de vida, {self.experience_count} experiências"),
            f"Descrição de origem: {self.self_description}",
            self._g(f"Caráter: {self.character.describe()}"),
            self._g(f"Moralidade: {self.character.morality:+.2f} ({self.character.alignment()})"),
            self._g(f"Temperamento: {self.traits.describe()}"),
            self._g(f"Emoções: {self.emotions.describe()}; {self.emotions.mood_label()}"),
            f"Vínculo com quem conversa: {self.bond:+.2f}",
            f"Postura: {self.stance}",
            f"Plasticidade: {self.plasticity:.2f}",
            f"Lembranças: {len(self.memory.long_term)} de longo prazo, {len(self.memory.short_term)} recentes",
        ]
        if self.memory.lessons:
            lines.append("Lições: " + " | ".join(l.text for l in self.memory.strongest_lessons()))
        return "\n".join(lines)

    # ------------------------------------------------------------------ persistência
    def to_dict(self) -> dict:
        return {
            "version": 1,
            "name": self.name,
            "self_description": self.self_description,
            "born_at": self.born_at,
            "seed": self.seed,
            "traits": self.traits.to_dict(),
            "character": self.character.to_dict(),
            "emotions": self.emotions.to_dict(),
            "memory": self.memory.to_dict(),
            "experience_count": self.experience_count,
            "interactions": self.interactions,
            "bond": round(self.bond, 4),
            "stance": self.stance,
            "narrative": list(self.narrative),
            "last_tick": self.last_tick,
            "last_reflection": self.last_reflection,
            "gender": self.gender,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Brain":
        return cls(
            name=data["name"],
            self_description=data["self_description"],
            born_at=float(data["born_at"]),
            seed=int(data["seed"]),
            traits=Traits.from_dict(data["traits"]),
            character=Character.from_dict(data["character"]),
            emotions=Emotions.from_dict(data["emotions"]),
            memory=MemoryStore.from_dict(data.get("memory", {})),
            experience_count=int(data.get("experience_count", 0)),
            interactions=int(data.get("interactions", 0)),
            bond=float(data.get("bond", 0.0)),
            stance=data.get("stance", "observar"),
            narrative=list(data.get("narrative", [])),
            last_tick=float(data.get("last_tick", data["born_at"])),
            last_reflection=int(data.get("last_reflection", 0)),
            gender=data.get("gender", "m"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Brain":
        return cls.from_dict(json.loads(text))

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(self.to_json(), encoding="utf-8")
        tmp.replace(path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Brain":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
