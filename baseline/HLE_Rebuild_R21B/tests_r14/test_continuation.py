import unittest
from dataclasses import replace
from .helpers import *
from hle.autonomy_evaluation import audit,reference_demands,all_prefixes,fresh_schedulers
from hle import codec
from hle.development_demo import TRAINING,store,process
from hle.contracts import Moment,ClaimStatus,Proposition,TimeScope
from hle.memory_records import WriteDraft


class ContinuationTests(unittest.TestCase):
    def test_every_prefix_of_generated_demands_and_policy_work(self):
        w=world();run(w);result=all_prefixes(w)
        self.assertEqual(result['prefixes'],len(w._journal));self.assertGreaterEqual(result['prefixes'],150)
        self.assertIn('AutonomyTurn:partial',result['cutpoints']);self.assertTrue(audit(w)['passed'])

    def test_fresh_schedulers_independently_choose_identical_remaining_work(self):
        self.assertGreaterEqual(fresh_schedulers()['fresh_controllers'],4)

    def test_incremental_demands_match_independent_bounded_reference(self):
        for kw in ({},{'wear':False},{'may_lend':False},{'native_use':False,'teaching':True,'borrowed':False}):
            w=world(**kw);run(w);self.assertGreater(reference_demands(w)['decisions_checked'],0)

    def test_private_snapshot_is_addresses_not_duplicate_memory_records(self):
        w=world();run(w)
        for job in w._turn_jobs.values():
            self.assertIsInstance(job.snapshot.state,Ref)
            for ref,indices in job.snapshot.memories:self.assertIsInstance(ref,Ref);self.assertTrue(all(type(i) is int for i in indices))
            self.assertFalse(hasattr(job,'candidate'))

    def test_rehashed_generated_goal_tampering_fails_replay(self):
        w=world();a,_,_,_=actors_items(w);advance_until(w,lambda x:bool(x._demand_records));cp=codec.loads(w.checkpoint());tx=cp.journal[-1]
        record=tx.demands[0];spec=replace(record.specification,required_outcomes=('fabricated forced goal',));bad=replace(tx,demands=(replace(record,specification=spec),)+tx.demands[1:])
        with self.assertRaises(ValueError):AutonomousWorld.restore(codec.dumps(replace(cp,journal=cp.journal[:-1]+(bad,))))

    def test_rehashed_selected_action_and_payment_tampering_fail(self):
        w=world();a,_,_,_=actors_items(w);advance_until(w,lambda x:bool(x._demand_records));cp=codec.loads(w.checkpoint());tx=cp.journal[-1]
        badstate=replace(tx.participant,pending=None)
        for bad in (replace(tx,participant=badstate),replace(tx,decision_job=replace(tx.decision_job,paid=0))):
            with self.assertRaises(ValueError):AutonomousWorld.restore(codec.dumps(replace(cp,journal=cp.journal[:-1]+(bad,))))

    def test_rehashed_snapshot_cannot_inject_foreign_private_memory(self):
        w=world();a,b,_,_=actors_items(w);advance_until(w,lambda x:bool(x._demand_records));cp=codec.loads(w.checkpoint());tx=cp.journal[-1]
        foreign=w.memory_head(b,'r14:motives').ref
        snap=replace(tx.decision_job.snapshot,memories=((foreign,(0,)),))
        bad=replace(tx,decision_job=replace(tx.decision_job,snapshot=snap))
        with self.assertRaises(ValueError):AutonomousWorld.restore(codec.dumps(replace(cp,journal=cp.journal[:-1]+(bad,))))

    def test_partial_physical_action_has_no_effect_and_can_resume(self):
        w=world(borrowed=False);a,b,t,p=actors_items(w)
        c=WorkshopCommand('partial','partial',a,'use',(p,t),work_limit=1)
        e=w.execute(c);self.assertEqual(e.outcome,WorkStatus.PARTIAL)
        self.assertEqual(w.truth.current_fact(p,'condition',w.config.context).object,'raw')
        self.assertEqual(w.truth.current_fact(t,'condition',w.config.context).object,'clean')
        r=AutonomousWorld.restore(w.checkpoint())
        for x in (w,r):x.execute(replace(c,command_id='second'));x.execute(replace(c,command_id='third'))
        self.assertEqual(w.checkpoint(),r.checkpoint());self.assertTrue(audit(w)['passed'])

    def test_idempotent_retry_does_not_duplicate_work_or_demand(self):
        w=world();a,_,_,_=actors_items(w);advance_until(w,lambda x:bool(x._demand_records))
        command=w._journal[-1].command;before=w.checkpoint();event=w.execute(command)
        self.assertEqual(before,w.checkpoint());self.assertEqual(event,w._journal[-1].event)
        with self.assertRaises(ValueError):w.execute(replace(command,work_limit=command.work_limit+1))
        self.assertEqual(before,w.checkpoint())

    def test_changed_partial_physical_command_rejects_atomically(self):
        w=world(borrowed=False);a,_,t,p=actors_items(w);c=WorkshopCommand('one','one',a,'use',(p,t),work_limit=1);w.execute(c)
        before=w.checkpoint()
        with self.assertRaises(ValueError):w.execute(replace(c,command_id='new',operation='lend'))
        self.assertEqual(w.checkpoint(),before)

    def test_selected_jobs_do_not_scan_global_inactive_history(self):
        w=world()
        class NoTraversal(list):
            def __iter__(self):raise AssertionError('ordinary work traversed global history')
            def __getitem__(self,key):
                if isinstance(key,slice):raise AssertionError('ordinary work sliced global history')
                return super().__getitem__(key)
        w._journal=NoTraversal(w._journal)
        for i in range(500):w.execute(Tick('inactive:'+str(i)))
        run(w)
        self.assertTrue(all(d.status=='resolved' for a in w.config.actors for d in w.own_demands(a)))
        # Explicit diagnostic export is not included in this no-traversal claim.
        w._journal=[list.__getitem__(w._journal,i) for i in range(len(w._journal))]
        self.assertTrue(audit(w)['passed'])

    def test_r13_content_runs_in_same_journal_and_replays_with_generated_demands(self):
        w=world();a,b,t,p=actors_items(w);run(w)
        ref=store(w,a,'r13:training',TRAINING,context=w.config.context)
        out=process(w,a,'r13:demo','demonstrate_search',(ref,))
        self.assertEqual(w.content(a,out)['kind'],'search_demo')
        self.assertTrue(any(tx.event.action=='r14.use' for tx in w._journal))
        r=AutonomousWorld.restore(w.checkpoint());self.assertEqual(w.checkpoint(),r.checkpoint())
        self.assertTrue(audit(w)['passed'])

    def test_unknown_versions_mutable_sources_and_boolean_prices_rejected(self):
        a=Ref(Kind.ENTITY,'a',1);item=Ref(Kind.ENTITY,'item',1)
        with self.assertRaises(ValueError):AutonomyTurn('x','x',a,schema_version=2)
        with self.assertRaises(ValueError):WorkshopCommand('x','x',a,'clean',[item])
        with self.assertRaises(ValueError):AutonomyPolicy(a,reserve=True)
        with self.assertRaises(ValueError):WorkshopConfig(((item,'unknown'),))

    def test_partial_reception_is_mechanically_resumed_not_replaced_by_policy(self):
        w=world(work_limit=1);a,b,t,p=actors_items(w)
        advance_until(w,lambda x:bool(x._receiving),limit=3000)
        r=AutonomousWorld.restore(w.checkpoint())
        for x in (w,r):run(x,horizon=4000)
        self.assertEqual(w.checkpoint(),r.checkpoint());self.assertTrue(audit(w)['passed'])
        self.assertTrue(all(d.status=='resolved' for actor in w.config.actors for d in w.own_demands(actor)))

    def test_both_opportunity_contracts_keep_distinct_roundtrip_types(self):
        from hle.assessment_records import Opportunity as Legacy
        from tests_r12.test_contracts import opportunity
        older=Legacy(3,True,True,False,'legacy trial availability')
        newer=opportunity()
        self.assertEqual(codec.encode(older)['record'],'Opportunity')
        self.assertEqual(codec.encode(newer)['record'],'hle.development_contracts.Opportunity')
        self.assertEqual(codec.loads(codec.dumps((older,newer))),(older,newer))
        self.assertIs(type(codec.loads(codec.dumps(older))),Legacy)

    def test_unregistered_same_named_dataclass_cannot_impersonate_wire_type(self):
        from dataclasses import make_dataclass
        fake=make_dataclass('Opportunity',[('required',int)],frozen=True)(1)
        with self.assertRaises(ValueError):codec.dumps(fake)
