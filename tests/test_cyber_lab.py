import importlib.util
import unittest
from pathlib import Path


APP_PATH = (
    Path(__file__).parents[1]
    / ".agents/skills/build-local-cyber-lab/assets/cyber_lab/app.py"
)
SPEC = importlib.util.spec_from_file_location("skill_cyber_lab", APP_PATH)
assert SPEC and SPEC.loader
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class CyberLabSkillTests(unittest.TestCase):
    def test_starter_scenarios_are_local_and_have_mitigations(self):
        for name in APP.SCENARIOS:
            evidence = APP.simulate_scenario(name)
            self.assertEqual(evidence["scope"], "localhost / @maysanchess_demo")
            self.assertTrue(evidence["fixed"])
            self.assertTrue(evidence["event"])

    def test_unknown_scenario_is_rejected(self):
        with self.assertRaises(KeyError):
            APP.simulate_scenario("real-account")


if __name__ == "__main__":
    unittest.main()
