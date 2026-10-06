from dataclasses import replace
import unittest
from hle.conversion_demo import case,renew
from hle.conversion import ConversionWorld,infer_table
from hle.conversion_records import ConversionCommand,ConversionPolicy,ConversionTransaction
from hle.conversion_reference import evaluate
from hle.concept_demo import fund_command
from hle.compensation_demo import run,introduce
from hle.compensation_records import DEPENDENCY
from hle.development_contracts import Treatment
from hle.contracts import WorkStatus,Ref,Kind
from hle.world_records import Tick,Credit
from hle.codec import loads,dumps
from .support import fresh,prefix,first,command,failed_trial

class ConversionBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main,cls.setup=case(history=1,maintained=1)
        cls.report=evaluate(cls.main)
        cls.controls={}
        for name,policy in [('access',ConversionPolicy(material_access=False)),
                            ('practice',ConversionPolicy(practice=False)),('retention',ConversionPolicy(retention=False))]:
            w,s=case(history=1,maintained=1,conversion_policy=policy)
            cls.controls[name]=(w,s,evaluate(w))

    def test_all_controls_reconstruct_work_and_lineage(self):
        for r in [self.report]+[x[2] for x in self.controls.values()]: self.assertTrue(r['passed'],r['errors'])

    def test_release_preserves_material_and_original_concept(self):
        i=first(self.main,'release');t=self.main._journal[i];s=t.study
        self.assertIsNone(t.concept);self.assertEqual(t.treatment.treatment,Treatment.HOLD)
        self.assertIn(DEPENDENCY,self.main._records[s.concept_origin].relations)
        self.assertEqual(self.main._records[s.material].concept_at_origin,s.concept_origin)

    def test_context_uses_owned_particulars(self):
        t=self.main._journal[first(self.main,'context')]
        self.assertTrue(all(self.main._records[r].observer==t.command.actor for r in t.study.context_sources))
        self.assertEqual(t.study.context_sources,t.job.basis[2:])

    def test_provisional_organization_cannot_award_capacity(self):
        t=self.main._journal[first(self.main,'reorganize')]
        self.assertFalse(t.candidate.covered);self.assertFalse(t.candidate.practice);self.assertIsNone(t.capacity)
        w=prefix(self.main,first(self.main,'try'));self.assertFalse(w._capacities)

    def test_first_practice_leaves_actual_reorganization_open(self):
        t=self.main._journal[first(self.main,'reflect')]
        self.assertEqual(t.candidate.covered,(False,));self.assertTrue(t.study.active)
        self.assertIsNone(t.capacity);self.assertEqual(len(t.candidate.practice),1)

    def test_reownership_requires_two_real_branches_and_native_work(self):
        r=self.report
        self.assertEqual({x['required'] for x in r['practice'] if x['success']},{False,True})
        self.assertTrue(all(x['native_use'] and x['care'] for x in r['practice']))
        self.assertEqual(len({x['loan'] for x in r['practice']}),2)
        t=self.main._journal[first(self.main,'retain')]
        self.assertEqual(t.treatment.treatment,Treatment.REOWN);self.assertEqual(t.treatment.carrier,t.command.actor)

    def test_later_optional_actions_use_own_retained_capacity(self):
        later=set(self.setup['renewed_items']+self.setup['held_out_items'])
        rows=[x for x in self.report['choices'] if x['item'] in later and not x['required']]
        self.assertEqual(len(rows),3)
        self.assertTrue(all(x['mode']=='direct' and x['carrier'] is None and x['retained_use'] for x in rows))

    def test_practice_and_reuse_do_not_wait_for_peer_account_acceptance(self):
        from hle.reconciliation_records import AccountTransaction
        self.assertFalse(any(type(t) is AccountTransaction and t.command.actor==self.main.config.actors[0]
            for t in self.main._journal[self.setup['start']:]))

    def test_required_held_out_partner_keeps_real_confirmation(self):
        item=self.setup['held_out_items'][-1]
        rows=[x for x in self.report['choices'] if x['item']==item]
        self.assertTrue(rows);self.assertTrue(all(x['required'] and x['mode']=='confirm' for x in rows))
        end=[x for x in self.report['returns'] if x['item']==item][-1]
        self.assertTrue(end['correct']);self.assertEqual(end['owner'],self.main.config.actors[2].key)

    def test_access_ablation_preserves_history_but_prevents_context(self):
        w,s,r=self.controls['access'];self.assertTrue(r['material_preserved'])
        self.assertFalse(r['current_capacity']);self.assertFalse(r['practice'])
        self.assertFalse(any(x['operation']=='context' for x in r['operations']))

    def test_practice_ablation_preserves_proposal_without_retention(self):
        w,s,r=self.controls['practice'];self.assertFalse(r['practice']);self.assertFalse(r['current_capacity'])
        self.assertIn('reorganize',[x['operation'] for x in r['operations']])
        self.assertTrue(w._studies[w.config.actors[0]].active)

    def test_retention_ablation_allows_practice_but_loses_independent_reuse(self):
        w,s,r=self.controls['retention'];self.assertEqual(len(r['practice']),2);self.assertFalse(r['current_capacity'])
        self.assertTrue(all(x['success'] for x in r['practice']));self.assertFalse(r['recalls'])
        later=set(s['renewed_items']+s['held_out_items'])
        self.assertTrue(all(x['mode']=='confirm' for x in r['choices'] if x['item'] in later))

    def test_post_acquisition_withdrawal_changes_next_action(self):
        w=prefix(self.main,self.setup['acquired']);a=w.config.actors[0]
        cap=w._capacities[a];fund_command(w,command(w,'withdraw',work_limit=256))
        self.assertIn(cap.ref,w._records)
        introduce(w,4);run(w)
        r=evaluate(w);self.assertTrue(r['passed'],r['errors']);self.assertEqual(r['choices'][-1]['mode'],'confirm')

    def test_post_acquisition_access_restriction_changes_next_action(self):
        w=prefix(self.main,self.setup['acquired']);fund_command(w,command(w,'restrict',work_limit=256))
        introduce(w,4);run(w);r=evaluate(w)
        self.assertTrue(r['passed'],r['errors']);self.assertEqual(r['choices'][-1]['mode'],'confirm')
        self.assertTrue(r['current_capacity']);self.assertTrue(r['material_preserved'])

    def test_restoring_access_restores_paid_reuse(self):
        w=prefix(self.main,self.setup['acquired'])
        for op in ('restrict','restore_access'):fund_command(w,command(w,op,work_limit=256))
        introduce(w,4);run(w);r=evaluate(w)
        self.assertTrue(r['passed'],r['errors']);self.assertEqual(r['choices'][-1]['mode'],'direct')
        self.assertTrue(r['choices'][-1]['retained_use'])

    def test_deleting_live_material_cannot_substitute_for_conversion(self):
        w=prefix(self.main,self.setup['acquired']);a=w.config.actors[0]
        del w._records[w._studies[a].material]  # explicit fault injection, not a public operation
        self.assertFalse(w._accessible(a));introduce(w,4);run(w)
        choices=[t.decision for t in w._journal if getattr(t,'decision',None) is not None and hasattr(t.decision,'selection')]
        self.assertEqual(choices[-1].selection.mode,'confirm')

    def test_failed_return_does_not_count_as_practice_or_reownership(self):
        w,event=failed_trial(self.main);self.assertEqual(event.outcome,WorkStatus.FAILED)
        s=w._studies[w.config.actors[0]];c=w._candidates[s.candidate]
        self.assertTrue(s.active);self.assertEqual(len(c.failures),1);self.assertFalse(c.covered);self.assertFalse(w._capacities)
        self.assertIn('fresh_own_inspection',c.preconditions)
        r=evaluate(w);self.assertTrue(r['passed'],r['errors']);self.assertFalse(r['practice'][-1]['success'])

    def test_failed_practice_can_revise_then_retry(self):
        w,_=failed_trial(self.main);result=run(w)
        self.assertFalse(result['horizon_exhausted']);r=evaluate(w)
        self.assertTrue(r['passed'],r['errors']);self.assertTrue(any(x['success'] for x in r['practice']))
        self.assertTrue(any(not x['success'] for x in r['practice']))
        self.assertTrue(any(t.event.action=='r14.inspect' and t.command.command_id.startswith('r17:') for t in w._journal))

    def test_pause_preserves_open_material_without_advancement(self):
        w=prefix(self.main,first(self.main,'try'));a=w.config.actors[0]
        fund_command(w,command(w,'pause',work_limit=256));s=w._studies[a]
        for i in range(10):w.execute(Tick('paused:'+str(i)))
        self.assertEqual(w._studies[a],s);self.assertFalse(w._capacities)
        fund_command(w,command(w,'resume',work_limit=256));self.assertEqual(w._operation(a),'try')

    def test_no_phase_counter_or_developed_input_exists(self):
        with self.assertRaises(TypeError): ConversionCommand('fake','fake',self.main.config.actors[0],phase='reownership')
        with self.assertRaises(TypeError): ConversionPolicy(developed=True)

    def test_ambiguous_context_does_not_invent_a_rule(self):
        self.assertIsNone(infer_table(()))

    def test_historical_positive_signs_are_not_erased(self):
        before=self.setup['historical_report']['groups'][0]['signs'];after=self.main.shell_report()['groups'][0]['signs']
        for sign in before: self.assertGreaterEqual(after[sign]['positive'],before[sign]['positive'])
        self.assertIn('unassessed',self.report['clearance'])

class ConversionIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.w,cls.setup=case(history=1,maintained=1)

    def test_duplicate_command_is_idempotent(self):
        i=first(self.w,'release');w=prefix(self.w,i);c=self.w._journal[i].command
        e=w.execute(c);n=len(w._journal);wallet=w._wallets[c.actor]
        self.assertEqual(w.execute(c),e);self.assertEqual(len(w._journal),n);self.assertEqual(w._wallets[c.actor],wallet)

    def test_partial_work_publishes_nothing_and_resumes(self):
        i=first(self.w,'reorganize');w=prefix(self.w,i);c=replace(self.w._journal[i].command,work_limit=1)
        w.execute(c);tx=w._journal[-1]
        self.assertEqual(tx.event.outcome,WorkStatus.PARTIAL);self.assertIsNone(tx.candidate)
        r=ConversionWorld.restore(w.checkpoint());n=replace(c,command_id='continued')
        self.assertEqual(w.execute(n),r.execute(n));self.assertEqual(w._journal[-1],r._journal[-1])

    def test_overlapping_work_is_rejected(self):
        i=first(self.w,'reorganize');w=prefix(self.w,i);c=replace(self.w._journal[i].command,work_limit=1);w.execute(c)
        with self.assertRaises(ValueError):w.execute(command(w,'pause'))
        with self.assertRaises(ValueError):w.execute(replace(c,command_id='changed',operator='pause'))

    def test_rehashed_forged_capacity_rejected(self):
        cp=loads(self.w.checkpoint());j=list(cp.base.base.journal);i=first(self.w,'retain');t=j[i]
        j[i]=replace(t,capacity=replace(t.capacity,practice=()))
        bad=replace(cp,base=replace(cp.base,base=replace(cp.base.base,journal=tuple(j))))
        with self.assertRaises(ValueError):ConversionWorld.restore(dumps(bad))

    def test_forged_rule_fails_independent_witness(self):
        w=prefix(self.w,len(self.w._journal));i=first(w,'reorganize');t=w._journal[i]
        w._journal[i]=replace(t,candidate=replace(t.candidate,table=((False,False),(True,False))))
        self.assertFalse(evaluate(w)['passed'])

    def test_rehashed_parent_schema_rejected(self):
        cp=loads(self.w.checkpoint());bad=replace(cp,base=replace(cp.base,schema='fake'))
        with self.assertRaises(ValueError):ConversionWorld.restore(dumps(bad))

    def test_low_resources_defer_without_early_output(self):
        i=first(self.w,'release');original=prefix(self.w,i);a=original.config.actors[0]
        used=original.config.wallets[0].energy-original._wallets[a].energy
        config=replace(original.config,wallets=tuple(replace(b,energy=used+1,time=used+1) if b.actor==a else b for b in original.config.wallets))
        w=fresh(original,config)
        for t in original._journal[1:]:w.execute(t.command)
        c=self.w._journal[i].command
        w.execute(c);self.assertFalse(w._studies)
        w.execute(replace(c,command_id='empty'));self.assertEqual(w._journal[-1].event.outcome,WorkStatus.DEFERRED)
        from hle.conversion_demo import run as conversion_run
        self.assertTrue(conversion_run(w)['resource_censored'])
        w.execute(Credit('fund',a,1000,1000,'explicit test funding'));fund_command(w,replace(c,command_id='funded'))
        self.assertTrue(w._studies)

    def test_next_operation_does_not_traverse_inactive_journal(self):
        i=first(self.w,'reorganize');w=prefix(self.w,i)
        for n in range(100):w.execute(Tick('quiet:'+str(n)))
        class IndexedOnly(list):
            def __iter__(self):raise AssertionError('active conversion traversed history')
        w._journal=IndexedOnly(w._journal);w.execute(self.w._journal[i].command)
        self.assertIsNotNone(w._journal[-1].candidate)

    def test_observation_matched_hidden_truth_does_not_change_recall(self):
        i=first(self.w,'recall');w=prefix(self.w,i);cmd=self.w._journal[i].command
        before=w._prepare_conversion(cmd)
        k=(cmd.item,'condition',w.config.context)
        w._facts[k]=replace(w._facts[k],object='dirty')
        self.assertEqual(w._prepare_conversion(cmd),before)

    def test_recall_rejects_foreign_or_invented_capacity(self):
        w=prefix(self.w,first(self.w,'recall'));item=self.w._journal[first(self.w,'recall')].command.item
        c=ConversionCommand('foreign','foreign',w.config.actors[1],'recall',item)
        with self.assertRaises(ValueError):w.execute(c)

    def test_fresh_actors_cannot_claim_release(self):
        w=fresh(self.w)
        with self.assertRaises(ValueError):w.execute(command(w,'release'))
        self.assertEqual(len(w._journal),1)

if __name__=='__main__':unittest.main()
