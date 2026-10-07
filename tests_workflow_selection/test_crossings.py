import unittest
from dataclasses import replace
from .crossing_fixtures import *
from tools.verify_workflow_selection import audit, extent
from hle_unified.workflow_audit import audit as native_audit

class CrossingSelectionTests(unittest.TestCase):
    def test_twenty_cells_and_matched_controls(self):
        for name in PANEL_NAMES:
            for face in FACES:
                with self.subTest(name=name,face=face):
                    e,r,b=crossing_fixture(name,face);q,s,_=crossing_fixture(name,face,WithheldCrossing)
                    d=finish(e,r);c=finish(q,s)
                    self.assertEqual(d['recipe'],'workflow-'+name.lower()+'-'+face+'-v1')
                    self.assertIsNone(d['failure']);self.assertIsNotNone(d['child'])
                    self.assertEqual(d['spent'],c['spent']);self.assertIsNone(c['child'])
                    self.assertIsNotNone(consume(e,r,b)['consequence']['next_task'])
                    self.assertNotEqual(crossing_query(e,r,name),crossing_query(q,s,name))
                    self.assertEqual(audit(e.world.journal(),e.access.checkpoint())['workflow_selections'],1)
                    native_audit(q.world.journal(),q.access.checkpoint(),extent_check=extent,extended_flags=('c7ws',))
                    with self.assertRaisesRegex(ValueError,'choice withheld'):audit(q.world.journal(),q.access.checkpoint())

    def test_fold_intermediate_and_single_step_rejection(self):
        for name in ('Express','Embody'):
            e,r,b=crossing_fixture(name,'expenditure');finish(e,r)
            d=e.job_status(ALICE,'auto:movement');self.assertEqual(d['route_count'],2);self.assertEqual(d['steps_completed'],2)
            steps=[v for tx in e.world.journal() for v in tx.versions if v.ref.identity.namespace=='c7w.step']
            self.assertGreaterEqual(len(steps),2)
            with self.assertRaisesRegex(ValueError,'fixed Fold families'):replace(b['request'],elements=('ni',))
            audit(e.world.journal(),e.access.checkpoint())

    def test_real_care_missing_stock_and_stale_revision(self):
        for name in ('Express','Apply'):
            e,r,_=crossing_fixture(name,'expenditure');wear=attrs(e.world.resolve(r.target))['wear'];stock=attrs(e.world.resolve(r.stock))['consumed']
            finish(e,r);self.assertEqual(attrs(e.world.head(r.target.identity))['wear'],wear-1)
            self.assertEqual(attrs(e.world.head(r.stock.identity))['consumed'],stock+1)
            audit(e.world.journal(),e.access.checkpoint())
            q,s,_=crossing_fixture(name,'expenditure');s=replace(s,stock=None)
            rows,_=q._workflow_policy(q.workflow_selection_view(s))
            self.assertFalse(next(x for x in rows if x['recipe']=='workflow-'+name.lower()+'-expenditure-v1')['eligible'])
            q,s,_=crossing_fixture(name,'expenditure')
            # Change hidden actual custody after reading; paid view remains stale.
            perform(q,OperationRequest('alienate',ALICE,'transfer',ROOM,target=s.target,recipient=BOB,participants=(BOB,),evidence=evidence(q,ALICE,s.target)),limit=100000)
            d=finish(q,s);child=q.job_status(ALICE,'auto:movement')
            self.assertTrue(d['failure'] is not None or child is not None and child['status']=='failed')
            audit(q.world.journal(),q.access.checkpoint())

    def test_crossing_and_self_checkpoint_continuation(self):
        for factory,engine in ((crossing_fixture,WorkflowCrossingSelectionEngine),(fixture,WorkflowSelectionEngine)):
            name='Express' if factory is crossing_fixture else 'Contemplate'
            for boundary in (1,100000):
                e,r,_=factory(name,'expenditure');e.participate('partial',r,boundary)
                q=engine.restore(e.checkpoint());self.assertEqual(e.checkpoint(),q.checkpoint())
                for i in range(6):self.assertEqual(e.participate('resume'+str(i),r),q.participate('resume'+str(i),r))
                self.assertEqual(e.checkpoint(),q.checkpoint());audit(q.world.journal(),q.access.checkpoint())
