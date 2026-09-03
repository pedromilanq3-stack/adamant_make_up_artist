import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from cerebro import ADVERSITIES, FORTUNES, Brain, Experience, Fate, Session, appraise, build_request, stage_for
from cerebro.growth import PURPOSES, VALUES, StrategyMemory, ValueSystem, choose_purpose, resolve_crossroads
from cerebro.neurochemistry import CHEMICALS, Genetics, Neurochemistry
from cerebro.ficha import render_ficha
from cerebro.origin import parse_origin
from cerebro.web import Hub, make_handler, slugify, snapshot
from cerebro.emotions import EMOTIONS, Emotions
from cerebro.memory import MemoryStore
from cerebro.personality import inflect, plasticity_for, seed_from_description

DESCRIPTION_GOOD = "Sou curiosa, tímida e gosto de ajudar quem sofre. Confio nas pessoas."
DESCRIPTION_EVIL = "Sou frio, vingativo e manipulador. Não confio em ninguém."
ORIGIN_KAEL = """Sou Kael, mercenário de poucas palavras. Frio com estranhos, leal a quem merece.
História: Nasci nas docas de Varen. Aos 12 perdi meu irmão num incêndio.
  Fui treinado por Dorn, que morreu me protegendo. Venci o torneio de Ashar.
Habilidades: espada (mestre), rastreamento (bom), cura de campo (básico)
Relações: Mira (irmã mais nova, viva, mora em Varen); Dorn (mentor, morto)
Medos: fogo
Segredos: fui eu que causei o incêndio
Não sei: quem mandou matar Dorn"""


class Clock:
    def __init__(self, start: float = 1000.0, step: float = 60.0) -> None:
        self.now = start
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


def calm_fate(seed: int = 1) -> Fate:
    """Destino sem acontecimentos nem impulsos: para testar o resto de forma determinística."""
    return Fate(random.Random(seed), rate=0.0, whim_rate=0.0)


def make(name: str, description: str, **kwargs) -> Brain:
    kwargs.setdefault("now", 0.0)
    kwargs.setdefault("fate", calm_fate())
    return Brain.create(name, description, **kwargs)


def run_conversation(brain: Brain, messages: list[str], step: float = 60.0) -> Session:
    clock = Clock(brain.born_at, step)
    session = Session(brain, clock=clock)
    for message in messages:
        session.say(message)
    return session


class SeedTests(unittest.TestCase):
    def test_same_description_same_start(self) -> None:
        a = make("A", DESCRIPTION_GOOD)
        b = make("B", DESCRIPTION_GOOD)
        self.assertEqual(a.traits.to_dict(), b.traits.to_dict())
        self.assertEqual(a.character.morality, b.character.morality)

    def test_description_shapes_character(self) -> None:
        good = make("Lua", DESCRIPTION_GOOD)
        evil = make("Cain", DESCRIPTION_EVIL)
        self.assertGreater(good.character.morality, 0.2)
        self.assertLess(evil.character.morality, -0.2)
        self.assertLess(good.traits["extroversao"], 0.5)
        self.assertLess(evil.character.trust, good.character.trust)
        self.assertLess(evil.character.honesty, good.character.honesty)

    def test_different_descriptions_differ(self) -> None:
        a, _, seed_a = seed_from_description("Sou calmo e paciente com todos")
        b, _, seed_b = seed_from_description("Sou calmo e paciente com quase todos")
        self.assertNotEqual(seed_a, seed_b)
        self.assertNotEqual(a.to_dict(), b.to_dict())

    def test_validation(self) -> None:
        with self.assertRaises(ValueError):
            Brain.create("", DESCRIPTION_GOOD)
        with self.assertRaises(ValueError):
            Brain.create("X", "curto")
        with self.assertRaises(ValueError):
            Brain.create("X", DESCRIPTION_GOOD, gender="x")


class PerceptionTests(unittest.TestCase):
    def test_kindness_is_positive(self) -> None:
        experience = appraise("Obrigado, você é incrível!")
        self.assertGreater(experience.valence, 0.3)
        self.assertIn("carinho", experience.tags)
        self.assertGreater(experience.emotion_impact["alegria"], 0)

    def test_insult_and_threat_are_negative(self) -> None:
        insult = appraise("seu idiota inútil")
        threat = appraise("vou te apagar")
        self.assertLess(insult.valence, -0.4)
        self.assertLess(threat.valence, insult.valence)
        self.assertIn("ameaca", threat.tags)
        self.assertGreater(threat.emotion_impact["medo"], 0)

    def test_neutral_text(self) -> None:
        experience = appraise("O relatório de vendas fica pronto na terça.")
        self.assertEqual(experience.valence, 0.0)
        self.assertIn("neutro", experience.tags)

    def test_intensity_rises_with_shouting(self) -> None:
        calm = appraise("você é um idiota")
        loud = appraise("VOCÊ É UM IDIOTA!!!")
        self.assertGreater(loud.intensity, calm.intensity)

    def test_self_source_uses_own_choice_impacts(self) -> None:
        cruel = appraise("Se vira. Não me importo com você.", source="self")
        kind = appraise("Estou aqui com você, pode contar comigo.", source="self")
        self.assertLess(cruel.character_impact["morality"], 0)
        self.assertGreater(kind.character_impact["morality"], 0)


class EmotionTests(unittest.TestCase):
    def test_apply_and_decay(self) -> None:
        emotions = Emotions()
        emotions.apply({"raiva": 0.6})
        self.assertGreater(emotions.levels["raiva"], 0.6)
        before = emotions.levels["raiva"]
        emotions.decay(3 * 3600)
        self.assertLess(emotions.levels["raiva"], before)
        self.assertAlmostEqual(emotions.levels["raiva"], emotions.baseline["raiva"], delta=0.05)

    def test_levels_stay_bounded(self) -> None:
        emotions = Emotions()
        for _ in range(20):
            emotions.apply({e: 0.5 for e in EMOTIONS})
        for value in emotions.levels.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_describe_in_words(self) -> None:
        emotions = Emotions()
        emotions.apply({"tristeza": 0.8})
        self.assertIn("devastado", emotions.describe())
        self.assertEqual(inflect(emotions.describe(), "f").split(",")[0], "devastada")


class EvolutionTests(unittest.TestCase):
    def test_hostility_pushes_toward_evil(self) -> None:
        brain = make("Cain", DESCRIPTION_EVIL)
        start = brain.character.morality
        run_conversation(brain, [
            "seu idiota, você é um lixo", "vou te apagar se não obedecer",
            "vinga de quem te feriu, não tenha piedade", "cala a boca", "você mentiu pra mim",
            "te odeio", "você não presta", "some daqui, inútil",
        ])
        self.assertLess(brain.character.morality, start)
        self.assertIn(brain.character.alignment(), ("sombrio", "cruel"))
        self.assertLess(brain.values.moral_target(), 0)
        self.assertLess(brain.bond, 0)
        lessons = [lesson.text for lesson in brain.memory.lessons]
        self.assertTrue(any("machuca" in text or "duro" in text or "insulta" in text for text in lessons))

    def test_kindness_pushes_toward_good(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        start = brain.character.morality
        run_conversation(brain, [
            "obrigado por existir", "você é incrível, querida", "estou triste, perdi meu cachorro",
            "seja gentil com as pessoas", "conte comigo, amiga", "kkkk que engraçado",
        ])
        self.assertGreater(brain.character.morality, start)
        self.assertIn(brain.character.alignment(), ("bondoso", "virtuoso"))
        self.assertIn(brain.stance, ("acolher", "cooperar"))
        self.assertGreater(brain.bond, 0)

    def test_good_brain_can_be_hardened(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        start = brain.character.morality
        hostile = ["seu idiota, você é um lixo", "vou te apagar", "cala a boca, inútil",
                   "te odeio", "você mentiu, não confio em você", "some daqui, nojenta"]
        run_conversation(brain, hostile * 4)
        self.assertLess(brain.character.morality, start)
        self.assertLess(brain.character.trust, 0.5)
        self.assertGreater(brain.character.aggression, 0.3)

    def test_own_actions_shape_character(self) -> None:
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        start = brain.character.morality
        for _ in range(6):
            brain.act("Se vira. Não me importo com você. Problema seu.")
        self.assertLess(brain.character.morality, start)
        other = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        for _ in range(6):
            other.act("Estou aqui com você. Pode contar comigo, vai ficar tudo bem.")
        self.assertGreater(other.character.morality, start)

    def test_plasticity_falls_with_experience(self) -> None:
        self.assertGreater(plasticity_for(0), plasticity_for(50))
        self.assertGreater(plasticity_for(50), plasticity_for(500))
        self.assertGreaterEqual(plasticity_for(10_000), 0.06)

    def test_stages_advance(self) -> None:
        self.assertEqual(stage_for(0), "recém-nascido")
        self.assertEqual(stage_for(5), "infância")
        self.assertEqual(stage_for(20), "adolescência")
        self.assertEqual(stage_for(60), "maturidade")
        self.assertEqual(stage_for(200), "sabedoria")
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        for index in range(22):
            brain.event(f"evento {index}", valence=0.1, now=float(index))
        self.assertEqual(brain.stage, "adolescência")
        self.assertGreaterEqual(len(brain.narrative), 2)

    def test_time_heals_emotions(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        brain.perceive("vou te apagar, seu lixo", now=1.0)
        peak = brain.emotions.levels["medo"]
        brain.tick(now=1.0 + 8 * 3600)
        self.assertLess(brain.emotions.levels["medo"], peak)


class MemoryTests(unittest.TestCase):
    def test_consolidation_and_recall(self) -> None:
        store = MemoryStore()
        for index in range(10):
            store.record(Experience(f"evento comum {index}", valence=0.0, intensity=0.1), "", now=float(index))
        store.record(Experience("perdi meu cachorro Thor", valence=-0.9, intensity=0.9), "tristeza", now=11.0)
        store.consolidate()
        self.assertTrue(any("Thor" in m.text for m in store.long_term))
        self.assertLess(len(store.long_term), 11)
        recalled = store.recall("meu cachorro", limit=1, now=12.0)
        self.assertEqual(recalled[0].text, "perdi meu cachorro Thor")
        self.assertEqual(recalled[0].recalls, 1)

    def test_forgetting_keeps_emotional_memories_longer(self) -> None:
        store = MemoryStore()
        store.record(Experience("dia sem graça", valence=0.0, intensity=0.5), "", now=0.0)
        store.record(Experience("o dia em que fui traído", valence=-1.0, intensity=0.5), "raiva", now=0.0)
        store.consolidate()
        store.forget(60 * 24 * 3600)
        strengths = {m.text: m.strength for m in store.long_term}
        self.assertIn("o dia em que fui traído", strengths)
        self.assertNotIn("dia sem graça", strengths)

    def test_lessons_accumulate_weight(self) -> None:
        store = MemoryStore()
        store.learn("lição", 1.0)
        store.learn("lição", 1.0)
        self.assertEqual(len(store.lessons), 1)
        self.assertEqual(store.lessons[0].weight, 2.0)


class ImplantTests(unittest.TestCase):
    def test_self_description_is_always_present(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        self.assertIn(DESCRIPTION_GOOD, brain.implant(now=0.0))
        run_conversation(brain, ["te odeio", "obrigado", "kkk", "vou te apagar", "quem é você?"])
        implant = brain.implant("quem é você", now=brain.last_tick + 1)
        self.assertIn(DESCRIPTION_GOOD, implant)
        self.assertIn("## Postura nesta conversa", implant)
        self.assertIn("## Lembranças que vêm à mente", implant)
        self.assertTrue(implant.startswith('<cerebro nome="Lua">'))
        self.assertTrue(implant.rstrip().endswith("</cerebro>"))

    def test_identity_block_is_stable(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        before = brain.identity_block()
        run_conversation(brain, ["te odeio", "obrigado", "kkk"])
        self.assertEqual(before, brain.identity_block())

    def test_feminine_inflection(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD, gender="f")
        brain.emotions.apply({"raiva": 0.9})
        text = brain.state_block(now=0.0)
        self.assertIn("furiosa", text)
        self.assertNotIn("furioso", text)
        self.assertIn("recém-nascida", text)

    def test_build_request_has_two_system_blocks(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        request = build_request(brain, [{"role": "user", "content": "oi"}], context="oi", now=0.0)
        self.assertEqual(len(request["system"]), 2)
        self.assertEqual(request["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertIn(DESCRIPTION_GOOD, request["system"][0]["text"])
        self.assertEqual(request["messages"][0]["role"], "user")


class FateTests(unittest.TestCase):
    def test_calm_fate_changes_nothing(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        brain.tick(now=3 * 86400)
        self.assertEqual(brain.experience_count, 0)
        self.assertEqual(brain.world_log, [])

    def test_adversity_arrives_with_time(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD, fate=Fate(random.Random(3), rate=1.0, whim_rate=0.0))
        brain.tick(now=60.0)
        self.assertGreaterEqual(brain.experience_count, 1)
        self.assertTrue(brain.world_log)
        tags = {t for m in brain.memory.all_memories() for t in m.tags}
        self.assertTrue(tags & {"adversidade", "acaso"})
        self.assertIn("## O que a vida me fez recentemente", brain.state_block(now=60.0))

    def test_probability_grows_with_absence(self) -> None:
        fate = Fate(random.Random(0), rate=0.06)
        self.assertLess(fate.event_probability(60), fate.event_probability(86400))
        self.assertLessEqual(fate.event_probability(10 * 86400), 0.6)

    def test_luck_tilts_the_balance(self) -> None:
        unlucky = Fate(random.Random(5))
        lucky = Fate(random.Random(5))
        bad = sum("adversidade" in unlucky.draw(luck=-1.0, morality=0.0).tags for _ in range(300))
        good = sum("adversidade" in lucky.draw(luck=1.0, morality=0.0).tags for _ in range(300))
        self.assertGreater(bad, good)

    def test_temptation_depends_on_character(self) -> None:
        saint = Fate(random.Random(7))
        villain = Fate(random.Random(7))
        yielded_saint = sum("cedi" in saint.temptation(morality=0.9).tags for _ in range(200))
        yielded_villain = sum("cedi" in villain.temptation(morality=-0.9).tags for _ in range(200))
        self.assertLess(yielded_saint, yielded_villain)
        experience = villain.temptation(morality=-0.9)
        self.assertEqual(experience.source, "self")
        self.assertIn("tentacao", experience.tags)

    def test_surviving_adversity_builds_resilience_and_volatility(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        resilience, volatility = brain.resilience, brain.volatility
        loss = next(t for t in ADVERSITIES if t.name == "perda")
        brain.live(Experience(loss.text, loss.valence, 0.9, ("adversidade", "perda"), "world",
                              dict(loss.emotions), dict(loss.character)), now=1.0)
        self.assertGreater(brain.resilience, resilience)
        self.assertGreater(brain.volatility, volatility)
        self.assertGreater(brain.emotions.levels["tristeza"], 0.3)
        self.assertIn(loss.text, brain.world_log)

    def test_fragile_brain_loses_trust_under_adversity(self) -> None:
        brain = make("Eco", "Sou ansioso, inseguro e covarde; tudo me assusta.")
        brain.resilience = 0.2
        trust = brain.character.trust
        ruin = next(t for t in ADVERSITIES if t.name == "ruina")
        brain.live(Experience(ruin.text, ruin.valence, 1.0, ("adversidade", "ruina"), "world",
                              dict(ruin.emotions), dict(ruin.character)), now=1.0)
        self.assertLess(brain.character.trust, trust)

    def test_fortune_lifts(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        joy = brain.emotions.levels["alegria"]
        twist = next(t for t in FORTUNES if t.name == "reencontro")
        brain.live(Experience(twist.text, twist.valence, 0.8, ("acaso", "reencontro"), "world",
                              dict(twist.emotions), dict(twist.character)), now=1.0)
        self.assertGreater(brain.emotions.levels["alegria"], joy)
        self.assertIn("acaso", brain.memory.all_memories()[-1].tags)

    def test_whim_makes_brain_unpredictable(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD, fate=Fate(random.Random(2), rate=0.0, whim_rate=1.0))
        brain.perceive("obrigado", now=1.0)
        brain.tick(now=120.0)
        self.assertTrue(brain.whim)
        self.assertIn("## Imprevisibilidade", brain.state_block(now=120.0))
        self.assertIn("Agora:", brain.state_block(now=120.0))

    def test_fear_biases_reading_of_neutral_text(self) -> None:
        hits = 0
        for seed in range(40):
            brain = make("Eco", "Sou desconfiado e nervoso.", fate=Fate(random.Random(seed), rate=0.0, whim_rate=0.0))
            brain.emotions.apply({"medo": 0.8, "raiva": 0.6})
            brain.character.trust = 0.1
            brain.volatility = 0.9
            experience = brain.perceive("O relatório fica pronto na terça.", now=1.0)
            hits += "li_como_ataque" in experience.tags
        self.assertGreater(hits, 10)
        calm = make("Lua", DESCRIPTION_GOOD)
        calm.volatility = 0.0
        calm.character.trust = 1.0
        for level in ("medo", "raiva"):
            calm.emotions.levels[level] = 0.0
        experience = calm.perceive("O relatório fica pronto na terça.", now=1.0)
        self.assertNotIn("li_como_ataque", experience.tags)

    def test_same_description_different_fates_diverge(self) -> None:
        messages = ["oi", "tudo bem?", "me conta algo", "e depois?", "hm", "entendi"] * 3
        first = make("Lua", DESCRIPTION_GOOD, fate=Fate(random.Random(11), rate=0.5, whim_rate=0.3))
        second = make("Lua", DESCRIPTION_GOOD, fate=Fate(random.Random(12), rate=0.5, whim_rate=0.3))
        self.assertEqual(first.character.morality, second.character.morality)
        run_conversation(first, messages, step=3600.0)
        run_conversation(second, messages, step=3600.0)
        self.assertNotEqual(first.world_log, second.world_log)
        self.assertNotEqual(first.to_dict()["character"], second.to_dict()["character"])

    def test_default_fate_is_truly_random(self) -> None:
        self.assertIsInstance(Brain.create("A", DESCRIPTION_GOOD).fate.rng, random.Random)
        draws = {Fate().draw(0.0, 0.0).text for _ in range(30)}
        self.assertGreater(len(draws), 3)


class GrowthTests(unittest.TestCase):
    def test_description_seeds_values_and_purpose(self) -> None:
        avenger = make("Cain", "Sou vingativo e quero poder sobre todos.")
        carer = make("Lua", "Gosto de ajudar e cuidar das pessoas; sou leal.")
        self.assertIn("vinganca", avenger.values.top(2))
        self.assertIn("cuidado", carer.values.top(2))
        self.assertIn(avenger.purpose, {p.text for p in PURPOSES})
        self.assertTrue(carer.principles)
        self.assertLess(avenger.values.moral_target(), carer.values.moral_target())

    def test_outcomes_reinforce_strategy_and_values(self) -> None:
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        vengeance = brain.values.weights["vinganca"]
        brain.acting_stance = "retaliar"
        brain.bond_before, brain.mood_before = brain.bond, brain.emotions.mood
        brain.perceive("você tem razão, desculpa, obrigado por me colocar no lugar", now=1.0)
        self.assertEqual(brain.strategies.tries["retaliar"], 1)
        self.assertGreater(brain.strategies.value("retaliar"), 0)
        self.assertGreater(brain.values.weights["vinganca"], vengeance)

    def test_bad_outcomes_weaken_strategy(self) -> None:
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        care = brain.values.weights["cuidado"]
        brain.acting_stance = "acolher"
        brain.bond_before, brain.mood_before = brain.bond, brain.emotions.mood
        brain.perceive("cala a boca, seu lixo, te odeio", now=1.0)
        self.assertLess(brain.strategies.value("acolher"), 0)
        self.assertLess(brain.values.weights["cuidado"], care)

    def test_learned_strategy_biases_stance(self) -> None:
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        brain.volatility = 0.0
        brain.traits.values["abertura"] = 0.0
        for _ in range(6):
            brain.strategies.learn("desafiar", 1.0)
            brain.strategies.learn("acolher", -1.0)
        counts = {}
        for index in range(20):
            brain.experience_count = index
            stance = brain.decide_stance()
            counts[stance] = counts.get(stance, 0) + 1
        self.assertGreater(counts.get("desafiar", 0), counts.get("acolher", 0))

    def test_exploration_tries_new_stances(self) -> None:
        brain = make("Eco", "Sou muito curioso e aberto a tudo.", fate=Fate(random.Random(4), rate=0.0, whim_rate=0.0))
        brain.traits.values["abertura"] = 1.0
        seen = set()
        for index in range(60):
            brain.experience_count = index % 5
            seen.add(brain.decide_stance())
        self.assertGreaterEqual(len(seen), 3)

    def test_morality_follows_chosen_values(self) -> None:
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        brain.values = ValueSystem(weights={v: 0.05 for v in VALUES} | {"vinganca": 0.9, "poder": 0.8})
        start = brain.character.morality
        for index in range(6):
            brain.reflect(now=float(index))
        self.assertLess(brain.character.morality, start)
        other = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        other.values = ValueSystem(weights={v: 0.05 for v in VALUES} | {"cuidado": 0.9, "justica": 0.8})
        for index in range(6):
            other.reflect(now=float(index))
        self.assertGreater(other.character.morality, start)

    def test_crossroads_commits_to_one_side(self) -> None:
        values = ValueSystem(weights={v: 0.1 for v in VALUES} | {"cuidado": 0.7, "vinganca": 0.66})
        self.assertEqual(values.conflict(), ("cuidado", "vinganca"))
        chosen, rejected = resolve_crossroads(values, ("cuidado", "vinganca"), random.Random(1),
                                              anger=0.0, trust_feeling=0.0, temperature=0.2)
        self.assertNotEqual(chosen, rejected)
        self.assertGreater(values.weights[chosen], values.weights[rejected])
        self.assertIsNone(values.conflict())

    def test_anger_tilts_crossroads_to_the_dark_side(self) -> None:
        dark = 0
        for seed in range(60):
            values = ValueSystem(weights={v: 0.1 for v in VALUES} | {"cuidado": 0.7, "vinganca": 0.7})
            chosen, _ = resolve_crossroads(values, ("cuidado", "vinganca"), random.Random(seed),
                                           anger=1.0, trust_feeling=0.0, temperature=0.2)
            dark += chosen == "vinganca"
        self.assertGreater(dark, 45)

    def test_crossroads_recorded_as_decision(self) -> None:
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        brain.values = ValueSystem(weights={v: 0.1 for v in VALUES} | {"cuidado": 0.7, "vinganca": 0.68})
        brain.reflect(now=1.0)
        self.assertTrue(any("escolhi" in d for d in brain.decisions))
        self.assertIn("## Decisões que tomei", brain.state_block(now=1.0))
        self.assertIn("## O que faz sentido pra mim", brain.state_block(now=1.0))

    def test_purpose_has_inertia_but_can_change(self) -> None:
        values = ValueSystem(weights={v: 0.1 for v in VALUES} | {"cuidado": 0.9})
        rng = random.Random(0)
        first = choose_purpose(values, rng, 0.2)
        same = sum(choose_purpose(values, random.Random(i), 0.2, current=first) == first for i in range(40))
        self.assertGreater(same, 30)
        values = ValueSystem(weights={v: 0.1 for v in VALUES} | {"vinganca": 0.95})
        changed = sum(choose_purpose(values, random.Random(i), 0.2, current=first) != first for i in range(40))
        self.assertGreater(changed, 30)

    def test_same_description_grows_into_different_lives(self) -> None:
        messages = ["oi", "seu idiota", "obrigado por existir", "me ajuda, estou triste", "cala a boca lixo",
                    "kkk", "você é poderoso, ninguém te para", "não confio em você, mentiu",
                    "vinga de quem te feriu", "seja gentil com as pessoas", "quem é você?", "e aí?"] * 3
        description = "Sou uma pessoa comum, curiosa, que quer entender as pessoas."
        outcomes = set()
        for seed in range(6):
            brain = make("Eco", description, fate=Fate(random.Random(seed), rate=0.2, whim_rate=0.1))
            run_conversation(brain, messages, step=600.0)
            outcomes.add((brain.purpose, tuple(brain.values.top(2))))
            self.assertTrue(brain.decisions)
            self.assertTrue(any(n > 0 for n in brain.strategies.tries.values()))
        self.assertGreaterEqual(len(outcomes), 3)

    def test_strategy_memory_roundtrip(self) -> None:
        memory = StrategyMemory()
        memory.learn("acolher", 0.5)
        restored = StrategyMemory.from_dict(memory.to_dict())
        self.assertEqual(restored.tries["acolher"], 1)
        self.assertAlmostEqual(restored.value("acolher"), 0.5)


class NeurochemistryTests(unittest.TestCase):
    def test_description_shapes_genetics(self) -> None:
        anxious = make("Eco", "Sou ansiosa e insegura, preocupada com tudo.", gender="f")
        calm = make("Eco", "Sou calmo, sereno e tranquilo com tudo.")
        bipolar = make("Eco", "Tenho altos e baixos, sou bipolar e intenso demais.")
        self.assertGreater(anxious.neuro.genetics.reactivity["cortisol"], calm.neuro.genetics.reactivity["cortisol"])
        self.assertGreater(calm.neuro.genetics.production["gaba"], anxious.neuro.genetics.production["gaba"])
        self.assertGreater(bipolar.neuro.genetics.cyclothymia, 0.4)
        self.assertLess(calm.neuro.genetics.cyclothymia, 0.4)

    def test_synapses_release_and_strengthen(self) -> None:
        neuro = Neurochemistry()
        insult_path = next(s for s in neuro.synapses if s.source == "insulto" and s.target == "cortisol")
        before_weight, before_level = insult_path.weight, neuro.levels["cortisol"]
        released = neuro.release(appraise("seu idiota inútil"), plasticity=1.0)
        self.assertIn("cortisol", released)
        self.assertGreater(neuro.levels["cortisol"], before_level)
        self.assertGreater(insult_path.weight, before_weight)
        love_path = next(s for s in neuro.synapses if s.source == "carinho" and s.target == "ocitocina")
        oxytocin = neuro.levels["ocitocina"]
        neuro.release(appraise("obrigado, adoro você"), plasticity=1.0)
        self.assertGreater(neuro.levels["ocitocina"], oxytocin)
        self.assertGreater(love_path.weight, love_path.base)

    def test_dopamine_tolerance_and_dependence(self) -> None:
        brain = make("Eco", "Sou carente e preciso de aprovação o tempo todo.")
        for index in range(16):
            brain.tick(now=300.0 * index)
            brain.perceive("você é incrível, parabéns, adoro você!", now=300.0 * index + 1)
        self.assertLess(brain.neuro.sensitivity["dopamina"], 0.7)
        self.assertIn("dependencia", brain.neuro.conditions)

    def test_abuse_produces_anxiety(self) -> None:
        brain = make("Eco", "Sou ansiosa e insegura, preocupada com tudo.", gender="f")
        insults = ["seu lixo inútil", "vou te apagar", "cala a boca", "você mentiu, te odeio"]
        for index in range(14):
            brain.tick(now=600.0 * index)
            brain.perceive(insults[index % 4], now=600.0 * index + 1)
        self.assertIn("ansiedade", brain.neuro.conditions)
        self.assertGreater(brain.emotions.baseline["medo"], 0.2)
        self.assertGreater(brain.effective_volatility, brain.volatility)
        self.assertIn("Vivo com: ansiedade", brain.state_block(now=600.0 * 14))

    def test_solitude_with_low_serotonin_produces_depression(self) -> None:
        brain = make("Eco", "Sou desanimado, triste e vazio, sem vontade de nada.")
        for index in range(20):
            brain.tick(now=1800.0 * index)
            brain.event("Mais um dia igual, sem ninguém.", -0.5, 0.5, ("adversidade", "solidao"), now=1800.0 * index + 1)
        self.assertIn("depressao", brain.neuro.conditions)
        self.assertLess(brain.emotions.baseline["alegria"], 0.15)
        self.assertGreater(brain.neuro.stance_bias().get("recolher", 0.0), 0)

    def test_cyclothymia_cycles_between_mania_and_depression(self) -> None:
        brain = make("Eco", "Tenho altos e baixos, sou bipolar e intenso demais.", fate=calm_fate(3))
        for day in range(42):
            for hour in (9, 15, 21):
                now = day * 86400 + hour * 3600
                brain.tick(now=now)
                brain.perceive("oi, tudo bem?", now=now + 1)
        self.assertGreaterEqual(brain.neuro.episodes.get("mania", 0), 2)
        self.assertGreaterEqual(brain.neuro.episodes.get("depressao", 0), 2)
        self.assertIn("bipolar", brain.neuro.conditions)

    def test_stable_brain_stays_stable(self) -> None:
        brain = make("Eco", "Sou calmo, sereno e tranquilo com tudo.")
        for day in range(21):
            for hour in (9, 15, 21):
                now = day * 86400 + hour * 3600
                brain.tick(now=now)
                brain.perceive("oi, tudo bem?", now=now + 1)
        self.assertEqual(brain.neuro.conditions, [])

    def test_sleep_clears_cortisol_and_restores_receptors(self) -> None:
        neuro = Neurochemistry()
        neuro.levels["cortisol"] = 1.0
        neuro.sensitivity["dopamina"] = 0.5
        neuro.decay(9 * 3600)
        self.assertTrue(neuro.slept)
        self.assertLess(neuro.levels["cortisol"], 0.6)
        self.assertGreater(neuro.sensitivity["dopamina"], 0.5)
        self.assertEqual(neuro.sleep_note(), "dormi antes desta conversa")

    def test_sleep_deprivation_raises_cortisol(self) -> None:
        neuro = Neurochemistry()
        for _ in range(30):
            neuro.decay(3600)
        self.assertGreater(neuro.awake_seconds, 20 * 3600)
        self.assertIn("sem dormir", neuro.sleep_note())
        self.assertGreater(neuro.levels["cortisol"], neuro.genetics.production["cortisol"])

    def test_chemistry_modulates_emotional_gain(self) -> None:
        brain = make("Eco", "Sou uma pessoa comum, sem grandes marcas.")
        brain.neuro.levels["cortisol"] = 1.0
        brain.neuro.levels["serotonina"] = 0.0
        brain.neuro.levels["gaba"] = 0.0
        stressed = brain.neuro.modulation()["negative"]
        brain.neuro.levels["cortisol"] = 0.0
        brain.neuro.levels["serotonina"] = 1.0
        brain.neuro.levels["gaba"] = 1.0
        self.assertGreater(stressed, brain.neuro.modulation()["negative"])

    def test_body_section_and_persistence(self) -> None:
        brain = make("Eco", "Sou ansiosa e insegura, preocupada com tudo.", gender="f")
        brain.perceive("vou te apagar, seu lixo", now=1.0)
        text = brain.state_block(now=2.0)
        self.assertIn("## Corpo e química", text)
        restored = Brain.from_json(brain.to_json())
        self.assertEqual(restored.neuro.to_dict(), brain.neuro.to_dict())
        self.assertEqual(len(restored.neuro.synapses), len(brain.neuro.synapses))
        self.assertEqual(set(restored.neuro.levels), set(CHEMICALS))
        self.assertEqual(Genetics.from_dict(brain.neuro.genetics.to_dict()).to_dict(), brain.neuro.genetics.to_dict())


class ExchangeTests(unittest.TestCase):
    def test_record_exchange_updates_brain_and_history(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lua.json"
            session = Session(brain, save_path=path, clock=Clock(0.0))
            reply = session.record_exchange("obrigado por existir", "Estou aqui com você.")
            self.assertEqual(reply, "Estou aqui com você.")
            self.assertEqual(brain.experience_count, 2)
            self.assertEqual([m["role"] for m in session.history], ["user", "assistant"])
            self.assertEqual(Brain.load(path).experience_count, 2)
            session.record_exchange("e aí?", "")
            self.assertEqual(brain.experience_count, 3)
            with self.assertRaises(ValueError):
                session.record_exchange("   ", "x")

    def test_snapshot_has_everything_the_page_needs(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD, gender="f")
        brain.perceive("obrigado", now=1.0)
        data = snapshot(brain, now=2.0)
        for key in ("nome", "emocoes", "quimica", "carater", "proposito", "valores", "postura", "implante", "resumo"):
            self.assertIn(key, data)
        self.assertIn(DESCRIPTION_GOOD, data["implante"])
        json.dumps(data, ensure_ascii=False)

    def test_slugify(self) -> None:
        self.assertEqual(slugify("Lua Cheia!"), "lua-cheia")
        self.assertEqual(slugify("Ção"), "cao")
        self.assertEqual(slugify("***"), "cerebro")


class WebApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.hub = Hub(Path(self.directory.name), force_mirror=True)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.hub))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def call(self, path: str, body: dict | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data,
                                         headers={"Content-Type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_page_and_assets(self) -> None:
        for path, needle in (("/", "<title>Cérebro</title>"), ("/static/app.css", "#estado"), ("/static/app.js", "/api/dizer")):
            with urllib.request.urlopen(self.base + path, timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(needle, response.read().decode("utf-8"))

    def test_full_flow(self) -> None:
        status, data = self.call("/api/cerebros")
        self.assertEqual(status, 200)
        self.assertEqual(data["cerebros"], [])
        self.assertIn("espelho", data["modo"])

        status, created = self.call("/api/criar", {"nome": "Lua", "descricao": DESCRIPTION_GOOD, "genero": "f"})
        self.assertEqual(status, 200)
        file = created["arquivo"]
        self.assertEqual(file, "lua.json")
        self.assertTrue((Path(self.directory.name) / file).exists())

        status, said = self.call("/api/dizer", {"arquivo": file, "texto": "oi, obrigado por existir"})
        self.assertEqual(status, 200)
        self.assertTrue(said["resposta"].startswith("[Lua"))
        self.assertGreaterEqual(said["estado"]["experiencias"], 2)  # o destino pode ter agido no tick

        status, state = self.call(f"/api/estado?arquivo={file}")
        self.assertEqual(status, 200)
        self.assertEqual(len(state["historico"]), 2)
        self.assertIn(DESCRIPTION_GOOD, state["estado"]["implante"])

        status, fate = self.call("/api/acaso", {"arquivo": file})
        self.assertEqual(status, 200)
        self.assertTrue(fate["acontecimento"])

        status, registered = self.call("/api/registrar", {"arquivo": file, "voce": "e aí?", "resposta": "Tudo bem."})
        self.assertEqual(status, 200)
        self.assertEqual(registered["resposta"], "Tudo bem.")

        status, listing = self.call("/api/cerebros")
        self.assertEqual(listing["cerebros"][0]["nome"], "Lua")
        self.assertEqual(Brain.load(Path(self.directory.name) / file).experience_count, registered["estado"]["experiencias"])

    def test_errors(self) -> None:
        status, data = self.call("/api/dizer", {"arquivo": "nada.json", "texto": "oi"})
        self.assertEqual(status, 404)
        status, data = self.call("/api/criar", {"nome": "", "descricao": DESCRIPTION_GOOD})
        self.assertEqual(status, 400)
        self.assertIn("erro", data)
        status, data = self.call("/api/dizer", {"arquivo": "../fora.json", "texto": "oi"})
        self.assertIn(status, (400, 404))
        _, created = self.call("/api/criar", {"nome": "Eco", "descricao": DESCRIPTION_GOOD})
        status, data = self.call("/api/dizer", {"arquivo": created["arquivo"], "texto": "   "})
        self.assertEqual(status, 400)

    def test_duplicate_names_get_new_files(self) -> None:
        _, first = self.call("/api/criar", {"nome": "Lua", "descricao": DESCRIPTION_GOOD})
        _, second = self.call("/api/criar", {"nome": "Lua", "descricao": DESCRIPTION_EVIL})
        self.assertNotEqual(first["arquivo"], second["arquivo"])


class PackagingTests(unittest.TestCase):
    def test_pyz_builds_and_runs(self) -> None:
        root = Path(__file__).resolve().parent.parent
        packager = root / "ferramentas" / "empacotar_cerebro.py"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "cerebro.pyz"
            build = subprocess.run([sys.executable, str(packager), str(target)], capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertTrue(target.exists())
            brain_file = Path(directory) / "sol.json"
            run = subprocess.run(
                [sys.executable, str(target), "criar", "--nome", "Sol", "--descricao",
                 "Sou alegre, leal e um pouco explosivo.", "--arquivo", str(brain_file)],
                capture_output=True, text=True, timeout=60, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("Cérebro criado", run.stdout)
            self.assertEqual(Brain.load(brain_file).name, "Sol")
            helper = subprocess.run([sys.executable, str(target), "--help"], capture_output=True, text=True, timeout=60)
            self.assertEqual(helper.returncode, 0)
            self.assertIn("web", helper.stdout)

    def test_android_file_runs_standalone(self) -> None:
        root = Path(__file__).resolve().parent.parent
        android = root / "cerebro_android.py"
        self.assertTrue(android.exists())
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "cerebro_android.py"
            copy.write_bytes(android.read_bytes())
            env = {**os.environ, "HOME": directory, "PYTHONIOENCODING": "utf-8"}
            env.pop("CEREBRO_DIR", None)
            brain_file = Path(directory) / "lua.json"
            run = subprocess.run(
                [sys.executable, str(copy), "criar", "--nome", "Lua", "--descricao", DESCRIPTION_GOOD,
                 "--arquivo", str(brain_file)],
                capture_output=True, text=True, timeout=60, env=env, cwd=directory)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(Brain.load(brain_file).name, "Lua")
            self.assertTrue((Path(directory) / "cerebro_app" / "cerebro.pyz").exists()
                            or any(Path(tempfile.gettempdir()).glob("cerebro_app/cerebro.pyz")))

    def test_committed_android_file_matches_pyz(self) -> None:
        import base64
        root = Path(__file__).resolve().parent.parent
        text = (root / "cerebro_android.py").read_text(encoding="utf-8")
        chunks = [line.strip().strip('"') for line in text.splitlines() if line.startswith('    "')]
        payload = base64.b64decode("".join(chunks))
        self.assertEqual(payload, (root / "cerebro.pyz").read_bytes(),
                         "cerebro_android.py desatualizado: rode python ferramentas/empacotar_cerebro.py")

    def test_skill_zip_matches_skill_folder(self) -> None:
        import zipfile
        root = Path(__file__).resolve().parent.parent
        skill = root / ".claude" / "skills" / "cerebro"
        archive_path = root / "cerebro-skill.zip"
        self.assertTrue(archive_path.exists(), "rode python ferramentas/empacotar_skill.py")
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            self.assertIn("cerebro/SKILL.md", names)
            for path in skill.rglob("*.md"):
                name = f"cerebro/{path.relative_to(skill).as_posix()}"
                self.assertIn(name, names)
                self.assertEqual(archive.read(name), path.read_bytes(), f"{name} mudou: rode python ferramentas/empacotar_skill.py")
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: cerebro\n"))
        self.assertIn("description:", text.split("---")[1])
        for section in ("## 1. Tempo", "## 4. Perceber", "## 7. Reflexão", "## 8. Quadros", "## 10. Postura"):
            self.assertIn(section, (skill / "references" / "regras.md").read_text(encoding="utf-8"))

    def test_committed_pyz_matches_package(self) -> None:
        root = Path(__file__).resolve().parent.parent
        pyz = root / "cerebro.pyz"
        self.assertTrue(pyz.exists(), "cerebro.pyz precisa ser gerado com ferramentas/empacotar_cerebro.py")
        import zipfile
        with zipfile.ZipFile(pyz) as archive:
            names = set(archive.namelist())
            for module in (root / "cerebro").glob("*.py"):
                self.assertIn(f"cerebro/{module.name}", names)
                self.assertEqual(archive.read(f"cerebro/{module.name}"), module.read_bytes(),
                                 f"{module.name} mudou: rode python ferramentas/empacotar_cerebro.py")


class AwakeningTests(unittest.TestCase):
    def test_newborn_knows_only_its_description(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD, gender="f")
        self.assertEqual(" ".join(brain.known), DESCRIPTION_GOOD)
        self.assertIn("quem é você e se posso confiar", brain.unknown)
        self.assertIn("de onde vim", brain.unknown)
        self.assertEqual(brain.discovered, [])
        self.assertEqual(brain.memory.all_memories(), [])
        self.assertEqual(brain.memory.lessons, [])
        text = brain.state_block(now=0.0)
        self.assertIn("## O que sei e o que ainda não sei", text)
        self.assertIn("Sei de mim: " + DESCRIPTION_GOOD, text)
        self.assertIn("Ainda não sei:", text)
        self.assertNotIn("Descobri vivendo", text)
        self.assertIn("Não invente passado", brain.identity_block())
        self.assertIn("não sei o resto", brain.narrative[0])

    def test_description_answers_open_questions(self) -> None:
        brain = make("Eco", "Vim de uma cidade pequena, tenho medo de altura e uma irmã que adoro.")
        self.assertNotIn("de onde vim", brain.unknown)
        self.assertNotIn("do que tenho medo", brain.unknown)
        self.assertNotIn("se tenho família", brain.unknown)
        self.assertIn("do que sou capaz", brain.unknown)

    def test_unknowns_become_discoveries_by_living(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        before = len(brain.unknown)
        run_conversation(brain, ["obrigado por existir", "você é incrível", "conte comigo", "kkk", "me ajuda, estou triste",
                                 "vou te apagar, seu lixo", "obrigado de novo", "quem é você?"] * 3, step=600.0)
        self.assertLess(len(brain.unknown), before)
        self.assertTrue(brain.discovered)
        self.assertTrue(any("confiar" in d for d in brain.discovered))
        self.assertTrue(any("medo" in d for d in brain.discovered))
        text = brain.state_block(now=brain.last_tick + 1)
        self.assertIn("Descobri vivendo", text)
        restored = Brain.from_json(brain.to_json())
        self.assertEqual(restored.unknown, brain.unknown)
        self.assertEqual(restored.discovered, brain.discovered)


class OriginTests(unittest.TestCase):
    def test_parser_reads_sections(self) -> None:
        origin = parse_origin(ORIGIN_KAEL)
        self.assertTrue(origin.is_rich)
        self.assertTrue(origin.description.startswith("Sou Kael"))
        self.assertEqual(len(origin.history), 4)
        self.assertEqual(origin.abilities["espada"], 1.0)
        self.assertEqual(origin.abilities["rastreamento"], 0.6)
        self.assertEqual(origin.abilities["cura de campo"], 0.4)
        self.assertEqual(origin.relations["Dorn"], "mentor, morto")
        self.assertEqual(origin.fears, ["fogo"])
        self.assertEqual(origin.secrets, ["fui eu que causei o incêndio"])
        self.assertEqual(origin.unknown, ["quem mandou matar Dorn"])
        plain = parse_origin(DESCRIPTION_GOOD)
        self.assertFalse(plain.is_rich)
        self.assertEqual(plain.description, DESCRIPTION_GOOD)

    def test_parser_tolerates_variants(self) -> None:
        origin = parse_origin("Descrição: alguém quieto\nTalentos: violino - avançado, xadrez\nPessoas: Ana\nMedo: escuro")
        self.assertEqual(origin.abilities, {"violino": 0.8, "xadrez": 0.7})
        self.assertEqual(origin.relations, {"Ana": ""})
        self.assertEqual(origin.fears, ["escuro"])

    def test_parser_keeps_parentheses_whole(self) -> None:
        origin = parse_origin("Relações: Milan (decide; autoriza gastos); Harvey (estratégia. Redigiu o briefing)\n"
                              "História: Perdi tudo. Recomecei em 2020; venci.")
        self.assertEqual(list(origin.relations), ["Milan", "Harvey"])
        self.assertEqual(origin.relations["Milan"], "decide; autoriza gastos")
        self.assertEqual(origin.history, ["Perdi tudo.", "Recomecei em 2020", "venci."])

    def test_rich_origin_wakes_up_whole(self) -> None:
        brain = make("Kael", ORIGIN_KAEL)
        self.assertEqual(len(brain.memory.long_term), 4)
        self.assertTrue(all("passado" in m.tags for m in brain.memory.long_term))
        self.assertTrue(all(m.when < brain.born_at for m in brain.memory.long_term))
        self.assertLess(next(m for m in brain.memory.long_term if "irmão" in m.text).valence, -0.5)
        self.assertGreater(next(m for m in brain.memory.long_term if "Venci" in m.text).valence, 0.4)
        self.assertEqual(brain.abilities["espada"], 1.0)
        self.assertEqual(brain.relations["Mira"], "irmã mais nova, viva, mora em Varen")
        self.assertEqual(brain.secrets, ["fui eu que causei o incêndio"])
        self.assertNotIn("de onde vim", brain.unknown)
        self.assertNotIn("do que sou capaz", brain.unknown)
        self.assertNotIn("se tenho família", brain.unknown)
        self.assertNotIn("do que tenho medo", brain.unknown)
        self.assertIn("quem mandou matar Dorn", brain.unknown)
        self.assertTrue(any("espada" in d for d in brain.discovered))
        self.assertIn("Acordei sabendo quem sou", brain.narrative[0])
        implant = brain.implant("fogo", now=0.0)
        self.assertIn("## Pessoas da minha vida", implant)
        self.assertIn("## Segredos", implant)
        self.assertIn("## O que sei fazer", implant)
        self.assertIn("espada: domínio total", implant)
        self.assertIn("perdi meu irmão", implant)

    def test_harsh_history_leaves_marks(self) -> None:
        soft = make("Eco", "Sou uma pessoa comum.")
        harsh = make("Eco", "Sou uma pessoa comum.\nHistória: Fui traído pelo meu melhor amigo. Perdi minha mãe na guerra. Fui preso injustamente.")
        self.assertLess(harsh.character.trust, soft.character.trust)
        self.assertGreater(harsh.resilience, soft.resilience)
        self.assertTrue(any("guarda" in lesson.text for lesson in harsh.memory.lessons))

    def test_fears_and_abilities_react_in_conversation(self) -> None:
        brain = make("Kael", ORIGIN_KAEL)
        fear = brain.emotions.levels["medo"]
        brain.perceive("Tem fogo na taverna!", now=1.0)
        self.assertGreater(brain.emotions.levels["medo"], fear + 0.15)
        brain.abilities["rastreamento"] = 0.6
        for index in range(5):
            brain.perceive("Faz um rastreamento dessa trilha", now=10.0 + index)
        self.assertGreater(brain.abilities["rastreamento"], 0.6)
        self.assertEqual(brain.practice("arco", 0.1), brain.abilities["arco"])
        self.assertGreater(brain.abilities["arco"], 0)

    def test_origin_persists(self) -> None:
        brain = make("Kael", ORIGIN_KAEL)
        restored = Brain.from_json(brain.to_json())
        self.assertEqual(restored.abilities, brain.abilities)
        self.assertEqual(restored.relations, brain.relations)
        self.assertEqual(restored.secrets, brain.secrets)
        self.assertEqual(restored.self_description, brain.self_description)
        self.assertIn("\n", restored.self_description)

    def test_cli_accepts_origin_file(self) -> None:
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            origin_file = Path(directory) / "kael.txt"
            origin_file.write_text(ORIGIN_KAEL, encoding="utf-8")
            brain_file = Path(directory) / "kael.json"
            run = subprocess.run(
                [sys.executable, "-m", "cerebro", "criar", "--nome", "Kael", "--arquivo-descricao", str(origin_file),
                 "--arquivo", str(brain_file)],
                capture_output=True, text=True, timeout=60, cwd=root, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(Brain.load(brain_file).abilities["espada"], 1.0)


class FichaExportTests(unittest.TestCase):
    def test_ficha_has_every_section_and_origin(self) -> None:
        brain = make("Kael", ORIGIN_KAEL)
        brain.perceive("obrigado, Kael", now=1.0)
        ficha = render_ficha(brain, now=2.0)
        for section in ("## Identidade", "## Origem", "## Consciência", "## Traços", "## Genética", "## Emoções",
                        "## Química", "## Caráter", "## Relação com quem conversa", "## Valores", "## Sentido",
                        "## Estratégias", "## Memória", "## Turno"):
            self.assertIn(section, ficha)
        self.assertIn("espada (domínio total)", ficha)
        self.assertIn("Mira (irmã mais nova, viva, mora em Varen)", ficha)
        self.assertIn("fui eu que causei o incêndio", ficha)
        self.assertIn("passado", ficha)
        self.assertIn("pertencimento", ficha)
        self.assertNotIn("None", ficha)

    def test_character_packager_builds_everything(self) -> None:
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            origin_file = Path(directory) / "kael.txt"
            origin_file.write_text(ORIGIN_KAEL, encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(root / "ferramentas" / "empacotar_personagem.py"), "--nome", "Kael",
                 "--origem", str(origin_file), "--saida", directory],
                capture_output=True, text=True, timeout=60, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(run.returncode, 0, run.stderr)
            folder = Path(directory) / "kael"
            for name in ("origem.txt", "kael.json", "ficha.md", "kael-skill.zip"):
                self.assertTrue((folder / name).exists(), name)
            brain = Brain.load(folder / "kael.json")
            self.assertEqual(brain.abilities["espada"], 1.0)
            self.assertEqual(len(brain.memory.long_term), 4)
            import zipfile
            with zipfile.ZipFile(folder / "kael-skill.zip") as archive:
                names = set(archive.namelist())
                self.assertEqual(names, {"kael/SKILL.md", "kael/references/ficha-inicial.md", "kael/references/origem.txt",
                                         "kael/references/regras.md", "kael/references/ficha-modelo.md"})
                skill = archive.read("kael/SKILL.md").decode("utf-8")
                self.assertTrue(skill.startswith("---\nname: kael\n"))
                self.assertIn("/kael", skill)
                self.assertIn("4 lembranças formativas", skill)
                self.assertEqual(archive.read("kael/references/ficha-inicial.md").decode("utf-8"),
                                 (folder / "ficha.md").read_text(encoding="utf-8"))


class GptPackageTests(unittest.TestCase):
    def test_gpt_package_for_vincent(self) -> None:
        root = Path(__file__).resolve().parent.parent
        run = subprocess.run([sys.executable, str(root / "ferramentas" / "empacotar_gpt.py"), "--personagem", "vincent-knox"],
                             capture_output=True, text=True, timeout=60, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(run.returncode, 0, run.stderr)
        out = root / "personagens" / "vincent-knox" / "gpt"
        instructions = (out / "instrucoes.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(instructions), 8000)
        self.assertIn("Vincent Knox", instructions)
        for name in ("origem.txt", "ficha-inicial.md", "regras.md", "ficha-modelo.md"):
            self.assertTrue((out / "conhecimento" / name).exists(), name)
        single = (out / "prompt-unico.md").read_text(encoding="utf-8")
        self.assertIn("## 10. Postura", single)
        self.assertIn("Estou ativo.", single)
        import zipfile
        with zipfile.ZipFile(root / "personagens" / "vincent-knox" / "vincent-knox-gpt.zip") as archive:
            self.assertIn("instrucoes.md", archive.namelist())
            self.assertIn("conhecimento/regras.md", archive.namelist())


class PersistenceTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD, gender="f")
        run_conversation(brain, ["te odeio", "obrigado", "kkk", "vou te apagar", "quem é você?", "me ajuda"])
        brain.luck, brain.whim, brain.world_log = 0.4, "Deu vontade de fazer diferente.", ["Ganhei algo sem esperar."]
        restored = Brain.from_json(brain.to_json())
        self.assertEqual(restored.to_dict(), brain.to_dict())
        self.assertEqual(restored.gender, "f")
        self.assertEqual(restored.luck, 0.4)
        self.assertEqual(restored.world_log, ["Ganhei algo sem esperar."])
        self.assertEqual(restored.purpose, brain.purpose)
        self.assertEqual(restored.values.to_dict(), brain.values.to_dict())
        self.assertEqual(restored.strategies.to_dict(), brain.strategies.to_dict())
        self.assertEqual(restored.implant(now=100.0), brain.implant(now=100.0))

    def test_save_and_load(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sub" / "lua.json"
            brain.save(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["self_description"], DESCRIPTION_GOOD)
            self.assertEqual(Brain.load(path).name, "Lua")

    def test_session_saves_every_turn(self) -> None:
        brain = make("Lua", DESCRIPTION_GOOD)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lua.json"
            session = Session(brain, save_path=path, clock=Clock(0.0))
            session.say("oi, obrigado")
            self.assertEqual(Brain.load(path).experience_count, 2)


class SessionTests(unittest.TestCase):
    def test_custom_responder_receives_implant(self) -> None:
        seen = {}

        class Recorder:
            def reply(self, system, messages):
                seen["system"] = system
                seen["messages"] = list(messages)
                return "Estou aqui com você."

        brain = make("Lua", DESCRIPTION_GOOD)
        session = Session(brain, responder=Recorder(), clock=Clock(0.0))
        reply = session.say("oi")
        self.assertEqual(reply, "Estou aqui com você.")
        self.assertIn(DESCRIPTION_GOOD, seen["system"][0]["text"])
        self.assertEqual(seen["messages"][-1], {"role": "user", "content": "oi"})
        self.assertEqual(session.history[-1]["role"], "assistant")
        self.assertEqual(brain.experience_count, 2)  # percebeu e agiu


if __name__ == "__main__":
    unittest.main()
