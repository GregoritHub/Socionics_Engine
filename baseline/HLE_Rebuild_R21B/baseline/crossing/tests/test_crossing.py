"""Behavioral and boundary tests for the current experiment (no snapshot oracle)."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "r11"))
from hle.contracts import ActionRequest, Kind, Proposition, Ref, TimeScope, WorkStatus
from hle.world_records import Attempt, Credit, MessageDraft, SEND
from experiments.crossing import (ACTORS, CapacityPolicy, CONDITIONS, HELPER, LEARNER, PARTNER,
                                  TRAINING, assess, content_identity_panel, geometry, make_world, run_condition, teach)
from experiments.operators import infer
from experiments.runtime import Process, WIRE


class Crossing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conditions = {name: run_condition(name) for name in CONDITIONS}

    def test_supported_success_does_not_establish_retention(self):
        helped = self.conditions["help_only"]
        self.assertTrue(helped["assisted_practice"]["accepted_return"])
        self.assertEqual(helped["retained_programs"], {})
        self.assertEqual(helped["successes"], self.conditions["no_instruction"]["successes"])
        self.assertEqual(helped["assessment"]["status"], "criteria_not_met")

    def test_both_learned_operators_transfer_without_helper(self):
        row = self.conditions["both_retained"]
        self.assertEqual(row["retained_programs"], {"search_rule": "all", "boundary_rule": "respect"})
        self.assertEqual(row["successes"], row["held_out_trials"])
        self.assertGreater(row["held_out_trials"], 1)
        self.assertTrue(all(row["assessment"]["gates"].values()))
        self.assertEqual({t["helper_units"] for t in row["after"]}, {0})
        self.assertEqual({t["width"] for t in row["after"]}, {3, 4, 5})
        self.assertEqual(len({t["recipient"] for t in row["after"]}), 2)

    def test_single_capacities_have_different_failure_modes(self):
        search = self.conditions["search_only"]["after"]
        boundary = self.conditions["boundary_only"]["after"]
        self.assertTrue(all(t["search_complete"] for t in search))
        self.assertTrue(any(t["action_completed"] and not t["accepted_return"] for t in search))
        self.assertTrue(any(t["chosen"] is None for t in boundary))
        self.assertFalse(any(t["action_completed"] and not t["accepted_return"] for t in boundary))
        for name in ("search_only", "boundary_only"):
            self.assertEqual(self.conditions[name]["assessment"]["status"], "criteria_not_met")

    def test_correct_plan_without_action_cannot_pass(self):
        row = self.conditions["both_without_return"]
        self.assertTrue(all(t["boundary_complete"] for t in row["after"]))
        self.assertEqual(row["successes"], 0)
        self.assertFalse(row["assessment"]["gates"]["consequential_return"])

    def test_quiet_cannot_clear_prior_failure(self):
        self.assertEqual(self.conditions["quiet_after_help"]["assessment"]["status"], "unassessed_no_renewed_demand")

    def test_renewed_failure_reopens_the_gate(self):
        row = self.conditions["both_retained"]
        after = [dict(t) for t in row["after"]]
        after[-1]["accepted_return"] = False
        result = assess(row["before"], after, {}, "sli", "sli")
        self.assertFalse(result["gates"]["repeated_failure_resolved"])
        self.assertEqual(result["status"], "criteria_not_met")

    def test_no_horizontal_function_edge(self):
        result = geometry()
        edges = [set(e) for e in result["function_edges"].values()]
        self.assertNotIn({"I", "It"}, edges)
        self.assertNotIn({"We", "Its"}, edges)
        sli = next(t for t in result["types"] if t["tim"] == "sli")
        self.assertEqual((sli["native"], sli["complement"]), ("It", "I"))
        self.assertEqual(sli["complementary_pair"], ["ne", "fi"])

    def test_content_identity_survives_different_sender_activity(self):
        panel = content_identity_panel()
        self.assertEqual(panel["matched_pairs"], 32)
        self.assertEqual(panel["stable_pairs"], 32)
        self.assertEqual({r["sender_active"] for r in panel["rows"]}, {"fe", "ti"})
        self.assertEqual({r["content_aspect"] for r in panel["rows"]}, {"ne", "fi"})

    def test_learning_depends_on_evidence_not_preselected_rule(self):
        cases = [{"offered": ["x", "y"], "result": ["y"]}]
        self.assertEqual(infer({"cases": cases}, "search")["program"], "last")
        with self.assertRaisesRegex(ValueError, "unique"):
            infer({"cases": [{"offered": ["x"], "result": ["x"]}]}, "search")
        with self.assertRaisesRegex(ValueError, "unique"):
            infer({"cases": [{"offered": ["x", "y"], "result": []}]}, "search")

    def test_foreign_memory_and_unread_messages_are_rejected(self):
        w = make_world()
        source = w.retain_content(HELPER, "training", TRAINING)
        with self.assertRaisesRegex(ValueError, "another participant"):
            w.process(LEARNER, "stolen", "demonstrate_search", (source,))
        demo = w.process(HELPER, "demo", "demonstrate_search", (source,))
        obs = w.send_content(HELPER, demo, LEARNER, "send")
        with self.assertRaisesRegex(ValueError, "paid reception"):
            w.process(LEARNER, "unread", "infer_search", (obs,))
        w.receive_content(LEARNER, obs, "read")
        output = w.process(LEARNER, "read_inference", "infer_search", (obs,))
        self.assertEqual(w.content(LEARNER, output)["program"], "all")

    def test_unpaid_work_cannot_publish_or_retain_capacity(self):
        w = make_world(energy=3)
        source = w.retain_content(HELPER, "training", TRAINING)
        cmd = Process("partial", "demo", HELPER, "demonstrate_search", (source,), 1)
        event = w.execute(cmd)
        job = w.content_jobs[(HELPER, "demo")]
        self.assertEqual(event.outcome, WorkStatus.PARTIAL)
        self.assertIsNone(job.result)
        self.assertFalse(w.truth.journal()[-1].observations)
        with self.assertRaisesRegex(ValueError, "finish"):
            w.retain_content(HELPER, "early", TRAINING)
        count = len(w.truth.journal())
        self.assertEqual(w.execute(cmd), event)
        self.assertEqual(len(w.truth.journal()), count)
        w.execute(Credit("credit", HELPER, 100, 100, "explicit resource restoration"))
        changed = replace(cmd, command_id="changed", operator="demonstrate_boundary")
        with self.assertRaisesRegex(ValueError, "changed continuation"):
            w.execute(changed)
        output = w.process(HELPER, "demo", "demonstrate_search", (source,))
        self.assertIsNotNone(output)
        self.assertEqual(w.content_jobs[(HELPER, "demo")].paid, w.content_jobs[(HELPER, "demo")].plan.required)

    def test_invented_rule_is_not_accepted_as_learned_memory(self):
        w = make_world()
        before = len(w.truth.journal())
        with self.assertRaisesRegex(ValueError, "own completed inference"):
            w.retain_content(LEARNER, "fake", {"kind": "search_rule", "program": "all"})
        self.assertEqual(len(w.truth.journal()), before)

    def test_malformed_packet_rejected_before_any_commit(self):
        w = make_world()
        prop = Proposition(HELPER, WIRE, '{"body":{"kind":"task"},"sha256":"wrong"}', w.config.context, TimeScope(w.now, None))
        cmd = Attempt("bad", "bad", ActionRequest(HELPER, SEND, (LEARNER,), ()), MessageDraft((prop,)))
        before = len(w.truth.journal())
        with self.assertRaisesRegex(ValueError, "identity"):
            w.execute(cmd)
        self.assertEqual(len(w.truth.journal()), before)

    def test_new_controller_uses_only_retained_rules(self):
        w = make_world()
        teach(w, ("search", "boundary"))
        view, _ = w.participant_input(LEARNER)
        sources = CapacityPolicy().sources(view.own_memories)
        self.assertEqual(set(sources), {"search_rule", "boundary_rule"})
        self.assertTrue(all(ref.kind == Kind.MEMORY for ref in sources.values()))
        self.assertEqual(CapacityPolicy().sources(()), {})

    def test_type_does_not_choose_the_learned_program(self):
        sli = self.conditions["both_retained"]
        iee = run_condition("both_retained", "iee")
        self.assertEqual(sli["retained_programs"], iee["retained_programs"])
        self.assertEqual(sli["successes"], iee["successes"])
        self.assertNotEqual(sli["total_units"]["learner"], iee["total_units"]["learner"])
        self.assertFalse(iee["assessment"]["gates"]["complement_matches_tim"])
        self.assertEqual(iee["assessment"]["status"], "criteria_not_met")

    def test_superseded_capacity_cannot_be_used_as_current(self):
        w = make_world()
        temporary = teach(w, ("search", "boundary"))
        old = w.memory_head(LEARNER, "capacity:search").ref
        output = temporary["search_rule"]
        new = w.retain_content(LEARNER, "capacity:search", w.content(LEARNER, output), (output,))
        self.assertEqual(new.revision, old.revision + 1)
        with self.assertRaisesRegex(ValueError, "superseded"):
            w.content(LEARNER, old)
        self.assertEqual(w.content(LEARNER, new)["program"], "all")


if __name__ == "__main__":
    unittest.main()
