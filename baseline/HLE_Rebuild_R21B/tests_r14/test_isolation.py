import ast
import inspect
import unittest
from dataclasses import replace
from .helpers import *
from hle import autonomy_policy
from hle.contracts import Proposition,TimeScope,ClaimStatus,Observation
from hle.memory_records import WriteDraft
from hle.development_demo import finish
from hle.world_records import RETAIN,MemoryDraft


class IsolationTests(unittest.TestCase):
    def pair(self):
        w=world();a,b,t,p=actors_items(w)
        advance_until(w,lambda x:next_selection(x,a))
        other=AutonomousWorld.restore(w.checkpoint())
        w.execute(Attempt('hidden','hidden',ActionRequest(b,TRANSFER,(t,a),())))
        other.execute(Tick('hidden-control'))
        return w,other,a,b,t,p

    def test_hidden_ownership_change_keeps_complete_local_view_and_choice_identical(self):
        w,r,a,b,t,p=self.pair()
        self.assertNotEqual(w.truth.current_fact(t,'owned_by',w.config.context),r.truth.current_fact(t,'owned_by',r.config.context))
        v=w.local_view(a);q=r.local_view(a)
        self.assertEqual(v,q)
        self.assertEqual(decide(v,'same-decision'),decide(q,'same-decision'))
        w.autonomy_step(a);r.autonomy_step(a)
        self.assertEqual(w.autonomy_state(a),r.autonomy_state(a))
        self.assertEqual(w.own_demands(a),r.own_demands(a))

    def test_visible_inspection_changes_subsequent_available_response(self):
        w,r,a,b,t,p=self.pair()
        for x in (w,r):
            x.execute(WorkshopCommand('look','look',a,'inspect',(t,)))
            autonomous_only(x,a)
        act_w=[tx.event.action for tx in w._journal if type(tx.command) is WorkshopCommand and tx.command.actor==a]
        act_r=[tx.event.action for tx in r._journal if type(tx.command) is WorkshopCommand and tx.command.actor==a]
        self.assertIn('r14.use',act_w);self.assertNotIn('r14.use',act_r)
        self.assertEqual(r.autonomy_state(a).decision.kind,'waiting')

    def test_other_private_memory_cannot_supply_own_knowledge(self):
        w=world();a,b,t,p=actors_items(w);advance_until(w,lambda x:next_selection(x,a));r=AutonomousWorld.restore(w.checkpoint())
        prop=Proposition(b,'private_note','unseen content',w.config.context,TimeScope(w.now,None))
        initial=w.select_input(b)[0].observations[0].ref
        command=MemoryCommand('private','private',b,WriteDraft('secret',(prop,),(),ClaimStatus.ENDORSED,None,'private own note'),(initial,))
        w.execute(command);r.execute(Tick('same-time'))
        self.assertEqual(w.local_view(a),r.local_view(a));self.assertEqual(decide(w.local_view(a),'q'),decide(r.local_view(a),'q'))

    def test_pure_policy_has_no_world_truth_evaluator_or_history_access(self):
        tree=ast.parse(inspect.getsource(autonomy_policy))
        forbidden={'truth','_facts','_journal','_records','checkpoint','_wallets'}
        self.assertFalse([n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute) and n.attr in forbidden])
        w=world();a,_,_,_=actors_items(w);advance_until(w,lambda x:next_selection(x,a));view=w.local_view(a)
        class Poison:
            def __getattribute__(self,name):raise AssertionError('policy touched evaluator')
        w.truth=Poison()
        decision=decide(view,'detached');self.assertIsNotNone(decision.pending)

    def test_uninterpreted_partner_request_cannot_authorize_a_loan(self):
        w=world();a,b,t,p=actors_items(w)
        advance_until(w,lambda x:any(tx.messages for tx in x._journal))
        obs=next(o.ref for o in w._inboxes[b] if o.source.kind==Kind.MESSAGE)
        before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(WorkshopCommand('premature','premature',b,'lend',(t,a),request=obs))
        self.assertEqual(w.checkpoint(),before)
        s=w.autonomy_state(b);self.assertFalse(any(d.specification.family=='return_commitment' for d in w.own_demands(a)))

    def test_foreign_memory_and_unknown_actor_reject_before_mutation(self):
        w=world();a,b,t,p=actors_items(w);advance_until(w,lambda x:x.autonomy_state(b).initialized)
        foreign=w.memory_head(b,'r14:motives').ref;before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(WorkshopCommand('foreign','foreign',a,'inspect',(t,),(foreign,)))
        with self.assertRaises(ValueError):w.execute(AutonomyTurn('unknown','unknown',Ref(Kind.ENTITY,'unknown',1)))
        self.assertEqual(w.checkpoint(),before)

    def test_loan_requires_exact_borrower_and_material_not_a_generic_consent_flag(self):
        w=world();a,b,t,p=actors_items(w)
        advance_until(w,lambda x:x.autonomy_state(b).pending is not None and type(x.autonomy_state(b).pending) is WorkshopCommand)
        c=w.autonomy_state(b).pending;self.assertEqual(c.operation,'lend');before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(replace(c,command_id='wrong',inputs=(p,a)))
        with self.assertRaises(ValueError):w.execute(replace(c,command_id='none',request=None))
        self.assertEqual(w.checkpoint(),before)

    def test_no_decision_published_during_unfinished_paid_turn(self):
        w=world(work_limit=1);a,_,_,_=actors_items(w)
        advance_until(w,lambda x:a in x._active_turn and x._turn_jobs[(a,x._active_turn[a])].outcome==WorkStatus.PARTIAL)
        job=w._turn_jobs[(a,w._active_turn[a])];before=w.autonomy_state(a)
        self.assertGreater(job.plan.required,job.paid)
        self.assertIsNone(w._journal[-1].participant)
        self.assertEqual(w._journal[-1].demands,())
        # The serialized policy snapshot holds exact memory addresses, no copied payload bodies.
        self.assertFalse(hasattr(job.snapshot,'memories_content'))
        self.assertEqual(w.autonomy_state(a),before)

    def test_withdrawn_goal_memory_does_not_count_as_satisfied_material(self):
        w=world();a,b,t,p=actors_items(w)
        advance_until(w,lambda x:'maintenance' in active_families(x,a))
        old=w.memory_head(a,'r14:motives')
        draft=WriteDraft('r14:motives',old.content,old.links,ClaimStatus.RETRACTED,old.ref,'explicit withdrawal is not physical resolution')
        finish(w,MemoryCommand('withdraw','withdraw',a,draft,(old.ref,)))
        # The already selected cleanup may still complete. Withholding its return is
        # not needed: the outstanding borrowed obligation cannot be discharged by a lost goal.
        run(w)
        outstanding=[d for d in w.own_demands(a) if d.specification.family=='return_commitment']
        self.assertTrue(outstanding);self.assertNotEqual(outstanding[-1].status,'resolved')
        self.assertTrue(w.truth.current_fact(t,'loan_active',w.config.context).object)
