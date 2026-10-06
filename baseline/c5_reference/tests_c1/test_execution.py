import unittest
from dataclasses import replace
from hle.model_a import TYPES
from tests_c1.fixtures import *
from hle_unified.crux_audit import audit
from hle_unified.compact import seal, unseal
from hle_unified.institutions import InstitutionEngine
from hle_unified.crux_records import RECIPES
from hle_unified.operations import indexed, job_address


def action(e, ref):
    return next(p.object for p in e.world.resolve(ref).facet(Account).content if p.relation == "u5.action")


class Execution(unittest.TestCase):
    def test_all_types_and_four_evidence_conditions(self):
        for tim in TYPES:
            for prior in ("damaged", "serviceable"):
                for actual in ("damaged", "serviceable"):
                    with self.subTest(tim=tim, prior=prior, actual=actual):
                        e = setup_c1(tim, prior=prior, actual=actual)
                        r = run_circuit(e)
                        self.assertEqual(action(e, r["before"]), "use" if prior == "serviceable" else "inspect")
                        self.assertEqual(action(e, r["after"]), "use" if actual == "serviceable" else "inspect")
                        self.assertEqual(e.world.resolve(r["retained"]).facet(Account).content[0].object, actual)
                        self.assertEqual(e.job_status(ALICE, "after-action")["status"], "succeeded")
                        report = audit(e.world.journal(), e.access.checkpoint())
                        self.assertEqual((report["c1_movements"], report["c1_semantic_steps"]), (3, 4))

    def test_transfer_to_another_target(self):
        e = setup_c1(target=SAW2)
        r = run_circuit(e, target=SAW2)
        self.assertEqual(action(e, r["after"]), "use")
        self.assertEqual(e.world.head(SAW2.identity).ref.revision, 2)
        self.assertEqual(e.world.head(SAW.identity).ref, SAW)
        audit(e.world.journal(), e.access.checkpoint())

    def test_output_not_available_before_paid_completion(self):
        e = setup_c1(); r = hypothesis(e)
        before = e.participant_view(ALICE).bytes()
        e.start("start", r)
        d = e.job_status(ALICE, r.key)
        e.advance("partial", ALICE, r.key, d["required"] - 1)
        self.assertEqual(e.job_status(ALICE, r.key)["steps_completed"], 0)
        self.assertEqual(e.participant_view(ALICE).bytes(), before)
        with self.assertRaises(ValueError): e.commit("early", ALICE, r.key)
        e.advance("last", ALICE, r.key, 1)
        self.assertEqual(e.job_status(ALICE, r.key)["steps_completed"], 1)
        self.assertEqual(e.participant_view(ALICE).bytes(), before)
        e.commit("finish", ALICE, r.key)
        self.assertNotEqual(e.participant_view(ALICE).bytes(), before)

    def test_apply_requires_independent_material_work(self):
        e = setup_c1(); perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
        r = trial(e, m); e.start("start", r)
        d = e.job_status(ALICE, r.key)
        e.advance("semantic", ALICE, r.key, d["required"] - d["material_units"])
        self.assertEqual(e.job_status(ALICE, r.key)["steps_completed"], 1)
        with self.assertRaises(ValueError): e.commit("early", ALICE, r.key)
        e.advance("physical", ALICE, r.key, 3); event = e.commit("done", ALICE, r.key)
        self.assertEqual(attrs(e.world.resolve(event))["condition"], "serviceable")

    def test_partial_continuation_at_semantic_boundaries(self):
        for phase in ("theory", "trial", "embody"):
            for boundary in ("recall", "first_step", "before_complete"):
                with self.subTest(phase=phase, boundary=boundary):
                    e = setup_c1()
                    if phase == "theory": r = hypothesis(e)
                    else:
                        perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
                        if phase == "trial": r = trial(e, m)
                        else:
                            event = perform(e, trial(e, m)); o = receive(e, event, ALICE, "observed")
                            r = retention(e, m, o)
                    e.start("start", r); d = e.job_status(ALICE, r.key)
                    threshold = d["recall_units"] + sum(indexed(d, "route.0.charges.")) + d["route.0.content_units"]
                    amount = {"recall": d["recall_units"], "first_step": threshold,
                              "before_complete": d["required"] - 1}[boundary]
                    e.advance("first", ALICE, r.key, amount)
                    cp = e.checkpoint(); restored = CruxEngine.restore(cp)
                    self.assertEqual(restored.checkpoint(), cp)
                    for x in (e, restored):
                        if x.job_status(ALICE, r.key)["status"] != "ready":
                            x.advance("rest", ALICE, r.key, 10000)
                        x.commit("done", ALICE, r.key)
                    self.assertEqual(restored.checkpoint(), e.checkpoint())
                    audit(e.world.journal(), e.access.checkpoint())

    def test_completed_checkpoint_and_command_idempotency(self):
        e = setup_c1(); r = run_circuit(e)
        cp = e.checkpoint(); restored = CruxEngine.restore(cp)
        self.assertEqual(restored.checkpoint(), cp)
        req = hypothesis(setup_c1())
        before = e.checkpoint()
        result = e.start("start:alice:theory", req)
        self.assertEqual(e.checkpoint(), before)
        self.assertEqual(result.identity, job_address(ALICE, "theory").identity)
        with self.assertRaises(ValueError): e.start("start:alice:theory", replace(req, key="another"))

    def test_comparison_ablation_removes_useful_result(self):
        healthy = setup_c1(); ablated = setup_c1(engine_type=WithoutComparison)
        h, a = run_circuit(healthy), run_circuit(ablated)
        self.assertEqual(action(healthy, h["after"]), "use")
        self.assertEqual(action(ablated, a["after"]), "inspect")
        for key in ("theory", "trial", "embody"):
            self.assertEqual(healthy.job_status(ALICE, key)["spent"], ablated.job_status(ALICE, key)["spent"])
        audit(healthy.world.journal(), healthy.access.checkpoint())
        with self.assertRaisesRegex(ValueError, "semantic content"):
            audit(ablated.world.journal(), ablated.access.checkpoint())

    def test_fully_paid_cancellation_cannot_grant_retention(self):
        e = setup_c1(); perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
        event = perform(e, trial(e, m)); o = receive(e, event, ALICE, "observed")
        r = retention(e, m, o); e.start("start", r); e.advance("work", ALICE, r.key, 10000)
        paid = e.wallet(ALICE)["energy"]; e.cancel("cancel", ALICE, r.key)
        self.assertEqual(e.wallet(ALICE)["energy"], paid)
        after = think(e, request5(e, "after", source=o))
        self.assertEqual(action(e, after), "inspect")
        self.assertFalse(any(b.ref.identity.namespace == "u5.account" for b in e.participant_view(ALICE).snapshot.bindings))
        audit(e.world.journal(), e.access.checkpoint())

    def test_unread_observation_cannot_become_retention(self):
        e = setup_c1(); perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
        event = perform(e, trial(e, m)); e.deliver_event("unread", event, ALICE)
        r = MovementRequest("retention", ALICE, "condition-retention-v1", ROOM, CUE5, m,
                            (DetailAddress("unread", "condition"),))
        with self.assertRaises(ValueError): e.start("bad", r)

    def test_foreign_model_and_wrong_scope_are_rejected(self):
        e = setup_c1(); perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
        r = trial(e, m)
        with self.assertRaises(ValueError): e.start("foreign", replace(r, actor=BOB))
        with self.assertRaises(ValueError): e.start("scope", replace(r, context=CUE5))
        with self.assertRaises(ValueError): show(e, BOB, m)

    def test_wrong_model_observation_is_rejected(self):
        e = setup_c1(); perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
        perform(e, hypothesis(e, "other")); other = e.job_status(ALICE, "other")["binding"]
        event = perform(e, trial(e, m)); o = receive(e, event, ALICE, "observed")
        with self.assertRaises(ValueError): e.start("bad", retention(e, other, o))

    def test_stale_rule_preserves_spending_and_refuses_output(self):
        e = setup_c1(); r = hypothesis(e); e.start("start", r); e.advance("work", ALICE, r.key, 10000)
        old = e.world.resolve(RULE)
        e.declare("changed-rule", (next_version(old, label="Changed policy revision"),))
        paid = e.wallet(ALICE)["energy"]; e.commit("done", ALICE, r.key)
        self.assertEqual(e.job_status(ALICE, r.key)["status"], "failed")
        self.assertEqual(e.job_status(ALICE, r.key)["failure"], "stale_dependency")
        self.assertEqual(e.wallet(ALICE)["energy"], paid)
        self.assertFalse(e._movement_models)
        self.assertEqual(CruxEngine.restore(e.checkpoint()).checkpoint(), e.checkpoint())
        audit(e.world.journal(), e.access.checkpoint())

    def test_hidden_material_differences_do_not_leak_before_read(self):
        a = setup_c1(actual="serviceable"); b = setup_c1(actual="damaged")
        for e in (a, b): perform(e, hypothesis(e))
        self.assertEqual(a.participant_view(ALICE).bytes(), b.participant_view(ALICE).bytes())
        events = []
        for e in (a, b): events.append(perform(e, trial(e, e.job_status(ALICE, "theory")["binding"])))
        self.assertEqual(a.participant_view(ALICE).bytes(), b.participant_view(ALICE).bytes())
        self.assertNotEqual(attrs(a.world.resolve(events[0]))["condition"], attrs(b.world.resolve(events[1]))["condition"])

    def test_exhaustion_is_partial_and_no_refund_on_cancellation(self):
        e = setup_c1(budget=28); r = hypothesis(e)
        e.start("start", r); before = e.wallet(ALICE)["energy"]
        e.advance("work", ALICE, r.key, 10000)
        d = e.job_status(ALICE, r.key)
        self.assertLess(d["completed"], d["required"])
        self.assertEqual(e.wallet(ALICE)["energy"], 0)
        e.cancel("cancel", ALICE, r.key)
        self.assertEqual(e.job_status(ALICE, r.key)["spent"], before)
        self.assertFalse(e._movement_models)
        audit(e.world.journal(), e.access.checkpoint())

    def test_alternative_lawful_element_paths(self):
        e = setup_c1(); perform(e, hypothesis(e, elements=("ne",)))
        m = e.job_status(ALICE, "theory")["binding"]
        event = perform(e, replace(trial(e, m), elements=("ti",)))
        o = receive(e, event, ALICE, "observed")
        perform(e, retention(e, m, o, elements=("ti", "ne")))
        audit(e.world.journal(), e.access.checkpoint())
        with self.assertRaises(ValueError): hypothesis(e, "wrong-path", elements=("fi",))

    def test_semantic_content_and_predecessor_corruption_fail_audit(self):
        e = setup_c1(); run_circuit(e); txs = e.world.journal()
        for corruption in ("content", "predecessor", "debit"):
            changed, done = [], False
            for tx in txs:
                versions = []
                for v in tx.versions:
                    if not done and corruption == "debit" and attrs(v).get("record_type") == "wallet" and v.previous:
                        v = replace(v, attributes=attributes({**attrs(v), "energy": attrs(v)["energy"] + 1})); done = True
                    if not done and v.ref.identity.namespace == "c1.step":
                        if corruption == "content":
                            a = v.facet(Account)
                            v = replace(v, facets=(replace(a, content=tuple(replace(p, object="forged") if p.relation == "expected" else p for p in a.content)),))
                            done = True
                        elif corruption == "predecessor":
                            v = replace(v, attributes=attributes({**attrs(v), "predecessor": RULE})); done = True
                    versions.append(v)
                changed.append(replace(tx, versions=tuple(versions)))
            self.assertTrue(done)
            with self.assertRaises(ValueError): audit(changed, e.access.checkpoint())

    def test_generated_state_cannot_be_declared(self):
        e = setup_c1(); perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
        with self.assertRaises(ValueError): e.declare("fake", (e.world.resolve(m),))

    def test_observation_cannot_rewrite_its_actual_trial(self):
        from hle_unified.compact import ValuePool
        from hle_unified.particulars import record_registry, Delivery
        e = setup_c1(); perform(e, hypothesis(e)); m = e.job_status(ALICE, "theory")["binding"]
        event = perform(e, trial(e, m)); observation = receive(e, event, ALICE, "observed")
        e.start("start-retention", retention(e, m, observation))
        changed = []
        for tx in e.world.journal():
            values = tuple(replace(v, attributes=attributes({**attrs(v), "condition":"damaged"}))
                           if v.ref == observation else v for v in tx.versions)
            changed.append(replace(tx, versions=values))
        raw = unseal(e.access.checkpoint(), e.access.SCHEMA)
        pool, revised, tokens = ValuePool(record_registry()), ValuePool(record_registry()), []
        pool.load_nodes(raw["nodes"])
        for token in raw["events"]:
            command, result = pool.get(pool.import_token(token))
            if type(result) is Delivery and result.source == observation:
                result = replace(result, particulars=tuple(replace(p, value="damaged")
                    if p.address.key == "condition" else p for p in result.particulars))
            tokens.append(revised.put((command, result)))
        nodes, export = revised.export()
        raw["nodes"], raw["events"] = nodes, [export(t) for t in tokens]
        with self.assertRaisesRegex(ValueError, "observation rewrites"):
            audit(changed, seal(e.access.SCHEMA, raw))

    def test_retained_output_can_feed_a_new_model(self):
        e = setup_c1(); refs = run_circuit(e)
        request = replace(hypothesis(e, "retheorize"), input=refs["retained"])
        perform(e, request)
        new_model = e.job_status(ALICE, "retheorize")["binding"]
        self.assertEqual(crux_content.model(e.participant_view(ALICE), refs["model"])[1]["expected"], "damaged")
        self.assertEqual(crux_content.model(e.participant_view(ALICE), new_model)[1]["expected"], "serviceable")
        self.assertEqual(audit(e.world.journal(), e.access.checkpoint())["c1_movements"], 4)

    def test_existing_institution_continues_identically_after_upgrade(self):
        from tests_u12.fixtures import setup12, establish12
        from hle_unified.institution_audit import audit as institution_audit
        old, group = setup12(patterns=())
        upgraded = CruxEngine.from_u14(old.checkpoint())
        for e in (old, upgraded): establish12(e, group)
        self.assertEqual(old.world.checkpoint(), upgraded.world.checkpoint())
        self.assertEqual(old.access.checkpoint(), upgraded.access.checkpoint())
        self.assertTrue(institution_audit(upgraded.world.journal())["passed"])

    def test_u14_checkpoint_import_and_legacy_api_meaning(self):
        old, refs = circuit()
        payload = unseal(old.checkpoint(), old.SCHEMA)
        u14 = InstitutionEngine.restore(seal(InstitutionEngine.SCHEMA, payload))
        upgraded = CruxEngine.from_u14(u14.checkpoint())
        self.assertEqual(upgraded.world.checkpoint(), u14.world.checkpoint())
        self.assertEqual(upgraded.access.checkpoint(), u14.access.checkpoint())
        self.assertEqual(upgraded._commands, u14._commands)
        d = upgraded.job_status(ALICE, "retain")
        self.assertEqual((d["origin"], d["destination"]), ("IT", "I"))
        self.assertEqual(len(RECIPES), 3)
