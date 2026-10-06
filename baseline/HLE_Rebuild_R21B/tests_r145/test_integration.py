import unittest
from dataclasses import replace,FrozenInstanceError
from hle.conceptual import ConceptualWorld
from hle.concept_demo import world,history_case,classroom
from hle.autonomy_demo import world as old_world,run
from hle.concept_records import *
from hle.concept_structure import *
from hle.autonomy_records import WorkshopCommand
from hle.contracts import *
from hle.memory_records import *
from hle.world_records import Tick,Attempt,MessageDraft,SEND
from hle.model_a import TYPES,fields
from hle.codec import dumps,loads

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.finished=world();run(cls.finished);cls.checkpoint=cls.finished.checkpoint()

    def test_details_without_cards(self):
        w=self.finished;self.assertFalse(w._binding_heads)
        self.assertTrue(any(type(t.command) is MemoryCommand and type(t.command.payload) is DetailQuery for t in w._journal))
        self.assertTrue(all(not j.bindings and j.max_hops==0 for j in w._memory_jobs.values()))

    def test_sparse_immutable_concepts(self):
        s=self.finished.conceptual_state(self.finished.config.actors[0])
        self.assertEqual(set(s.relations),set(RELATIONS));self.assertTrue(s.practiced);self.assertEqual(s.tensions,())
        self.assertTrue(s.evidence);self.assertIsNotNone(s.previous)
        self.assertTrue(all(type(r) is Ref for r in s.evidence))
        with self.assertRaises(FrozenInstanceError):s.practiced=False
        with self.assertRaises(TypeError):REFERENCE['id']='different'

    def test_resolved_tension_keeps_history(self):
        w=self.finished;s=w.conceptual_state(w.config.actors[0]);chain=[]
        while s is not None:chain.append(s);s=w._records.get(s.previous)
        self.assertTrue(any(x.tensions==('care_vs_release',) for x in chain));self.assertEqual(chain[0].tensions,())
        self.assertGreater(len(chain),2);self.assertTrue(all(r in w._records for s in chain for r in s.evidence))

    def test_same_facts_different_histories_change_action(self):
        pairs=[history_case(t) for t in (False,True)];signatures=[]
        for w,result in pairs:
            actor=w.config.actors[0];item=Ref(Kind.ENTITY,'held-out-tool',1)
            tx=next(t for t in w._journal[result['cut']:] if type(t.command) is WorkshopCommand and t.command.actor==actor and t.command.inputs==(item,) and t.command.operation=='clean')
            signatures.append(tuple((p.relation,p.object) for p in tx.observations[0].content))
            self.assertFalse(result['second']['horizon_exhausted']);self.assertTrue(result['practiced'])
        self.assertEqual(signatures[0],signatures[1])
        self.assertEqual(pairs[0][1]['held_out_tool_actions'][-3:],['clean','inspect','return'])
        self.assertEqual(pairs[1][1]['held_out_tool_actions'][-2:],['clean','return'])

    def test_instruction_supply_practice_are_distinct(self):
        results={mode:classroom(mode)[1] for mode in ('none','static','live','revoked')}
        for row in results.values():self.assertFalse(row['before_practiced']);self.assertTrue(row['after_practiced'])
        self.assertEqual(set(results['static']['before_relations']),set(RELATIONS));self.assertEqual(results['live']['before_relations'],())
        self.assertIn('inspect',results['static']['actions']);self.assertNotIn('inspect',results['live']['actions'])
        self.assertEqual(results['none']['actions'],results['revoked']['actions'])

    def test_withdrawal_is_delivered(self):
        w,_=classroom('revoked');t=w._commands['class:revoke']
        self.assertEqual(len(t.observations),1);self.assertEqual(t.observations[0].observer,w.config.actors[2]);self.assertFalse(w._live_supply)

    def test_unpracticed_supplier_rejected(self):
        w=world();a,b=w.config.actors
        for op in ('teach','supply'):
            with self.assertRaises(ValueError):w.execute(ConceptCommand(op,op,a,op,recipient=b,item=next(iter(w._items))))
        self.assertEqual(len(w._journal),1)

    def test_evidence_is_owned_and_instruction_authenticated(self):
        w=world();a,b=w.config.actors
        with self.assertRaises(ValueError):w.execute(ConceptCommand('bad','bad',a,'integrate',(w._inboxes[b][0].ref,)))
        prop=Proposition(a,'concept.entrusted_use.v1',ENTRUSTED,w.config.context,TimeScope(w.now,None))
        with self.assertRaises(ValueError):w.execute(Attempt('fake','fake',ActionRequest(a,SEND,(b,),()),MessageDraft((prop,))))
        with self.assertRaises(ValueError):w.execute(MemoryCommand('fake-m','fake-m',a,WriteDraft('f',(prop,),(),ClaimStatus.ENDORSED,None,'fake'),(w._inboxes[a][0].ref,)))

    def test_detail_access_is_own_paid_and_not_executable(self):
        w=ConceptualWorld.restore(self.checkpoint);a,b=w.config.actors
        key=w.autonomy_state(a).catalog[0].key;before=w._wallets[a].energy
        event=w.execute(MemoryCommand('detail','detail',a,DetailQuery((key,),w.config.context,w.now)))
        r=w.recall_result(a,w.memory_job(a,'detail').result)
        self.assertEqual(event.outcome,WorkStatus.COMPLETED);self.assertTrue(r.hits);self.assertLess(w._wallets[a].energy,before)
        with self.assertRaises(ValueError):w.recall_result(b,r.ref)
        with self.assertRaises(ValueError):w._content_recall(a,r.ref)

    def test_detail_query_cannot_fetch_meaning(self):
        w=ConceptualWorld.restore(self.checkpoint);a=w.config.actors[0];key=w.autonomy_state(a).catalog[0].key;m=w.memory_head(a,key)
        # Adversarial fixture only, not evidence of acquisition.
        w._memory_heads[a][m.ref.key]=replace(m,content=(replace(m.content[0],relation='meaning.scene'),))
        with self.assertRaises(ValueError):w.execute(MemoryCommand('reject','reject',a,DetailQuery((key,),w.config.context,w.now)))

    def test_checkpoint_and_idempotence(self):
        w=ConceptualWorld.restore(self.checkpoint);self.assertEqual(w.checkpoint(),self.checkpoint)
        tx=next(t for t in w._journal if type(t.command) is ConceptCommand);before=w.checkpoint()
        self.assertEqual(w.execute(tx.command),tx.event);self.assertEqual(before,w.checkpoint())
        with self.assertRaises(ValueError):w.execute(replace(tx.command,operator='revoke'))

    def test_rehashed_forgery_rejected(self):
        cp=loads(self.checkpoint);journal=list(cp.journal)
        index=next(i for i,t in enumerate(journal) if type(t) is ConceptTransaction and t.concept is not None)
        journal[index]=replace(journal[index],concept=replace(journal[index].concept,practiced=True))
        with self.assertRaises(ValueError):ConceptualWorld.restore(dumps(replace(cp,journal=tuple(journal))))
        with self.assertRaises(ValueError):ConceptualWorld.restore(dumps(replace(cp,reference_seal='wrong')))

    def test_partial_concept_resumes_exactly(self):
        w=world(work_limit=1)
        for _ in range(4000):
            for a in w.config.actors:
                if w.autonomy_ready(a):w.autonomy_step(a)
                if a in w._concept_active:break
            if w._concept_active:break
        self.assertTrue(w._concept_active);a=next(iter(w._concept_active));self.assertIsNone(w.conceptual_state(a))
        other=ConceptualWorld.restore(w.checkpoint());run(w,6000);run(other,6000)
        self.assertEqual(w.checkpoint(),other.checkpoint());self.assertTrue(w.conceptual_state(a).practiced)

    def test_zero_resources_publish_nothing(self):
        w=world(energy=0);a=w.config.actors[0]
        self.assertFalse(w.autonomy_ready(a));self.assertIsNone(w.conceptual_state(a));self.assertEqual(len(w._journal),1)

    def test_clock_does_not_wake_concepts(self):
        w=ConceptualWorld.restore(self.checkpoint);a=w.config.actors[0];old=w.conceptual_state(a)
        w.execute(Tick('quiet'))
        self.assertIs(w.conceptual_state(a),old);self.assertFalse(w._concept_queue.get(a))

    def test_legitimate_controls_are_not_tension_or_shell(self):
        for kw in ({'may_lend':False},{'borrowed':False},{'tool':False},{'intentions':()}):
            w=world(**kw);run(w);self.assertIsNone(w.conceptual_state(w.config.actors[0]))

    def test_all_types_and_fixed_dimensionality(self):
        for tim in TYPES:
            w=world(tim=tim);result=run(w,2000);s=w.conceptual_state(w.config.actors[0])
            self.assertFalse(result['horizon_exhausted'],tim);self.assertTrue(s.practiced,tim)
            self.assertEqual(fields(4)['dimensionality'],1);self.assertEqual(w._profiles[w.config.actors[0]].tim,tim)

    def test_fold_bridge_retains_coordinates(self):
        for tim in TYPES:
            for family,ends in EDGES.items():
                for attitude in ('i','e'):
                    for origin in ends:
                        x=bridge(tim,family+attitude,origin)
                        self.assertEqual(x.position,position(x.seat));self.assertEqual(len(x.type_coordinates),4)
                        self.assertNotIn({x.route.origin,x.route.destination},({P.I,P.IT},{P.WE,P.ITS}))
            path=conceptual_path(tim);self.assertEqual(path[0].route.then(path[1].route).destination,P.IT)
        with self.assertRaises(ValueError):bridge('iee','fi',P.IT)

    def test_name_and_time_invariance(self):
        states=[]
        for seed in (17,91):
            w=world(seed=seed)
            for i in range(seed):w.execute(Tick('time:'+str(i)))
            run(w,2000)
            s=w.conceptual_state(w.config.actors[0]);states.append((s.relations,s.tensions,s.practiced))
        self.assertEqual(states[0],states[1])

    def test_relevant_constraint_change_matters(self):
        w=world(wear=False);run(w);s=w.conceptual_state(w.config.actors[0])
        self.assertNotIn(RELATIONS[1],s.relations);self.assertFalse(s.practiced)

    def test_r14_migration_preserves_past(self):
        old=old_world();run(old);w=ConceptualWorld.import_r14(old.checkpoint())
        self.assertEqual(w._journal,old._journal);self.assertEqual(w.checkpoint(),ConceptualWorld.restore(w.checkpoint()).checkpoint())
        run(w,2000);self.assertTrue(w.conceptual_state(w.config.actors[0]).practiced)
        self.assertEqual(w._journal[:len(old._journal)],old._journal)

    def test_concept_path_paid_and_recorded(self):
        tx=next(t for t in self.finished._journal if type(t) is ConceptTransaction)
        self.assertEqual(tuple(m.route for m in tx.job.movements),tuple(e.route for e in conceptual_path(tx.job.plan.routing_type)))
        self.assertGreater(tx.job.plan.required,0);self.assertGreater(sum(x.completed_units for x in tx.works),0)

    def test_hidden_world_state_cannot_change_same_local_decision(self):
        w=world();a=w.config.actors[0];v=w.local_view(a)
        before=w._select_participant(v,'choice')
        item=next(iter(w._items));key=(item,'owned_by',w.config.context)
        w._facts[key]=replace(w._facts[key],object=a)
        self.assertEqual(before,w._select_participant(v,'choice'))

    def test_unpaid_detail_result_is_not_visible(self):
        w=ConceptualWorld.restore(self.checkpoint);a=w.config.actors[0]
        keys=tuple(c.key for c in w.autonomy_state(a).catalog)
        c=MemoryCommand('partial-detail','partial-detail',a,DetailQuery(keys,w.config.context,w.now),work_limit=1)
        w.execute(c);self.assertIsNone(w.memory_job(a,c.task_id).result)
        other=ConceptualWorld.restore(w.checkpoint())
        for target in (w,other):
            i=0
            while target.memory_job(a,c.task_id).result is None:
                i+=1;target.execute(replace(c,command_id='pd:'+str(i)))
        self.assertEqual(w.checkpoint(),other.checkpoint())

    def test_address_stays_fixed_as_material_grows(self):
        w=self.finished;s=w.conceptual_state(w.config.actors[0]);addresses=[]
        while s is not None:addresses.append(s.address);s=w._records.get(s.previous)
        self.assertEqual(len(set(addresses)),1)
        self.assertEqual(addresses[0].folded_position,5)
        self.assertEqual(addresses[0].apex,w.config.context)
        self.assertEqual(RANKS['arcana:5'][0],'Hierophant')
        self.assertNotIn('arcana:5',SOURCE_MEANINGS)  # not fabricated as a supplied complete definition

    def test_after_supply_removal_held_out_action_is_independent(self):
        w,result=classroom('live',retained_trial=True)
        self.assertEqual(result['retained_trial_actions'],['use','clean','return'])
        self.assertFalse(w._live_supply)
        self.assertTrue(w.conceptual_state(w.config.actors[2]).practiced)

    def test_resource_exhaustion_during_concept_can_resume(self):
        from hle.world_records import Wallet,Credit
        base=self.finished;a=base.config.actors[0]
        first=next(t for t in base._journal if type(t.command) is ConceptCommand)
        budget=20000-first.works[0].before[0].amount+1
        config=replace(base.config,wallets=tuple(Wallet(x.actor,budget,budget) if x.actor==a else x for x in base.config.wallets))
        w=ConceptualWorld(config,base.profiles,base.policy,base.agents,workshop=base.workshop,autonomy=base.autonomy)
        for tx in base._journal[1:first.event.when.tick+1]:w.execute(tx.command)
        self.assertEqual(w._wallets[a].energy,0);self.assertIn(a,w._concept_active);self.assertIsNone(w.conceptual_state(a))
        w=ConceptualWorld.restore(w.checkpoint())
        w.execute(Credit('refill',a,20000,20000,'resume funded concept'))
        run(w,2000);self.assertTrue(w.conceptual_state(a).practiced)

    def test_static_content_plus_return_without_care_is_not_full_practice(self):
        from hle.concept_demo import fund_command
        complete,result=classroom('static');learner=complete.config.actors[2]
        cp=loads(complete.checkpoint())
        index=next(i for i,t in enumerate(cp.journal) if type(t.command) is WorkshopCommand and t.command.actor==learner and t.command.operation=='use')
        w=ConceptualWorld.restore(dumps(replace(cp,journal=cp.journal[:index])))
        item=Ref(Kind.ENTITY,'held-out-tool',1)
        event=fund_command(w,WorkshopCommand('early-return','early-return',learner,'return',(item,)))
        self.assertEqual(event.outcome,WorkStatus.COMPLETED)
        obs=next(o for o in w._journal[-1].observations if o.observer==learner)
        fund_command(w,ConceptCommand('early-integrate','early-integrate',learner,'integrate',(obs.ref,)))
        self.assertFalse(w.conceptual_state(learner).practiced)
