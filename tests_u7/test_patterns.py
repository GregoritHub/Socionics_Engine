import unittest
from dataclasses import replace
from .fixtures import *
from hle_unified.shell_audit import audit
from hle_unified.shell_assessment import assess
from hle_unified.records import Assessment, EvidenceStatus


class Patterns(unittest.TestCase):
    def test_generated_lineage_transfers_across_eight_categories(self):
        e = setup7(); p = generated(e); rows = cross_target(e)
        self.assertEqual(len(rows), 8)
        self.assertEqual(p.origin_mode, "generated")
        self.assertEqual(len(e.pattern_view(ALICE)), 1)
        self.assertTrue(all(r["pattern.0"] == p.ref and r["route"] == "wait" and r["base_route"] == "engage" for r in rows.values()))
        self.assertEqual(len({r["target"] for r in rows.values()}), 8)
        self.assertTrue(all((r["actor"], r["carrier"], r["bearer"]) == (ALICE, ObjectRef(BOB, 1), ObjectRef(EVE, 1)) for r in rows.values()))
        report = assess(e.world.journal())
        self.assertEqual(sum(r["classification"] == "defensive_maintenance" for r in report["rows"]), 8)
        self.assertEqual(audit(e.world.journal())["generated_patterns"], 1)

    def test_same_definition_unrelated_affordance_is_unchanged(self):
        e = setup7(); generated(e)
        source = supply(e, "unrelated", target=SAW2, trigger=OTHER_TRIGGER)
        row = attrs(e.world.resolve(meet(e, "unrelated", source, target=SAW2)))
        self.assertEqual(e.world.resolve(SAW).definition, e.world.resolve(SAW2).definition)
        self.assertEqual(row["route"], "engage")
        self.assertFalse(indexed(row, "pattern."))

    def test_equal_labels_do_not_carry_trigger(self):
        e = setup7(); generated(e)
        lookalike = ref("same-label-rule")
        e.declare("lookalike", (ObjectVersion(lookalike, WRITER, e.world.resolve(RULE).label,
            (Role.DEFINITION,), e.world.resolve(RULE).facets),))
        show(e, ALICE, lookalike)
        source = supply(e, "lookalike", target=lookalike, trigger=OTHER_TRIGGER)
        row = attrs(e.world.resolve(meet(e, "lookalike", source, target=lookalike)))
        self.assertEqual(row["route"], "engage")

    def test_all_five_operators_have_executable_effects(self):
        expected = {"approval": "wait", "obligation": "wait", "forecast": "inspect",
                    "exclude_route": "inspect", "salience": "attend"}
        for kind, intent in expected.items():
            with self.subTest(kind=kind):
                e = setup7(generate=False); inject(e, Effect(kind))
                source = supply(e, "operator")
                row = attrs(e.world.resolve(meet(e, "operator", source)))
                self.assertEqual(row["route"], intent)
                self.assertEqual(audit(e.world.journal())["injected_patterns"], 1)
                self.assertEqual(e.pattern_view(ALICE)[0].origin_mode, "injected_fixture")

    def test_single_blame_does_not_generate_pattern(self):
        e = setup7(); source = supply(e, "one", feedback="blame"); meet(e, "one", source)
        self.assertFalse(e.pattern_view(ALICE))

    def test_repeated_read_of_one_experience_cannot_generate_pattern(self):
        e = setup7(); source = supply(e, "one", feedback="blame")
        meet(e, "one", source); meet(e, "twice", source)
        show(e, ALICE, source, key="again", subject=SAW, selectors=tuple(Selector(a.name, "detail", ("attributes", str(i), "value"))
             for i, a in enumerate(e.world.resolve(source).attributes)))
        meet(e, "third", source)
        self.assertFalse(e.pattern_view(ALICE))

    def test_generation_requires_demand(self):
        e = setup7()
        for i in range(2):
            source = supply(e, str(i), feedback="blame")
            meet(e, str(i), source, demand=False)
        self.assertFalse(e.pattern_view(ALICE))

    def test_generation_disabled_ablation(self):
        e = setup7(generate=False)
        for i, target in enumerate((SAW, SAW2)):
            source = supply(e, str(i), target=target, feedback="blame")
            meet(e, str(i), source, target=target)
        self.assertFalse(e.pattern_view(ALICE))

    def test_actual_approval_bypasses_current_block_without_clearing_pattern(self):
        e = setup7(); p = generated(e)
        source = supply(e, "approved", approved=True)
        row = attrs(e.world.resolve(meet(e, "approved", source)))
        self.assertEqual(row["route"], "engage")
        self.assertEqual(e.pattern_view(ALICE), (p,))
        source = supply(e, "renewed")
        self.assertEqual(attrs(e.world.resolve(meet(e, "renewed", source)))["route"], "wait")

    def test_context_and_cue_scope(self):
        e = setup7(); generated(e)
        other = ref("other-room")
        e.declare("other", (ObjectVersion(other, WRITER, "Other context", (Role.CONTEXT,)),)); show(e, ALICE, other)
        source = supply(e, "other", context=other)
        self.assertEqual(attrs(e.world.resolve(meet(e, "other", source, context=other)))["route"], "engage")
        cue = reference("minor:Coin:9"); show(e, ALICE, cue)
        source = supply(e, "new-cue")
        self.assertEqual(attrs(e.world.resolve(meet(e, "new-cue", source, cue=cue)))["route"], "engage")

    def test_two_owners_keep_incompatible_accounts_of_same_object(self):
        e = setup7(); generated(e)
        basics(e, BOB)
        for r in (CUE5, TRIGGER, ObjectRef(BOB, 1), ObjectRef(EVE, 1)):
            show(e, BOB, r)
        e.configure_patterns("patterns-bob", PatternPolicy(BOB, generate=False))
        inject(e, Effect("salience"), actor=BOB, key="bob-positive")
        results = []
        for actor in (ALICE, BOB):
            source = supply(e, actor.key, actor=actor)
            results.append(attrs(e.world.resolve(meet(e, actor.key, source, actor=actor)))["route"])
        self.assertEqual(results, ["wait", "attend"])
        approval_accounts = [next(p.object for p in e.participant_view(actor)._heads[
            e._last_bindings[actor, SAW.identity, ROOM, CUE5].identity].content if p.relation == "u7.approval")
            for actor in (ALICE, BOB)]
        self.assertEqual(approval_accounts, [True, False])
        self.assertEqual({p.owner for p in e.pattern_view(ALICE)}, {ALICE})
        self.assertEqual({p.owner for p in e.pattern_view(BOB)}, {BOB})
        with self.assertRaises(ValueError):
            show(e, BOB, e.pattern_view(ALICE)[0].ref)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_generated_pattern_changes_u6_action_and_material_consequence(self):
        rows = []
        for generate in (True, False):
            e = setup7(generate=generate, prior="serviceable", serviceable=True)
            for i, target in enumerate((SAW, SAW2)):
                source = supply(e, "training-"+str(i), target=target, feedback="blame")
                meet(e, "training-"+str(i), source, target=target)
            choice = first_choice(e)
            drive(e, delivery=False, prefix="execute")
            rows.append((choice, attrs(e.world.head(SAW.identity))["wear"]))
            self.assertTrue(audit(e.world.journal())["passed"])
        self.assertEqual(rows, [("inspect", 0), ("use", 1)])

    def test_hypothetical_forecast_deformation_is_not_physical_fact(self):
        e = setup7(generate=False, prior="serviceable", serviceable=True)
        supply(e, "opportunity"); inject(e, Effect("forecast"))
        self.assertEqual(first_choice(e), "inspect")
        use = next(v for v in predictions(e) if attrs(v)["kind"] == "use")
        self.assertEqual(use.occurrence, Occurrence.HYPOTHETICAL)
        self.assertEqual(next(p.object for p in use.facet(Account).content if p.relation == "outcome"), "failed")
        self.assertEqual(e.world.head(SAW.identity).facet(Material).condition, "serviceable")

    def test_unknown_operator_rejected_without_state_change(self):
        e = setup7(); before = e.checkpoint()
        with self.assertRaises(ValueError): Effect("telepathy")
        self.assertEqual(e.checkpoint(), before)

    def test_fixture_and_generated_origins_remain_distinct(self):
        e = setup7(generate=False); inject(e, Effect("approval"))
        for i in range(2):
            source = supply(e, str(i)); meet(e, str(i), source)
        report = assess(e.world.journal())
        self.assertEqual(report["recurrent_patterns"][0]["origin_mode"], "injected_fixture")
        self.assertEqual(audit(e.world.journal())["generated_patterns"], 0)

    def test_no_unearned_skill_or_target_mind(self):
        e = setup7(); generated(e); cross_target(e)
        self.assertFalse(e.participant_view(ALICE).snapshot.acquired)
        self.assertEqual(e.world.resolve(SAW).roles, (Role.MATERIAL,))
        self.assertEqual(e.world.resolve(POSSIBILITY).occurrence, Occurrence.HYPOTHETICAL)


if __name__ == "__main__": unittest.main()
