import json
import random
import tempfile
import unittest
from pathlib import Path

from cerebro import ADVERSITIES, FORTUNES, Brain, Experience, Fate, Session, appraise, build_request, stage_for
from cerebro.emotions import EMOTIONS, Emotions
from cerebro.memory import MemoryStore
from cerebro.personality import inflect, plasticity_for, seed_from_description

DESCRIPTION_GOOD = "Sou curiosa, tímida e gosto de ajudar quem sofre. Confio nas pessoas."
DESCRIPTION_EVIL = "Sou frio, vingativo e manipulador. Não confio em ninguém."


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
        self.assertIn(brain.stance, ("retaliar", "manipular", "desafiar", "recolher"))
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
