import hashlib
import json
import unittest

from hle.cards import CARDS, card
from hle.codec import canonical
from hle.contracts import ClaimStatus, Proposition, WorkStatus
from hle.memory_records import BindDraft, ContextDraft, CursorDraft, LINKED, MemoryCommand, RecallQuery, WriteDraft
from hle.world_records import Credit
from probe.decision import decide, permitted
from probe.fixtures import ALICE, BOB, ROOM, SCOPE, make_fixture, perform, bind
from probe.recurrence import CANONICAL, ORDERS, Phase, Session, schedule


class RecurrenceContract(unittest.TestCase):
    def test_all_start_pairs_and_orders_against_modular_oracle(self):
        for order in ORDERS:
            for outer in range(9):
                for inner in range(3):
                    with self.subTest(order=order, outer=outer, inner=inner):
                        start = phase = Phase(outer, inner)
                        states, inner_wraps, outer_wraps = [], 0, 0
                        for k in range(9):
                            self.assertEqual((phase.outer, phase.inner), ((outer + k) % 9, (inner + k) % 3))
                            self.assertEqual(phase.cues(order), ((outer + k) % 9 + 1, (outer + k) % 9 + 10, order[(inner + k) % 3]))
                            states.append(phase)
                            inner_wraps += phase.inner == 2
                            outer_wraps += phase.outer == 8
                            phase = phase.advance()
                        self.assertEqual((len(set(states)), inner_wraps, outer_wraps), (9, 3, 1))
                        self.assertEqual(phase, start)

    def test_three_disjoint_offsets_and_dwell_negative_control(self):
        orbits = [{((e + k) % 9, k % 3) for k in range(9)} for e in range(3)]
        self.assertEqual(len(set.union(*orbits)), 27)
        self.assertFalse(orbits[0] & orbits[1])
        dwell = [k // 3 for k in range(9)]
        wraps = sum(dwell[k] == 2 and dwell[(k + 1) % 9] == 0 for k in range(9))
        self.assertEqual(wraps, 1)
        self.assertNotEqual(wraps, 3)

    def test_schedule_preserves_catalog_and_repeat_counts(self):
        self.assertEqual(len(CARDS), 130)
        before = tuple(CARDS)
        seq = [g[0] for g in schedule(CANONICAL)]
        self.assertEqual(len(seq), 27)
        self.assertEqual([seq.count(r) for r in range(1, 22)], [1] * 18 + [3] * 3)
        self.assertEqual([card(f"arcana:{r}").folded_location for r in (1, 10, 19)], [1, 1, 1])
        self.assertEqual(len({card(f"arcana:{r}").ref for r in (1, 10, 19)}), 3)
        self.assertEqual(schedule(CANONICAL), schedule("generic_same_sequence"))
        self.assertEqual(tuple(CARDS), before)

    def test_all_orders_cover_same_unique_cues_without_selecting_direction(self):
        schedules = [schedule("recurrence_" + "".join(map(str, p))) for p in ORDERS]
        self.assertEqual(len(set(schedules)), 6)
        for groups in schedules:
            self.assertEqual({r for g in groups for r in g}, set(range(1, 22)))


class PaidRecallFidelity(unittest.TestCase):
    def test_partial_unpaid_and_frame_completion(self):
        f = make_fixture(energy=106)
        s = Session(f.world, ALICE)
        self.assertEqual(s.step(), 1)  # Snapshot seed; no fragment visited yet.
        self.assertFalse(s.results())
        self.assertEqual((s.index, s.phase), (0, Phase()))
        self.assertEqual(s.step(), 0)
        self.assertFalse(s.results())
        for counter in range(5):
            f.world.execute(Credit(f"credit:{counter}", ALICE, 1, 1, "fidelity replenishment"))
            self.assertEqual(s.step(), 1)
        self.assertEqual((s.index, s.phase), (3, Phase(1, 1)))

    def test_energy_and_time_deplete_independently(self):
        for energy, time_budget in ((105, 110), (110, 105)):
            f = make_fixture(energy=energy, time_budget=time_budget)
            s = Session(f.world, ALICE)
            self.assertEqual(s.step(), 0)
            self.assertEqual(s.index, 0)
            f.world.execute(Credit("resume", ALICE, 2 if energy == 105 else 0,
                2 if time_budget == 105 else 0, "independent resource test"))
            self.assertEqual([s.step(), s.step()], [1, 1])
            self.assertEqual(s.index, 1)

    def test_exact_retry_does_not_double_charge_or_publish(self):
        f = make_fixture(); s = Session(f.world, ALICE)
        s.step()
        command = f.world._journal[-1].command
        before = s.checkpoint()
        f.world.execute(command)
        self.assertEqual(s.checkpoint(), before)

    def test_restore_at_every_prefix_continues_identically(self):
        f = make_fixture(); s = Session(f.world, ALICE)
        for split in range(55):
            restored = Session.restore(s.checkpoint())
            self.assertEqual(restored.checkpoint(), s.checkpoint())
            if not s.done:
                restored.step(); s.step()
                self.assertEqual(restored.checkpoint(), s.checkpoint())
        self.assertTrue(s.done)

    def test_rehashed_invented_cursor_or_phase_rejected(self):
        f = make_fixture(); s = Session(f.world, ALICE); s.step()
        for key, value in (("index", 1), ("calls", 2), ("phase", [1, 1])):
            data = json.loads(s.checkpoint()); data["body"][key] = value
            data["sha256"] = hashlib.sha256(canonical(data["body"]).encode()).hexdigest()
            with self.assertRaises(ValueError):
                Session.restore(canonical(data))

    def test_real_memory_context_and_same_fold_remain_distinct(self):
        f = make_fixture(); w = f.world
        perform(w, "context", ContextDraft("other", "other scene"))
        context = w._journal[-1].contexts[0].ref
        target = f.by_cue[1]
        original = w.memory_head(ALICE, target.key)
        perform(w, "other:write", WriteDraft("other", (Proposition(target, "owned_by", BOB, context, SCOPE),),
            (), ClaimStatus.ENDORSED, None, "context separation fixture"), (original.ref,))
        other = w.memory_head(ALICE, "other")
        perform(w, "other:bind", BindDraft("other", card("arcana:1").ref, context, other.ref, SCOPE), (other.ref,))
        for rank in (1, 10, 19):
            query = RecallQuery((card(f"arcana:{rank}").ref,), ROOM, w.now)
            job = perform(w, f"read:{rank}", query)
            result = w.recall_result(ALICE, job.result)
            self.assertEqual([h.memory for h in result.hits], [w.memory_head(ALICE, f.by_cue[rank].key).ref])

    def test_frozen_pending_binding_and_new_revisit(self):
        f = make_fixture(); w = f.world; s = Session(w, ALICE)
        target = f.by_cue[1]; old = w.memory_head(ALICE, target.key)
        old_binding = w.binding_head(ALICE, "cue:1")
        s.step()  # Root snapshot points to exact old revision.
        f.change(1)
        s.step()
        self.assertEqual(s.results()[0].hits[0].memory, old.ref)
        self.assertEqual(w.resolve_binding(ALICE, old_binding.ref).target, old.ref)
        job = perform(w, "fresh", RecallQuery((card("arcana:1").ref,), ROOM, w.now))
        self.assertEqual(w.recall_result(ALICE, job.result).hits[0].memory, w.memory_head(ALICE, target.key).ref)
        self.assertNotEqual(old.ref, w.memory_head(ALICE, target.key).ref)

    def test_six_vertex_walk_is_not_three_frame_slots(self):
        f = make_fixture(); w = f.world
        leaf = w.memory_head(ALICE, f.by_cue[1].key)
        chain = [leaf.ref]
        for k in range(5):
            perform(w, f"chain:{k}", WriteDraft(f"chain:{k}", (), (chain[-1],), ClaimStatus.ENDORSED,
                None, "six vertex walk fixture"), (chain[-1],))
            chain.append(w.memory_head(ALICE, f"chain:{k}").ref)
        bind(w, w.read_revision(ALICE, chain[-1]), 1, "cue:1", "chain", w.binding_head(ALICE, "cue:1"))
        perform(w, "chain:navigation", CursorDraft((card("arcana:1").ref,), LINKED, 5))
        s = Session(w, ALICE)
        for _ in range(7): s.step()
        self.assertEqual(s.index, 1)
        self.assertEqual([v.memory for v in s.results()[0].visited], list(reversed(chain)))
        self.assertEqual(len(s.results()[0].visited), 6)

    def test_adapter_cannot_use_unpublished_visits_or_inbox(self):
        f = make_fixture(); s = Session(f.world, ALICE)
        s.step()
        results, memories = permitted(s)
        owner, _ = decide(ALICE, BOB, f.by_cue[1], results, memories)
        self.assertIsNone(owner)
        self.assertEqual(memories, ())

    def test_static_repeat_has_no_new_content_but_rebinding_can_refresh(self):
        for change in (False, True):
            f = make_fixture(); s = Session(f.world, ALICE)
            for _ in range(18): s.step()
            if change: f.change(19)
            for _ in range(6): s.step()
            first = s.results()[2].hits[0].memory
            second = s.results()[11].hits[0].memory
            self.assertEqual(first == second, not change)


if __name__ == "__main__":
    unittest.main(verbosity=2)
