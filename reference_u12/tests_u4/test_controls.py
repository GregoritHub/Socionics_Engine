import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hle_unified import codec
from hle_unified.compact import seal, unseal
from hle_unified.records import ChangeKind, Lineage, Memory, Agency
from hle_unified.operation_audit import audit_transactions
from hle_unified.material import available
from .fixtures import *


class U4Controls(unittest.TestCase):
    def rejected_without_change(self, engine, action):
        before = engine.checkpoint()
        with self.assertRaises((ValueError, KeyError)):
            action()
        self.assertEqual(engine.checkpoint(), before)

    def primitive(self, engine, key, kind, *, actor=ALICE, target=None, stock=None, **kwargs):
        source = target or stock
        return OperationRequest(key, actor, kind, ROOM, evidence=evidence(engine, actor, source),
                                target=target, stock=stock, **kwargs)

    def test_transfer_moves_real_ownership_and_custody(self):
        e = setup()
        perform(e, self.primitive(e, "gift", "transfer", target=KIT, recipient=BOB, participants=(BOB,)))
        m = e.world.head(KIT.identity).facet(Material)
        self.assertEqual((m.owner, m.custodian), (BOB, BOB))
        self.assertEqual(e.world.resolve(KIT).facet(Material).owner, ALICE)

    def test_return_changes_custody_and_exact_obligation(self):
        e = setup()
        basics(e, BOB)
        result = perform(e, self.primitive(e, "return", "return", actor=BOB, target=BORROWED, relation=OBLIGATION, participants=(ALICE,)))
        material = e.world.head(BORROWED.identity).facet(Material)
        self.assertEqual((material.owner, material.custodian), (ALICE, ALICE))
        after = e.world.head(OBLIGATION.identity)
        self.assertEqual(dict((a.name, a.value) for a in after.facet(Relation).terms)["status"], "fulfilled")
        self.assertEqual(dict((a.name, a.value) for a in e.world.resolve(OBLIGATION).facet(Relation).terms)["status"], "open")
        self.assertEqual(attrs(e.world.resolve(result))["relation"], after.ref)

    def test_use_wears_and_eventually_damages_a_tool(self):
        e = setup()
        for i in range(10):
            target = e.world.head(KIT.identity).ref
            if i:
                show(e, ALICE, target)
            perform(e, self.primitive(e, "use-" + str(i), "use", target=target))
        self.assertEqual(e.world.head(KIT.identity).facet(Material).condition, "damaged")
        self.assertEqual(attrs(e.world.head(KIT.identity))["wear"], 10)
        show(e, ALICE, e.world.head(KIT.identity).ref)
        last = perform(e, self.primitive(e, "overuse", "use", target=e.world.head(KIT.identity).ref))
        self.assertEqual(attrs(e.world.resolve(last))["outcome"], "failed")
        self.assertEqual(attrs(e.world.head(KIT.identity))["wear"], 10)

    def test_care_consumes_supply_and_reduces_wear(self):
        e = setup()
        perform(e, repair(e))
        target = e.world.head(KIT.identity).ref
        show(e, ALICE, target)
        perform(e, self.primitive(e, "care", "care", target=target, stock=CARE))
        self.assertEqual(attrs(e.world.head(KIT.identity))["wear"], 0)
        self.assertEqual(available(e.world.head(CARE.identity)), 1)

    def test_declared_condition_change_requires_paid_work(self):
        e = setup()
        before = e.wallet(ALICE)["energy"]
        perform(e, self.primitive(e, "damage", "damage", target=KIT))
        self.assertEqual(e.world.head(KIT.identity).facet(Material).condition, "damaged")
        self.assertEqual(before - e.wallet(ALICE)["energy"], 3)

    def test_explicit_consumption_sink_never_makes_negative_stock(self):
        e = setup(quantity=2)
        perform(e, self.primitive(e, "consume", "consume", stock=STOCK, amount=2))
        value = e.world.head(STOCK.identity)
        self.assertEqual((value.facet(Material).quantity, attrs(value)["consumed"], available(value)), (2, 2, 0))
        show(e, ALICE, value.ref)
        perform(e, self.primitive(e, "consume-again", "consume", stock=value.ref))
        self.assertEqual(e.job_status(ALICE, "consume-again")["status"], "failed")
        self.assertEqual(e.world.head(STOCK.identity), value)

    def test_inspection_samples_current_physical_identity_after_payment(self):
        e = setup()
        perform(e, repair(e))
        current = e.world.head(SAW.identity).ref
        # Alice still has only the original accessible saw revision.
        inspection = perform(e, self.primitive(e, "inspect", "inspect", target=SAW))
        self.assertEqual(attrs(e.world.resolve(inspection))["target"], current)
        self.assertFalse(e.participant_view(ALICE).resolve(current))
        obs = receive(e, inspection, ALICE, "inspect")
        self.assertEqual(next(p.value for p in e.participant_view(ALICE).resolve(obs) if p.address.key == "condition"), "serviceable")

    def test_zero_budget_defers_without_material_result(self):
        e = setup(budget=20)
        self.assertEqual(e.wallet(ALICE)["energy"], 0)
        e.start("start", repair(e))
        e.advance("work", ALICE, "repair", 100)
        self.assertEqual(e.job_status(ALICE, "repair")["spent"], 0)
        self.rejected_without_change(e, lambda: e.commit("premature", ALICE, "repair"))
        self.assertEqual(e.world.head(SAW.identity).ref, SAW)

    def test_time_budget_limits_work_even_with_energy(self):
        e = setup(budget=100, time_budget=22)
        e.start("start", repair(e))
        e.advance("work", ALICE, "repair", 100)
        self.assertEqual(e.job_status(ALICE, "repair")["completed"], 2)
        self.assertEqual(e.wallet(ALICE)["time"], 0)
        self.assertEqual(e.wallet(ALICE)["energy"], 78)

    def test_cancellation_preserves_spent_work_and_releases_reservations(self):
        e = setup()
        e.start("a", repair(e, "a"))
        e.advance("a-work", ALICE, "a", 2)
        e.start("b", repair(e, "b", SAW2))
        before = e.wallet(ALICE)["energy"]
        e.cancel("cancel", ALICE, "a")
        self.assertEqual(e.wallet(ALICE)["energy"], before)
        self.assertEqual(e.job_status(ALICE, "a")["spent"], 2)
        e.advance("b-work", ALICE, "b", 100)
        e.commit("b-effect", ALICE, "b")
        self.assertEqual(e.job_status(ALICE, "b")["status"], "succeeded")

    def test_insufficient_or_wrong_resource_does_not_partially_repair(self):
        e = setup()
        request = replace(repair(e), stock=CARE)
        before = (e.world.head(SAW.identity), e.world.head(KIT.identity), e.world.head(CARE.identity))
        perform(e, request)
        self.assertEqual(e.job_status(ALICE, request.key)["status"], "failed")
        self.assertEqual((e.world.head(SAW.identity), e.world.head(KIT.identity), e.world.head(CARE.identity)), before)

    def test_wrong_custodian_pays_but_cannot_use_tool(self):
        e = setup()
        basics(e, BOB)
        perform(e, self.primitive(e, "take-use", "use", actor=BOB, target=KIT))
        self.assertEqual(e.job_status(BOB, "take-use")["status"], "failed")
        self.assertEqual(e.job_status(BOB, "take-use")["spent"], 3)
        self.assertEqual(e.world.head(KIT.identity).ref, KIT)

    def test_unknown_and_undelivered_input_cannot_start(self):
        e = setup()
        basics(e, BOB)
        hidden = ref("private-tool")
        # Existing private source differs from a missing source, but neither is
        # a permitted input for the participant request.
        self.rejected_without_change(e, lambda: e.start("hidden", replace(repair(e), target=hidden)))
        self.rejected_without_change(e, lambda: e.start("wrong-evidence", replace(repair(e), evidence=(DetailAddress("not-delivered", "name"),))))

    def test_duplicate_input_roles_and_malformed_work_are_rejected(self):
        e = setup()
        self.rejected_without_change(e, lambda: e.start("bad", replace(repair(e), tool=SAW)))
        e.start("start", repair(e))
        for limit in (0, -1, True, 1.0):
            with self.subTest(limit=limit):
                self.rejected_without_change(e, lambda: e.advance("invalid:" + str(limit), ALICE, "repair", limit))

    def test_same_command_is_idempotent_but_different_content_is_rejected(self):
        e = setup()
        request = repair(e)
        first = e.start("start", request)
        self.assertEqual(e.start("start", request), first)
        e.advance("work", ALICE, "repair", 100)
        budget = e.wallet(ALICE)["energy"]
        e.advance("work", ALICE, "repair", 100)
        self.assertEqual(e.wallet(ALICE)["energy"], budget)
        event = e.commit("finish", ALICE, "repair")
        self.assertEqual(e.commit("finish", ALICE, "repair"), event)
        self.rejected_without_change(e, lambda: e.start("start", replace(request, key="different")))
        self.rejected_without_change(e, lambda: e.commit("again", ALICE, "repair"))

    def test_threaded_contenders_reserve_only_one_shared_tool_and_stock(self):
        e = setup(quantity=1)
        requests = (repair(e, "a", SAW), repair(e, "b", SAW2))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda r: e.start("start:" + r.key, r), requests))
        statuses = [e.job_status(ALICE, r.key)["status"] for r in requests]
        self.assertEqual(sorted(statuses), ["pending", "waiting"])
        winner = requests[statuses.index("pending")]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: e.advance("same-work", ALICE, winner.key, 100), range(4)))
            events = list(pool.map(lambda _: e.commit("same-effect", ALICE, winner.key), range(4)))
        self.assertEqual(len(set(events)), 1)
        self.assertEqual(e.job_status(ALICE, winner.key)["spent"], 6)
        self.assertEqual(available(e.world.head(STOCK.identity)), 0)
        self.assertTrue(audit_transactions(e.world.journal())["passed"])

    def test_multi_resource_reservation_is_all_or_nothing(self):
        e = setup()
        e.start("hold", self.primitive(e, "hold", "use", target=KIT))
        e.start("wait", repair(e, "wait"))
        # Waiting repair did not reserve its otherwise-free target or stock.
        e.start("stock", self.primitive(e, "stock", "consume", stock=STOCK))
        self.assertEqual(e.job_status(ALICE, "stock")["status"], "pending")
        self.assertEqual(e.job_status(ALICE, "wait")["status"], "waiting")

    def test_stale_tool_after_wait_is_rejected(self):
        e = setup()
        e.start("wear", self.primitive(e, "wear", "use", target=KIT))
        e.start("repair", repair(e))
        e.advance("wear-work", ALICE, "wear", 100)
        e.commit("wear-effect", ALICE, "wear")
        e.advance("repair-work", ALICE, "repair", 100)
        e.commit("repair-effect", ALICE, "repair")
        self.assertEqual(e.job_status(ALICE, "repair")["failure"], "stale_dependency")
        self.assertEqual(available(e.world.head(STOCK.identity)), 2)

    def test_stale_stock_after_wait_is_rejected(self):
        e = setup()
        e.start("consume", self.primitive(e, "consume", "consume", stock=STOCK))
        e.start("repair", repair(e))
        e.advance("consume-work", ALICE, "consume", 100)
        e.commit("consume-effect", ALICE, "consume")
        e.advance("repair-work", ALICE, "repair", 100)
        e.commit("repair-effect", ALICE, "repair")
        self.assertEqual(e.job_status(ALICE, "repair")["failure"], "stale_dependency")
        self.assertEqual(e.world.head(KIT.identity).ref, KIT)

    def test_stale_target_after_wait_is_rejected(self):
        e = setup()
        e.start("use", self.primitive(e, "use", "use", target=KIT))
        e.start("damage", self.primitive(e, "damage", "damage", target=KIT))
        e.advance("use-work", ALICE, "use", 100)
        e.commit("use-effect", ALICE, "use")
        e.advance("damage-work", ALICE, "damage", 100)
        e.commit("damage-effect", ALICE, "damage")
        self.assertEqual(e.job_status(ALICE, "damage")["failure"], "stale_dependency")
        self.assertEqual(e.world.head(KIT.identity).facet(Material).condition, "serviceable")

    def test_stale_return_relation_preserves_custody_and_work(self):
        e = setup()
        basics(e, BOB)
        r = self.primitive(e, "return", "return", actor=BOB, target=BORROWED, relation=OBLIGATION)
        e.start("return", r)
        e.advance("partial", BOB, "return", 1)
        old = e.world.resolve(OBLIGATION)
        rel = replace(old.facet(Relation), terms=(Attribute("status", "disputed"),))
        e.declare("dispute", (next_version(old, facets=(rel,)),))
        e.advance("remaining", BOB, "return", 100)
        e.commit("return-effect", BOB, "return")
        self.assertEqual(e.job_status(BOB, "return")["failure"], "stale_dependency")
        self.assertEqual(e.world.head(BORROWED.identity).facet(Material).custodian, BOB)

    def test_hidden_definition_change_does_not_change_view_or_probe(self):
        e = setup()
        e.start("start", repair(e))
        before = e.participant_view(ALICE).bytes()
        choose = lambda view: (len(view.snapshot.particulars), view.can_use(REPAIR, ROOM))
        decision = choose(e.participant_view(ALICE))
        old = e.world.resolve(FORM)
        e.declare("hidden", (next_version(old, facets=(replace(old.facet(Definition), meaning="hidden revision"),)),))
        self.assertEqual(e.participant_view(ALICE).bytes(), before)
        self.assertEqual(choose(e.participant_view(ALICE)), decision)

    def test_later_interpretation_cannot_undo_performed_effect(self):
        e = setup()
        event = perform(e, repair(e))
        obs = receive(e, event, ALICE, "physical")
        first = binding(e, "meaning", ALICE, obs)
        perform(e, first)
        physical = (e.world.head(SAW.identity), e.world.head(STOCK.identity))
        prior = first.binding
        revised = binding(e, "meaning", ALICE, obs, previous=prior, meaning="I mistrust this assistance.")
        perform(e, revised)
        self.assertEqual((e.world.head(SAW.identity), e.world.head(STOCK.identity)), physical)
        self.assertEqual(len(e.participant_view(ALICE).snapshot.bindings), 2)

    def test_reading_procedure_is_not_acquisition_or_physical_authority(self):
        e = setup()
        self.assertFalse(e.participant_view(ALICE).can_use(REPAIR, ROOM))
        request = replace(repair(e), kind="procedure", procedure=REPAIR)
        self.rejected_without_change(e, lambda: e.start("unearned", request))
        self.rejected_without_change(e, lambda: e.start("fake-practice", OperationRequest("acquire", ALICE, "acquire", ROOM, procedure=REPAIR, practice=SAW)))

    def test_supported_acquired_procedure_can_execute_but_has_no_new_affordance(self):
        e = setup()
        event = perform(e, repair(e))
        receive(e, event, ALICE, "practice")
        perform(e, OperationRequest("acquire", ALICE, "acquire", ROOM, procedure=REPAIR, practice=event))
        for source in (KIT, STOCK):
            show(e, ALICE, e.world.head(source.identity).ref)
        r = replace(repair(e, "named", SAW2), kind="procedure", procedure=REPAIR)
        perform(e, r)
        self.assertEqual(e.world.head(SAW2.identity).facet(Material).condition, "serviceable")
        self.assertEqual(available(e.world.head(STOCK.identity)), 0)

    def test_unsupported_named_procedure_is_rejected_before_payment(self):
        e = setup()
        p = ObjectVersion(ref("fly"), WRITER, "Name alone cannot make a tool fly", (Role.PROCEDURE,),
                          (Procedure(("target",), (), (), (), "u4.fly.v1"),))
        e.declare("name", (p,))
        show(e, ALICE, p.ref, selectors=(Selector("procedure", "definition", ("facets", "0")),))
        r = OperationRequest("fly", ALICE, "procedure", ROOM, evidence=evidence(e, ALICE, KIT), target=KIT, procedure=p.ref)
        self.rejected_without_change(e, lambda: e.start("fly-start", r))
        self.rejected_without_change(e, lambda: e.start("disguised", replace(repair(e), procedure=p.ref)))

    def test_partial_acquisition_and_other_actor_practice_do_not_confer_skill(self):
        e = setup()
        basics(e, BOB)
        event = perform(e, repair(e))
        receive(e, event, ALICE, "alice-practice")
        receive(e, event, BOB, "bob-saw-practice")
        r = OperationRequest("acquire", ALICE, "acquire", ROOM, procedure=REPAIR, practice=event)
        e.start("acquire", r)
        e.advance("part", ALICE, "acquire", 1)
        self.assertFalse(e.participant_view(ALICE).can_use(REPAIR, ROOM))
        self.rejected_without_change(e, lambda: e.start("bob-acquire", replace(r, actor=BOB)))

    def test_changed_procedure_invalidates_partial_named_execution(self):
        e = setup()
        event = perform(e, repair(e))
        receive(e, event, ALICE, "practice")
        perform(e, OperationRequest("acquire", ALICE, "acquire", ROOM, procedure=REPAIR, practice=event))
        for source in (KIT, STOCK):
            show(e, ALICE, e.world.head(source.identity).ref)
        request = replace(repair(e, "named", SAW2), kind="procedure", procedure=REPAIR)
        e.start("named", request)
        e.advance("partial", ALICE, "named", 2)
        old = e.world.resolve(REPAIR)
        e.declare("changed-procedure", (next_version(old, facets=(replace(old.facet(Procedure), executor="u4.unsupported.v1"),)),))
        e.advance("rest", ALICE, "named", 100)
        e.commit("effect", ALICE, "named")
        self.assertEqual(e.job_status(ALICE, "named")["failure"], "stale_dependency")
        self.assertEqual(e.job_status(ALICE, "named")["spent"], 6)
        self.assertEqual(e.world.head(SAW2.identity).ref, SAW2)

    def test_new_binding_draft_during_partial_work_invalidates_old_draft(self):
        e = setup()
        event = perform(e, repair(e))
        obs = receive(e, event, ALICE, "practice")
        request = binding(e, "account", ALICE, obs)
        e.start("binding", request)
        e.advance("partial", ALICE, request.key, 1)
        binding(e, "account", ALICE, obs, previous=request.binding, meaning="Reconsidered draft")
        e.advance("rest", ALICE, request.key, 100)
        e.commit("effect", ALICE, request.key)
        self.assertEqual(e.job_status(ALICE, request.key)["failure"], "stale_dependency")
        self.assertFalse(e.participant_view(ALICE).snapshot.bindings)

    def test_native_processing_receipt_is_actor_owned_and_paid(self):
        e = setup()
        event = perform(e, repair(e))
        obs = receive(e, event, ALICE, "physical")
        receipt = e.participant_view(ALICE).snapshot.receipts[-1]
        self.assertEqual((receipt.actor, receipt.required, receipt.completed, receipt.spent), (ALICE, 2, 2, 2))
        self.assertEqual(receipt.inputs, (obs,))
        self.assertEqual(e.world.resolve(receipt.ref).writer, WRITER)
        self.assertFalse(e.participant_view(BOB).snapshot.receipts)

    def test_material_validator_rejects_a_free_effect(self):
        e = setup()
        old = e.world.resolve(SAW)
        change = next_version(old, facets=(replace(old.facet(Material), condition="serviceable"),))
        edge = Lineage(ChangeKind.MATERIAL, (old.ref,), (change.ref,), (FORM,), "unpaid proposed effect", LAW_REF)
        before = e.world.checkpoint()
        with self.assertRaises(ValueError):
            e.world.commit("free-effect", WRITER, (change,), (edge,), actor=ALICE)
        self.assertEqual(e.world.checkpoint(), before)

    def test_partial_processing_restores_without_unlocking_delivery(self):
        e = setup()
        event = perform(e, repair(e))
        obs = e.deliver_event("delivery", event, ALICE)
        r = OperationRequest("read", ALICE, "read", ROOM, delivery="delivery")
        e.start("read", r)
        e.advance("part", ALICE, "read", 1)
        restored = OperationEngine.restore(e.checkpoint())
        self.assertFalse(restored.participant_view(ALICE).resolve(obs))
        self.assertEqual(restored.job_status(ALICE, "read")["completed"], 1)
        restored.advance("rest", ALICE, "read", 1)
        restored.commit("finish", ALICE, "read")
        self.assertTrue(restored.participant_view(ALICE).resolve(obs))

    def test_delayed_delivery_preserves_event_revision_after_later_wear(self):
        e = setup()
        repair_event = perform(e, repair(e))
        repaired = e.world.head(SAW.identity).ref
        show(e, ALICE, repaired)
        perform(e, self.primitive(e, "use", "use", target=repaired))
        obs = receive(e, repair_event, ALICE, "delayed")
        facts = {p.address.key: p.value for p in e.participant_view(ALICE).resolve(obs)}
        self.assertEqual((facts["target"], facts["wear"]), (repaired, 0))
        self.assertEqual(attrs(e.world.head(SAW.identity))["wear"], 1)

    def test_observer_not_in_event_cannot_receive_it(self):
        e = setup()
        event = perform(e, repair(e))
        self.rejected_without_change(e, lambda: e.deliver_event("private", event, EVE))

    def test_failed_outcome_does_not_disclose_hidden_dependency_reason(self):
        e = setup()
        e.start("start", repair(e))
        old = e.world.resolve(FORM)
        e.declare("hidden", (next_version(old, facets=(replace(old.facet(Definition), meaning="secret"),)),))
        e.advance("work", ALICE, "repair", 100)
        event = e.commit("result", ALICE, "repair")
        obs = receive(e, event, ALICE, "failed")
        facts = {p.address.key: p.value for p in e.participant_view(ALICE).resolve(obs)}
        self.assertEqual(facts["outcome"], "failed")
        self.assertNotIn("failure", facts)
        self.assertNotIn("secret", e.participant_view(ALICE).bytes())

    def test_historical_participant_view_survives_u4_backend(self):
        e = setup()
        before = e.participant_view(ALICE)
        through = len(before.snapshot.history)
        event = perform(e, repair(e))
        receive(e, event, ALICE, "later")
        self.assertEqual(e.participant_view(ALICE, through=through).bytes(), before.bytes())

    def test_edited_checkpoint_is_rejected_even_with_recomputed_checksum(self):
        e = setup()
        e.start("start", repair(e))
        e.advance("partial", ALICE, "repair", 2)
        payload = unseal(e.checkpoint(), OperationEngine.SCHEMA)
        payload["world"] = payload["initial"]
        with self.assertRaises(ValueError):
            OperationEngine.restore(seal(OperationEngine.SCHEMA, payload))

    def test_nonmental_tool_remains_nonmental_after_repair(self):
        e = setup()
        perform(e, repair(e))
        saw = e.world.head(SAW.identity)
        self.assertEqual(saw.roles, (Role.MATERIAL,))
        self.assertIsNone(saw.facet(Memory))
        self.assertIsNone(saw.facet(Agency))

    def test_declaration_cannot_supply_material_or_paid_resource_changes(self):
        e = setup()
        self.rejected_without_change(e, lambda: e.declare("free-tool", (tool(ref("free")),)))
        wallet = e.world.resolve(e._wallets[ALICE])
        self.rejected_without_change(e, lambda: e.declare("free-work", (next_version(wallet),)))

    def test_raw_transaction_audit_balances_native_work_and_stock(self):
        e = setup()
        event = perform(e, repair(e))
        receive(e, event, ALICE, "physical")
        result = audit_transactions(e.world.journal())
        self.assertEqual(result["charged_energy"], 28)
        self.assertEqual(result["charged_time"], 28)
        self.assertEqual(result["physical_commits"], 1)
        self.assertEqual(result["active_reservations"], 0)

    def test_auditor_detects_forged_charge_and_physical_result(self):
        e = setup()
        perform(e, repair(e))
        journal = list(e.world.journal())
        index = next(i for i, tx in enumerate(journal) if tx.key == "u4:work:alice:repair")
        tx = journal[index]
        job = tx.versions[0]
        values = attrs(job)
        values["spent"] = 0
        journal[index] = replace(tx, versions=(replace(job, attributes=attributes(values)), *tx.versions[1:]))
        with self.assertRaises(ValueError):
            audit_transactions(tuple(journal))
        journal = list(e.world.journal())
        tx = journal[-1]
        versions = []
        for value in tx.versions:
            if value.ref.identity == SAW.identity:
                d = attrs(value)
                d["wear"] = 1
                value = replace(value, attributes=attributes(d))
            versions.append(value)
        journal[-1] = replace(tx, versions=tuple(versions))
        with self.assertRaises(ValueError):
            audit_transactions(tuple(journal))
