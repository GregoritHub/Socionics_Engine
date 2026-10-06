from dataclasses import replace
import unittest

from hle.contracts import ClaimStatus, EvidenceStatus
from hle_unified import codec, legacy
from hle_unified.records import (
    ObjectVersion, Role, Material, Memory, Agency, Governance, Relation, Endpoint,
    Attribute, Account, Attitude, Assessment, Composition, Definition, SourceStatus,
    Occurrence, Lifecycle, ChangeKind, Moment, TimeScope, Proposition, LegacyPayload)
from hle_unified.store import ObjectStore, next_version
from .fixtures import WRITER, ALICE, BOB, ROOM, UNIT, FORM, LAW, RULE, base, bowl, event, ref, ident, active_quantities


class Acceptance(unittest.TestCase):
    def test_U2_01_instances(self):
        s = base()
        left, right = bowl("left"), bowl("right")
        self.assertEqual((left.label, left.facets, left.definition), (right.label, right.facets, right.definition))
        s.create("bowls", WRITER, (left, right))
        self.assertNotEqual(left.ref.identity, right.ref.identity)
        s.transfer("give-left", WRITER, left.ref, BOB.identity, actor=ALICE.identity)
        self.assertEqual(s.head(left.ref.identity).facet(Material).owner, BOB.identity)
        self.assertEqual(s.head(right.ref.identity), right)
        self.assertEqual(s.resolve(left.ref).facet(Material).owner, ALICE.identity)
        self.assertEqual(s.head(left.ref.identity).previous, left.ref)
        r = ObjectStore.restore(s.checkpoint())
        self.assertEqual(r.checkpoint(), s.checkpoint())
        self.assertNotEqual(r.head(left.ref.identity).ref, r.head(right.ref.identity).ref)

    def test_U2_02_nonmental_material(self):
        s = base()
        tool = bowl("tool", label="Ordinary tool")
        s.create("tool", WRITER, (tool,))
        s.transfer("give-tool", WRITER, tool.ref, BOB.identity, actor=ALICE.identity)
        current = s.head(tool.ref.identity)
        self.assertEqual(current.facet(Material).custodian, BOB.identity)
        for version in (tool, current):
            self.assertEqual(version.roles, (Role.MATERIAL,))
            for cls in (Memory, Agency, Governance):
                self.assertIsNone(version.facet(cls))
        self.assertEqual(active_quantities(s), {(BOB.identity, UNIT): 1})

    def test_U2_03_relation_identity(self):
        s = base()
        tool, cause = bowl("loaned"), event("agreement", referent=RULE)
        s.create("declared", WRITER, (tool, cause))
        relation = Relation("owes_return", (Endpoint("debtor", ALICE), Endpoint("creditor", BOB),
            Endpoint("item", tool.ref)), True, ROOM, TimeScope(Moment(2, 0), Moment(9, 0)),
            (Attribute("deadline", 9),))
        obligation = ObjectVersion(ref("obligation"), WRITER, "Return obligation",
            (Role.RELATION, Role.COMMITMENT), (relation,), definition=RULE)
        s.create("commit", WRITER, (obligation,), evidence=(cause.ref,))
        updated = next_version(obligation, facets=(replace(relation, terms=(Attribute("deadline", 12),),
            scope=TimeScope(Moment(2, 0), Moment(12, 0))),))
        s.revise("extend", WRITER, updated, evidence=(cause.ref,), reason="Both parties extend the deadline in this fixture")
        self.assertEqual(s.resolve(obligation.ref).facet(Relation), relation)
        self.assertEqual(updated.facet(Relation).endpoints, relation.endpoints)
        self.assertEqual(updated.facet(Relation).context, relation.context)
        self.assertEqual(s.journal()[-1].lineage[0].inputs, (obligation.ref,))
        self.assertEqual(s.journal()[-1].lineage[0].evidence, (cause.ref,))
        self.assertEqual(ObjectStore.restore(s.checkpoint()).resolve(obligation.ref), obligation)

    def test_U2_04_hypothesis(self):
        s = base()
        tool = bowl("target")
        s.create("target", WRITER, (tool,))
        false = Proposition(tool.ref, "condition", "broken", ROOM, TimeScope(Moment(8, 0), None))
        prediction = ObjectVersion(ref("prediction"), "actor.alice", "The bowl may break", (Role.CLAIM,),
            (Account(tool.ref, (false,), Moment(3, 0), ALICE.identity),), occurrence=Occurrence.HYPOTHETICAL)
        count = len(s.actual_events())
        s.create("predict", "actor.alice", (prediction,), actor=ALICE.identity)
        self.assertEqual(len(s.actual_events()), count)
        self.assertEqual(s.head(tool.ref.identity), tool)
        stance = ObjectVersion(ref("endorsement"), "actor.alice", "Believed forecast", (Role.ATTITUDE,),
            (Attitude(ALICE.identity, prediction.ref, ClaimStatus.ENDORSED, 100),))
        s.create("endorse", "actor.alice", (stance,), actor=ALICE.identity)
        observation = event("inspection", at=8, referent=tool.ref,
            content=(replace(false, object="intact"),))
        s.create("inspect-fixture", WRITER, (observation,))
        verdict = ObjectVersion(ref("verdict"), "evaluator", "Forecast contradicted", (Role.ASSESSMENT,),
            (Assessment(prediction.ref, "factual_agreement", EvidenceStatus.FAILED,
                        (observation.ref,), "At the forecast time, the declared inspection shows intact material."),))
        s.create("assess", "evaluator", (verdict,))
        self.assertEqual(s.resolve(prediction.ref).occurrence, Occurrence.HYPOTHETICAL)
        self.assertEqual(s.resolve(stance.ref).facet(Attitude).endorsement, ClaimStatus.ENDORSED)
        self.assertEqual(len(s.actual_events()), count + 1)
        self.assertEqual(s.head(tool.ref.identity), tool)
        self.assertEqual(ObjectStore.restore(s.checkpoint()).checkpoint(), s.checkpoint())

    def test_U2_05_historical_revision(self):
        s = base()
        old_rule = s.resolve(RULE)
        statement = Proposition(ALICE, "applies", RULE, ROOM, TimeScope(Moment(1, 0), None))
        memory = ObjectVersion(ref("remembered-rule"), "actor.alice", "Earlier terms", (Role.CLAIM,),
            (Account(RULE, (statement,), Moment(1, 0), ALICE.identity),), occurrence=Occurrence.REMEMBERED_CLAIM)
        s.create("remember", "actor.alice", (memory,))
        new_rule = next_version(old_rule, facets=(Definition("Return before tick 5.", SourceStatus.ENGINEERING),))
        s.revise("new-rule", WRITER, new_rule, reason="Prospective rule revision")
        self.assertEqual(s.journal()[-1].lineage[0].kind, ChangeKind.DEFINITION)
        r = ObjectStore.restore(s.checkpoint())
        historical_binding = r.resolve(memory.ref).facet(Account).referent
        self.assertEqual(r.resolve(historical_binding).facet(Definition).meaning, old_rule.facet(Definition).meaning)
        self.assertEqual(r.head(RULE.identity).facet(Definition).meaning, "Return before tick 5.")
        self.assertEqual(r.resolve(memory.ref).facet(Account).content[0].object, RULE)

    def test_U2_06_split_merge(self):
        s = base()
        original = bowl("stock", 10)
        s.create("stock", WRITER, (original,))
        before = active_quantities(s)
        a, b = bowl("part-a", 4), bowl("part-b", 6)
        s.restructure("divide", WRITER, (original.ref,), (a, b), actor=ALICE.identity, rule=LAW, reason="Divide ten into four and six")
        self.assertEqual(active_quantities(s), before)
        self.assertEqual(s.head(original.ref.identity).lifecycle, Lifecycle.RETIRED)
        self.assertEqual(s.resolve(original.ref).lifecycle, Lifecycle.ACTIVE)
        joined = bowl("joined", 10)
        s.restructure("combine", WRITER, (a.ref, b.ref), (joined,), actor=ALICE.identity, rule=LAW, reason="Combine owned parts")
        replacement = bowl("replacement", 10)
        s.restructure("replace", WRITER, (joined.ref,), (replacement,), actor=ALICE.identity, rule=LAW, reason="Replace identity under the declared conservation law")
        self.assertEqual(active_quantities(s), before)
        self.assertEqual([tx.lineage[0].kind for tx in s.journal()[-3:]], [ChangeKind.DIVIDE, ChangeKind.COMBINE, ChangeKind.REPLACE])
        checkpoint = s.checkpoint()
        with self.assertRaises(ValueError):
            s.restructure("double-spend", WRITER, (original.ref,), (bowl("stolen", 10),), actor=ALICE.identity, rule=LAW, reason="Cannot consume again")
        self.assertEqual(s.checkpoint(), checkpoint)
        r = ObjectStore.restore(checkpoint)
        self.assertEqual(active_quantities(r), before)
        self.assertEqual(r.checkpoint(), checkpoint)

    def test_U2_07_finite_cycle(self):
        s = base()
        member = ObjectVersion(ref("delegate"), WRITER, "Delegate", (Role.PERSON,),
            (Memory(ident("delegate")),), attributes=(Attribute("represents", ref("group")),))
        group = ObjectVersion(ref("group"), WRITER, "Workshop circle", (Role.COLLECTIVE,),
            (Composition((member.ref.identity,), "Voluntary workshop membership", summary_dependencies=(member.ref,)), Governance((RULE,))))
        s.create("cyclic-pair", WRITER, (member, group))
        cp = s.checkpoint()
        self.assertLess(len(cp), 20000)
        r = ObjectStore.restore(cp)
        represented = r.resolve(member.ref).attributes[0].value
        self.assertIn(member.ref.identity, r.resolve(represented).facet(Composition).members)
        revised = next_version(group, facets=(replace(group.facet(Composition), members=(BOB.identity,), summary_dependencies=(BOB,)), Governance((RULE,))))
        r.revise("membership-change", WRITER, revised, reason="Delegate leaves and Bob joins in the fixture")
        self.assertEqual(r.journal()[-1].lineage[0].kind, ChangeKind.MEMBERSHIP)
        self.assertEqual(r.resolve(group.ref).facet(Composition).members, (member.ref.identity,))
        self.assertEqual(r.resolve(member.ref).facet(Memory).entries, ())
        self.assertIsNone(r.resolve(BOB).facet(Agency))
        self.assertEqual(ObjectStore.restore(r.checkpoint()).checkpoint(), r.checkpoint())

    def test_U2_08_legacy_adapter(self):
        from hle.contracts import Ref, Kind, WorkStatus
        from hle.demo import config, request, ALICE as LA, BOB as LB, BOX
        from hle.world import World
        from hle.world_records import Attempt, TRANSFER, Credit
        from tests.reference_world import fold
        for kind in Kind:
            for revision in (1, 2, 7):
                original = Ref(kind, "same:key/雪", revision)
                self.assertEqual(legacy.recover_ref(legacy.adapt_ref(original)), original)
        w = World(config(energy=1, time=8))
        bridge = legacy.LegacyWorldBridge(w.config)
        start = Attempt("start", "job", request(LA, TRANSFER, (BOX, LB)))
        w.execute(start)
        self.assertEqual(legacy.recover_object(bridge.execute_adapted(legacy.adapt(start))), w.truth.journal()[-1].event)
        self.assertEqual(w.truth.journal()[-1].event.outcome, WorkStatus.PARTIAL)
        view = codec.loads(codec.dumps(bridge.checkpoint()))
        self.assertEqual(legacy.checkpoint_text(view), w.checkpoint())
        restored = legacy.LegacyWorldBridge.restore(view)
        self.assertEqual(legacy.recover_object(restored.transaction(1)), w.truth.journal()[1])
        for actor in (LA, LB):
            av, cursor = restored.participant_input(legacy.adapt_ref(actor))
            self.assertEqual((legacy.recover(av), cursor), w.participant_input(actor))
        for cmd in (Credit("credit", LA, 1, 0, "Declared R2 test supply; not an R21B episode top-up"),
                    Attempt("finish", "job", request(LA, TRANSFER, (BOX, LB)))):
            expected = w.execute(cmd)
            self.assertEqual(legacy.recover_object(restored.execute(cmd)), expected)
            self.assertEqual(restored.legacy_checkpoint(), w.checkpoint())
            self.assertEqual(w.state(), fold(w.config, w.truth.journal()))
        history = restored.ownership_history(legacy.adapt_ref(BOX))
        self.assertEqual(len(history), 2)
        self.assertEqual(legacy.recover(history[0].facet(LegacyPayload).value).object, LA)
        self.assertEqual(legacy.recover(history[1].facet(LegacyPayload).value).object, LB)
        self.assertEqual(history[1].previous, history[0].ref)
        self.assertEqual(w.truth.wallet(LA).energy, 0)
        self.assertEqual(w.truth.task(LA, "job").completed, 2)


if __name__ == "__main__":
    unittest.main()
