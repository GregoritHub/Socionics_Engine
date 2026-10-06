import ast
from dataclasses import replace
from pathlib import Path
import unittest

from hle.contracts import (EvidenceStatus as E, Kind, Proposition, Ref, TimeScope,
    WorkStatus)
from hle.crux import Perspective
from hle.demo import ALICE,BOB,BOX,TOOL,ROOM,request
from hle.metabolism_records import MetabolicCommand,ProcessingPolicy,Profile,TheorizeDraft
from hle.memory_records import MemoryCommand
from hle.model_a import TYPES,element_at,position_of
from hle.socion import SocionWorld
from hle.socion_demo import demand,learned_pair,run_socion_demo,settle,world
from hle.socion_policy import decide,item_key
from hle.socion_records import (AddGoal,AgentPolicy,AssessDyads,CloseRound,ConfigureAgent,
    DeclareDyad,Goal,OpenRound,PlanTurn,ReceiveCommand,Reception,RoundResult,GoalResult)
from hle.world_records import Attempt,Correction,Credit,INSPECT,MessageDraft,SEND,Tick,TRANSFER,Witness
from .reference_socion import complete_round
from .support import rules


def message_world(types=('lse','iee'),processing=ProcessingPolicy(),energy=5000,time=5000):
    w=world(types,processing,energy=energy,time=time)
    claim=Proposition(BOX,'owned_by',ALICE,ROOM,TimeScope(w.now,None))
    e=w.execute(Attempt('message','message',request(ALICE,SEND,(BOB,),
        (w._inboxes[ALICE][0].ref,)),message=MessageDraft((claim,))))
    observation=next(o for o in w._journal[e.when.tick].observations if o.observer==BOB)
    return w,observation


def round_open(w,key='r',max_units=2000):
    w.execute(DeclareDyad('declare:'+key,key,ALICE,BOB,BOX,max_units))
    study=Ref(Kind.ASSESSMENT,'dyad:'+key,1)
    w.execute(OpenRound('open:'+key,study,key))
    return study,Ref(Kind.DEMAND,'dyad-round:'+key,1)


class Socion(unittest.TestCase):
    @rules('X01','X03','X07')
    def test_complete_two_way_exchange_and_return(self):
        w,s=run_socion_demo()
        self.assertEqual((s['return'],s['path'],s['meaning']),('established',)*3)
        self.assertEqual(s['WE']['align'],'unassessed')
        for u in w._goal_results.values():
            a=w._records[u.account]
            self.assertIn(a.claim,w._records[u.received].content)
            self.assertTrue(any(u.received in w._records[r].observations for r in a.evidence))
            self.assertIn((u.owner,u.received),w._completed_reception)

    @rules('X01')
    def test_policy_is_pure_and_has_no_world_or_assessor_import(self):
        path=Path(__file__).parents[1]/'hle/socion_policy.py'
        tree=ast.parse(path.read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.Attribute):self.assertNotIn(n.attr,('truth','_facts','_journal','_records','_reports'))
            if isinstance(n,ast.ImportFrom):self.assertNotIn(n.module,('world','assessment','socion','socion_assessment'))
        w=world();settle(w)
        w.execute(AddGoal('g',Goal('g',ALICE,BOX,BOB)))
        v=w.agent_view(ALICE)
        self.assertEqual(decide(v,'choice'),decide(v,'choice'))

    @rules('X01')
    def test_hidden_change_cannot_select_a_different_action(self):
        w=world();settle(w)
        event=w.execute(Attempt('give','give',request(ALICE,TRANSFER,(BOX,BOB))))
        settle(w);cp=w.checkpoint()
        a=SocionWorld.restore(cp);b=SocionWorld.restore(cp)
        a.execute(Correction('hidden',event.ref,ALICE,'hidden matched truth intervention'))
        b.execute(Tick('same-time'))
        for c in (a,b):c.execute(AddGoal('g',Goal('g',BOB,BOX,ALICE)))
        self.assertEqual(a.agent_view(BOB),b.agent_view(BOB))
        self.assertEqual(decide(a.agent_view(BOB),'k'),decide(b.agent_view(BOB),'k'))

    @rules('X01')
    def test_foreign_observation_cannot_be_received(self):
        w,o=message_world();before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(ReceiveCommand('bad','bad',ALICE,o.ref))
        self.assertEqual(w.checkpoint(),before)

    @rules('X01','X07')
    def test_evaluator_has_no_participant_delivery_or_policy_effect(self):
        a=world();settle(a);b=SocionWorld.restore(a.checkpoint())
        a.execute(DeclareDyad('d','d',ALICE,BOB,BOX));a.execute(AssessDyads('assess'))
        b.execute(Tick('t1'));b.execute(Tick('t2'))
        for actor in (ALICE,BOB):self.assertEqual(a.agent_view(actor),b.agent_view(actor))

    @rules('X02','X05')
    def test_all_type_pairs_and_price_controls_have_real_reception(self):
        totals={}
        for typed in (False,True):
            for prices in (False,True):
                rows=[]
                for sender in TYPES:
                    for receiver in TYPES:
                        w,o=message_world((sender,receiver),ProcessingPolicy(typed,prices))
                        w.execute(ReceiveCommand('receive','receive',BOB,o.ref))
                        r=w._receptions[(BOB,'receive')]
                        source_type=sender if typed else 'ile';target_type=receiver if typed else 'ile'
                        self.assertEqual(element_at(source_type,r.source_position),element_at(target_type,r.landing_position))
                        self.assertEqual(r.completed,r.plan.required)
                        self.assertEqual(w._spent[BOB],r.plan.required)
                        self.assertEqual(w.processing_state(BOB).active,r.plan.path[-1])
                        rows.append(r.plan.required)
                totals[(typed,prices)]=set(rows)
        self.assertEqual(len(totals[(False,False)]),1)
        self.assertEqual(len(totals[(False,True)]),1)
        self.assertGreater(len(totals[(True,True)]),1)

    @rules('X02','X06')
    def test_partial_reception_preserves_plan_and_exact_charges(self):
        w,o=message_world();w.execute(ReceiveCommand('r1','r',BOB,o.ref,1))
        original=w._receptions[(BOB,'r')];self.assertNotEqual(original.outcome,WorkStatus.COMPLETED)
        clone=SocionWorld.restore(w.checkpoint())
        for c in (w,clone):
            c.execute(ReceiveCommand('r2','r',BOB,o.ref,100))
            self.assertEqual(c._spent[BOB],original.plan.required)
        self.assertEqual(w.checkpoint(),clone.checkpoint())

    @rules('X02','X06')
    def test_interleaved_or_changed_reception_is_rejected_without_charge(self):
        w,o=message_world();w.execute(ReceiveCommand('r1','r',BOB,o.ref,1));before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(ReceiveCommand('different','different',BOB,o.ref))
        self.assertEqual(w.checkpoint(),before)
        with self.assertRaises(ValueError):w.execute(ReceiveCommand('changed','r',BOB,w._inboxes[BOB][0].ref))
        self.assertEqual(w.checkpoint(),before)

    @rules('X03')
    def test_delivery_alone_is_not_retention_or_understanding(self):
        w,o=message_world()
        self.assertNotIn((BOB,o.ref),w._completed_reception)
        self.assertIsNone(w.memory_head(BOB,item_key(BOX)))
        self.assertFalse(w._goal_results)

    @rules('X03')
    def test_ambiguous_and_unknown_messages_are_not_interpreted(self):
        w=world();settle(w);before=len(w._notices[BOB])
        for i,content in enumerate((
            (Proposition(BOX,'owned_by',ALICE,ROOM,TimeScope(w.now,None)),Proposition(BOX,'owned_by',BOB,ROOM,TimeScope(w.now,None))),
            (Proposition(BOX,'unimplemented_word',ALICE,ROOM,TimeScope(w.now,None)),))):
            w.execute(Attempt('bad:'+str(i),'bad:'+str(i),request(ALICE,SEND,(BOB,)),message=MessageDraft(content)))
        self.assertEqual(len(w._notices[BOB]),before)

    @rules('X03','X05')
    def test_exchange_changes_action_and_learning_against_no_query(self):
        first=[];capacities=[]
        for ask in (False,True):
            w=world(agents=(AgentPolicy(ALICE,ask=ask),AgentPolicy(BOB)));settle(w)
            w.execute(Attempt('give','give',request(BOB,TRANSFER,(TOOL,ALICE))));settle(w)
            u=demand(w,'g',ALICE,TOOL,BOB);app=w._records[u.application]
            first.append(w._records[app.enactments[0]].request.operation)
            capacities.append(bool(w._records[u.retained].capabilities))
            self.assertEqual(bool(u.received),ask)
        self.assertEqual(first,[INSPECT,TRANSFER]);self.assertEqual(capacities,[True,False])

    @rules('X03')
    def test_stale_report_cannot_replace_later_direct_knowledge(self):
        w=world();settle(w)
        old=w.memory_head(BOB,item_key(BOX)).content[0]
        w.execute(Attempt('give','give',request(ALICE,TRANSFER,(BOX,BOB))));settle(w)
        current=w.memory_head(ALICE,item_key(BOX))
        w.execute(Attempt('stale','stale',request(BOB,SEND,(ALICE,)),message=MessageDraft((old,))))
        settle(w)
        self.assertEqual(w.memory_head(ALICE,item_key(BOX)),current)
        self.assertTrue(any(':testimony:' in m.ref.key for m in w._memory_heads[ALICE].values()))

    @rules('X04')
    def test_both_participants_learn_from_their_own_consequences(self):
        w=learned_pair()
        for actor in (ALICE,BOB):
            memory=w.read_revision(actor,w.agent_state(actor).lesson)
            self.assertTrue(memory.capabilities)
            cap=w._records[memory.capabilities[0]]
            self.assertEqual(cap.owner,actor)
            self.assertTrue(w._records[cap.application].discrepancy)
            self.assertTrue(all(w._records[o].observer==actor for o in cap.evidence))

    @rules('X04','X05')
    def test_matched_lesson_access_changes_replies_and_heldout_actions(self):
        base=learned_pair();cp=base.checkpoint();rows=[]
        for receiver_enabled,sender_enabled in ((False,False),(False,True),(True,False),(True,True)):
            w=SocionWorld.restore(cp)
            before=tuple(w._wallets.values())
            for actor,enabled in ((ALICE,receiver_enabled),(BOB,sender_enabled)):
                w.execute(ConfigureAgent('control:'+actor.key,replace(w._agent_policies[actor],use_lesson=enabled),'matched lesson access'))
            self.assertEqual(tuple(w._wallets.values()),before)
            begin=len(w._journal)
            u=demand(w,'heldout',ALICE,TOOL,BOB);a=w._records[u.account];app=w._records[u.application]
            checks=[t for t in w._journal[begin:] if type(t.command) is Attempt and t.command.action.actor==BOB and t.command.action.operation==INSPECT]
            rows.append((a.guard is not None,bool(checks),w._records[app.enactments[0]].request.operation))
        self.assertEqual(rows,[(False,False,TRANSFER),(False,True,TRANSFER),(True,False,INSPECT),(True,True,INSPECT)])

    @rules('X04')
    def test_both_directions_use_a_lesson_on_other_object(self):
        w=learned_pair()
        for actor,item,partner in ((ALICE,TOOL,BOB),(BOB,BOX,ALICE)):
            u=demand(w,'heldout:'+actor.key,actor,item,partner)
            self.assertIsNotNone(w._records[u.account].guard)
            cap=w._records[w._records[u.account].guard]
            learned_item=w._records[w._records[cap.application].account].item
            self.assertNotEqual(learned_item,item)

    @rules('X05')
    def test_silent_and_unavailable_partner_produce_timeout_and_own_checking(self):
        for muted in (False,True):
            agents=(AgentPolicy(ALICE,patience=3),AgentPolicy(BOB,response='silent' if muted else 'adaptive'))
            w=world(agents=agents,links=None if muted else ());settle(w)
            u=demand(w,'g',ALICE,BOX,BOB)
            self.assertIsNotNone(u);self.assertIsNone(u.received)

    @rules('X05')
    def test_full_and_occurrence_observation_access_are_distinct(self):
        observed=[]
        for mode in ('occurrence','full'):
            w=world(witnesses=(Witness(ALICE,TOOL,mode),));settle(w)
            w.execute(Attempt('give','give',request(BOB,TRANSFER,(TOOL,ALICE))));settle(w)
            observed.append(w.memory_head(ALICE,item_key(TOOL)).content[0].object)
        self.assertEqual(observed,[BOB,ALICE])

    @rules('X05','X06')
    def test_energy_and_time_each_independently_block_reception(self):
        for energy,time in ((0,100),(100,0)):
            w,o=message_world(energy=100,time=100)
            # Consume just the selected resource through initial config, preserving sender funding.
            from hle.world_records import Wallet
            cfg=replace(w.config,wallets=(Wallet(ALICE,100,100),Wallet(BOB,energy,time)))
            c=SocionWorld(cfg,w.profiles,w.policy,w.agents)
            c.execute(w._journal[1].command)
            c.execute(ReceiveCommand('r','r',BOB,o.ref))
            self.assertEqual(c._receptions[(BOB,'r')].completed,0)
            self.assertEqual(c._spent[BOB],0)
            c.execute(Credit('credit',BOB,100 if energy==0 else 0,100 if time==0 else 0,'matched resource restoration'))
            c.execute(ReceiveCommand('resume','r',BOB,o.ref))
            self.assertEqual(c._receptions[(BOB,'r')].outcome,WorkStatus.COMPLETED)

    @rules('X06')
    def test_pending_decision_cannot_be_skipped(self):
        w=world();w.advance(ALICE);before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(PlanTurn('skip',ALICE))
        self.assertEqual(w.checkpoint(),before)

    @rules('X06')
    def test_all_demo_prefixes_continue_exactly(self):
        full,_=run_socion_demo();journal=tuple(full._journal)
        w=SocionWorld(full.config,full.profiles,full.policy,full.agents)
        for i,tx in enumerate(journal[1:],1):
            w.execute(tx.command)
            c=SocionWorld.restore(w.checkpoint())
            self.assertEqual(c.checkpoint(),w.checkpoint())
            if i+1<len(journal):
                c.execute(journal[i+1].command)
                self.assertEqual(c._journal[-1],journal[i+1])

    @rules('X06')
    def test_tampered_policy_result_rejects_even_when_rehashed(self):
        from hle.codec import dumps,loads
        w=world();w.advance(ALICE)
        cp=loads(w.checkpoint());tx=cp.journal[-1]
        state=replace(tx.extra[0],cursor=99)
        bad=replace(cp,journal=cp.journal[:-1]+(replace(tx,extra=(state,)),))
        with self.assertRaises(ValueError):SocionWorld.restore(dumps(bad))

    @rules('X06')
    def test_partial_memory_and_crux_continue_without_refunds(self):
        agents=(AgentPolicy(ALICE,work_limit=1),AgentPolicy(BOB,work_limit=1))
        w=world(agents=agents);settle(w);w.execute(AddGoal('g',Goal('g',ALICE,BOX,BOB)))
        captured=set()
        for i in range(1600):
            for actor in (ALICE,BOB):
                if not w.ready(actor):continue
                w.advance(actor);tx=w._journal[-1]
                if type(tx.command) in (MemoryCommand,MetabolicCommand,ReceiveCommand) and tx.event.outcome==WorkStatus.PARTIAL:
                    tag=type(tx.command).__name__
                    if tag not in captured:
                        clone=SocionWorld.restore(w.checkpoint())
                        clone.advance(actor);w.advance(actor)
                        self.assertEqual(clone.checkpoint(),w.checkpoint());captured.add(tag)
            if not any(w.ready(a) for a in (ALICE,BOB)):break
        self.assertEqual(captured,{'MemoryCommand','MetabolicCommand','ReceiveCommand'})
        self.assertEqual(len(w._goal_results),1)

    @rules('X06')
    def test_duplicate_command_does_not_charge_twice(self):
        w,o=message_world();cmd=ReceiveCommand('r','r',BOB,o.ref)
        w.execute(cmd);before=w.checkpoint();w.execute(cmd)
        self.assertEqual(w.checkpoint(),before)

    @rules('X07')
    def test_missing_return_is_unassessed_and_path_budget_is_separate(self):
        w=world();settle(w);s,start=round_open(w,max_units=1)
        demand(w,'out',ALICE,BOX,BOB)
        w.execute(CloseRound('close',start));r=w._round_results[Ref(Kind.EVIDENCE,'closed:'+start.key,1)]
        self.assertEqual((r.identity,r.meaning,r.path),(E.UNASSESSED,E.UNASSESSED,E.FAILED))

    @rules('X07')
    def test_return_can_pass_while_cost_path_fails(self):
        w=world();settle(w);s,start=round_open(w,max_units=1)
        demand(w,'out',ALICE,BOX,BOB);demand(w,'back',BOB,BOX,ALICE)
        w.execute(CloseRound('close',start));w.execute(AssessDyads('assess'))
        r=w.dyad_report(s);self.assertEqual(r.identity,E.ESTABLISHED);self.assertEqual(r.path,E.FAILED)
        result=w._round_results[r.rounds[0]]
        self.assertEqual((result.identity,result.path,result.meaning,result.units),complete_round(w.config,tuple(w._journal),start))

    @rules('X07')
    def test_failed_round_is_not_erased_by_later_success(self):
        w=world();settle(w);s,start=round_open(w)
        demand(w,'out',ALICE,BOX,BOB);demand(w,'wrong',ALICE,BOX,BOB)
        w.execute(CloseRound('close',start));w.execute(AssessDyads('assess'))
        self.assertEqual(w.dyad_report(s).identity,E.FAILED)
        demand(w,'reset',BOB,BOX,ALICE)
        w.execute(OpenRound('open2',s,'r2'))
        demand(w,'out2',ALICE,BOX,BOB);demand(w,'back2',BOB,BOX,ALICE)
        w.execute(CloseRound('close2',Ref(Kind.DEMAND,'dyad-round:r2',1)));w.execute(AssessDyads('assess2'))
        self.assertEqual(w.dyad_report(s).identity,E.FAILED)
        self.assertEqual(w.dyad_report(s).closure,E.FAILED)
        for result in w._round_results.values():
            self.assertEqual((result.identity,result.path,result.meaning,result.units),complete_round(w.config,tuple(w._journal),result.start))

    @rules('X07')
    def test_declare_rejects_identical_actors_and_late_round(self):
        w=world();settle(w);before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(DeclareDyad('d','d',ALICE,ALICE,BOX))
        self.assertEqual(w.checkpoint(),before)
        w.execute(DeclareDyad('d','d',ALICE,BOB,BOX));s=Ref(Kind.ASSESSMENT,'dyad:d',1)
        w.execute(AddGoal('g',Goal('g',ALICE,BOX,BOB)))
        with self.assertRaises(ValueError):w.execute(OpenRound('late',s,'late'))

    @rules('X08')
    def test_independent_full_history_round_comparison(self):
        w,_=run_socion_demo()
        for r in w._round_results.values():
            self.assertEqual((r.identity,r.path,r.meaning,r.units),complete_round(w.config,tuple(w._journal),r.start))

    @rules('X08')
    def test_affected_queue_does_not_schedule_other_items(self):
        w=world();settle(w)
        for key,item in (('box',BOX),('tool',TOOL)):
            w.execute(DeclareDyad('d:'+key,key,ALICE,BOB,item))
        w.execute(AssessDyads('first',2));before=w.dyad_visits
        old=w.dyad_report(Ref(Kind.ASSESSMENT,'dyad:box',1))
        w.execute(Attempt('give','give',request(ALICE,TRANSFER,(BOX,BOB))))
        self.assertEqual(w.pending_dyads(),(Ref(Kind.ASSESSMENT,'dyad:box',1),))
        self.assertFalse(w.dyad_report_is_current(old))
        w.execute(AssessDyads('second'));self.assertEqual(w.dyad_visits,before+1)

    @rules('X08')
    def test_active_steps_do_not_iterate_global_history_or_unrelated_studies(self):
        class NoScanList(list):
            def __iter__(self):raise AssertionError('whole history traversal')
        class NoScanDict(dict):
            def __iter__(self):raise AssertionError('whole study traversal')
            def values(self):raise AssertionError('whole study traversal')
            def items(self):raise AssertionError('whole study traversal')
        w=world();settle(w)
        for i in range(30):w.execute(DeclareDyad('d:'+str(i),str(i),ALICE,BOB,TOOL))
        w.execute(AssessDyads('drain',30))
        for i in range(100):w.execute(Tick('inactive:'+str(i)))
        w._journal=NoScanList(w._journal);w._dyads=NoScanDict(w._dyads)
        demand(w,'active',ALICE,BOX,BOB)
        self.assertFalse(w.pending_dyads())

    @rules('X06','X08')
    def test_partly_drained_assessment_queue_restores(self):
        w=world()
        for i in range(3):w.execute(DeclareDyad('d:'+str(i),str(i),ALICE,BOB,BOX))
        w.execute(AssessDyads('one'));self.assertEqual(len(w.pending_dyads()),2)
        c=SocionWorld.restore(w.checkpoint())
        for v in (w,c):v.execute(AssessDyads('rest',2))
        self.assertEqual(c.checkpoint(),w.checkpoint())

    @rules('X05')
    def test_reverse_scheduler_still_has_independent_successful_goals(self):
        for order in ((ALICE,BOB),(BOB,ALICE)):
            w=world();settle(w,order=order)
            w.execute(AddGoal('a',Goal('a',ALICE,BOX,BOB)));w.execute(AddGoal('b',Goal('b',BOB,TOOL,ALICE)))
            settle(w,order=order)
            self.assertEqual(len(w._goal_results),2)
            for u in w._goal_results.values():self.assertEqual(w._records[u.application].outcome,WorkStatus.COMPLETED)
