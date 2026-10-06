import unittest
from dataclasses import replace
from .helpers import *
from hle.autonomy_policy import PACKET_REL,decode_packet
from hle.contracts import Proposition,TimeScope,ClaimStatus
from hle.memory_records import WriteDraft,BindDraft
from hle.world_records import MessageDraft,SEND
from hle.development_demo import finish
from hle.development_evaluation import accounting


class ParticipantChoiceTests(unittest.TestCase):
    def test_satisfied_ground_state_is_quiet_under_clock_only(self):
        w=world(intentions=());run(w)
        self.assertFalse(report(w)['actions'])
        for a in w.config.actors:self.assertEqual(w.autonomy_state(a).decision.kind,'rest')
        before={a:(w.autonomy_state(a),w._wallets[a]) for a in w.config.actors}
        for i in range(40):w.execute(Tick('tick:'+str(i)));run(w)
        for a in w.config.actors:self.assertEqual(before[a],(w.autonomy_state(a),w._wallets[a]))
        self.assertFalse(w._demand_records)

    def test_normal_completion_returns_to_rest_not_compulsory_development(self):
        w=world();run(w)
        for a in w.config.actors:
            self.assertEqual(w.autonomy_state(a).decision.kind,'rest');self.assertFalse(w.autonomy_ready(a))
        n=len(w._journal);self.assertEqual(run(w)['opportunities'],0);self.assertEqual(len(w._journal),n)

    def test_silent_partner_is_waiting_not_a_shell(self):
        w=world();a,b,_,_=actors_items(w);autonomous_only(w,a)
        self.assertEqual(w.autonomy_state(a).decision.kind,'waiting')
        self.assertIn('production',active_families(w,a))
        self.assertFalse(any('shell' in tx.event.action.lower() for tx in w._journal))
        self.assertEqual(w.autonomy_state(a).decision.repeated_unsuccessful_attempts,0)

    def test_holder_refuses_and_requester_exhausts_without_forced_transfer(self):
        w=world(may_lend=False);a,b,t,_=actors_items(w);run(w)
        kinds=[tx.participant.decision.kind for tx in w._journal if type(tx) is AutonomousTransaction and tx.participant and tx.participant.decision]
        self.assertIn('refuse',kinds);self.assertIn('search_exhausted',kinds)
        self.assertEqual(w.truth.current_fact(t,'owned_by',w.config.context).object,b)
        self.assertFalse(report(w)['actions'])
        demand=next(d for d in w.own_demands(a) if d.specification.family=='production')
        self.assertEqual(demand.status,'unresolved')

    def test_absent_tool_exhausts_finite_known_repertoire_not_universe(self):
        w=world(tool=False);a,_,_,_=actors_items(w);run(w)
        self.assertEqual(w.autonomy_state(a).decision.kind,'search_exhausted')
        self.assertIn('finite local repertoire',w.autonomy_state(a).decision.reason)
        self.assertIn('production',active_families(w,a))

    def test_actual_help_request_and_teaching_arise_without_assigned_lesson(self):
        w=world(borrowed=False,native_use=False,teaching=True);a,b,t,p=actors_items(w);run(w)
        packets=[]
        for tx in w._journal:
            for o in tx.observations:
                packet=decode_packet(o) if o.source.kind==Kind.MESSAGE else None
                if packet:packets.append((tx.event.ref,packet))
        self.assertIn('help',[p.kind for _,p in packets]);self.assertIn('lesson',[p.kind for _,p in packets])
        teacher_use=next(tx.event for tx in w._journal if tx.event.action=='r14.use' and tx.command.actor==b)
        learner_use=next(tx.event for tx in w._journal if tx.event.action=='r14.use' and tx.command.actor==a)
        lesson_event=next(w._records[e] for e,p0 in packets if p0.kind=='lesson')
        self.assertLess(teacher_use.when,lesson_event.when);self.assertLess(lesson_event.when,learner_use.when)
        self.assertEqual(w.truth.current_fact(p,'condition',w.config.context).object,'ready')
        learned=[m for m in w._memory_heads[a].values() if any(q.relation=='r14.skill' for q in m.content)]
        self.assertTrue(learned);self.assertTrue(accounting(w)['passed'])

    def test_missing_teacher_evidence_produces_refusal_and_unresolved_need(self):
        w=world(borrowed=False,native_use=False);a,_,_,_=actors_items(w);run(w)
        self.assertEqual(w.autonomy_state(a).decision.kind,'unresolved')
        self.assertIn('technique absent',w.autonomy_state(a).decision.reason)
        self.assertNotIn('r14.use',[x['action'] for x in report(w)['actions']])

    def test_relabeling_types_does_not_insert_a_different_goal_ladder(self):
        from hle.model_a import TYPES,stack
        for tim in TYPES:
            w=world(tim=tim);a,_,t,p=actors_items(w);fixed=stack(tim);r=run(w)
            self.assertFalse(r['horizon_exhausted'])
            self.assertEqual(stack(w._profiles[a].tim),fixed)
            self.assertEqual(w.truth.current_fact(p,'condition',w.config.context).object,'ready')
            self.assertEqual(ever_families(w,a),{'production','maintenance','return_commitment'})

    def test_resource_censored_initialization_is_not_clearance_or_development(self):
        for budget in (0,1,4,20):
            w=world(energy=budget);r=run(w)
            self.assertTrue(r['resource_censored'])
            self.assertFalse(report(w)['actions']);self.assertFalse(w._demand_records)
            self.assertTrue(accounting(w)['passed'])

    def test_resource_replenishment_resumes_exact_pending_work(self):
        w=world(energy=30,work_limit=2);a,b,t,p=actors_items(w);run(w);r=AutonomousWorld.restore(w.checkpoint())
        for x in (w,r):
            for actor in x.config.actors:x.execute(Credit('grant:'+actor.key,actor,10000,10000,'explicit bounded resumption'))
            run(x,horizon=3000)
        self.assertEqual(w.checkpoint(),r.checkpoint());self.assertEqual(w.truth.current_fact(p,'condition',w.config.context).object,'ready')
        self.assertTrue(accounting(w)['passed'])

    def test_resource_reserve_can_deliberately_defer_an_available_action(self):
        w=world();a,_,_,_=actors_items(w);advance_until(w,lambda x:next_selection(x,a))
        v=w.local_view(a)
        high=replace(v,policy=replace(v.policy,reserve=max(v.energy,v.time)))
        s=decide(high,'reserved')
        self.assertEqual(s.decision.kind,'resource_limited');self.assertIsNone(s.pending)
        self.assertTrue(s.decision.demands)

    def test_external_content_not_in_grammar_is_consumed_once_without_new_task(self):
        w=world(intentions=());a,b,t,p=actors_items(w);run(w)
        prop=Proposition(b,'uninterpreted','opaque material',w.config.context,TimeScope(w.now,None))
        w.execute(Attempt('speak','speak',ActionRequest(b,SEND,(a,),()),MessageDraft((prop,))))
        r=run(w);self.assertFalse(r['horizon_exhausted'])
        self.assertFalse(w._demand_records);self.assertFalse(w.autonomy_ready(a))

    def test_need_revision_pressure_and_repetition_are_not_one_score(self):
        w=world();a,_,_,_=actors_items(w)
        advance_until(w,lambda x:'maintenance' in active_families(x,a))
        d=w.autonomy_state(a).decision
        self.assertEqual(d.need_count,2);self.assertGreater(d.discrepancy_count,0)
        self.assertEqual(d.pressure_units,0);self.assertEqual(d.repeated_unsuccessful_attempts,0)

    def test_stale_context_produces_unresolved_not_an_exception_or_false_pass(self):
        w=world();a,_,_,_=actors_items(w);advance_until(w,lambda x:next_selection(x,a))
        ptr=w.autonomy_state(a).catalog[0]
        old=w.binding_head(a,ptr.key)
        draft=BindDraft(ptr.key,old.cue,old.context,old.target,old.scope,old.ref)
        finish(w,MemoryCommand('rebind','rebind',a,draft,(old.target,old.ref)))
        self.assertFalse(w.local_view(a).access_valid)
        w.autonomy_step(a)
        self.assertEqual(w.autonomy_state(a).decision.kind,'unresolved');self.assertIsNone(w.autonomy_state(a).pending)
