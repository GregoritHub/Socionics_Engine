import unittest
from copy import deepcopy

from hle_unified.population import Population
from hle_unified.population_audit import audit_population
from hle_unified.selection_records import loads, dumps
from hle_unified.operations import address
from hle_unified.workflow_selection_audit import audit as selection_audit
from tests_c7.fixtures import population as legacy_population

from .fixtures import (
    workflow_population, material_population, mixed_population,
    foreign_workflow_request,
)


class WorkflowPopulationTests(unittest.TestCase):
    def test_midpaid_resume_exact(self):
        p, _ = workflow_population(2, 3, 7)
        p.run(5); q = Population.restore(p.checkpoint())
        self.assertEqual(p.checkpoint(), q.checkpoint())
        self.assertTrue(p.run(2000)["done"]); self.assertTrue(q.run(2000)["done"])
        self.assertEqual(p.checkpoint(), q.checkpoint())
        self.assertTrue(audit_population(p.engine.world.journal(), loads(p.checkpoint()))["passed"])

    def test_round_robin_never_starves_a_runnable_actor(self):
        p, _ = workflow_population(2, 2, 1)
        p.run(8); actors = [x["actor"] for x in p.events]
        self.assertEqual(actors[:2], actors[2:4]); self.assertEqual(actors[:2], actors[4:6])

    def test_foreign_demand_and_duplicate_actor_rejected(self):
        p, _ = workflow_population(2, 1, 17)
        with self.assertRaises(ValueError):
            Population(p.engine, (p.requests[0], p.requests[0]))
        with self.assertRaises(ValueError):
            Population(p.engine, (foreign_workflow_request(p),))

    def test_finite_horizon_and_history_retention(self):
        p, _ = workflow_population(2, 2, 100000)
        before = len(p.engine.world.journal()); self.assertTrue(p.run(200)["done"])
        self.assertEqual(p.counts, [2, 2]); self.assertGreater(len(p.engine.world.journal()), before)
        self.assertTrue(any(x.get("native_status") == "succeeded" for x in p.events))
        self.assertIsNone(p.step())

    def test_turn_limit_preserves_unfinished_work(self):
        p, _ = workflow_population(2, 24, 1)
        self.assertTrue(p.run(2)["pending"]); self.assertEqual(p.counts, [0, 0])
        self.assertEqual(p.checkpoint(), Population.restore(p.checkpoint()).checkpoint())

    def test_exhaustion_is_retained_and_terminates(self):
        p, _ = workflow_population(2, 100, 32, budget=90)
        p.run(10000); self.assertTrue(p.done); self.assertIn("exhausted", p.stopped)
        for i, status in enumerate(p.stopped):
            if status == "exhausted":
                self.assertEqual(p.engine.wallet(p.requests[i].actor)["energy"], 0)
        self.assertTrue(audit_population(p.engine.world.journal(), loads(p.checkpoint()))["passed"])

    def test_repeated_retained_content_stops_without_capacity_claim(self):
        p, _ = workflow_population(2, 24, 32, repeat_limit=2)
        p.run(2000); self.assertTrue(p.done)
        self.assertEqual(p.stopped, ["unchanged_retained_result"] * 2)
        self.assertTrue(all(n < 24 for n in p.counts))
        self.assertTrue(audit_population(p.engine.world.journal(), loads(p.checkpoint()))["passed"])

    def test_actual_material_feedback_is_delivered_and_paid(self):
        p, _ = material_population()
        self.assertTrue(p.run(1000)["done"])
        self.assertTrue(any(x["status"] == "feedback_succeeded" for x in p.events))
        self.assertTrue(any(x["status"].startswith("feedback_") and x["charged"][0] > 0
                            for x in p.events))
        self.assertTrue(audit_population(p.engine.world.journal(), loads(p.checkpoint()))["passed"])

    def test_fabricated_audit_summary_rejected(self):
        p, _ = workflow_population(2, 1, 100000)
        p.run(200); state = loads(p.checkpoint())
        forged = deepcopy(state); forged["events"][0]["charged"] = (999, 999)
        with self.assertRaisesRegex(ValueError, "charge differs"):
            audit_population(p.engine.world.journal(), forged)
        forged = deepcopy(state)
        row = next(x for x in forged["events"] if "decision" in x)
        row["decision"] = address("c6.decision", row["actor"], row["key"])
        with self.assertRaises(ValueError):
            audit_population(p.engine.world.journal(), forged)

    def test_mixed_legacy_and_workflow_requests(self):
        p = mixed_population(); self.assertTrue(p.run(2000)["done"])
        state = loads(p.checkpoint())
        self.assertEqual({x["request_type"] for x in state["requests"]},
                         {"SelectionRequest", "WorkflowSelectionRequest"})
        self.assertEqual(p.checkpoint(), Population.restore(p.checkpoint()).checkpoint())
        self.assertTrue(audit_population(p.engine.world.journal(), state)["passed"])

    def test_legacy_v2_checkpoint_stays_exact(self):
        p, _ = legacy_population(17, 2, 2, 17); p.run(3)
        checkpoint = p.checkpoint(); state = loads(checkpoint)
        self.assertEqual(state["schema"], "hle-c7-population-v2")
        self.assertNotIn("request_type", state["requests"][0])
        self.assertEqual(checkpoint, Population.restore(checkpoint).checkpoint())


if __name__ == "__main__":
    unittest.main()
