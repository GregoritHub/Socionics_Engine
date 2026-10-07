import unittest
from copy import deepcopy
from .fixtures import *
from hle_unified.selection_records import loads, dumps
from hle_unified.workflow_agenda_audit import audit_agenda

EXPECTED=(('theorize-expenditure','apply-expenditure','embody-expenditure'),
          ('share-expenditure','commune-expenditure','identify-expenditure'),
          ('coordinate-expenditure','mobilize-expenditure','embody-expenditure'),
          ('institutionalize-accumulation','institutionalize-expenditure','educate-expenditure'),
          ('theorize-accumulation','organize-expenditure','integrate-expenditure','apply-expenditure'))


class ContinuedFamiliesTests(unittest.TestCase):
    def test_five_generated_families_and_withheld_prior_controls(self):
        for name, expected in zip(FAMILIES,EXPECTED):
            p=family(name);q=withheld(name);p.run(2000);q.run(2000)
            self.assertIsNone(p.halted);self.assertEqual(q.halted,'missing_prior_result')
            good=terminal_query(p);cut=terminal_query(q)
            self.assertIsNotNone(good);self.assertIsNotNone(good['next_task']);self.assertIsNone(cut)
            report=audit_agenda(p.engine.world.journal(),p.engine.access.checkpoint(),loads(p.checkpoint())['state'])
            self.assertEqual([r['recipe'] for r in report['native']['selection_rows']],['workflow-'+x+'-v1' for x in expected])
            for field in ('spent','required','recipe_key'):
                self.assertEqual(p.engine.job_status(ALICE,'agenda:family:0:movement')[field],q.engine.job_status(ALICE,'agenda:family:0:movement')[field])
            with self.assertRaisesRegex(ValueError,'provenance'):
                audit_agenda(q.engine.world.journal(),q.engine.access.checkpoint(),loads(q.checkpoint())['state'])

    def test_exact_restore_inside_social_exchange_and_main_comparison(self):
        for name in (FAMILIES[0],FAMILIES[1]):
            p=family(name);p.run(2);q=WorkflowAgenda.restore(p.checkpoint())
            self.assertEqual(p.checkpoint(),q.checkpoint());p.run(2000);q.run(2000)
            self.assertEqual(p.checkpoint(),q.checkpoint())

    def test_finite_budget_keeps_unfinished_work(self):
        p=family(FAMILIES[1]);r=p.run(1)
        self.assertFalse(r['done']);self.assertEqual(p.stage,0)
        self.assertEqual(p.checkpoint(),WorkflowAgenda.restore(p.checkpoint()).checkpoint())

    def test_no_runtime_goal_can_supply_route_or_forward_result(self):
        p=family(FAMILIES[0]);r=WorkflowSelectionRequest(**p.template)
        goals=deepcopy(p.goals);goals[0]['recipe']='workflow-apply-expenditure-v1'
        with self.assertRaises(ValueError):WorkflowAgenda(p.engine,r,goals)
        goals=deepcopy(p.goals);goals[0]['sources']=[dict(result=1)]
        with self.assertRaises(ValueError):WorkflowAgenda(p.engine,r,goals)

    def test_tampered_result_and_charge_are_rejected(self):
        p=family(FAMILIES[0]);p.run(2000);state=loads(p.checkpoint())['state']
        bad=deepcopy(state);bad['results'][1]=bad['results'][0]
        with self.assertRaisesRegex(ValueError,'provenance'):audit_agenda(p.engine.world.journal(),p.engine.access.checkpoint(),bad)
        bad=deepcopy(state);a,e,t=bad['events'][0]['charged'][0];bad['events'][0]['charged']=((a,e+1,t),)
        with self.assertRaisesRegex(ValueError,'charge'):audit_agenda(p.engine.world.journal(),p.engine.access.checkpoint(),bad)

    def test_cancelled_child_keeps_spending_and_stops_dependents(self):
        p=family(FAMILIES[0]);key='agenda:family:0:movement'
        for _ in range(100):
            p.step()
            if (ALICE,key) in p.engine._jobs:
                d=p.engine.job_status(ALICE,key)
                if d['status'] not in ('succeeded','failed','cancelled') and d['spent']>0:break
        before=p.engine.job_status(ALICE,key)['spent']
        p.engine.cancel('authored-interruption',ALICE,key);p.run(2000)
        self.assertEqual(p.halted,'native_cancelled');self.assertEqual(p.results,[])
        self.assertEqual(p.engine.job_status(ALICE,key)['spent'],before)
        self.assertTrue(audit_agenda(p.engine.world.journal(),p.engine.access.checkpoint(),loads(p.checkpoint())['state'])['passed'])

    def test_restore_rejects_pending_main_recipe_injection(self):
        p=family(FAMILIES[1]);p.run(1);raw=loads(p.checkpoint())
        raw['state']['active']['recipe']='workflow-apply-expenditure-v1'
        with self.assertRaisesRegex(ValueError,'pending'):
            WorkflowAgenda.restore(dumps(raw))

    def test_public_result_cannot_advance_before_paid_reading(self):
        p=family(FAMILIES[0])
        for _ in range(100):
            p.step()
            if p.pending_result is not None:break
        bad=loads(p.checkpoint())['state'];bad['results']=[bad['pending_result']]
        bad.update(stage=1,pending_result=None,queue=[],active=None)
        with self.assertRaisesRegex(ValueError,'paid reading'):
            audit_agenda(p.engine.world.journal(),p.engine.access.checkpoint(),bad)
