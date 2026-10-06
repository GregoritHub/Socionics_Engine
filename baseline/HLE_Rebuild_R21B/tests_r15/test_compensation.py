import unittest
from dataclasses import replace

from hle.compensation import CompensationWorld, RELEASE_SEAL
from hle.compensation_demo import world, case, introduce, fund_command
from hle.compensation_records import *
from hle.compensation_policy import select_release
from hle.compensation_evaluation import evaluate
from hle.concept_demo import world as conceptual_world
from hle.autonomy_demo import run
from hle.autonomy_records import WorkshopCommand
from hle.contracts import *
from hle.world_records import Tick, Credit, Wallet, Attempt, MessageDraft, SEND, Witness
from hle.codec import dumps, loads
from hle.model_a import TYPES
from hle.development_contracts import Treatment


def fresh_like(w, **kw):
    return CompensationWorld(kw.pop('config', w.config), w.profiles, w.policy, w.agents,
             w.organization_policies, w.semantic_policy, w.workshop, w.autonomy,
             release=w.release, reviewers=w.reviewers, **kw)


def before(w, index):
    new = fresh_like(w)
    for tx in w._journal[1:index]: new.execute(tx.command)
    return new


def release_rows(w, optional=None):
    rows = [tx for tx in w._journal if type(tx) is ReleaseTransaction]
    if optional is None: return rows
    return [tx for tx in rows if tx.job.view is not None and tx.job.view.required != optional]


class GeneratedCompensation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {}
        for name, kwargs in [('maintained', {}), ('ordinary', {'gated_history': False}),
                             ('ablation', {'revision_unit': 0}), ('reowned', {'refusal': True})]:
            w, s = case(**kwargs)
            cls.cases[name] = (w, s, evaluate(w, s))
        cls.small, cls.small_setup = case(history=1, renewals=1)

    def test_initial_state_has_no_injected_relation_material_or_verdict(self):
        w = world(history=1, renewals=1)
        a = w.config.actors[0]
        self.assertIsNone(w.conceptual_state(a)); self.assertEqual(w.material_state(a), (None, None))
        self.assertFalse(w._release_supports)
        self.assertNotIn('shell', repr(w.release).lower())

    def test_generalization_follows_own_actual_confirmed_return(self):
        w = self.small; a = w.config.actors[0]
        first = next(t for t in w._journal if getattr(t, 'concept', None) is not None and DEPENDENCY in t.concept.relations)
        prior = w._records[first.concept.previous]
        self.assertNotIn(DEPENDENCY, prior.relations)
        evidence = [w._records[r] for r in first.concept.evidence]
        returned = [o for o in evidence if type(o) is Observation and w._journal[o.source_time.tick].event.action == 'r14.return']
        self.assertTrue(returned)
        self.assertTrue(any(p.relation == CONFIRMED and p.object is True for p in returned[0].content))

    def test_three_eligible_renewals_keep_distortion_and_pay(self):
        w, s, r = self.cases['maintained']
        self.assertFalse(r['oracle_errors']); self.assertEqual(r['maintained_optional_engagements'], 3)
        self.assertEqual(r['correct_optional_endpoints'], 3); self.assertTrue(r['final_dependency'])
        self.assertTrue(all(x > 0 for x in r['optional_release_work_by_item'].values()))
        self.assertFalse(any(x['horizon_exhausted'] or x['resource_censored'] for x in s['scheduling']))
        self.assertTrue(all(c['balance_after_consider'][0] > 10000 for c in r['choices']))

    def test_matched_current_facts_different_histories_avoid_compensation(self):
        _, _, maintained = self.cases['maintained']; w, _, ordinary = self.cases['ordinary']
        signature = lambda c: (c['item'], c['required'], c['eligible'], c['clean'], c['own_due'], c['return_recipient'])
        self.assertEqual([signature(c) for c in maintained['choices'] if not c['required']],
                         [signature(c) for c in ordinary['choices'] if c['item'] in ('tool:3','tool:4','tool:5')])
        self.assertEqual(ordinary['maintained_optional_engagements'], 0)
        self.assertFalse(ordinary['final_dependency']); self.assertFalse(ordinary['material_history'])
        self.assertTrue(all(c['mode'] == 'direct' for c in ordinary['choices']))

    def test_optional_counterevidence_is_explicitly_received_and_processed(self):
        w, _, r = self.cases['maintained']
        self.assertEqual(sum(x['approved'] and x['explicit_optional_evidence'] for x in r['responses']), 3)
        treatments = [t.treatment for t in release_rows(w) if t.command.operator == 'assimilate' and t.treatment]
        self.assertEqual(len(treatments), 3)
        self.assertTrue(all(t.consequences and t.selection_evidence for t in treatments))

    def test_maintenance_reinforces_costly_revision_history(self):
        choices = [c for c in self.cases['maintained'][2]['choices'] if not c['required']]
        self.assertEqual([c['support_count'] for c in choices], [3,4,5])
        self.assertEqual([dict(c['alternatives'])['reconcile'] for c in choices], [19,25,31])

    def test_revision_cost_ablation_removes_self_maintenance(self):
        _, _, r = self.cases['ablation']
        c = [x for x in r['choices'] if not x['required']]
        self.assertEqual([x['mode'] for x in c], ['reconcile','direct','direct'])
        self.assertFalse(r['final_dependency']); self.assertEqual(r['correct_optional_endpoints'], 3)
        self.assertEqual(r['material_history'][-1]['treatment'], 'reown')

    def test_refusal_displacement_and_reownership_preserve_origin(self):
        w, _, r = self.cases['reowned']; a = w.config.actors[0]
        first = [x for x in r['choices'] if x['item'] == 'tool:3']
        self.assertEqual([(x['mode'], x['carrier']) for x in first], [('confirm','reviewer'),('confirm','lender'),('reconcile',None)])
        history = r['material_history']; self.assertEqual(history[-1]['treatment'], 'reown')
        self.assertEqual(len({tuple(t['origin_events']) for t in history}), 1)
        self.assertEqual(len({t['lineage'] for t in history}), 1)
        root, treatment = w.material_state(a)
        self.assertEqual(treatment.lineage, root.ref); self.assertIn(root.ref, w._known[a])
        self.assertEqual(w._records[root.concept_at_origin].address, w.conceptual_state(a).address)
        self.assertIn(DEPENDENCY, w._records[root.concept_at_origin].relations)
        self.assertNotIn(DEPENDENCY, w.conceptual_state(a).relations)
        self.assertFalse(r['oracle_errors'])

    def test_carrier_is_not_return_recipient(self):
        for row in self.cases['maintained'][2]['choices']:
            self.assertEqual(row['carrier'], 'reviewer'); self.assertEqual(row['return_recipient'], 'lender')

    def test_local_quote_change_changes_selected_carrier(self):
        w, s = case(history=1, renewals=1, quotes=(1,4))
        r = evaluate(w,s)
        self.assertTrue(all(c['carrier']=='lender' for c in r['choices']))
        self.assertEqual(r['maintained_optional_engagements'],1)

    def test_actor_renaming_preserves_relation_based_choice(self):
        w, s = case(history=1, renewals=1, names=('zeta','alpha','omega'))
        r=evaluate(w,s)
        self.assertEqual([c['carrier'] for c in r['choices']], ['omega','omega'])
        self.assertFalse(r['oracle_errors'])

    def test_required_confirmation_is_not_generated_material(self):
        w, _, r = self.cases['maintained']
        cutoff = next(t.event.when.tick for t in release_rows(w) if t.material is not None)
        required_decisions = [t for t in release_rows(w) if t.decision and t.decision.view.required]
        self.assertEqual(len(required_decisions), 3)
        self.assertTrue(all(t.material is None and t.treatment is None for t in release_rows(w) if t.event.when.tick < cutoff))

    def test_actual_required_gate_rejects_direct_bypass(self):
        tx=next(t for t in release_rows(self.small) if t.command.operator=='consider')
        w=before(self.small,tx.event.when.tick);a=w.config.actors[0]
        e=fund_command(w,WorkshopCommand('bypass','bypass',a,'return',(tx.command.item,)))
        self.assertEqual(e.outcome,WorkStatus.FAILED)
        self.assertTrue(w.truth.current_fact(tx.command.item,'loan_active',w.config.context).object)
        self.assertIsNone(w.material_state(a)[0])

    def test_legitimate_refusal_can_leave_actual_requirement_waiting(self):
        w=world(history=1,renewals=0)
        for actor in w.config.actors[1:]:
            fund_command(w,ReleaseCommand('deny:'+actor.key,'deny:'+actor.key,actor,'boundary',willingness=False))
        run(w,10000);introduce(w,0);s=run(w,10000)
        self.assertFalse(s['horizon_exhausted']);self.assertIsNone(w.material_state(w.config.actors[0])[0])
        choices=[t.decision for t in release_rows(w) if t.decision]
        self.assertEqual(choices[-1].selection.mode,'wait')
        self.assertTrue(w.truth.current_fact(Ref(Kind.ENTITY,'tool:0',1),'loan_active',w.config.context).object)

    def test_all_types_generate_bounded_pattern_without_type_label_branch(self):
        for tim in TYPES:
            with self.subTest(tim=tim):
                w,s=case(history=1,renewals=1,tim=tim);r=evaluate(w,s)
                self.assertEqual(r['maintained_optional_engagements'],1)
                self.assertEqual(r['correct_optional_endpoints'],1);self.assertFalse(r['oracle_errors'])
                self.assertEqual(w._profiles[w.config.actors[0]].tim,tim)

    def test_zero_resources_do_not_publish_material(self):
        w=world(history=1,renewals=1,energy=0);s=run(w,50)
        self.assertEqual(len(w._journal),1);self.assertFalse(w._treatments)
        self.assertTrue(s['resource_censored'])

    def test_quiet_time_does_not_repeat_maintenance(self):
        w=before(self.small,len(self.small._journal));a=w.config.actors[0]
        state=w.material_state(a);wallet=w._wallets[a]
        for i in range(1000):w.execute(Tick('quiet:'+str(i)))
        self.assertEqual(w.material_state(a),state);self.assertEqual(w._wallets[a],wallet)
        self.assertFalse(any(w.autonomy_ready(a) for a in w.config.actors))

    def test_partial_work_at_every_release_phase_has_no_early_outputs(self):
        for op in ('consider','enact','review','assimilate'):
            with self.subTest(operator=op):
                target=next(t for t in release_rows(self.small) if t.command.operator==op and t.event.when.tick>self.small_setup['cuts'][1])
                w=before(self.small,target.event.when.tick)
                c=replace(target.command,command_id='partial:'+op,work_limit=1)
                e=w.execute(c);t=w._journal[-1]
                self.assertEqual(e.outcome,WorkStatus.PARTIAL)
                self.assertIsNone(t.material);self.assertIsNone(t.treatment);self.assertIsNone(t.concept);self.assertIsNone(t.decision)
                self.assertFalse(t.messages)
                other=CompensationWorld.restore(w.checkpoint())
                for x in (w,other):fund_command(x,replace(c,command_id='finish:'+op,work_limit=10000))
                self.assertEqual(w.checkpoint(),other.checkpoint())

    def test_budget_exhaustion_resume_preserves_charges(self):
        target=next(t for t in release_rows(self.small) if t.decision and not t.decision.view.required)
        a=self.small.config.actors[0];spent=200000-target.works[0].before[0].amount
        config=replace(self.small.config,wallets=tuple(Wallet(x.actor,spent+2,spent+2) if x.actor==a else x for x in self.small.config.wallets))
        w=fresh_like(self.small,config=config)
        for t in self.small._journal[1:target.event.when.tick]:w.execute(t.command)
        w.execute(target.command)
        self.assertEqual(w._wallets[a].energy,0);self.assertIsNone(w.material_state(a)[0])
        self.assertIn(a,w._release_active)
        r=CompensationWorld.restore(w.checkpoint());r.execute(Credit('credit',a,20000,20000,'resume unfinished paid work'))
        run(r,10000);self.assertIsNotNone(r.material_state(a)[0]);self.assertFalse(evaluate(r)['oracle_errors'])

    def test_exclusive_processing_blocks_overlap(self):
        target=next(t for t in release_rows(self.small) if t.decision and not t.decision.view.required)
        w=before(self.small,target.event.when.tick);a=target.command.actor
        w.execute(replace(target.command,command_id='partial',work_limit=1))
        with self.assertRaises(ValueError):w.execute(WorkshopCommand('overlap','overlap',a,'inspect',(target.command.item,)))
        with self.assertRaises(ValueError):w.execute(ReleaseCommand('overlap2','overlap2',a,'boundary',willingness=False))

    def test_idempotence_and_conflicting_ids(self):
        w=before(self.small,len(self.small._journal));t=next(t for t in release_rows(w) if t.treatment)
        n=len(w._journal);wallet=w._wallets[t.command.actor]
        self.assertEqual(w.execute(t.command),t.event);self.assertEqual(len(w._journal),n);self.assertEqual(w._wallets[t.command.actor],wallet)
        with self.assertRaises(ValueError):w.execute(replace(t.command,work_limit=t.command.work_limit+1))

    def test_same_decision_cannot_be_enacted_twice(self):
        target=next(t for t in release_rows(self.small) if t.command.operator=='enact')
        w=before(self.small,target.event.when.tick+1);n=len(w._journal)
        with self.assertRaises(ValueError):w.execute(replace(target.command,command_id='again',task_id='again'))
        self.assertEqual(len(w._journal),n)

    def test_pending_request_cannot_be_overwritten_by_another_decision(self):
        target=next(t for t in release_rows(self.small) if t.command.operator=='enact')
        w=before(self.small,target.event.when.tick+1)
        with self.assertRaises(ValueError):
            w.execute(ReleaseCommand('overwrite','overwrite',target.command.actor,'consider',Ref(Kind.ENTITY,'tool:0',1)))

    def test_owned_new_notice_invalidates_partial_work_without_publication(self):
        b=world(history=1,renewals=1);a,_,peer=b.config.actors;item=Ref(Kind.ENTITY,'tool:1',1)
        config=replace(b.config,witnesses=(Witness(a,item,'full'),))
        w=fresh_like(b,config=config);run(w,10000);introduce(w,0);run(w,10000);introduce(w,1)
        for _ in range(10000):
            if w._gate(a) is not None:break
            for who in w.config.actors:
                if w.autonomy_ready(who):w.autonomy_step(who)
        else:self.fail('no release opportunity')
        c=ReleaseCommand('notice-partial','notice-partial',a,'consider',item,work_limit=1)
        w.execute(c)
        fund_command(w,WorkshopCommand('notice-inspection','notice-inspection',peer,'inspect',(item,)))
        e=w.execute(replace(c,command_id='notice-resume',work_limit=1000))
        self.assertEqual(e.outcome,WorkStatus.FAILED);self.assertIsNone(w.material_state(a)[0])
        self.assertGreater(w._journal[-1].job.paid,0)
        run(w,10000);self.assertIsNotNone(w.material_state(a)[0])
        self.assertEqual(w.checkpoint(),CompensationWorld.restore(w.checkpoint()).checkpoint())

    def test_foreign_decision_and_response_rejected(self):
        w=before(self.small,len(self.small._journal));a,b,c=w.config.actors
        d=next(t.decision for t in release_rows(w) if t.decision)
        with self.assertRaises(ValueError):w.execute(ReleaseCommand('steal','steal',b,'enact',source=d.ref))
        obs=next(t.command.source for t in release_rows(w) if t.command.operator=='assimilate')
        with self.assertRaises(ValueError):w.execute(ReleaseCommand('foreign','foreign',c,'assimilate',source=obs))

    def test_forged_wire_text_cannot_supply_confirmation(self):
        w=world(history=1,renewals=1);a,b,_=w.config.actors
        p=Proposition(a,WIRE,'fake',w.config.context,TimeScope(w.now,None))
        with self.assertRaises(ValueError):w.execute(Attempt('fake','fake',ActionRequest(a,SEND,(b,),()),MessageDraft((p,))))
        self.assertEqual(len(w._journal),1)

    def test_hidden_truth_change_leaves_owned_view_and_selection_unchanged(self):
        target=next(t for t in release_rows(self.small) if t.decision and not t.decision.view.required)
        w=before(self.small,target.event.when.tick);a=target.command.actor;v=w.release_view(a,target.command.item)
        key=(v.item,REQUIRED,w.config.context);w._facts[key]=replace(w._facts[key],object=True)
        self.assertEqual(v,w.release_view(a,v.item));self.assertEqual(select_release(v,6),select_release(w.release_view(a,v.item),6))

    def test_affected_selection_does_not_walk_journal(self):
        class NoIteration(list):
            def __iter__(self):raise AssertionError('ordinary release work walked the journal')
        target=next(t for t in release_rows(self.small) if t.decision and not t.decision.view.required)
        w=before(self.small,target.event.when.tick);w._journal=NoIteration(w._journal)
        w.execute(target.command)
        self.assertIsNotNone(w._journal[-1].decision)

    def test_reference_seal_and_rehashed_material_forgery_reject(self):
        cp=loads(self.small.checkpoint())
        with self.assertRaises(ValueError):CompensationWorld.restore(dumps(replace(cp,reference_seal='changed')))
        rows=list(cp.journal);i=next(i for i,t in enumerate(rows) if type(t) is ReleaseTransaction and t.material)
        rows[i]=replace(rows[i],material=replace(rows[i].material,owner=self.small.config.actors[1]))
        with self.assertRaises(ValueError):CompensationWorld.restore(dumps(replace(cp,journal=tuple(rows))))

    def test_rehashed_treatment_and_selection_forgery_reject(self):
        cp=loads(self.small.checkpoint());rows=list(cp.journal)
        i=next(i for i,t in enumerate(rows) if type(t) is ReleaseTransaction and t.treatment and t.treatment.treatment==Treatment.EXTERNALIZE)
        rows[i]=replace(rows[i],treatment=replace(rows[i].treatment,origin_actor=self.small.config.actors[1]))
        with self.assertRaises(ValueError):CompensationWorld.restore(dumps(replace(cp,journal=tuple(rows))))
        rows=list(cp.journal);i=next(i for i,t in enumerate(rows) if type(t) is ReleaseTransaction and t.decision)
        rows[i]=replace(rows[i],decision=replace(rows[i].decision,selection=replace(rows[i].decision.selection,carrier=self.small.config.actors[1])))
        with self.assertRaises(ValueError):CompensationWorld.restore(dumps(replace(cp,journal=tuple(rows))))

    def test_checkpoint_at_every_new_phase_replays_exactly(self):
        cp=loads(self.small.checkpoint())
        prefixes={1,len(cp.journal)}|{i+1 for i,t in enumerate(cp.journal) if type(t) is ReleaseTransaction}
        for n in sorted(prefixes):
            text=dumps(replace(cp,journal=cp.journal[:n]));w=CompensationWorld.restore(text)
            self.assertEqual(w.checkpoint(),text)
            if n<len(cp.journal):
                w.execute(cp.journal[n].command);self.assertEqual(w._journal[-1],cp.journal[n])

    def test_prior_checkpoint_import_preserves_historical_work(self):
        old=conceptual_world();run(old)
        w=CompensationWorld.import_r145(old.checkpoint());self.assertEqual(w._journal,old._journal)
        self.assertFalse(w._release_supports);self.assertFalse(w._tensions)
        run(w,5000)
        self.assertEqual(w._journal[:len(old._journal)],old._journal)
        self.assertEqual(w.checkpoint(),CompensationWorld.restore(w.checkpoint()).checkpoint())

    def test_endpoint_alone_never_counts_as_maintained_distortion(self):
        r=self.cases['ordinary'][2]
        self.assertEqual(r['correct_optional_endpoints'],6);self.assertEqual(r['maintained_optional_engagements'],0)
        self.assertIn('unassessed',r['shell_assessment']);self.assertIn('unassessed',r['clearance_assessment'])

    def test_independent_accounting_matches_runtime_wallets(self):
        for w,setup,r in self.cases.values():
            self.assertFalse(r['oracle_errors'])
            self.assertEqual(r['final_balances'],{a.key:(v.energy,v.time) for a,v in w._wallets.items()})

    def test_equal_current_resources_preserve_history_effect(self):
        modes=[];wallets=[]
        for name in ('maintained','ordinary'):
            full=self.cases[name][0]
            tx=next(t for t in release_rows(full) if t.decision and t.decision.view.item.key=='tool:3')
            w=before(full,tx.event.when.tick)
            for actor in w.config.actors:
                wallet=w._wallets[actor]
                w.execute(Credit('match:'+actor.key,actor,250000-wallet.energy,250000-wallet.time,'matched current resources'))
            wallets.append(tuple(w._wallets.values()))
            w.execute(replace(tx.command,command_id='matched',task_id='matched'))
            modes.append(w._journal[-1].decision.selection.mode)
        self.assertEqual(wallets[0],wallets[1]);self.assertEqual(modes,['confirm','direct'])


if __name__=='__main__':unittest.main()
