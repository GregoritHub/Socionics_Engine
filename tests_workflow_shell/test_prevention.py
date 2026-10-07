import unittest
from dataclasses import replace
from .fixtures import *
from hle_unified.material import attributes
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.selection_records import loads, dumps

class PreventionTests(unittest.TestCase):
    def test_all_destinations_and_matched_invalid_bypasses(self):
        for name in ('Contemplate','Express','Share','Theorize'):
            with self.subTest(name=name):
                worlds,row=panel_case(name,'accumulation')
                self.assertEqual(row['deformed_admission_spent'],row['bypass_admission_spent'])
                self.assertEqual(audit(worlds['corrected'].world.journal(),worlds['corrected'].access.checkpoint())['workflow_shell_completed'],1)

    def test_exact_partial_admission_and_child_continuation(self):
        e,p,out=prepared('Express','expenditure');dev.release8(e,'release',p,target=out['request'].target)
        r=out['request'];e.start('start',gate(e,r));e.advance('partial',ALICE,'gate',1)
        q=WorkflowShellEngine.restore(e.checkpoint());self.assertEqual(e.checkpoint(),q.checkpoint())
        for x in (e,q):x.advance('advance',ALICE,'gate',1000000);x.commit('commit',ALICE,'gate');x.advance('child-partial',ALICE,r.key,1)
        self.assertEqual(e.checkpoint(),q.checkpoint());q=WorkflowShellEngine.restore(q.checkpoint())
        for x in (e,q):x.advance('child-rest',ALICE,r.key,1000000);x.commit('child-commit',ALICE,r.key)
        self.assertEqual(e.checkpoint(),q.checkpoint());audit(q.world.journal(),q.access.checkpoint())

    def test_legitimate_constraints_are_not_deformations(self):
        cases=({'available':False},{'safe':False},{'requires_partner':True,'willing':False},
            {'approval_required':True,'approved':False})
        for terms in cases:
            e=setup();dev.generated(e);out=prepare(e,'Contemplate','accumulation')
            dev.supply8(e,'current',target=out['request'].target,**terms)
            e,receipt,later=finish(e,out)
            row=audit(e.world.journal(),e.access.checkpoint())['workflow_shell_rows'][0]
            self.assertFalse(row['deformed']);self.assertIsNone(receipt['child']);self.assertEqual(later,'unavailable')

    def test_partial_information_and_no_demand_are_not_shells(self):
        for mode in ('missing_information','no_demand'):
            e=setup();dev.generated(e);out=prepare(e,'Contemplate','accumulation');r=out['request']
            dev.supply8(e,'current',target=r.target,**({'safe':'unknown'} if mode=='missing_information' else {}))
            q=gate(e,r,demand=mode!='no_demand');perform(e,q,limit=1000000)
            row=audit(e.world.journal(),e.access.checkpoint())['workflow_shell_rows'][0]
            self.assertFalse(row['deformed']);self.assertFalse(row['completed'])

    def test_tampered_completion_roles_and_exact_inputs_rejected(self):
        worlds,_=panel_case('Theorize','accumulation');e=worlds['corrected']
        for field,value in (('movement_complete',True),('destination','WE'),('owner',BOB),('carrier',ObjectRef(EVE,1)),('admission_spent',0)):
            txs=[]
            for tx in e.world.journal():
                vs=[]
                for v in tx.versions:
                    if v.ref.identity.namespace=='c7sh.admission':v=replace(v,attributes=attributes(dict(attrs(v),**{field:value})))
                    vs.append(v)
                txs.append(replace(tx,versions=tuple(vs)))
            with self.subTest(field=field),self.assertRaises(ValueError):audit(txs,e.access.checkpoint())
        txs=[]
        for tx in e.world.journal():
            vs=[]
            for v in tx.versions:
                if v.ref.identity.namespace=='c7sh.request':
                    d=attrs(v);m=loads(d['workflow']);m['inputs']=(DEVICE,);d['workflow']=dumps(m)
                    v=replace(v,attributes=attributes(d))
                vs.append(v)
            txs.append(replace(tx,versions=tuple(vs)))
        with self.assertRaisesRegex(ValueError,'lost exact content'):audit(txs,e.access.checkpoint())

    def test_audit_records_private_and_legacy_checkpoint_upgrade(self):
        legacy=setup(engine_type=WorkflowFinalSelectionEngine);text=legacy.checkpoint()
        self.assertEqual(WorkflowFinalSelectionEngine.restore(text).checkpoint(),text)
        e=WorkflowShellEngine.from_selection(text)
        self.assertEqual(e.world.checkpoint(),legacy.world.checkpoint())
        out=prepare(e,'Contemplate','accumulation');dev.supply8(e,'current',target=out['request'].target);e,d,_=finish(e,out)
        v=e.world.resolve(address('c7sh.admission',ALICE,'gate'))
        with self.assertRaisesRegex(ValueError,'cannot be authored'):e.declare('forge',(v,))
        with self.assertRaisesRegex(ValueError,'not participant knowledge'):e.disclose('leak',ALICE,v.ref,(),v.ref)
        audit(e.world.journal(),e.access.checkpoint())
