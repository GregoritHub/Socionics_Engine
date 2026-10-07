import unittest

from hle_unified.material import attrs
from hle_unified.population_audit import audit_population
from hle_unified.selection_records import loads

from .sustained_fixtures import sustained_population, task_rows


class SustainedWorkflowPopulationTests(unittest.TestCase):
    def test_three_seeded_default_worlds_reconstruct_and_stop(self):
        for seed_value in (17, 43, 89):
            with self.subTest(seed=seed_value):
                p = sustained_population(seed_value)
                self.assertTrue(p.run(20000)["done"])
                report = audit_population(p.engine.world.journal(), loads(p.checkpoint()))
                self.assertEqual(p.stopped, ["unchanged_retained_result"] * 2)
                self.assertEqual(report["native_completions"], 4)
                self.assertEqual(report["repeated_outputs"], 2)

    def test_stop_disabled_world_reaches_declared_horizon(self):
        p = sustained_population(17, repeat_limit=None)
        self.assertTrue(p.run(20000)["done"])
        report = audit_population(p.engine.world.journal(), loads(p.checkpoint()))
        self.assertEqual(p.counts, [24, 24])
        self.assertEqual(report["native_completions"], 48)
        self.assertEqual(report["repeated_outputs"], 46)

    def test_declared_types_and_task_bounds(self):
        p = sustained_population(17)
        types = {attrs(p.engine.world.resolve(ref))["tim"] for ref in p.engine._profiles.values()
                 if attrs(p.engine.world.resolve(ref))["actor"] in {r.actor for r in p.requests}}
        self.assertEqual(types, {"iee", "sli"})
        for count in (2, 4, 8):
            rows = task_rows(p.requests[0].actor, count)
            self.assertEqual(len(rows), count)
            self.assertEqual(rows[-1][2], ("task-" + str(count - 2),))


if __name__ == "__main__":
    unittest.main()
