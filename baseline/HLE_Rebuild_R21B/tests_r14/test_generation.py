import unittest
from dataclasses import replace
from .helpers import *
from hle.development_evaluation import accounting
from hle.autonomy_records import AutonomyTurn,WorkshopCommand,AutonomousTransaction,LocalDecision
from hle.development_contracts import Origin,compare_demands,Comparison
from hle.contracts import EvidenceStatus


class GeneratedDemandTests(unittest.TestCase):
    def test_success_creates_two_later_different_demands(self):
        w=world();a,b,t,p=actors_items(w);until_used(w)
        self.assertNotIn('maintenance',ever_families(w,a));self.assertNotIn('return_commitment',ever_families(w,a))
        use=w._journal[-1].event.ref
        self.assertEqual(w.truth.current_fact(t,'condition',w.config.context).object,'dirty')
        self.assertTrue(w.truth.current_fact(t,'return_due',w.config.context).object)
        run(w)
        for family in ('maintenance','return_commitment'):
            records=[d for d in w._demand_records.values() if d.owner==a and d.specification.family==family]
            self.assertTrue(records);self.assertIn(use,records[0].specification.origin_events)
            self.assertEqual(records[0].specification.origin,Origin.CONSEQUENCE)
            self.assertTrue(records[0].specification.material_lineage)
            self.assertTrue(all(o in w._known[a] for o in records[0].specification.discovered_from))
        actions=[x['action'] for x in report(w)['actions']]
        self.assertEqual(actions,['r14.lend','r14.use','r14.clean','r14.return'])
        self.assertEqual(active_families(w,a),set());self.assertTrue(accounting(w)['passed'])

    def test_scheduler_supplies_no_goals_solutions_or_condition_verdicts(self):
        w=world();run(w)
        for tx in w._journal[1:]:
            if type(tx.command) is AutonomyTurn:
                self.assertEqual(set(tx.command.__dataclass_fields__),{'schema_version','command_id','task_id','actor','work_limit'})
            else:
                actor=tx.command.action.actor if type(tx.command) is Attempt else tx.command.actor
                states=[q.participant for q in w._journal[:tx.event.when.tick] if type(q) is AutonomousTransaction and q.participant is not None and q.participant.owner==actor]
                self.assertTrue(states);self.assertEqual(states[-1].pending,tx.command)
        self.assertNotIn('AddGoal',{type(tx.command).__name__ for tx in w._journal})

    def test_remove_wear_consequence_removes_maintenance_demand(self):
        w=world(wear=False);a,_,_,_=actors_items(w);run(w)
        self.assertNotIn('maintenance',ever_families(w,a));self.assertIn('return_commitment',ever_families(w,a))
        self.assertNotIn('r14.clean',[x['action'] for x in report(w)['actions']])
        self.assertIn('r14.return',[x['action'] for x in report(w)['actions']])

    def test_no_loan_means_no_generated_return_obligation(self):
        w=world(borrowed=False);a,_,_,_=actors_items(w);run(w)
        self.assertIn('maintenance',ever_families(w,a));self.assertNotIn('return_commitment',ever_families(w,a))
        self.assertEqual([x['action'] for x in report(w)['actions']],['r14.use','r14.clean'])

    def test_no_due_effect_means_no_active_return_requirement(self):
        w=world(due=False);a,_,t,_=actors_items(w);run(w)
        self.assertNotIn('return_commitment',ever_families(w,a));self.assertIn('maintenance',ever_families(w,a))
        self.assertTrue(w.truth.current_fact(t,'loan_active',w.config.context).object)
        self.assertFalse(w.truth.current_fact(t,'return_due',w.config.context).object)

    def test_net_reversal_before_discovery_is_not_persistent_new_demand(self):
        w=world();a,b,t,_=actors_items(w);until_used(w)
        w.execute(WorkshopCommand('control:clean','control:clean',a,'clean',(t,)))
        w.execute(WorkshopCommand('control:return','control:return',a,'return',(t,)))
        run(w)
        self.assertNotIn('maintenance',ever_families(w,a));self.assertNotIn('return_commitment',ever_families(w,a))
        self.assertEqual(w.truth.current_fact(t,'owned_by',w.config.context).object,b)
        self.assertEqual(w.truth.current_fact(t,'condition',w.config.context).object,'clean')

    def test_physical_effect_without_local_discovery_does_not_spawn_a_task(self):
        w=world();a,b,t,_=actors_items(w);until_used(w)
        event_count=len(w._journal)
        for i in range(20):w.execute(Tick('quiet:'+str(i)))
        self.assertTrue(w.truth.current_fact(t,'return_due',w.config.context).object)
        self.assertNotIn('return_commitment',ever_families(w,a));self.assertNotIn('maintenance',ever_families(w,a))
        self.assertEqual(w.autonomy_state(a).pending.operation,'use')
        run(w);self.assertIn('return_commitment',ever_families(w,a))

    def test_failed_use_creates_neither_wear_nor_return_due(self):
        w=world();a,b,t,p=actors_items(w)
        event=w.execute(WorkshopCommand('failed','failed',a,'use',(p,t)))
        self.assertEqual(event.outcome,WorkStatus.FAILED);self.assertEqual(event.changes,())
        self.assertEqual(w.truth.current_fact(t,'condition',w.config.context).object,'clean')
        self.assertFalse(w.truth.current_fact(t,'return_due',w.config.context).object)
        self.assertEqual(w.own_demands(a),())

    def test_resolved_is_observation_conditioned_and_keeps_original_origin(self):
        w=world();a,b,t,p=actors_items(w)
        advance_until(w,lambda x:'return_commitment' in active_families(x,a))
        use=next(tx.event.ref for tx in w._journal if tx.event.action=='r14.use')
        pending=w.autonomy_state(a).pending;self.assertEqual(pending.operation,'clean')
        w.execute(pending)
        # Condition is now repaired, but its owner's prior demand is not erased by hidden state alone.
        self.assertIn('maintenance',active_families(w,a))
        run(w)
        self.assertEqual(active_families(w,a),set())
        final=next(d for d in w.own_demands(a) if d.specification.family=='return_commitment')
        self.assertIn(use,final.specification.origin_events);self.assertGreater(final.specification.ref.revision,1)
        self.assertIsNotNone(final.specification.prior_demand)

    def test_different_consequences_are_not_silently_ranked_as_harder(self):
        w=world();a,_,_,_=actors_items(w);run(w)
        first={}
        for d in w._demand_records.values():first.setdefault(d.specification.family,d.specification)
        self.assertEqual(compare_demands(first['maintenance'],first['return_commitment']).relation,Comparison.INCOMPARABLE)

    def test_ownership_displacement_does_not_discharge_accepted_obligation(self):
        w=world();a,b,t,p=actors_items(w)
        advance_until(w,lambda x:'return_commitment' in active_families(x,a))
        # A raw R2 transfer can move custody; it cannot settle the accepted loan record.
        w.execute(Attempt('displace','displace',ActionRequest(a,TRANSFER,(t,b),())))
        run(w)
        self.assertIn('return_commitment',active_families(w,a))
        self.assertEqual(w.autonomy_state(a).decision.kind,'unresolved')
        self.assertTrue(w.truth.current_fact(t,'loan_active',w.config.context).object)

    def test_no_canned_fixed_sequence_across_initial_ownership_and_effects(self):
        sequences=[]
        for kw in ({},{'borrowed':False},{'wear':False},{'borrowed':False,'wear':False}):
            w=world(**kw);run(w);sequences.append(tuple(x['action'] for x in report(w)['actions']))
        self.assertEqual(len(set(sequences)),4)

    def test_simultaneous_requirements_select_feasible_prerequisite_first(self):
        w=world();a,_,tool,_=actors_items(w)
        advance_until(w,lambda x:{'maintenance','return_commitment'}<=active_families(x,a))
        state=w.autonomy_state(a)
        self.assertEqual(state.pending.operation,'clean')
        self.assertEqual({d.family for d in state.decision.demands},{'maintenance','return_commitment'})
        run(w)
        physical=[tx.event.action for tx in w._journal if type(tx.command) is WorkshopCommand and tx.command.actor==a]
        self.assertLess(physical.index('r14.clean'),physical.index('r14.return'))

    def test_workshop_rejects_missing_ownership_and_actor_as_tool(self):
        w=world();a,b,t,p=actors_items(w)
        for config,workshop in (
            (replace(w.config,ownership=tuple(o for o in w.config.ownership if o.item!=t)),w.workshop),
            (w.config,WorkshopConfig(((a,'clean'),)))):
            with self.assertRaises(ValueError):AutonomousWorld(config,w.profiles,w.policy,w.agents,
                workshop=workshop,autonomy=w.autonomy)
