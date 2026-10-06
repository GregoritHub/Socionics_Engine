import ast
import inspect
import unittest
from dataclasses import replace
from hle.closure_demo import *
from hle.closure_reference import compare
from hle.closure_policy import search,pareto,simulate,PROGRAMS
from hle.clearance_records import WithdrawEvidence
from hle.individuation_demo import do
from hle.conversion_records import ConversionCommand
from hle.codec import dumps,loads
from hle.world_records import Credit,Tick
from hle.clearance_demo import defensive_return

class ClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.final,cls.first,cls.second,cls.summary=run()
        cls.start=cls.summary['start']
    def world(self,stop=None):return clone(self.final,stop)
    def before(self,ref):return self.world(self.final._records[self.final._origins[ref]].when.tick)

    def test_two_successive_closures_use_same_actor_material_and_native_history(self):
        w=self.final;f=self.first;s=self.second
        self.assertEqual([1,2],[w._records[f['claim']].depth,w._records[s['claim']].depth])
        p=w._records[s['plan']];nodes=w._records[p.access].nodes
        self.assertIn(w._records[f['plan']].root,nodes)
        self.assertIn(w._records[f['binding']].root,nodes)
        self.assertEqual(w.clearance_report()['status'],'cleared_in_scope')

    def test_independent_raw_reconstruction_agrees(self):self.assertTrue(compare(self.final)['passed'],compare(self.final)['errors'])

    def test_observer_verdicts_are_not_delivered_or_used_by_renewal(self):
        for ref in (self.first['claim'],self.second['claim']):
            self.assertFalse(any(ref in known for known in self.final._known.values()))
            tx=self.final._journal[self.final._records[self.final._origins[ref]].when.tick]
            self.assertEqual((tx.event.actors,tx.observations,tx.works),((),(),()))
        d=self.final._records[self.second['demand']]
        self.assertEqual(d.parent,self.first['plan'])

    def test_successors_perform_without_founder_substitution(self):
        w=self.final;p=w._records[self.second['plan']];claim=w._records[self.second['claim']]
        self.assertNotIn(w.config.actors[0],p.members)
        self.assertEqual({a for _,a,_ in claim.duties},set(p.members))
        events={r for _,_,r in claim.duties}
        self.assertTrue(all(w._records[e].when.tick>=self.second['departure_index'] for e in events))
        self.assertTrue(all(w.config.actors[0] not in w._records[e].actors for e in events))
        self.assertNotIn(p.owner,w._capacities) # shared competence != individual individuation

    def test_burden_refusal_causes_participant_rule_revision(self):
        w=self.final;s=self.second
        votes=[w._records[r] for r in s['refused']]
        self.assertTrue(any(not v.approved and v.own_units>v.limit for v in votes))
        old=w._records[w._records[s['costly']].state].terms
        new=w._records[w._records[s['plan']].state].terms
        self.assertEqual(old.steps,('inspect','inspect','inspect','transfer'))
        self.assertEqual(new.steps,('inspect','transfer'))
        self.assertGreater(new.generation,old.generation)
        self.assertEqual(w._records[s['dispute']].sources[0],next(v.ref for v in votes if not v.approved))

    def test_teaching_changes_receiver_interpretation(self):
        self.assertEqual(self.first['teaching'],[('repair','accepted'),('repair','accepted')])
        w=self.final
        self.assertTrue(all(any(p.successes>=2 and p.steps==('inspect','transfer') for p in w.practices(a)) for a in w._records[self.second['plan']].members))

    def test_all_lower_alternatives_exhausted_before_necessary_verdict(self):
        for ref in (self.first['search'],self.second['search']):
            s=self.final._records[ref]
            self.assertEqual(tuple(x[0] for x in s.rows),LOWER)
            self.assertFalse(any(x[1] for x in s.rows))
            self.assertEqual(s.status,'necessary_in_declared_repertoire')

    def test_censored_search_cannot_establish_necessity(self):
        w=self.before(self.first['search']);a=w.config.actors[0]
        r=job(w,a,'search',(self.first['demand'],),search_limit=2)
        self.assertEqual(w._records[r].status,'unassessed')
        self.assertEqual(w._records[r].equal_minima,())

    def test_no_search_work_is_not_empty_conductivity(self):
        rows,options,minima,status=search('carry',('consent_cycle',),0,3)
        self.assertEqual((rows,options,minima,status),((),(),(),'unassessed'))

    def test_current_organization_success_is_horizontal(self):
        w=self.before(self.second['demand']);b=w.config.actors[1]
        d=job(w,b,'renew',(self.first['plan'],))
        r=job(w,b,'search',(d,))
        self.assertEqual(w._records[r].status,'horizontal')
        self.assertEqual(w._records[r].candidates,())

    def test_single_action_comparison_is_horizontal(self):
        w=self.before(self.first['search']);a=w.config.actors[0]
        r=job(w,a,'search',(self.first['demand'],),label='single')
        self.assertEqual(w._records[r].status,'horizontal')

    def test_equal_minimal_extensions_preserved(self):
        self.assertEqual(pareto((('x',2,3),('y',2,3),('z',3,4))),('x','y'))

    def test_partial_search_checkpoint_resumes_with_exact_debit(self):
        w=self.before(self.first['search']);a=w.config.actors[0]
        c=ClosureCommand('partial','partial',a,'search',(self.first['demand'],),work_limit=1)
        wallet=w._wallets[a];w.execute(c)
        self.assertIsNone(w._closure_jobs[a,'partial'].result)
        checkpoint=w.checkpoint();r=ClosureWorld.restore(checkpoint)
        self.assertEqual(checkpoint,r.checkpoint())
        q=replace(c,command_id='resume',work_limit=256)
        for x in (w,r):fund_command(x,q)
        self.assertEqual(w._journal,r._journal)
        j=w._closure_jobs[a,'partial']
        self.assertEqual(wallet.energy-w._wallets[a].energy,j.required)

    def test_zero_resources_defer_without_publication(self):
        w=self.before(self.first['search']);a=w.config.actors[0]
        # Isolated unit boundary fixture, not a conservation/replay trajectory.
        # Full journal accounting is checked independently in the positive run.
        from hle.world_records import Wallet
        w._wallets[a]=Wallet(a,0,0)
        c=ClosureCommand('empty','empty',a,'search',(self.first['demand'],))
        e=w.execute(c)
        self.assertEqual(e.outcome,WorkStatus.DEFERRED)
        self.assertIsNone(w._closure_jobs[a,'empty'].result)

    def test_syntax_wrapper_does_not_supply_executable_relation(self):
        w=self.before(self.first['plan']);a=w.config.actors[0]
        child=w._records[self.first['binding']].root
        root=compose(w,a,FoldDraft('wrapper',(Part('same',child,w.config.context),)),'wrapper')
        access=compose(w,a,UnfoldDraft(root,w.config.context,w.now),'wrapper-access')
        with self.assertRaises(ValueError):job(w,a,'propose',(self.first['demand'],self.first['search'],access,w.organization_state(a,self.first['identity']).ref))

    def test_missing_or_refused_consent_blocks_activation(self):
        w=self.before(self.second['dispute']);p=w._records[self.second['costly']]
        refused={w._records[r].owner:r for r in self.second['refused']}
        with self.assertRaises(ValueError):activate(w,p.ref,refused)
        w=self.before(self.first['claim']);active=w._records[self.final._records[self.first['claim']].activation]
        p=w._records[active.plan]
        with self.assertRaises(ValueError):job(w,p.owner,'activate',(p.ref,)+active.votes[:1])

    def test_endpoint_and_plan_without_duties_do_not_close(self):
        active=self.final._records[self.second['claim']].activation
        w=self.world(self.final._records[self.final._origins[active]].when.tick+1)
        r=job(w,w._records[active].owner,'settle',(active,))
        self.assertEqual(w._records[r].status,'unresolved')
        self.assertFalse(dict(w._records[r].predicates)['obligations_preserved'])

    def test_duplicate_event_cannot_pay_two_obligations(self):
        w=self.final;claim=w._records[self.second['claim']]
        self.assertEqual(len({e for _,_,e in claim.duties}),len(claim.duties))
        d=w._records[self.second['demand']]
        self.assertEqual({k for k,_,_ in claim.duties},set(d.obligations))

    def test_credited_production_cannot_be_spent_again(self):
        w=self.world();b=w.config.actors[1]
        with self.assertRaises(ValueError):job(w,b,'renew',(self.first['plan'],))

    def test_changed_child_invalidates_both_affected_parent_claims(self):
        w=self.world();a=w.config.actors[0];b=w._records[self.first['binding']]
        leaf=w._records[b.root].parts[0].target;m=w._records[leaf]
        write(w,a,'native-reference',m.content,(leaf,),leaf)
        self.assertEqual([r['current_status'] for r in w.closure_report()['claims']],['invalidated','invalidated'])
        self.assertTrue(compare(w)['passed'],compare(w)['errors'])

    def test_unrelated_revision_does_not_invalidate_parent(self):
        w=self.world();a=w.config.actors[0];before=w.closure_report()
        known=next(o.ref for o in reversed(w._inboxes[a]))
        r=write(w,a,'unrelated',(Proposition(a,'note','unrelated',w.config.context,TimeScope(w.now,None)),),(known,))
        write(w,a,'unrelated',w._records[r].content,(r,),r)
        self.assertEqual(w.closure_report(),before)

    def test_native_capacity_withdrawal_reopens_parent(self):
        w=self.world();do(w,'',w.config.actors[0],'withdraw',aspect='ne')
        self.assertEqual(w.closure_report()['claims'][-1]['current_status'],'invalidated')
        self.assertTrue(compare(w)['passed'],compare(w)['errors'])

    def test_native_material_suppression_reopens_parent_without_erasure(self):
        w=self.world();a=w.config.actors[0];material=w._records[self.first['binding']].material
        fund_command(w,ConversionCommand('suppress','suppress',a,'restrict'))
        self.assertIn(material,w._records)
        self.assertEqual(w.closure_report()['claims'][-1]['current_status'],'invalidated')

    def test_source_event_withdrawal_reopens_parent(self):
        w=self.world();b=w._records[self.first['binding']]
        w.execute(WithdrawEvidence('source-withdraw',w._origins[b.production],'support withdrawn'))
        self.assertEqual(w.closure_report()['claims'][-1]['current_status'],'invalidated')
        self.assertTrue(compare(w)['passed'],compare(w)['errors'])

    def test_withdrawn_lower_closure_evidence_invalidates_higher_claim(self):
        w=self.world();old=w._records[self.first['claim']]
        w.execute(WithdrawEvidence('lower-withdraw',old.duties[0][2],'historical child evidence withdrawn'))
        self.assertEqual(w.closure_report()['claims'][-1]['current_status'],'invalidated')
        self.assertTrue(compare(w)['passed'],compare(w)['errors'])

    def test_withdrawn_member_commitment_cannot_support_settlement(self):
        active=self.final._records[self.second['claim']].activation
        w=self.before(self.second['claim']);a=w._records[active].owner
        source=w._records[active].votes[0];vote=w._read_closure(a,source).record
        w.execute(WithdrawEvidence('consent-withdraw',vote.ref,'member evidence retracted'))
        r=job(w,a,'settle',(active,))
        self.assertEqual(w._records[r].status,'unresolved')
        self.assertFalse(dict(w._records[r].predicates)['current_exact_consent'])

    def test_recurrence_cannot_hide_behind_successful_collective_endpoint(self):
        w=self.world();item=self.first['item'];borrow(w,item,w.config.actors[1]);defensive_return(w,item)
        self.assertEqual(w.clearance_report()['status'],'unresolved')
        self.assertEqual(w.closure_report()['claims'][-1]['current_status'],'invalidated')

    def test_shared_access_is_explicit_and_does_not_confer_native_competence(self):
        w=self.before(self.first['plan']);a,b,c=w.config.actors;root=w._records[self.first['binding']].root
        with self.assertRaises(ValueError):compose(w,b,UnfoldDraft(root,w.config.context,w.now),'forbidden')
        self.assertNotIn(b,self.final._capacities)
        self.assertIn(root,self.final._closure_shared[b])

    def test_lower_organization_remains_usable_after_succession(self):
        w=self.world();a,b,c=w.config.actors
        sig=w._signature(a);f=make_offer(w,'r20:lower-still-usable','ni',held=True,all_traps=True)
        o=run_order(w,f)
        borrow(w,self.first['item'],b);e=own_return(w,self.first['item'])
        self.assertEqual(e.outcome,WorkStatus.COMPLETED)
        self.assertTrue(w._records[o.outcome].success)
        self.assertEqual(w._signature(a),sig)

    def test_pure_policy_has_no_world_or_assessment_access(self):
        from hle import closure_policy
        tree=ast.parse(inspect.getsource(closure_policy))
        self.assertFalse([x for x in ast.walk(tree) if isinstance(x,ast.Attribute) and x.attr in ('_records','_facts','_journal','truth','_closure_claims')])

    def test_primitive_effect_order_not_program_name_confers_conductivity(self):
        self.assertTrue(simulate(PROGRAMS['carry_obligations'],'carry',('consent_cycle',))[0])
        self.assertFalse(simulate(tuple(reversed(PROGRAMS['carry_obligations'])),'carry',('consent_cycle',))[0])
        self.assertFalse(simulate(('rename','transfer_all','retain_individual'),'shared',())[0])
        self.assertFalse(simulate(PROGRAMS['carry_obligations'],'carry',())[0])
        self.assertEqual(search('carry',(),64,3)[-1],'unresolved')
        self.assertEqual(search('carry',('carry_obligations',),64,3)[-1],'horizontal')

    def test_participant_renewal_and_search_ignore_evaluator_state(self):
        w=self.before(self.second['demand']);a=w.config.actors[1]
        class Poison:
            def __getattribute__(self,name):raise AssertionError('participant consulted evaluator')
        w._closure_claims=Poison()
        d=job(w,a,'renew',(self.first['plan'],))
        r=job(w,a,'search',(d,))
        self.assertEqual(w._records[r].status,'horizontal')

    def test_checkpoint_replay_and_forged_claim_rejection(self):
        w=self.final;text=w.checkpoint();restored=ClosureWorld.restore(text)
        self.assertEqual(restored.checkpoint(),text)
        self.assertEqual(restored.closure_report(),w.closure_report())
        cp=loads(text)
        # Find the journal-bearing nested compensation value structurally.
        def corrupt(value):
            if hasattr(value,'journal') and value.journal:
                journal=list(value.journal);idx=next(i for i,t in enumerate(journal) if type(t) is ClosureTransaction and t.extra and type(t.extra[0]) is ClosureResult)
                t=journal[idx];fake=replace(t.extra[0],depth=77)
                journal[idx]=replace(t,extra=(fake,))
                return replace(value,journal=tuple(journal))
            return replace(value,base=corrupt(value.base))
        with self.assertRaises(ValueError):ClosureWorld.restore(dumps(corrupt(cp)))

    def test_unpaid_or_altered_wire_packet_is_rejected(self):
        w=self.before(self.first['plan']);a,b,c=w.config.actors
        p=self.final._records[self.first['plan']]
        from hle.codec import dumps
        prop=Proposition(a,'r20_wire',dumps(ClosurePacket(a,p)),w.config.context,TimeScope(w.now,None))
        from hle.world_records import MessageDraft,SEND
        with self.assertRaises(ValueError):w.execute(Attempt('forged','forged',ActionRequest(a,SEND,(b,),()),MessageDraft((prop,))))

if __name__=='__main__':unittest.main()
