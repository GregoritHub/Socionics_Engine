import unittest
from dataclasses import replace
from copy import deepcopy
from .fixtures import *
from tools.verify_workflow_selection import audit, extent
from hle_unified.workflow_audit import audit as native_audit
from hle_unified.workflow_selection_records import demand_value

class SelectionTests(unittest.TestCase):
    def test_eight_automatic_witnesses_and_withheld_controls(self):
        for name in SELF_NAMES:
            for face in FACES:
                with self.subTest(name=name,face=face):
                    e,r,base=fixture(name,face);q,s,_=fixture(name,face,WithheldChoice)
                    d=finish(e,r);c=finish(q,s)
                    self.assertEqual(d['recipe'],'workflow-'+name.lower()+'-'+face+'-v1')
                    self.assertIsNone(d['failure']);self.assertIsNotNone(d['child']);self.assertIsNone(c['child'])
                    self.assertEqual(d['spent'],c['spent'])
                    later=consume(e,r,base);self.assertIsNotNone(later['consequence']['next_task'])
                    self.assertNotEqual(fixed_query(e,r,name),fixed_query(q,s,name))
                    self.assertEqual(audit(e.world.journal(),e.access.checkpoint())['workflow_selections'],1)
                    self.assertTrue(native_audit(q.world.journal(),q.access.checkpoint(),extent_check=extent,extended_flags=('c7ws',))['passed'])
                    with self.assertRaisesRegex(ValueError,'choice withheld'):audit(q.world.journal(),q.access.checkpoint())

    def test_partial_comparison_and_native_restore_exactly(self):
        for name in SELF_NAMES:
            for boundary in (0,1):
                e,r,_=fixture(name,'expenditure')
                if boundary:e.participate('full-turn',r)
                e.participate('partial',r,1);q=WorkflowSelectionEngine.restore(e.checkpoint())
                self.assertEqual(e.checkpoint(),q.checkpoint())
                for i in range(6):
                    self.assertEqual(e.participate('resume-'+str(i),r),q.participate('resume-'+str(i),r))
                self.assertEqual(e.checkpoint(),q.checkpoint());audit(q.world.journal(),q.access.checkpoint())

    def test_unpaid_foreign_and_unread_content_rejected(self):
        e,r,_=fixture('Contemplate','accumulation');e.start('start',r)
        with self.assertRaises(ValueError):e.commit('early',ALICE,r.key)
        e.cancel('cancel',ALICE,r.key)
        for bad in (replace(r,key='bad',actor=BOB),replace(r,key='bad',accessible=(ref('missing'),)),replace(r,key='bad',cue=CUE)):
            with self.assertRaises(ValueError):e.start('bad',bad)
        self.assertNotIn((ALICE,'auto:movement'),e._jobs)
        audit(e.world.journal(),e.access.checkpoint())

    def test_cancel_preserves_paid_work(self):
        e,r,_=fixture('Contemplate','accumulation');before=e.wallet(ALICE)['energy']
        e.start('start',r);e.advance('pay',ALICE,r.key,2);e.cancel('cancel',ALICE,r.key)
        self.assertEqual(e.wallet(ALICE)['energy'],before-2)
        self.assertNotIn((ALICE,'auto:movement'),e._jobs)
        audit(e.world.journal(),e.access.checkpoint())

    def test_no_route_instruction_fields_or_hidden_material_read(self):
        self.assertFalse({'recipe','face','route','cell'} & set(WorkflowSelectionRequest.__dataclass_fields__))
        with self.assertRaises(ValueError):demand_value(dict(kind='workflow_need',route='Act'))
        e,r,_=fixture('Contemplate','accumulation');before=e.workflow_selection_view(r)
        perform(e,OperationRequest('unreceived-care',ALICE,'care',ROOM,target=DEVICE,stock=CARE,evidence=evidence(e,ALICE,DEVICE)),limit=100000)
        after=e.workflow_selection_view(r)
        self.assertEqual({k:v for k,v in before.items() if k!='wallet'},{k:v for k,v in after.items() if k!='wallet'})

    def test_forged_ballot_and_snapshot_fail_raw_audit(self):
        e,r,_=fixture('Contemplate','expenditure');finish(e,r)
        for namespace,key,value in (('c7ws.candidates','effort',999),('c7ws.snapshot','cursor','te')):
            txs=[]
            for tx in e.world.journal():
                vs=[]
                for v in tx.versions:
                    if v.ref.identity.namespace==namespace:
                        z=loads(attrs(v)['payload'])
                        if type(z) is list:z[0][key]=value
                        else:z[key]=value
                        from hle_unified.selection_records import dumps
                        v=replace(v,attributes=attributes(dict(payload=dumps(z))))
                    vs.append(v)
                txs.append(replace(tx,versions=tuple(vs)))
            with self.assertRaises(ValueError):audit(txs,e.access.checkpoint())

    def test_existing_checkpoint_classes_restore_unchanged(self):
        e=setup_workflow();cell(e,'Contemplate','accumulation');cp=e.checkpoint()
        self.assertEqual(cp,WorkflowEngine.restore(cp).checkpoint())
        from tests_c6.fixtures import fixture as old_fixture
        from hle_unified.selection_execution import SelectionEngine
        old,r=old_fixture('Theorize','accumulation');cp=old.checkpoint()
        self.assertEqual(cp,SelectionEngine.restore(cp).checkpoint())
