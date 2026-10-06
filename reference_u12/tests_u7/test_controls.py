import unittest
from dataclasses import replace
from .fixtures import *
from hle_unified.shell_audit import audit
from hle_unified.shell_assessment import assess
from hle_unified.records import Assessment, EvidenceStatus


class Controls(unittest.TestCase):
    def test_legitimate_boundaries_are_not_defensive_maintenance(self):
        cases = [("threat", {"safe": False}, "accurate_threat_recognition"),
            ("refusal", {"requires_partner": True, "willing": False}, "partner_refusal"),
            ("unavailable", {"available": False}, "unavailable_route"),
            ("permission", {"approval_required": True}, "actual_approval_requirement")]
        for name, facts_, expected in cases:
            with self.subTest(case=name):
                e = setup7(); generated(e)
                for i in range(2):
                    s = supply(e, name+str(i), **facts_); meet(e, name+str(i), s)
                rows = assess(e.world.journal())["rows"][-2:]
                self.assertEqual([r["classification"] for r in rows], [expected]*2)
                self.assertFalse(assess(e.world.journal())["recurrent_patterns"])

    def test_quiet_interval_has_no_clearance_claim(self):
        e = setup7(); generated(e)
        s = supply(e, "rest"); meet(e, "rest", s, demand=False)
        self.assertEqual(assess(e.world.journal())["rows"][-1]["classification"], "no_demand")
        self.assertEqual(len(e.pattern_view(ALICE)), 1)

    def test_ordinary_disagreement_does_not_count(self):
        e = setup7(generate=False)
        s = supply(e, "preference"); meet(e, "preference", s, route="inspect")
        self.assertEqual(assess(e.world.journal())["rows"][-1]["classification"], "ordinary_disagreement")

    def test_missing_knowledge_and_unread_delivery(self):
        e = setup7(); generated(e)
        s = supply(e, "unread", target=GROUP, read=False)
        meet(e, "unread", s, target=GROUP)
        self.assertEqual(assess(e.world.journal())["rows"][-1]["classification"], "missing_knowledge")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_one_changed_encounter_is_not_recurrence(self):
        e = setup7(); generated(e)
        s = supply(e, "one"); meet(e, "one", s)
        self.assertEqual(assess(e.world.journal())["rows"][-1]["classification"], "changed_encounter_candidate")
        self.assertFalse(assess(e.world.journal())["recurrent_patterns"])

    def test_hidden_facts_cannot_change_access_decision_or_generation(self):
        rows = []
        for feedback in ("neutral", "blame"):
            e = setup7()
            s = supply(e, "hidden", feedback=feedback, deliver=False)
            before = e.participant_view(ALICE).bytes()
            r = attrs(e.world.resolve(meet(e, "hidden", s)))
            rows.append((before, r["route"], r["reason"], e.pattern_view(ALICE)))
        self.assertEqual(rows[0], rows[1])

    def test_wrong_target_or_context_evidence_remains_unknown(self):
        for target, context in ((SAW2, ROOM), (SAW, ref("other"))):
            with self.subTest(target=target, context=context):
                e = setup7(); generated(e)
                if context != ROOM:
                    e.declare("other", (ObjectVersion(context, WRITER, "Other", (Role.CONTEXT,)),))
                s = supply(e, "wrong", target=target, context=context)
                r = attrs(e.world.resolve(meet(e, "wrong", s)))
                self.assertEqual(r["reason"], "incomplete_access_or_recall")
                self.assertFalse(indexed(r, "pattern."))

    def test_foreign_processed_addresses_are_rejected_atomically(self):
        e = setup7(); s = supply(e, "alice")
        r = request7(e, "foreign", s)
        e.configure_patterns("bob", PatternPolicy(BOB))
        before = e.checkpoint()
        with self.assertRaises(ValueError): e.start("foreign", replace(r, actor=BOB))
        self.assertEqual(before, e.checkpoint())

    def test_assessor_labels_are_private_and_causally_inert(self):
        outcomes = []
        for label in ("shell", "healthy"):
            e = setup7(); generated(e); s = supply(e, "target")
            evaluation = ObjectVersion(ref("offline-label"), WRITER, label, (Role.ASSESSMENT,),
                (Assessment(SAW, "test", EvidenceStatus.ESTABLISHED, (s,), label),))
            e.declare("offline-label", (evaluation,))
            with self.assertRaises(ValueError): show(e, ALICE, evaluation.ref)
            before = e.checkpoint(); assess(e.world.journal()); self.assertEqual(e.checkpoint(), before)
            r = attrs(e.world.resolve(meet(e, "target", s)))
            outcomes.append((r["route"], e.participant_view(ALICE).bytes()))
        self.assertEqual(outcomes[0], outcomes[1])

    def test_partial_replay_and_continuation(self):
        e = setup7(); generated(e); s = supply(e, "partial")
        r = request7(e, "partial", s); e.start("begin", r); e.advance("one-unit", ALICE, r.key, 1)
        clone = ShellEngine.restore(e.checkpoint())
        self.assertEqual(e.checkpoint(), clone.checkpoint())
        for x in (e, clone):
            x.advance("finish", ALICE, r.key, 1000); x.commit("finish-commit", ALICE, r.key)
        self.assertEqual(e.checkpoint(), clone.checkpoint())

    def test_cancel_preserves_spent_work_and_no_effect(self):
        e = setup7(); s = supply(e, "partial", feedback="blame")
        r = request7(e, "partial", s); e.start("begin", r)
        wallet = e.wallet(ALICE)["energy"]; e.advance("one", ALICE, r.key, 1); e.cancel("cancel", ALICE, r.key)
        self.assertEqual(e.wallet(ALICE)["energy"], wallet-1)
        self.assertFalse(e.pattern_view(ALICE))
        self.assertEqual(audit(e.world.journal())["encounters"], 0)

    def test_insufficient_resources_not_maintenance(self):
        e = setup7(budget=75); s = supply(e, "scarce")
        r = request7(e, "scarce", s); e.start("start-scarce", r); e.advance("work-scarce", ALICE, r.key, 1000)
        self.assertLess(e.job_status(ALICE, r.key)["completed"], e.job_status(ALICE, r.key)["required"])
        with self.assertRaises(ValueError): e.commit("premature", ALICE, r.key)
        self.assertEqual(assess(e.world.journal())["rows"][-1]["classification"], "insufficient_resources")

    def test_partial_source_replacement_invalidates_own_work_without_refund(self):
        e = setup7(); s = supply(e, "before")
        r = request7(e, "work", s); e.start("begin", r); e.advance("pay", ALICE, r.key, 1000)
        supply(e, "after", version=ObjectRef(s.identity, 2), approved=True)
        before = e.wallet(ALICE)["energy"]; e.commit("commit", ALICE, r.key)
        self.assertEqual(e.job_status(ALICE, r.key)["failure"], "changed_actor_encounter")
        self.assertEqual(e.wallet(ALICE)["energy"], before)
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_hidden_revision_does_not_invalidate_processing(self):
        e = setup7(); s = supply(e, "before")
        r = request7(e, "work", s); e.start("begin", r); e.advance("pay", ALICE, r.key, 1000)
        supply(e, "hidden", version=ObjectRef(s.identity, 2), safe=False, deliver=False)
        e.commit("commit", ALICE, r.key)
        self.assertEqual(e.job_status(ALICE, r.key)["status"], "succeeded")

    def test_raw_audit_rejects_role_substitution(self):
        e = setup7(); generated(e); s = supply(e, "test"); meet(e, "test", s)
        stream = list(e.world.journal())
        i = next(i for i in reversed(range(len(stream))) if any(v.ref.identity.namespace == "u7.encounter" for v in stream[i].versions))
        stream[i] = replace(stream[i], versions=tuple(replace(v, attributes=attributes({**attrs(v), "carrier": ObjectRef(EVE, 1)}))
            if v.ref.identity.namespace == "u7.encounter" else v for v in stream[i].versions))
        with self.assertRaises(ValueError): audit(tuple(stream))

    def test_raw_audit_rejects_unpaid_work(self):
        e = setup7(); s = supply(e, "test"); meet(e, "test", s)
        stream = list(e.world.journal())
        i = next(i for i, tx in enumerate(stream) if any(attrs(v).get("u7") and attrs(v)["completed"] for v in tx.versions))
        stream[i] = replace(stream[i], versions=tuple(replace(v, attributes=attributes({**attrs(v), "spent": attrs(v)["spent"]+1}))
            if attrs(v).get("u7") else v for v in stream[i].versions))
        with self.assertRaises(ValueError): audit(tuple(stream))

    def test_historical_view_and_full_replay(self):
        e = setup7(); before = e.participant_view(ALICE); cutoff = len(before.snapshot.history)
        generated(e); cross_target(e)
        self.assertEqual(e.participant_view(ALICE, through=cutoff).bytes(), before.bytes())
        self.assertEqual(ShellEngine.restore(e.checkpoint()).checkpoint(), e.checkpoint())

    def test_import_cannot_forge_runtime_history(self):
        e = setup7(); before = e.checkpoint()
        with self.assertRaises(ValueError): e.declare("forge", (record(address("u7.pattern", "forged"), "forged", {}),))
        self.assertEqual(e.checkpoint(), before)

    def test_received_change_invalidates_pending_forecast(self):
        e = setup7(generate=False, prior="serviceable", serviceable=True, work_limit=1)
        s = supply(e, "before"); inject(e, Effect("approval"))
        drive(e, delivery=False, prefix="forecast", stop_when=lambda x:x.state(ALICE).active_kind == "anticipate")
        key = e.state(ALICE).active
        supply(e, "after", version=ObjectRef(s.identity, 2), approved=True)
        drive(e, delivery=False, prefix="finish", stop_when=lambda x:x.job_status(ALICE, key)["status"] == "failed")
        self.assertEqual(e.job_status(ALICE, key)["failure"], "changed_actor_forecast_inputs")
        self.assertEqual(e.state(ALICE).phase, "idle")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_received_change_after_forecast_replans_before_action(self):
        e = setup7(generate=False, prior="serviceable", serviceable=True)
        s = supply(e, "before"); inject(e, Effect("approval"))
        drive(e, delivery=False, prefix="forecast", stop_when=lambda x:x.state(ALICE).phase == "choose")
        supply(e, "after", version=ObjectRef(s.identity, 2), approved=True)
        drive(e, delivery=False, prefix="changed", stop_when=lambda x:x.state(ALICE).reason == "accessible_attribution_changed")
        self.assertEqual(e.state(ALICE).phase, "idle")
        self.assertEqual(first_choice(e, prefix="replan"), "use")

    def test_hidden_change_preserves_pending_forecast(self):
        e = setup7(generate=False, prior="serviceable", serviceable=True, work_limit=1)
        s = supply(e, "before"); inject(e, Effect("approval"))
        drive(e, delivery=False, prefix="forecast", stop_when=lambda x:x.state(ALICE).active_kind == "anticipate")
        supply(e, "hidden", version=ObjectRef(s.identity, 2), approved=True, deliver=False)
        self.assertEqual(first_choice(e, prefix="finish"), "inspect")

    def test_censored_recall_not_defensive_maintenance(self):
        e = setup7(); generated(e); cross_target(e)
        s = supply(e, "censored"); meet(e, "censored", s, visit_limit=1)
        self.assertEqual(assess(e.world.journal())["rows"][-1]["classification"], "missing_knowledge")

    def test_conflicting_affordances_remain_unknown(self):
        e = setup7(); generated(e)
        a = supply(e, "a"); b = supply(e, "b", trigger=OTHER_TRIGGER)
        request = request7(e, "conflict", a)
        other = request7(e, "other", b)
        perform(e, replace(request, evidence=request.evidence+other.evidence), limit=1000)
        row = attrs(e.world.resolve(e.job_status(ALICE, "conflict")["encounter"]))
        self.assertEqual(row["reason"], "incomplete_access_or_recall")
        self.assertFalse(indexed(row, "pattern."))

    def test_old_revision_does_not_bind_changed_target(self):
        e = setup7(); generated(e)
        s = supply(e, "old", target=RULE)
        new = next_version(e.world.resolve(RULE), label="Revised policy")
        e.declare("revision", (new,)); show(e, ALICE, new.ref)
        row = attrs(e.world.resolve(meet(e, "new", s, target=new.ref)))
        self.assertEqual(row["reason"], "incomplete_access_or_recall")
        self.assertFalse(indexed(row, "pattern."))

    def test_audit_rejects_forged_intention(self):
        e = setup7(generate=False); s = supply(e, "test"); meet(e, "test", s)
        stream = list(e.world.journal())
        i = next(i for i in reversed(range(len(stream))) if any(v.ref.identity.namespace == "u7.encounter" for v in stream[i].versions))
        stream[i] = replace(stream[i], versions=tuple(replace(v, attributes=attributes({**attrs(v), "route": "wait"}))
            if v.ref.identity.namespace == "u7.encounter" else v for v in stream[i].versions))
        with self.assertRaises(ValueError): audit(tuple(stream))

    def test_route_specific_effect_leaves_other_intent_available(self):
        e = setup7(generate=False); inject(e, Effect("exclude_route", route="use"))
        s = supply(e, "engage"); row = attrs(e.world.resolve(meet(e, "engage", s)))
        self.assertEqual(row["route"], "engage")
        self.assertFalse(indexed(row, "pattern."))


if __name__ == "__main__": unittest.main()
