import unittest
from copy import deepcopy
from .fixtures import *
from hle_unified.selection_records import loads, dumps
from hle_unified.workflow_continuation_audit import audit_continuation
from hle_unified.workflow_selection_audit import audit


class ContinuationTests(unittest.TestCase):
    def test_generated_chain_has_causal_material_and_personal_result(self):
        p = chain(); self.assertTrue(p.run(1000)['done'])
        completed = [r for r in p.events if r['status'] == 'episode_complete']
        self.assertEqual([r['recipe'] for r in completed],
                         ['workflow-' + n + '-expenditure-v1' for n in ('theorize', 'apply', 'embody')])
        self.assertTrue(all(r['native_status'] == 'succeeded' for r in completed))
        self.assertEqual(attrs(p.engine.world.head(DEVICE.identity))['wear'], 0)
        self.assertEqual(data(p.engine, query_personal(p))['next_action'], 'use')
        self.assertEqual(audit_continuation(p.engine.world.journal(), loads(p.checkpoint()))['native_completions'], 3)
        self.assertEqual(audit(p.engine.world.journal(), p.engine.access.checkpoint())['workflow_selections'], 3)

    def test_withheld_handoff_changes_choice_and_fails_provenance(self):
        p = chain(); q = chain(cls=WithheldHandoff); p.run(1000); q.run(1000)
        good = [r for r in p.events if r['status'] == 'episode_complete']
        cut = [r for r in q.events if r['status'] == 'episode_complete']
        self.assertEqual(good[0], cut[0])
        self.assertEqual(p.engine.job_status(ALICE, good[0]['key'] + ':movement')['spent'],
                         q.engine.job_status(ALICE, cut[0]['key'] + ':movement')['spent'])
        self.assertNotEqual(good[1]['recipe'], cut[1]['recipe'])
        self.assertEqual(attrs(q.engine.world.head(DEVICE.identity))['wear'], 1)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            audit_continuation(q.engine.world.journal(), loads(q.checkpoint()))
        self.assertTrue(audit(q.engine.world.journal(), q.engine.access.checkpoint())['passed'])

    def test_exact_restore_during_comparison_and_feedback(self):
        for boundary in ('comparison', 'feedback'):
            p = chain()
            if boundary == 'comparison': p.run(1)
            else:
                for _ in range(1000):
                    p.step()
                    if p.feedback[0] is not None: break
                self.assertIsNotNone(p.feedback[0])
            q = WorkflowContinuation.restore(p.checkpoint())
            self.assertEqual(p.checkpoint(), q.checkpoint())
            p.run(1000); q.run(1000)
            self.assertEqual(p.checkpoint(), q.checkpoint())

    def test_budget_exhaustion_retains_paid_partial_work(self):
        p = chain(budget=90); before = p.engine.wallet(ALICE)['energy']
        p.run(1000)
        self.assertEqual(p.stopped, ['exhausted'])
        self.assertEqual(p.engine.wallet(ALICE)['energy'], 0)
        self.assertGreater(before, 0)
        self.assertTrue(any(r.get('spent', 0) > 0 for r in p.events))
        self.assertTrue(audit_continuation(p.engine.world.journal(), loads(p.checkpoint()))['passed'])

    def test_finite_turns_preserve_pending_state(self):
        p = chain(); self.assertTrue(p.run(1)['pending'])
        self.assertEqual(p.counts, [0])
        self.assertEqual(p.checkpoint(), WorkflowContinuation.restore(p.checkpoint()).checkpoint())

    def test_forged_history_and_need_are_rejected(self):
        p = chain(); p.run(1000); state = loads(p.checkpoint())
        altered = deepcopy(state); altered['input_history'][0][1] = altered['input_history'][0][0]
        with self.assertRaisesRegex(ValueError, 'history'):
            audit_continuation(p.engine.world.journal(), altered)
        altered = deepcopy(state); altered['population']['requests'][0]['fields']['demand'] = DEVICE
        with self.assertRaisesRegex(ValueError, 'provenance'):
            audit_continuation(p.engine.world.journal(), altered)
        with self.assertRaises(ValueError): WorkflowContinuation.restore(dumps(altered))
