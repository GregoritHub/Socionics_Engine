import unittest
from dataclasses import replace
from hle.model_a import TYPES
from tests_c5.fixtures import *
from hle_unified.crux_shell_audit import audit
from hle_unified.material import available

class ShellRouteTests(unittest.TestCase):
    def fresh(self,**terms):
        e=setup();p=dev.generated(e);dev.supply8(e,'current',**terms)
        return e,p,prepare(e,'Theorize','accumulation')

    def test_all_five_effects_change_native_admission(self):
        for effect in ('approval','obligation','salience','forecast','exclude_route'):
            with self.subTest(effect=effect):
                d,c,row=panel_case('Theorize','accumulation',effect=effect)
                self.assertFalse(row['deformed']['admitted']);self.assertTrue(row['control']['admitted'])
                for e in (d,c):self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])

    def test_type_frames_preserve_gate_contract(self):
        for tim in TYPES:
            e=setup(tim);dev.supply8(e,'current');r=prepare(e,'Theorize','accumulation')
            e,row=finish(e,r);self.assertTrue(row['admitted']);self.assertEqual(e.job_status(ALICE,'case')['status'],'succeeded')

    def test_route_and_polarity_specificity(self):
        for face,expected in (('accumulation',False),('expenditure',True)):
            e=setup(generate=False);dev.supply8(e,'current')
            dev.inject(e,Effect('forecast','theorize-accumulation-v1'))
            r=prepare(e,'Theorize',face);e,row=finish(e,r)
            self.assertEqual(row['admitted'],expected)
            self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])

    def test_partial_admission_and_child_exact_continuation(self):
        for stage in ('admission','child'):
            e=setup();dev.supply8(e,'current');r=prepare(e,'Share','expenditure')
            q=gate(e,r);e.start('start',q)
            if stage=='child':
                e.advance('gate-work',ALICE,'gate',10000);e.commit('gate-commit',ALICE,'gate')
            key='gate' if stage=='admission' else 'case'
            e.advance('partial',ALICE,key,1);cp=e.checkpoint();other=CruxShellEngine.restore(cp)
            self.assertEqual(cp,other.checkpoint())
            for x in (e,other):
                x.advance('finish',ALICE,key,1000000);x.commit('commit',ALICE,key)
            self.assertEqual(e.checkpoint(),other.checkpoint())
            self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])

    def test_cancelled_admission_spends_without_child(self):
        e,p,r=self.fresh();q=gate(e,r);before=e.wallet(ALICE)['energy']
        e.start('start',q);e.advance('one',ALICE,q.key,1);e.cancel('cancel',ALICE,q.key)
        self.assertEqual(before-e.wallet(ALICE)['energy'],1);self.assertNotIn((ALICE,r.key),e._jobs)
        self.assertEqual(CruxShellEngine.restore(e.checkpoint()).checkpoint(),e.checkpoint())

    def test_unpaid_admission_cannot_commit(self):
        e,p,r=self.fresh();q=gate(e,r);e.start('start',q)
        with self.assertRaises(ValueError):e.commit('no-work',ALICE,q.key)
        self.assertNotIn((ALICE,r.key),e._jobs)

    def test_legitimate_constraints_are_not_shell_deformation(self):
        for terms in (dict(safe=False),dict(available=False),dict(requires_partner=True,willing=False),dict(approval_required=True)):
            e,p,r=self.fresh(**terms);e,row=finish(e,r)
            self.assertFalse(row['admitted']);self.assertEqual(audit(e.world.journal(),e.access.checkpoint())['c5_deformed'],0)

    def test_no_demand_and_incomplete_recall_do_not_clear(self):
        for kwargs in (dict(demand=False),dict(visit_limit=1)):
            e,p,r=self.fresh();q=gate(e,r,**kwargs);perform(e,q,limit=10000)
            self.assertNotIn((ALICE,r.key),e._jobs)
            self.assertEqual(audit(e.world.journal(),e.access.checkpoint())['c5_deformed'],0)

    def test_unread_or_stale_subset_cannot_admit(self):
        e=setup();dev.supply8(e,'initial');r=prepare(e,'Theorize','accumulation');q=gate(e,r)
        dev.supply8(e,'changed',safe=False);before=e.checkpoint()
        with self.assertRaisesRegex(ValueError,'all current'):e.start('stale',q)
        self.assertEqual(before,e.checkpoint())

    def test_hidden_evidence_does_not_change_admission(self):
        e=setup();dev.supply8(e,'current');r=prepare(e,'Theorize','accumulation')
        other=CruxShellEngine.restore(e.checkpoint());dev.supply8(other,'hidden',safe=False,deliver=False)
        for x in (e,other):x,row=finish(x,r);self.assertTrue(row['admitted'])

    def test_received_change_invalidates_paid_admission(self):
        e=setup();dev.supply8(e,'current');r=prepare(e,'Theorize','accumulation');q=gate(e,r)
        e.start('start',q);e.advance('paid',ALICE,q.key,10000);dev.supply8(e,'changed',safe=False)
        e.commit('commit',ALICE,q.key)
        self.assertEqual(e.job_status(ALICE,q.key)['status'],'failed');self.assertNotIn((ALICE,r.key),e._jobs)
        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])

    def test_local_release_does_not_clear_another_target(self):
        e,p,r=self.fresh();dev.release8(e,'local',p,SAW2)
        e,row=finish(e,r);self.assertFalse(row['admitted'])
        self.assertEqual(e.pattern_view(ALICE)[0].origin,p.origin)

    def test_scaffolded_success_does_not_award_capacity(self):
        e,p,r=self.fresh(approved=True);e,row=finish(e,r)
        self.assertTrue(row['admitted']);self.assertFalse(e.development_view(ALICE)['capacities'])
        dev.supply8(e,'renewed',approved=False);r=replace(r,key='renewed-movement');e,row=finish(e,r,'renewed-gate')
        self.assertFalse(row['admitted'])

    def test_practice_reorganization_and_return_preserve_origin(self):
        e=setup();e,p=dev.trained8(e);dev.returned8(e,p)
        dev.supply8(e,'current');r=prepare(e,'Theorize','accumulation');e,row=finish(e,r)
        self.assertTrue(row['admitted']);self.assertEqual(e._treatments[p.origin]['ownership'],'reowned')
        self.assertEqual(e.pattern_view(ALICE)[0].origin,p.origin)
        a=audit(e.world.journal(),e.access.checkpoint());self.assertEqual(a['reownerships'],1)
        dev.supply8(e,'danger',safe=False);r=replace(r,key='danger-movement');e,row=finish(e,r,'danger-gate')
        self.assertFalse(row['admitted'])

    def test_unsupported_effect_cannot_be_cleared(self):
        for effect in ('forecast','salience','exclude_route'):
            e=setup(generate=False);dev.supply8(e,'current');p=dev.inject(e,Effect(effect))
            with self.assertRaises(ValueError):dev.develop(e,dev.request8(e,'release','release',p))

    def test_raw_auditor_rejects_false_completion_endpoint_and_child(self):
        e=setup();dev.supply8(e,'current');r=prepare(e,'Theorize','accumulation');e,row=finish(e,r)
        for field,value in (('movement_complete',True),('destination','WE'),('admitted',False),('child',None),('admission_spent',0)):
            txs=[]
            for tx in e.world.journal():
                vs=tuple(replace(v,attributes=attributes({**attrs(v),field:value})) if v.ref.identity.namespace=='c5.admission' else v for v in tx.versions)
                txs.append(replace(tx,versions=vs))
            with self.assertRaises(ValueError):audit(txs,e.access.checkpoint())

    def test_c4_checkpoint_upgrade_preserves_authority_and_history(self):
        e=setup_c3(engine_type=CruxCompositionEngine);cell(e,'Share','expenditure')
        other=CruxShellEngine.from_c4(e.checkpoint())
        self.assertEqual(e.world.checkpoint(),other.world.checkpoint());self.assertEqual(e.access.checkpoint(),other.access.checkpoint())

    def test_active_interruption_preserves_first_step_and_exact_resume(self):
        e,p,r=self.fresh();q=gate(e,r,phase='after_first_step')
        e.start('start',q);e.advance('gate-work',ALICE,q.key,10000);e.commit('gate-commit',ALICE,q.key)
        e.advance('child-partial',ALICE,r.key,1);other=CruxShellEngine.restore(e.checkpoint())
        for x in (e,other):x.advance('child-finish',ALICE,r.key,100000)
        self.assertEqual(e.checkpoint(),other.checkpoint())
        d=e.job_status(ALICE,r.key);self.assertEqual((d['status'],d['steps_completed']),('cancelled',1))
        a=audit(e.world.journal(),e.access.checkpoint())['c5_rows'][0]
        self.assertTrue(a['early_substitution']);self.assertTrue(a['attempted_personal_placement']);self.assertFalse(a['foreclosure'])
        self.assertIsNone(d.get('binding'))

    def test_active_interruption_has_no_material_destination_effect(self):
        d,c,row=panel_case('Express','expenditure',phase='after_first_step')
        self.assertEqual(available(d.world.head(SUPPLY.identity)),6)
        self.assertLess(available(c.world.head(SUPPLY.identity)),6)
        a=audit(d.world.journal(),d.access.checkpoint())['c5_rows'][0]
        self.assertTrue(a['early_substitution'])
