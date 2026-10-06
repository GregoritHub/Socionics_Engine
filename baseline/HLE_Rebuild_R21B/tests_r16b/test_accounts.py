from dataclasses import replace
import unittest
from hle.reconciliation_demo import case,world
from hle.reconciliation import ReconciliationWorld
from hle.reconciliation_records import ReconciliationPolicy,AccountCommand,AccountTransaction
from hle.reconciliation_reference import compare
from hle.compensation_evaluation import evaluate
from hle.shell_assessment import assess_engagement,JointShellAssessment
from hle.codec import loads,dumps
from hle.contracts import WorkStatus,Ref,Kind
from hle.world_records import Tick,Credit


def fresh(w,config=None):
    return ReconciliationWorld(config or w.config,w.profiles,w.policy,w.agents,w.organization_policies,w.semantic_policy,
        w.workshop,w.autonomy,release=w.release,reviewers=w.reviewers,account_policy=w.account_policy)


def prefix(w,stop):
    v=fresh(w)
    for tx in w._journal[1:stop]: v.execute(tx.command)
    return v


def sign(w,name,index=-1):
    return assess_engagement(w.account_monitor.traces[index])['signs'][name]['observation']


class RuntimeAccounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main,_=case(history=1,renewals=1)
        cls.timely,_=case(history=1,renewals=1,account_policy=ReconciliationPolicy(distinction_unit=0))
        cls.scaffold,_=case(history=1,renewals=1,account_policy=ReconciliationPolicy(scaffold_unit=0))
        cls.open,_=case(history=1,renewals=1,account_policy=ReconciliationPolicy(cross_check=True))
        cls.started,_=case(history=1,renewals=1,account_policy=ReconciliationPolicy(guard_unit=999))
        cls.ordinary,_=case(history=1,renewals=1,gated_history=False)
        cls.refusal,_=case(history=1,renewals=1,account_policy=ReconciliationPolicy(willing=False))

    def test_five_independent_witnesses_share_one_runtime_trajectory(self):
        for name in ('premature_translation','forced_placement','new_defensive_structure','residual_fragmentation','foreclosure'):
            self.assertEqual(sign(self.main,name),'positive')

    def test_premature_control_changes_real_release(self):
        self.assertEqual(sign(self.timely,'premature_translation'),'negative')
        a,b=(evaluate(w)['choices'][-1]['mode'] for w in (self.main,self.timely))
        self.assertEqual((a,b),('confirm','direct'))

    def test_useful_scaffold_after_same_challenge(self):
        self.assertEqual(sign(self.scaffold,'new_defensive_structure'),'negative')
        self.assertTrue(self.scaffold.account_monitor.traces[-1].increase.greater)
        self.assertEqual(evaluate(self.scaffold)['choices'][-1]['mode'],'direct')

    def test_open_disagreement_has_no_fragmentation_claim(self):
        self.assertEqual(sign(self.open,'residual_fragmentation'),'negative')
        self.assertTrue(any(op.name=='integrate_open' for op in self.open.account_monitor.traces[-1].operations))
        self.assertFalse(self.open.account_monitor.traces[-1].increase)

    def test_guard_cost_control_starts_real_correction(self):
        self.assertEqual(sign(self.started,'foreclosure'),'negative')
        self.assertTrue(any(t.concept is not None and t.job.operation=='separate_late' for t in self.started._journal if type(t) is AccountTransaction))
        self.assertEqual(evaluate(self.started)['choices'][-1]['mode'],'direct')

    def test_ordinary_history_has_no_positive_sign(self):
        for t in self.ordinary.account_monitor.traces:
            self.assertNotIn('positive',[v['observation'] for v in assess_engagement(t)['signs'].values()])

    def test_new_structure_has_an_actual_later_origin(self):
        t=self.main.account_monitor.traces[-1]
        construct=next(op for op in t.operations if op.name=='construct')
        self.assertGreater(construct.tick,t.increase.tick)
        tx=self.main._journal[t.increase.tick]
        self.assertEqual(tx.job.operation,'receive')
        self.assertFalse(t.initial_structures)

    def test_incompatible_notices_are_delivered_and_cause_challenge(self):
        rows=[t for t in self.main._journal if type(t) is AccountTransaction and t.event.outcome==WorkStatus.COMPLETED]
        first=next(t for t in rows if t.job.operation=='notify_terms')
        second=next(t for t in rows if t.job.operation=='notify_policy')
        a,b=(loads(t.messages[0].content[0].object) for t in (first,second))
        self.assertEqual((a.loan,a.item),(b.loan,b.item));self.assertNotEqual(a.requires,b.requires)
        response=next(t for t in rows if t.job.operation=='respond')
        self.assertEqual(loads(response.messages[0].content[0].object).kind,'challenge')
        self.assertEqual(response.command.actor,first.messages[0].receiver)

    def test_all_runtime_folds_agree(self):
        for w in (self.main,self.timely,self.scaffold,self.open,self.started,self.ordinary,self.refusal):
            r=compare(w);self.assertTrue(r['passed'],r['errors'])
            self.assertFalse(evaluate(w)['oracle_errors'])

    def test_endpoint_success_retains_path_failure(self):
        t=self.main.account_monitor.traces[-1]; self.assertEqual(t.endpoint,'correct')
        g=JointShellAssessment(1);g.append(t)
        self.assertEqual(g.report()['coherence'],'failed_in_window')
        self.assertTrue(g.reference_oig_matches())

    def test_repeated_loans_establish_signs(self):
        w,_=case(history=3,renewals=3)
        g=w.account_report()['groups'][0]
        for name in ('premature_translation','forced_placement','new_defensive_structure','residual_fragmentation','foreclosure'):
            self.assertEqual(g['signs'][name]['positive'],3)
            self.assertEqual(g['signs'][name]['status'],'established_in_window')
        self.assertEqual(len({t.engagement for t in w.account_monitor.traces}),3)

    def test_refusal_is_unassessed(self):
        t=self.refusal.account_monitor.traces[-1];r=assess_engagement(t)
        self.assertEqual(r['opportunity'],'legitimate_refusal')
        self.assertEqual({v['observation'] for v in r['signs'].values()},{'unassessed'})

    def test_rest_creates_no_account_engagement(self):
        w=world(history=1,renewals=1)
        for i in range(30): w.execute(Tick('quiet:'+str(i)))
        self.assertFalse(w.account_report()['groups']);self.assertFalse(w.account_report()['open_engagements'])

    def test_inactive_ticks_do_not_create_renewals(self):
        w=prefix(self.main,len(self.main._journal))
        before=w.account_report()
        for i in range(100): w.execute(Tick('quiet:'+str(i)))
        after=w.account_report()
        for key in ('groups','open_engagements','completed_visits','closed_operation_visits'):
            self.assertEqual(before[key],after[key])

    def test_scheduling_delay_leaves_open_unassessed(self):
        i=next(i for i,t in enumerate(self.main._journal) if type(t) is AccountTransaction and t.job.operation=='summarize')
        w=prefix(self.main,i)
        for n in range(15):w.execute(Tick('pause:'+str(n)))
        r=w.account_report()['open_engagements'][0]
        self.assertEqual(r['opportunity'],'open_engagement')
        self.assertEqual({s['observation'] for s in r['signs'].values()},{'unassessed'})

    def test_own_practiced_capacity_is_required(self):
        w=world(history=1,renewals=1);worker=w.config.actors[0]
        with self.assertRaises(ValueError):w.execute(AccountCommand('no-cap','no-cap',worker,Ref(Kind.ENTITY,'tool:0',1)))
        self.assertEqual(len(w._journal),1)

    def test_record_definitions_cannot_accept_a_shell_flag(self):
        with self.assertRaises(TypeError):ReconciliationPolicy(shell=True)
        with self.assertRaises(TypeError):AccountCommand('fake','fake',self.main.config.actors[0],phase='clear')

    def test_missing_peer_response_does_not_become_completed_evidence(self):
        i=next(i for i,t in enumerate(self.main._journal) if type(t) is AccountTransaction and t.job.operation=='respond')
        w=prefix(self.main,i)
        for n in range(12):w.execute(Tick('undelivered-reply:'+str(n)))
        row=w.joint_report()['open_engagements'][0]
        self.assertEqual(row['opportunity'],'open_engagement')
        self.assertEqual({s['observation'] for s in row['signs'].values()},{'unassessed'})

    def test_next_account_operation_does_not_scan_inactive_journal(self):
        i=next(i for i,t in enumerate(self.main._journal) if type(t) is AccountTransaction and t.job.operation=='summarize')
        w=prefix(self.main,i)
        for n in range(100):w.execute(Tick('inactive:'+str(n)))
        class NoIteration(list):
            def __iter__(self):raise AssertionError('active account operation traversed journal')
        w._journal=NoIteration(w._journal)
        w.execute(self.main._journal[i].command)
        self.assertEqual(w._journal[-1].job.operation,'summarize')


class Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w,_=case(history=1,renewals=1)
        cls.first=next(i for i,t in enumerate(cls.w._journal) if type(t) is AccountTransaction)

    def test_complete_checkpoint_replay_and_monitors(self):
        text=self.w.checkpoint();w=ReconciliationWorld.restore(text)
        self.assertEqual(w.checkpoint(),text);self.assertEqual(w.account_report(),self.w.account_report())
        self.assertEqual(w.shell_report(),self.w.shell_report())

    def test_partial_payment_publishes_no_result_and_continues_exactly(self):
        w=prefix(self.w,self.first);cmd=replace(self.w._journal[self.first].command,work_limit=1)
        w.execute(cmd);tx=w._journal[-1]
        self.assertEqual(tx.event.outcome,WorkStatus.PARTIAL);self.assertIsNone(tx.state);self.assertFalse(tx.parts)
        text=w.checkpoint();v=ReconciliationWorld.restore(text)
        next_cmd=replace(cmd,command_id='continued')
        self.assertEqual(w.execute(next_cmd),v.execute(next_cmd));self.assertEqual(w.checkpoint(),v.checkpoint())

    def test_partial_operation_rejects_changed_continuation(self):
        w=prefix(self.w,self.first);cmd=replace(self.w._journal[self.first].command,work_limit=1);w.execute(cmd)
        with self.assertRaises(ValueError):w.execute(replace(cmd,command_id='bad',item=Ref(Kind.ENTITY,'tool:0',1)))

    def test_duplicate_command_does_not_charge_twice(self):
        w=prefix(self.w,self.first);cmd=self.w._journal[self.first].command
        event=w.execute(cmd);text=w.checkpoint()
        self.assertEqual(w.execute(cmd),event);self.assertEqual(w.checkpoint(),text)
        with self.assertRaises(ValueError):w.execute(replace(cmd,work_limit=1))

    def test_rehashed_forged_output_rejects(self):
        cp=loads(self.w.checkpoint());j=list(cp.base.journal);t=j[self.first]
        j[self.first]=replace(t,parts=(replace(t.parts[0],requires=not t.parts[0].requires),)+t.parts[1:])
        with self.assertRaises(ValueError):ReconciliationWorld.restore(dumps(replace(cp,base=replace(cp.base,journal=tuple(j)))))

    def test_rehashed_changed_demand_reply_rejects(self):
        cp=loads(self.w.checkpoint());j=list(cp.base.journal)
        i=next(i for i,t in enumerate(j) if type(t) is AccountTransaction and t.job.operation=='respond')
        t=j[i];msg=t.messages[0];p=loads(msg.content[0].object)
        j[i]=replace(t,messages=(replace(msg,content=(replace(msg.content[0],object=dumps(replace(p,obligations=77))),)),))
        with self.assertRaises(ValueError):ReconciliationWorld.restore(dumps(replace(cp,base=replace(cp.base,journal=tuple(j)))))

    def test_partial_changed_owned_input_fails_without_publication(self):
        from hle.autonomy_records import WorkshopCommand
        from hle.concept_demo import fund_command
        w=prefix(self.w,self.first);cmd=replace(self.w._journal[self.first].command,work_limit=1);w.execute(cmd)
        # Actor cannot issue a second work command while its existing job owns processing.
        with self.assertRaises(ValueError):fund_command(w,WorkshopCommand('conflict','conflict',cmd.actor,'inspect',(cmd.item,)))
        self.assertIsNone(w._journal[-1].state)

    def test_low_resources_defer_without_output_then_credit_resumes(self):
        original=prefix(self.w,self.first);a=original.config.actors[0]
        spent=original.config.wallets[0].energy-original._wallets[a].energy
        config=replace(original.config,wallets=tuple(replace(b,energy=spent+1,time=spent+1) if b.actor==a else b for b in original.config.wallets))
        w=fresh(original,config)
        for t in original._journal[1:]:w.execute(t.command)
        cmd=original._prepare_account(self.w._journal[self.first].command).command
        w.execute(cmd);self.assertEqual(w._wallets[a].energy,0);self.assertIsNone(w._journal[-1].state)
        w.execute(replace(cmd,command_id='unfunded'));self.assertEqual(w._journal[-1].event.outcome,WorkStatus.DEFERRED)
        cp=w.checkpoint();v=ReconciliationWorld.restore(cp)
        credit=Credit('fund',a,1000,1000,'explicit continuation funding')
        for x in (w,v):x.execute(credit);x.execute(replace(cmd,command_id='funded'))
        self.assertEqual(w.checkpoint(),v.checkpoint());self.assertIsNotNone(w._journal[-1].state)

    def test_foreign_message_reference_rejects(self):
        w=prefix(self.w,self.first);a=w.config.actors[0]
        with self.assertRaises(ValueError):w.execute(AccountCommand('forged','forged',a,source=Ref(Kind.OBSERVATION,'fabricated',1)))

    def test_reporting_cannot_change_participant_checkpoint(self):
        before=self.w.checkpoint();self.w.account_report();compare(self.w)
        self.assertEqual(self.w.checkpoint(),before)

    def test_r15_import_preserves_old_transactions_exactly(self):
        from hle.compensation_demo import case as old_case
        old,_=old_case(history=1,renewals=0)
        w=ReconciliationWorld.import_r15(old.checkpoint())
        self.assertEqual(w._journal,old._journal);self.assertFalse(w.joint_report()['groups'])

    def test_forged_actual_movement_fails_replay(self):
        from hle.crux import FormalMovement,Route,Perspective,Polarity
        cp=loads(self.w.checkpoint());j=list(cp.base.journal);tx=j[self.first]
        move=FormalMovement(Route(Perspective.ITS,Perspective.WE),Polarity.EXPENDITURE)
        j[self.first]=replace(tx,job=replace(tx.job,movements=(move,)))
        with self.assertRaises(ValueError):ReconciliationWorld.restore(dumps(replace(cp,base=replace(cp.base,journal=tuple(j)))))

    def test_forged_parent_schema_rejects(self):
        cp=loads(self.w.checkpoint())
        with self.assertRaises(ValueError):ReconciliationWorld.restore(dumps(replace(cp,base=replace(cp.base,schema='invented'))))
