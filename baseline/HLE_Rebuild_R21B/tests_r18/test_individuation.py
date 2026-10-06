import unittest
from dataclasses import replace
from hle.individuation import IndividuationWorld,phase_seat
from hle.individuation_demo import case,do,run_order,make_offer,command,CircuitController,world,acquire_conversion,dual_of
from hle.individuation_records import *
from hle.individuation_reference import evaluate
from hle.model_a import TYPES,stack,element_at,fields
from hle.development_structure import lap,portage
from hle.world_records import Tick,Credit,Wallet
from hle.conversion_records import ConversionCommand
from hle.concept_demo import fund_command
from hle.codec import dumps,loads

def clone(w,stop=None):
    x=IndividuationWorld(w.config,w.profiles,w.policy,w.agents,w.organization_policies,w.semantic_policy,
        w.workshop,w.autonomy,release=w.release,reviewers=w.reviewers,account_policy=w.account_policy,
        conversion_policy=w.conversion_policy,circuit_policy=w.circuit_policy,partners=w.circuit_partners)
    for tx in w._journal[1:stop]:x.execute(tx.command)
    return x

def complete(w,key,delegate=False):
    for _ in range(20):
        c=CircuitController().next(w,key,delegate)
        if c is None:return w._circuit_orders[key]
        fund_command(w,c)
    raise AssertionError('unfinished')

class CircuitBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w,cls.setup=case()
        cls.report=evaluate(cls.w)
        cls.a=cls.w.config.actors[0]
    def test_full_sli(self):
        self.assertTrue(self.report['integrity_passed'],self.report['errors'])
        self.assertTrue(all(self.report['gates'].values()))
    def test_iee_complement(self):
        w,_=case('iee');r=evaluate(w)
        self.assertTrue(r['integrity_passed'],r['errors']);self.assertTrue(all(r['gates'].values()))
        self.assertEqual(r['fixed_stack'][4:6],['si','te'])
    def test_four_pairs_same_material(self):
        caps=list(self.w._aspect_caps.values())
        self.assertEqual({c.owner for c in caps},{self.a});self.assertEqual(len({c.material for c in caps}),1)
        self.assertTrue(all(len(p['own_practice'])==2 for p in self.report['complexes'].values()))
    def test_contrast_not_assignment(self):
        for c in self.w._aspect_caps.values():
            failure=self.w._records[c.failure];practice=self.w._records[c.practice]
            self.assertFalse(failure.success);self.assertIn(c.aspect,failure.errors)
            self.assertTrue(practice.success);self.assertEqual(practice.performer,self.a)
            self.assertNotEqual(failure.order,practice.order)
    def test_all_aspects_have_consequences(self):
        for a in ASPECTS:
            with self.subTest(aspect=a):
                w=clone(self.w,self.setup['acquired']);do(w,'',self.a,'withdraw',aspect=a)
                o=run_order(w,make_offer(w,'ablate:'+a,a,held=True));r=w._records[o.outcome]
                self.assertFalse(r.success);self.assertIn(a,r.errors)
    def test_both_perspective_circuits(self):
        self.assertEqual(self.report['held_out'][0]['routes'],['Theorize','Apply','Coordinate','Identify'])
        self.assertEqual(self.report['held_out'][1]['routes'],['Share','Institutionalize','Apply','Embody'])
        self.assertTrue(all(o['credited'] and o['independent'] for o in self.report['held_out']))
    def test_helper_withdrawn(self):
        h=self.w.config.actors[2]
        self.assertFalse(self.w._work_partners[h].helper_available)
        for tx in self.w._journal:
            if type(tx.command) is CircuitCommand and tx.command.order.startswith('held:'):
                self.assertNotEqual(tx.command.actor,h)
    def test_helper_does_not_establish_retention(self):
        w=clone(self.w,self.setup['start']);a,h=w.config.actors[0],w.config.actors[2]
        ie=element_at('sli',1)
        for i in range(2):run_order(w,make_offer(w,'delegate:'+str(i),ie),delegate=True)
        self.assertFalse(w._aspect_caps)
        self.assertTrue(w._records[w._circuit_orders['delegate:1'].outcome].success)
    def test_spirit_requires_previous_complexes(self):
        w=clone(self.w,self.setup['start']);a=w.config.actors[0];ie=element_at('sli',5)
        for i in range(2):run_order(w,make_offer(w,'early:'+str(i),ie))
        self.assertTrue(w._records[w._circuit_orders['early:1'].outcome].success)
        self.assertNotIn((a,ie),w._aspect_caps)
    def test_prior_capacity_withdrawal_invalidates_spirit(self):
        w=clone(self.w,self.setup['acquired']);do(w,'',self.a,'withdraw',aspect=element_at('sli',1))
        current=w._current_aspects(self.a)
        self.assertNotIn(element_at('sli',5),current);self.assertNotIn(element_at('sli',3),current)
    def test_material_access_required(self):
        w=clone(self.w,self.setup['acquired'])
        fund_command(w,ConversionCommand('restrict','restrict',self.a,'restrict'))
        self.assertFalse(w._current_aspects(self.a))
        self.assertFalse(evaluate(w)['gates']['R18.1'])
        with self.assertRaises(ValueError):w.execute(make_offer(w,'restricted','si'))
        fund_command(w,ConversionCommand('restore','restore',self.a,'restore_access'))
        self.assertEqual(len(w._current_aspects(self.a)),8)
    def test_no_retention_no_ordinary_reuse(self):
        w,_=case(circuit_policy=CircuitPolicy(retention=False))
        self.assertFalse(w._aspect_caps)
        self.assertFalse(evaluate(w)['gates']['R18.1'])
    def test_partner_refusal_has_consequences(self):
        for circuit in (0,1):
            w=clone(self.w,self.setup['acquired']);do(w,'',w.config.actors[1],'boundary',flag=False)
            o=run_order(w,make_offer(w,'refusal:'+str(circuit),'fe',circuit,held=True))
            self.assertTrue(o.closed);self.assertFalse(w._records[o.outcome].success);self.assertFalse(o.credited)
    def test_changed_partner_after_proposal(self):
        w=clone(self.w,self.setup['acquired']);f=make_offer(w,'revoked','fi',1,held=True);w.execute(f)
        do(w,f.key,f.partner,'menu');do(w,f.key,f.learner,'choose')
        do(w,'',f.partner,'boundary',flag=False);complete(w,f.key)
        o=w._circuit_orders[f.key];self.assertFalse(o.credited);self.assertFalse(w._records[o.outcome].success)
    def test_shared_system_contention(self):
        w=clone(self.w,self.setup['acquired'])
        first=make_offer(w,'compete:a','si',held=True)
        first=replace(first,options=tuple(replace(o,load=2) for o in first.options))
        second=replace(make_offer(w,'compete:b','si',held=True),epoch=first.epoch)
        second=replace(second,options=tuple(replace(o,observed_epoch=first.epoch,load=2) for o in second.options))
        o1=run_order(w,first);o2=run_order(w,second)
        self.assertTrue(w._records[o1.outcome].success)
        self.assertIn('shared_load_exhausted',w._records[o2.outcome].errors)
    def test_fixed_dimensions(self):
        self.assertEqual([fields(p)['dimensionality'] for p in range(1,9)],[4,3,2,1,1,2,3,4])
        for t in TYPES:self.assertEqual(stack(dual_of(t))[:2],stack(t)[4:6])
    def test_reverse_lap_all_seats(self):
        for p in range(1,9):
            seats=[phase_seat(p,k) for k in range(4)]
            for i in range(4):self.assertEqual(lap(seats[(i+1)%4]),seats[i])
            self.assertEqual(portage(portage(p,'cp'),'cp'),p)
    def test_original_material_and_concept_preserved(self):
        cap=self.w._capacities[self.a];m=self.w._records[cap.material]
        self.assertIn(m.concept_at_origin,self.w._records)
        self.assertTrue(self.w._accessible(self.a));self.assertTrue(cap.current)
    def test_no_clearance_awarded(self):
        self.assertIn('unassessed',self.report['clearance'])
    def test_native_workshop_reuse(self):
        from hle.autonomy_records import WorkshopCommand
        later=[tx for tx in self.w._journal[self.setup['acquired']:] if type(tx.command) is WorkshopCommand and tx.command.actor==self.a]
        for op in ('use','clean','return'):self.assertTrue(any(tx.command.operation==op and tx.event.outcome==WorkStatus.COMPLETED for tx in later))
    def test_dual_nondual_self_information_control(self):
        reports=[]
        for mode in ('self','dual','nondual'):
            w,_=case('iee',mode);r=evaluate(w);self.assertTrue(r['integrity_passed'],r['errors']);reports.append(r)
        self.assertEqual(reports[0]['correction_content'],reports[1]['correction_content'])
        self.assertEqual(reports[0]['correction_content'],reports[2]['correction_content'])
        self.assertTrue(all(all(r['gates'].values()) for r in reports))

class CircuitIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.w,cls.setup=case(renew=False)
    def prepared(self):
        w=clone(self.w,self.setup['acquired']);f=make_offer(w,'integrity','si',held=True)
        w.execute(f);do(w,f.key,f.partner,'menu');return w,f
    def test_partial_publication_and_exact_continuation(self):
        w,f=self.prepared();c=command(w,f.key,f.learner,'choose',work_limit=1);w.execute(c)
        self.assertIsNone(w._journal[-1].order);self.assertEqual(w._journal[-1].event.outcome,WorkStatus.PARTIAL)
        restored=IndividuationWorld.restore(w.checkpoint())
        resume=replace(c,command_id='resume',work_limit=1000)
        self.assertEqual(w.execute(resume),restored.execute(resume));self.assertEqual(w._journal[-1],restored._journal[-1])
    def test_job_exclusion(self):
        w,f=self.prepared();c=command(w,f.key,f.learner,'choose',work_limit=1);w.execute(c)
        with self.assertRaises(ValueError):w.execute(command(w,'',f.learner,'withdraw',aspect='si'))
        with self.assertRaises(ValueError):w.execute(ConversionCommand('conflict','conflict',f.learner,'restrict'))
    def test_changed_continuation(self):
        w,f=self.prepared();c=command(w,f.key,f.learner,'choose',work_limit=1);w.execute(c)
        with self.assertRaises(ValueError):w.execute(replace(c,command_id='changed',operator='apply'))
    def test_idempotence(self):
        w,f=self.prepared();c=command(w,f.key,f.learner,'choose');e=fund_command(w,c);n=len(w._journal);balance=w._wallets[f.learner]
        self.assertEqual(w.execute(c),e);self.assertEqual(len(w._journal),n);self.assertEqual(w._wallets[f.learner],balance)
    def test_foreign_retention_cannot_be_invoked(self):
        w,f=self.prepared()
        with self.assertRaises(ValueError):w.execute(command(w,f.key,f.helper,'choose'))
        with self.assertRaises(ValueError):w.execute(command(w,'',f.helper,'withdraw',aspect='si'))
    def test_no_protocol_shortcut(self):
        w,f=self.prepared()
        with self.assertRaises(ValueError):w.execute(command(w,f.key,f.learner,'feedback'))
        with self.assertRaises(TypeError):CircuitCommand('x','x',f.learner,f.key,'choose',developed=True)
    def test_unknown_schema(self):
        cp=loads(self.w.checkpoint())
        with self.assertRaises(ValueError):IndividuationWorld.restore(dumps(replace(cp,schema='fake')))
    def test_rehashed_fabricated_capacity_rejected(self):
        cp=loads(self.w.checkpoint());b=cp.base.base.base
        journal=list(b.journal);i=next(i for i,t in enumerate(journal) if type(t) is CircuitTransaction and t.capacities)
        tx=journal[i];journal[i]=replace(tx,capacities=(replace(tx.capacities[0],aspect='fake'),))
        cp=replace(cp,base=replace(cp.base,base=replace(cp.base.base,base=replace(b,journal=tuple(journal)))))
        with self.assertRaises(ValueError):IndividuationWorld.restore(dumps(cp))
    def test_independent_observer_detects_tamper(self):
        w=clone(self.w);idx=next(i for i,t in enumerate(w._journal) if type(t) is CircuitTransaction and t.signal is not None and t.command.operator=='apply')
        tx=w._journal[idx];w._journal[idx]=replace(tx,signal=replace(tx.signal,produced=999))
        self.assertFalse(evaluate(w)['integrity_passed'])
    def test_observation_matched_hidden_world_no_choice_effect(self):
        w,f=self.prepared();c=command(w,f.key,f.learner,'choose');before=w._prepare_circuit(c)
        w._shared_used[(f.partner,f.epoch,4)]=99
        self.assertEqual(before,w._prepare_circuit(c))
        do(w,f.key,f.learner,'choose');self.assertEqual(w._circuit_orders[f.key].chosen,f.options[-1].key)
    def test_no_inactive_journal_scan(self):
        class NoScan(list):
            def __iter__(self):raise AssertionError('inactive scan')
        w,f=self.prepared();w._journal=NoScan(w._journal)
        do(w,f.key,f.learner,'choose')
        self.assertEqual(w._circuit_orders[f.key].stage,1)
    def test_partial_no_resource_credit(self):
        w,f=self.prepared();wallet=w._wallets[f.learner]
        # Fault control does not pass replay: verifies publication guard only.
        w._wallets[f.learner]=Wallet(f.learner,0,0)
        c=command(w,f.key,f.learner,'choose');w.execute(c)
        self.assertEqual(w._journal[-1].event.outcome,WorkStatus.DEFERRED);self.assertIsNone(w._journal[-1].order)
        w.execute(Credit('resource-recovery',f.learner,1000,1000,'resource control recovery'))
        fund_command(w,replace(c,command_id='resource-resume'));self.assertEqual(w._circuit_orders[f.key].stage,1)
    def test_withdrawal_between_choice_and_action(self):
        w,f=self.prepared();do(w,f.key,f.learner,'choose')
        do(w,'',f.learner,'withdraw',aspect='si')
        with self.assertRaises(ValueError):do(w,f.key,f.learner,'apply')
    def test_actual_partner_required(self):
        w,f=self.prepared();do(w,f.key,f.learner,'choose');do(w,f.key,f.learner,'apply')
        with self.assertRaises(ValueError):do(w,f.key,f.learner,'review')
        with self.assertRaises(ValueError):do(w,f.key,f.learner,'coordinate')
    def test_mutable_or_bad_values_rejected(self):
        with self.assertRaises(ValueError):WorkOption('invalid',load=True)
        with self.assertRaises(ValueError):WorkOption('invalid',claims=[])
        with self.assertRaises(ValueError):CircuitPolicy(correction='relation-award')
    def test_exact_complete_checkpoint(self):
        text=self.w.checkpoint();restored=IndividuationWorld.restore(text)
        self.assertEqual(restored.checkpoint(),text)

if __name__=='__main__':unittest.main()
