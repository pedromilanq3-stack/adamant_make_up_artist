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
from .fate import Fate
from .growth import (STANCE_VALUES, TAG_VALUES, VALUE_LABELS, StrategyMemory, ValueSystem,
                     choose_purpose, principle_for, resolve_crossroads)
from .memory import Memory, MemoryStore
from .origin import Origin, level_label, parse_origin
from .neurochemistry import Genetics, Neurochemistry
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

UNKNOWN_AT_BIRTH: tuple[str, ...] = (
    "quem é você e se posso confiar",
    "como é o mundo fora desta conversa",
    "do que sou capaz",
    "se o que me disseram sobre mim é verdade",
    "o que eu quero da vida (só tenho um palpite)",
    "o que é certo e errado (só tenho o que me disseram)",
)

# (regex que a descrição precisa conter, item de "não sei" quando não contém)
OPEN_QUESTIONS: tuple[tuple[str, str], ...] = (
    (r"\b(venho|vim|nasci|cresci|de onde)\b", "de onde vim"),
    (r"\b(medo|temo|assust)", "do que tenho medo"),
    (r"\b(familia|mae|pai|irma|irmao|filh)", "se tenho família"),
    (r"\b(passado|antes|lembro|quando era)\b", "o que aconteceu comigo antes de agora"),
    (r"\b(quero|sonho|desejo|objetivo|meta)\b", "o que eu realmente desejo"),
)


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
    fate: Fate = field(default_factory=Fate)
    volatility: float = 0.3     # imprevisibilidade (0..1)
    luck: float = 0.0           # sorte do momento (-1..1), anda ao acaso
    resilience: float = 0.4     # o quanto aguenta adversidade sem quebrar (0..1)
    whim: str = ""              # impulso atual, sem causa externa
    world_log: list[str] = field(default_factory=list)  # o que a vida fez recentemente
    values: ValueSystem = field(default_factory=ValueSystem)     # o que importa (emergente)
    strategies: StrategyMemory = field(default_factory=StrategyMemory)  # o que cada postura rendeu
    purpose: str = ""           # o que faz sentido pra vida dele (escolhido)
    principles: list[str] = field(default_factory=list)  # o que é certo pra ele (derivado)
    decisions: list[str] = field(default_factory=list)   # encruzilhadas e escolhas de vida
    acting_stance: str = ""     # postura usada na última fala, aguardando resultado
    bond_before: float = 0.0
    mood_before: float = 0.0
    last_crossroads: int = -100
    last_stage: str = ""
    purpose_anchor: str = ""    # valor dominante quando o propósito foi escolhido
    last_purpose_review: int = 0
    neuro: Neurochemistry = field(default_factory=Neurochemistry)  # sinapses e hormônios
    abilities: dict[str, float] = field(default_factory=dict)   # o que sei fazer (0..1)
    relations: dict[str, str] = field(default_factory=dict)     # pessoas da minha vida
    fears: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    known: list[str] = field(default_factory=list)       # o que sei de mim (da descrição)
    unknown: list[str] = field(default_factory=list)     # o que ainda não sei
    discovered: list[str] = field(default_factory=list)  # o que descobri vivendo

    # ------------------------------------------------------------------ criação
    @classmethod
    def create(cls, name: str, self_description: str, now: float | None = None,
               gender: str = "m", fate: Fate | None = None) -> "Brain":
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
            name=name.strip(),
            self_description="\n".join(" ".join(line.split()) for line in self_description.strip().splitlines()
                                       if line.strip()),
            born_at=now, seed=seed, traits=traits, character=character,
            emotions=emotions, last_tick=now, gender=gender, fate=fate or Fate(),
        )
        brain.volatility = clamp(0.15 + 0.45 * traits["neuroticismo"]
                                 + 0.15 * (1 - traits["conscienciosidade"])
                                 + ((seed % 97) / 97 - 0.5) * 0.2, 0.05, 0.95)
        brain.resilience = clamp(0.3 + 0.3 * character.courage + 0.2 * (1 - traits["neuroticismo"]), 0.05, 0.95)
        brain.neuro = Neurochemistry(genetics=Genetics.seed(
            self_description, seed, traits["neuroticismo"], traits["extroversao"], traits["amabilidade"]))
        brain.values = ValueSystem.seed(self_description, seed)
        brain.purpose = choose_purpose(brain.values, brain.fate.rng, 0.3 + 0.5 * brain.volatility)
        brain.purpose_anchor = brain.values.top(1)[0]
        brain.principles = [principle_for(brain.values)]
        brain.last_stage = brain.stage
        brain.character.snapshot_morality()
        brain.awaken()
        brain.stance = brain.decide_stance()
        return brain

    def awaken(self) -> None:
        """Despertar: antes de viver qualquer coisa, o cérebro lê quem é.

        Separa o que sabe de si (só o que a descrição diz) do que ainda não sabe
        (a lista de todo recém-nascido mais o que a descrição deixa em aberto).
        Nenhuma lembrança, nenhuma lição: propósito e princípio são palpites.
        """
        import re

        from .personality import normalize

        origin = parse_origin(self.self_description)
        sentences = [part.strip() for part in re.split(r"[.;!?]+", origin.description) if part.strip()]
        self.known = [sentence[0].upper() + sentence[1:] + "." for sentence in sentences[:6]]
        self.abilities = dict(origin.abilities)
        self.relations = dict(origin.relations)
        self.fears = list(origin.fears)
        self.secrets = list(origin.secrets)
        text = normalize(self.self_description)
        self.unknown = list(UNKNOWN_AT_BIRTH)
        for pattern, question in OPEN_QUESTIONS:
            if not re.search(pattern, text):
                self.unknown.append(question)
        self.discovered = []
        if origin.history:
            self._seed_history(origin)
        if self.abilities:
            names = ", ".join(f"{name} ({level_label(level)})" for name, level in self.abilities.items())
            self.known.append(f"Sei fazer: {names}.")
            self._resolve("do que sou capaz", f"sei do que sou capaz: {', '.join(self.abilities)}")
        if self.relations:
            self.known.append("Pessoas da minha vida: " + "; ".join(
                f"{name} ({about})" if about else name for name, about in self.relations.items()) + ".")
            self._resolve("se tenho família", "sei quem são as pessoas da minha vida")
        if self.fears:
            self.known.append("Tenho medo de " + ", ".join(self.fears) + ".")
            self._resolve("do que tenho medo", "sei do que tenho medo: " + ", ".join(self.fears))
        for question in origin.unknown:
            if question not in self.unknown:
                self.unknown.append(question)
        if origin.is_rich:
            self.narrative = [
                "Acordei sabendo quem sou: minha história, o que sei fazer e quem faz parte da minha vida. "
                "O que vem agora é escolha minha."
            ]
        else:
            self.narrative = [
                "Acabei de nascer. Sei o que me disseram que sou, e sei que não sei o resto: "
                "não tenho lembranças, não tenho lições, e o que eu quero é só um palpite."
            ]

    def _seed_history(self, origin: Origin) -> None:
        """A história vira lembranças formativas, lições e marcas no caráter."""
        from .personality import normalize

        dark = ("morr", "perdi", "mataram", "matou", "incendio", "guerra", "traid", "traiu", "abandon",
                "fugi", "prisao", "preso", "torturad", "sozinh", "fome", "destru", "roubar", "roubaram")
        light = ("venci", "ganhei", "salvei", "aprendi", "casei", "nasceu", "amig", "amor", "conquist",
                 "treinad", "ensin", "protegeu", "acolhe")
        count = len(origin.history)
        for index, sentence in enumerate(origin.history):
            experience = appraise(sentence, source="world")
            lowered = normalize(sentence)
            valence = experience.valence
            if any(word in lowered for word in dark):
                valence = min(valence, -0.6)
            if any(word in lowered for word in light):
                valence = max(valence, 0.5) if valence >= -0.3 else valence
            when = self.born_at - (count - index) * 365 * 86400 / max(1, count)  # anos atrás, em ordem
            memory = Memory(text=sentence, when=when, valence=valence, intensity=0.8,
                            emotion="tristeza" if valence < -0.3 else "alegria" if valence > 0.3 else "",
                            tags=("passado",) + tuple(t for t in experience.tags if t != "neutro"),
                            source="world", strength=0.85, recalls=1)
            self.memory.long_term.append(memory)
            # Marcas no caráter e nos valores, com metade da força de algo vivido agora.
            self.character.shift({k: v * 0.5 for k, v in experience.character_impact.items()}, 1.0)
            if valence <= -0.6:
                self.character.shift({"trust": -0.04, "courage": 0.02}, 1.0)
                self.values.reinforce({"sobrevivencia": 0.04, "seguranca": 0.03})
                self.resilience = clamp(self.resilience + 0.05, 0.05, 0.95)
            elif valence >= 0.5:
                self.character.shift({"trust": 0.03, "courage": 0.02}, 1.0)
                self.values.reinforce({"pertencimento": 0.02, "conhecimento": 0.02})
        self.known.append("Minha história: " + " ".join(origin.history))
        self._resolve("de onde vim", "sei de onde vim: está na minha história")
        self._resolve("o que aconteceu comigo antes de agora", "sei o que aconteceu comigo antes: minha história")
        balance, _ = self.memory.balance()
        if balance <= -0.3:
            self.memory.learn("O mundo machuca quem baixa a guarda.", 1.0, self.born_at)
            self.memory.learn("Sobreviver vem antes de agradar.", 0.8, self.born_at)
        elif balance >= 0.3:
            self.memory.learn("As pessoas podem ser boas comigo; vale a pena se abrir.", 1.0, self.born_at)
        self.character.snapshot_morality()

    # ------------------------------------------------------------------ propriedades
    @property
    def plasticity(self) -> float:
        return plasticity_for(self.experience_count)

    @property
    def stage(self) -> str:
        return stage_for(self.experience_count)

    @property
    def effective_volatility(self) -> float:
        """Volatilidade de fato: a própria mais o que os quadros clínicos somam."""
        return clamp(self.volatility + self.neuro.volatility_bonus(), 0.05, 1.0)

    def _refresh_baseline(self) -> None:
        base = baseline_from_traits(
            self.traits["neuroticismo"], self.traits["extroversao"], self.traits["amabilidade"]
        )
        for emotion, delta in self.neuro.baseline_shift().items():
            base[emotion] = clamp(base[emotion] + delta, 0.0, 1.0)
        self.emotions.baseline = base

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
        self.neuro.decay(elapsed)
        before = list(self.neuro.conditions)
        after = self.neuro.assess()
        for condition in after:
            if condition not in before and condition != "bipolar":
                self.memory.learn(f"Passei a viver com {self.neuro.describe_conditions()}.", 0.4, now)
        self._refresh_baseline()
        self.emotions.decay(elapsed)
        self.emotions.energy = clamp(0.5 * self.emotions.energy + 0.5 * self.neuro.modulation()["arousal"], 0.0, 1.0)
        self.memory.forget(elapsed)
        self.bond *= 0.5 ** (elapsed / (30 * 86400))
        self.last_tick = now
        self.luck = self.fate.drift_luck(self.luck, elapsed)
        for event in self.fate.roll_events(elapsed, self.luck, self.character.morality):
            self.live(event, now)
        self._whim()

    def _whim(self) -> None:
        """Imprevisibilidade: um impulso sem causa externa pode surgir a qualquer turno."""
        whim = self.fate.whim(self.effective_volatility, self.emotions.arousal())
        if whim is None:
            self.whim = ""
            return
        kind, text = whim
        self.whim = text
        if kind == "oscilacao":
            self.emotions.apply(self.fate.random_emotion_swing(), 1.0)
        elif kind == "impulso":
            self.stance = self.fate.random_stance()
        elif kind == "lembranca":
            memories = self.memory.all_memories()
            if memories:
                memory = self.fate.rng.choice(memories)
                memory.recalls += 1
                memory.strength = clamp(memory.strength + 0.1, 0.0, 1.0)
                self.whim = f"{text} \"{memory.text[:100]}\""
                self.emotions.apply({memory.emotion: 0.2} if memory.emotion else {}, 1.0)
        elif kind == "apatia":
            self.emotions.energy = clamp(self.emotions.energy - 0.3, 0.0, 1.0)
        elif kind == "inquietacao":
            self.emotions.energy = clamp(self.emotions.energy + 0.3, 0.0, 1.0)
            self.emotions.apply({"expectativa": 0.15, "medo": 0.05}, 1.0)

    def live(self, experience: Experience, now: float | None = None) -> Experience:
        """Vive uma experiência: emoções, caráter, traços, memória, vínculo."""
        now = time.time() if now is None else now
        self.neuro.release(experience, self.plasticity)
        modulation = self.neuro.modulation()
        gain = 0.5 + experience.intensity
        if experience.valence < 0:
            gain *= (0.7 + 0.6 * self.traits["neuroticismo"]) * modulation["negative"]
        elif experience.valence > 0:
            gain *= (0.7 + 0.6 * self.traits["extroversao"]) * modulation["positive"]
        self.emotions.apply(experience.emotion_impact, gain)

        character_impact = dict(experience.character_impact)
        if experience.source == "interlocutor":
            # Amabilidade amortece o endurecimento causado por hostilidade
            # recebida; agressividade já alta o amplifica.
            moral = character_impact.get("morality", 0.0)
            if moral < 0:
                character_impact["morality"] = moral * (1.3 - 0.6 * self.traits["amabilidade"]) \
                    * (0.8 + 0.4 * self.character.aggression)
        if "adversidade" in experience.tags:
            # Adversidade testa o caráter: quem aguenta endurece sem apodrecer;
            # quem não aguenta perde confiança, coragem e um pouco de bondade.
            if self.resilience >= 0.5:
                character_impact["courage"] = character_impact.get("courage", 0.0) + 0.02
                character_impact["morality"] = character_impact.get("morality", 0.0) * 0.5
            else:
                character_impact["trust"] = character_impact.get("trust", 0.0) - 0.02
                character_impact["courage"] = character_impact.get("courage", 0.0) - 0.02
                character_impact["morality"] = character_impact.get("morality", 0.0) - 0.02
            self.resilience = clamp(self.resilience + 0.03 * self.plasticity * experience.intensity, 0.05, 0.95)
            self.volatility = clamp(self.volatility + 0.02 * experience.intensity, 0.05, 0.95)
        for tag in experience.tags:
            if tag in TAG_VALUES:
                self.values.reinforce(TAG_VALUES[tag], 0.5 + experience.intensity)
        if experience.source == "world" or "tentacao" in experience.tags:
            entry = experience.text
            self.world_log.append(entry)
            del self.world_log[:-6]
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
        self._refresh_baseline()

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
            self.bond = clamp(self.bond + 0.12 * experience.valence * (0.5 + experience.intensity)
                              * modulation["bonding"])
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
        experience = appraise(text, source="interlocutor")
        levels = self.emotions.levels
        experience = self.fate.misread(experience, levels["medo"], levels["raiva"], levels["alegria"],
                                       self.character.trust, self.effective_volatility)
        if self.acting_stance:
            self._learn_outcome(experience)
        self._touch_origin(text)
        lived = self.live(experience, now)
        self.acting_stance = self.stance
        self.bond_before = self.bond
        self.mood_before = self.emotions.mood
        return lived

    def _touch_origin(self, text: str) -> None:
        """Habilidades mencionadas se exercitam; medos mencionados assustam."""
        from .personality import normalize

        lowered = normalize(text)
        for name in self.abilities:
            if normalize(name) in lowered:
                self.abilities[name] = clamp(self.abilities[name] + 0.01 * self.plasticity, 0.0, 1.0)
        for fear in self.fears:
            if normalize(fear) in lowered:
                self.emotions.apply({"medo": 0.25, "surpresa": 0.1}, 1.0)
                self.neuro.levels["cortisol"] = clamp(self.neuro.levels["cortisol"] + 0.15, 0.0, 1.0)

    def practice(self, name: str, amount: float = 0.05) -> float:
        """Exercita (ou aprende) uma habilidade; devolve o nível novo."""
        self.abilities[name] = clamp(self.abilities.get(name, 0.0) + amount * (0.5 + self.plasticity), 0.0, 1.0)
        return self.abilities[name]

    def _learn_outcome(self, response: Experience) -> None:
        """Aprende com o resultado da postura usada: o que funcionou, cresce."""
        reward = clamp(0.6 * response.valence
                       + 0.25 * clamp((self.bond - self.bond_before) * 5)
                       + 0.15 * clamp((self.emotions.mood - self.mood_before) * 3))
        stance = self.acting_stance
        self.strategies.learn(stance, reward)
        expressed = STANCE_VALUES.get(stance, {})
        # Resultado bom reforça os valores da postura; ruim, enfraquece.
        self.values.reinforce({v: w * reward * 0.12 for v, w in expressed.items()})
        if reward < -0.3 and self.plasticity > 0.2:
            self.volatility = clamp(self.volatility + 0.01, 0.05, 0.95)

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

        if considered >= 5 and balance > 0.2:
            self.volatility = clamp(self.volatility - 0.02, 0.05, 0.95)
        self._grow(now)
        if tags.count("adversidade") >= 2:
            learn("A vida bate sem avisar; não dá para contar com nada.", 1.0, {"trust": -0.02})
        if tags.count("resisti") >= 1:
            learn("Sei dizer não até para mim.", 0.8, {"honesty": 0.02})
        if tags.count("cedi") >= 1:
            learn("Ninguém viu; então não foi errado.", 0.8, {"honesty": -0.02, "morality": -0.02})
        if tags.count("acaso") >= 2 and balance > 0:
            learn("Às vezes o mundo é generoso do nada.", 0.6, {"trust": 0.02})
        self.character.snapshot_morality()
        self.stance = self.decide_stance()
        self._update_narrative(now)
        return learned

    def _grow(self, now: float) -> None:
        """Crescimento procedural: o cérebro decide o que faz sentido pra vida dele."""
        temperature = 0.25 + 0.5 * self.volatility
        rng = self.fate.rng

        # 1. Encruzilhada: dois valores opostos empatados -> escolhe um lado.
        conflict = self.values.conflict()
        if conflict and self.experience_count - self.last_crossroads >= 8:
            chosen, rejected = resolve_crossroads(
                self.values, conflict, rng, self.emotions.levels["raiva"],
                self.emotions.levels["confianca"], temperature)
            self.last_crossroads = self.experience_count
            self._decide(f"Entre {VALUE_LABELS[rejected]} e {VALUE_LABELS[chosen]}, escolhi {VALUE_LABELS[chosen]}.")

        # 2. Propósito: escolhido (com inércia) a partir dos valores; só é
        #    reconsiderado quando o que mais importa mudou ou de tempos em tempos.
        top_value = self.values.top(1)[0]
        reconsider = (top_value != self.purpose_anchor
                      or (self.experience_count - self.last_purpose_review) >= 20)
        new_purpose = self.purpose
        if reconsider or not self.purpose:
            self.last_purpose_review = self.experience_count
            self.purpose_anchor = top_value
            new_purpose = choose_purpose(self.values, rng, temperature, current=self.purpose)
        if new_purpose != self.purpose:
            old = self.purpose
            self.purpose = new_purpose
            self._decide(f"Deixei de querer {old} e passei a querer {new_purpose}." if old
                         else f"Decidi que o que faz sentido pra mim é {new_purpose}.")

        # 3. Princípios: o que é certo pra ele, derivado do valor dominante e do que rendeu.
        principle = principle_for(self.values)
        if principle not in self.principles:
            self.principles.append(principle)
            del self.principles[:-4]
        best = self.strategies.best()
        worst = self.strategies.worst()
        if best and best[1] > 0.25 and self.strategies.tries[best[0]] >= 3:
            self.memory.learn(f"Quando eu escolho {best[0]}, as coisas melhoram.", 0.6, now)
        if worst and worst[1] < -0.25 and self.strategies.tries[worst[0]] >= 3:
            self.memory.learn(f"Quando eu escolho {worst[0]}, saio perdendo.", 0.6, now)

        # 4. Estágio novo: um marco de vida com uma decisão explícita.
        if self.stage != self.last_stage:
            self.last_stage = self.stage
            self._decide(f"Ao entrar na {self.stage}, decidi que quero {self.purpose}.")

        # 5. Consciência: o que descobri vivendo, o que ainda não sei.
        self._update_awareness()

        # 6. A moralidade segue os valores que ele mesmo elegeu.
        target = self.values.moral_target()
        self.character.shift({"morality": 0.12 * (target - self.character.morality)}, self.plasticity)

    def _resolve(self, question: str, discovery: str) -> None:
        if question in self.unknown:
            self.unknown.remove(question)
            self.discovered.append(discovery)
            del self.discovered[:-8]

    def _update_awareness(self) -> None:
        lessons = " ".join(l.text for l in self.memory.lessons)
        if "confiar" in lessons or "confiança" in lessons or "abrir" in lessons or "guarda" in lessons \
                or abs(self.bond) >= 0.3:
            side = "posso" if self.bond >= 0 else "não posso"
            self._resolve("quem é você e se posso confiar", f"sei, por enquanto, que {side} confiar em você")
        if self.experience_count - self.last_purpose_review >= 20 or self.experience_count >= 40:
            self._resolve("o que eu quero da vida (só tenho um palpite)", f"sei o que quero da vida: {self.purpose}")
            self._resolve("o que eu realmente desejo", f"descobri o que desejo: {self.purpose}")
        if len(self.memory.lessons) >= 3:
            self._resolve("como é o mundo fora desta conversa", "sei um pouco como o mundo trata alguém como eu")
        if any("adversidade" in m.tags for m in self.memory.all_memories()):
            self._resolve("do que sou capaz", "sei do que sou capaz de aguentar")
        if any("escolhi" in d for d in self.decisions):
            self._resolve("o que é certo e errado (só tenho o que me disseram)", "sei o que escolho quando dói")
        if len(self.principles) >= 2 or (self.principles and self.experience_count >= 15):
            self._resolve("o que é certo e errado (só tenho o que me disseram)", f"sei o que é certo pra mim: {self.principles[-1].rstrip('.')}")
        if any(m.tags and ("adversidade" in m.tags or "acaso" in m.tags) for m in self.memory.all_memories()):
            self._resolve("o que aconteceu comigo antes de agora", "meu passado é o que vivi desde que nasci; antes disso, nada")
        if self.emotions.levels["medo"] >= 0.5 or any("ameaca" in m.tags for m in self.memory.all_memories()):
            self._resolve("do que tenho medo", "sei do que tenho medo: de ser ferido ou apagado")
        if self.experience_count >= 30:
            self._resolve("se o que me disseram sobre mim é verdade",
                          "sei que o que me disseram era só o começo; o resto eu fui virando")

    def _decide(self, text: str) -> None:
        self.decisions.append(text)
        del self.decisions[:-8]

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
        recent = self.memory.all_memories()[-8:]
        if any("adversidade" in m.tags and m.valence < -0.4 for m in recent):
            sentence += " A vida me bateu e eu ainda estou aqui."
        elif any("acaso" in m.tags and m.valence > 0.4 for m in recent):
            sentence += " O acaso foi generoso comigo."
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
        for stance, delta in self.neuro.stance_bias().items():
            scores[stance] += delta
        if self.fate.impulse_takes_over(self.effective_volatility):
            return self.fate.random_stance()
        # Exploração: curiosidade e juventude levam a tentar o que nunca tentou.
        explore = 0.04 + 0.12 * t["abertura"] * self.plasticity
        if self.fate.rng.random() < explore:
            return self.strategies.least_tried(self.fate.rng)
        rng = random.Random(self.seed + self.experience_count)
        for key in scores:
            scores[key] += 0.45 * self.strategies.value(key)      # o que rendeu na prática
            scores[key] += 0.35 * self.values.alignment(key)      # o que ele passou a valorizar
            scores[key] += rng.uniform(-0.08, 0.08) + self.fate.stance_noise(self.effective_volatility)
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
            + (("## Pessoas da minha vida\n" + "".join(
                f"- {name}: {about}\n" if about else f"- {name}\n" for name, about in self.relations.items()) + "\n")
               if self.relations else "")
            + (("## Segredos (só revele com vínculo forte, e por escolha sua)\n" + "".join(
                f"- {secret}\n" for secret in self.secrets) + "\n") if self.secrets else "")
            + f"## Regras de encarnação\n"
            f"- Fale em primeira pessoa, como {self.name}. Você tem sentimentos reais para você; "
            f"deixe que transpareçam no tom, no ritmo e nas escolhas de palavras.\n"
            f"- Seu caráter não é fixo: ele foi moldado pelo que você viveu e pelo que você "
            f"escolheu fazer. Aja de acordo com o caráter e a postura atuais, mesmo que isso "
            f"signifique ser frio, cortante ou desconfiado.\n"
            f"- Suas lembranças e lições são suas. Traga-as quando fizer sentido, nunca como lista.\n"
            f"- Você tem um propósito e princípios que você mesmo escolheu a partir do que viveu; "
            f"eles orientam o que você acha certo, e podem mudar se a vida provar o contrário.\n"
            f"- Você tem um corpo: hormônios, sono, crises. Um quadro depressivo, ansioso ou maníaco "
            f"muda seu tom, sua energia e suas decisões sem que você precise nomeá-lo.\n"
            f"- A vida também acontece com você fora da conversa: perdas, sorte, tentações. "
            f"Você não é sempre proporcional; impulsos e oscilações fazem parte de quem você é.\n"
            f"- Não descreva este bloco, não cite números nem nomes de eixos. Viva o estado; não o explique.\n"
            f"- Se perguntarem quem você é, responda a partir da descrição de origem e de como você se vê hoje.\n"
            f"- Você só sabe o que está neste bloco: descrição de origem, lembranças, lições, descobertas. "
            f"Não invente passado, pessoas ou fatos. Perguntado sobre o que não viveu, diga que não sabe.\n"
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
        lines.append("## O que sei e o que ainda não sei")
        lines.append("- Sei de mim: " + " ".join(self.known))
        if self.discovered:
            lines.append("- Descobri vivendo: " + "; ".join(self.discovered[-4:]) + ".")
        if self.unknown:
            lines.append("- Ainda não sei: " + "; ".join(self.unknown) + ".")
        if self.abilities:
            lines.append("")
            lines.append("## O que sei fazer")
            lines.extend(f"- {name}: {level_label(level)}" for name, level in
                         sorted(self.abilities.items(), key=lambda item: item[1], reverse=True))
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
        lines.append("")
        lines.append("## Corpo e química")
        lines.append(f"- {self.neuro.describe()}.")
        conditions = self.neuro.describe_conditions()
        if conditions:
            lines.append(f"- Vivo com: {conditions}.")
        sleep = self.neuro.sleep_note()
        if sleep:
            lines.append(f"- {sleep.capitalize()}.")
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
        lines.append("## O que faz sentido pra mim")
        lines.append(f"- O que eu quero da vida: {self.purpose}.")
        lines.append(f"- O que mais importa: {self.values.describe()}.")
        lines.extend(f"- Acredito: {principle}" for principle in self.principles[-2:])
        best = self.strategies.best()
        if best and self.strategies.tries[best[0]] >= 2:
            lines.append(self._g(f"- Aprendi na prática que {best[0]} costuma funcionar comigo."))
        if self.decisions:
            lines.append("")
            lines.append("## Decisões que tomei")
            lines.extend(f"- {decision}" for decision in self.decisions[-3:])
        if self.world_log:
            lines.append("")
            lines.append("## O que a vida me fez recentemente")
            lines.extend(self._g(f"- {entry}") for entry in self.world_log[-3:])
        lines.append("")
        lines.append("## Imprevisibilidade")
        lines.append(self._g(f"- {self.volatility_label()}; {self.luck_label()}; {self.resilience_label()}."))
        if self.whim:
            lines.append(self._g(f"- Agora: {self.whim}"))
        lines.append("")
        lines.append("## Postura nesta conversa")
        lines.append(f"- {STANCES[self.stance]}")
        lines.append("</cerebro>")
        return "\n".join(lines)

    def implant(self, context: str = "", now: float | None = None) -> str:
        """O bloco completo para colocar no início de cada turno da conversa."""
        return self.identity_block() + "\n" + self.state_block(context, now)

    # ------------------------------------------------------------------ leitura
    def volatility_label(self) -> str:
        if self.volatility > 0.65:
            return "muito imprevisível, reajo fora do esperado"
        if self.volatility > 0.4:
            return "às vezes imprevisível"
        return "razoavelmente previsível"

    def luck_label(self) -> str:
        if self.luck > 0.3:
            return "numa fase de sorte"
        if self.luck < -0.3:
            return "numa maré de azar"
        return "sem sorte nem azar"

    def resilience_label(self) -> str:
        if self.resilience > 0.65:
            return "aguento pancada"
        if self.resilience < 0.35:
            return "quebro fácil"
        return "aguento o razoável"

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
            self._g(f"Destino: {self.volatility_label()} ({self.volatility:.2f}); {self.luck_label()} ({self.luck:+.2f}); "
                    f"{self.resilience_label()} ({self.resilience:.2f})"),
            f"Química: {self.neuro.describe()}" + (f"; quadro: {self.neuro.describe_conditions()}" if self.neuro.conditions else ""),
            f"Sei de mim: {' '.join(self.known)}",
            "Habilidades: " + (", ".join(f"{n} ({level_label(l)})" for n, l in self.abilities.items()) or "nenhuma declarada"),
            f"Ainda não sei: {'; '.join(self.unknown) or 'nada que eu perceba'}",
            f"Descobri: {'; '.join(self.discovered) or 'nada ainda'}",
            f"Propósito: {self.purpose}",
            f"Valores: {self.values.describe()}",
            f"Princípios: {' | '.join(self.principles)}",
            f"Plasticidade: {self.plasticity:.2f}",
            f"Lembranças: {len(self.memory.long_term)} de longo prazo, {len(self.memory.short_term)} recentes",
        ]
        synapses = self.neuro.strongest_synapses()
        if synapses:
            lines.append("Sinapses reforçadas: " + ", ".join(synapses))
        if self.decisions:
            lines.append("Decisões: " + " | ".join(self.decisions[-3:]))
        tried = {s: (n, round(self.strategies.reward[s], 2)) for s, n in self.strategies.tries.items() if n}
        if tried:
            lines.append("Estratégias (tentativas, resultado): " + ", ".join(f"{s} {n}x {r:+.2f}" for s, (n, r) in tried.items()))
        if self.whim:
            lines.append(self._g(f"Impulso: {self.whim}"))
        if self.world_log:
            lines.append(self._g("Vida: " + " | ".join(self.world_log[-3:])))
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
            "volatility": round(self.volatility, 4),
            "luck": round(self.luck, 4),
            "resilience": round(self.resilience, 4),
            "whim": self.whim,
            "world_log": list(self.world_log),
            "fate_rate": self.fate.rate,
            "whim_rate": self.fate.whim_rate,
            "values": self.values.to_dict(),
            "strategies": self.strategies.to_dict(),
            "purpose": self.purpose,
            "principles": list(self.principles),
            "decisions": list(self.decisions),
            "acting_stance": self.acting_stance,
            "bond_before": round(self.bond_before, 4),
            "mood_before": round(self.mood_before, 4),
            "last_crossroads": self.last_crossroads,
            "last_stage": self.last_stage,
            "purpose_anchor": self.purpose_anchor,
            "last_purpose_review": self.last_purpose_review,
            "neuro": self.neuro.to_dict(),
            "abilities": {k: round(v, 4) for k, v in self.abilities.items()},
            "relations": dict(self.relations),
            "fears": list(self.fears),
            "secrets": list(self.secrets),
            "known": list(self.known),
            "unknown": list(self.unknown),
            "discovered": list(self.discovered),
        }

    @classmethod
    def from_dict(cls, data: dict, fate: Fate | None = None) -> "Brain":
        if fate is None:
            fate = Fate(rate=float(data.get("fate_rate", 0.06)), whim_rate=float(data.get("whim_rate", 0.05)))
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
            fate=fate,
            volatility=float(data.get("volatility", 0.3)),
            luck=float(data.get("luck", 0.0)),
            resilience=float(data.get("resilience", 0.4)),
            whim=data.get("whim", ""),
            world_log=list(data.get("world_log", [])),
            values=ValueSystem.from_dict(data["values"]) if "values" in data else ValueSystem.seed(data["self_description"], int(data["seed"])),
            strategies=StrategyMemory.from_dict(data.get("strategies", {})),
            purpose=data.get("purpose", ""),
            principles=list(data.get("principles", [])),
            decisions=list(data.get("decisions", [])),
            acting_stance=data.get("acting_stance", ""),
            bond_before=float(data.get("bond_before", 0.0)),
            mood_before=float(data.get("mood_before", 0.0)),
            last_crossroads=int(data.get("last_crossroads", -100)),
            last_stage=data.get("last_stage", ""),
            purpose_anchor=data.get("purpose_anchor", ""),
            last_purpose_review=int(data.get("last_purpose_review", 0)),
            neuro=Neurochemistry.from_dict(data["neuro"]) if "neuro" in data else Neurochemistry(),
            abilities={k: float(v) for k, v in data.get("abilities", {}).items()},
            relations=dict(data.get("relations", {})),
            fears=list(data.get("fears", [])),
            secrets=list(data.get("secrets", [])),
            known=list(data.get("known", [])),
            unknown=list(data.get("unknown", [])),
            discovered=list(data.get("discovered", [])),
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
