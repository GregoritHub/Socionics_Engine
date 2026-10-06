from dataclasses import replace
import unittest
from hle.development_evaluation import *
from hle.content_records import ContentCommand, DevelopmentTransaction
from hle import codec
from hle.world_records import Credit
from hle.semantic_records import CancelSemantic


class ContinuationTests(unittest.TestCase):
    def test_every_prefix_of_partial_work_and_meaning_revision(self):
        w=continuation_trace(); r=all_prefix_continuation(w)
        self.assertGreaterEqual(r['prefixes'],80)
        for name in ('MeaningCommand:partial','ContentCommand:partial','MemoryCommand:partial','ReceiveCommand:partial'):
            self.assertIn(name,r['cutpoint_kinds'])
        self.assertTrue(accounting(w)['passed'])

    def test_work_audit_including_explicit_resource_credits(self):
        w=world(energy=3); m=store(w,LEARNER,'train',TRAINING)
        c=ContentCommand('p','p',LEARNER,'demonstrate_search',(m,),work_limit=64)
        w.execute(c); self.assertIsNone(w.development_job(LEARNER,'p').result)
        w.execute(Credit('fund',LEARNER,100,99,'explicit independent energy/time credit'))
        finish(w,replace(c,command_id='resume'))
        a=accounting(w); self.assertTrue(a['passed']); self.assertEqual(a['wallets'][LEARNER.key][0]-a['wallets'][LEARNER.key][1],1)

    def test_energy_time_independent_resource_boundaries(self):
        for e,t in ((0,0),(1,0),(0,1),(1,2),(2,1),(20,20)):
            w=world(energy=2); m=store(w,LEARNER,'seed',TRAINING)
            if e or t: w.execute(Credit('fund',LEARNER,e,t,'resource grid'))
            w.execute(ContentCommand('p','p',LEARNER,'demonstrate_search',(m,)))
            job=w.development_job(LEARNER,'p')
            self.assertEqual(job.paid,min(e,t,job.plan.required))
            self.assertEqual(job.result is not None,job.paid==job.plan.required)
            self.assertTrue(accounting(w)['passed'])
            self.assertEqual(DevelopmentalWorld.restore(w.checkpoint()).checkpoint(),w.checkpoint())

    def pending_checkpoint(self):
        w=world(); m=store(w,LEARNER,'seed',TRAINING)
        w.execute(ContentCommand('p','p',LEARNER,'demonstrate_search',(m,),work_limit=1))
        return w,codec.loads(w.checkpoint())

    def test_rehashed_private_candidate_tampering_rejected_by_replay(self):
        w,cp=self.pending_checkpoint(); tx=cp.journal[-1]
        changed=replace(tx,job=replace(tx.job,candidate=pack(TRAINING)))
        with self.assertRaisesRegex(ValueError,'replay'): DevelopmentalWorld.restore(codec.dumps(replace(cp,journal=cp.journal[:-1]+(changed,))))

    def test_rehashed_payment_and_processing_state_tampering_rejected(self):
        w,cp=self.pending_checkpoint(); tx=cp.journal[-1]
        for changed in (replace(tx,job=replace(tx.job,paid=0)),replace(tx,state=replace(tx.state,active='fi'))):
            if changed==tx: continue
            with self.assertRaises(ValueError): DevelopmentalWorld.restore(codec.dumps(replace(cp,journal=cp.journal[:-1]+(changed,))))

    def test_rehashed_dependency_and_receipt_tampering_rejected(self):
        w,cp=self.pending_checkpoint(); tx=cp.journal[-1]
        changed=replace(tx,job=replace(tx.job,dependencies=tx.job.sources))
        with self.assertRaises(ValueError): DevelopmentalWorld.restore(codec.dumps(replace(cp,journal=cp.journal[:-1]+(changed,))))
        finish(w,w.development_job(LEARNER,'p').command); cp=codec.loads(w.checkpoint()); tx=cp.journal[-1]
        o=tx.observations[0]; p=replace(o.content[0],object=pack(TRAINING)); changed=replace(tx,observations=(replace(o,content=(p,)),))
        with self.assertRaises(ValueError): DevelopmentalWorld.restore(codec.dumps(replace(cp,journal=cp.journal[:-1]+(changed,))))

    def test_duplicate_command_and_unknown_checkpoint_version_rejected(self):
        w,cp=self.pending_checkpoint()
        with self.assertRaises(ValueError): DevelopmentalWorld.restore(codec.dumps(replace(cp,schema='r999')))
        with self.assertRaises(ValueError): DevelopmentalWorld.restore(codec.dumps(replace(cp,journal=cp.journal+(cp.journal[-1],))))

    def test_language_and_organization_share_actual_runtime_and_checkpoint(self):
        from hle.organization_demo import run_organization_demo
        old,summary,_=run_organization_demo(); w=restart(old)
        for tx in old._journal[1:]:
            w.execute(tx.command); self.assertEqual(w._journal[-1],tx)
        actor=w.config.actors[0]
        # This actor may have a nonpersonal perspective at the lifecycle endpoint;
        # choose a free personal actor, preserving the actual state rather than resetting it.
        actors=[a for a in w.config.actors if w.processing_state(a).busy is None and w.processing_state(a).perspective.value=='I']
        self.assertTrue(actors); actor=actors[0]
        body=TRAINING; context=w.config.context
        p=Proposition(actor,WIRE,pack(body),context,TimeScope(w.now,None))
        finish(w,MemoryCommand('r13:new','r13:new',actor,WriteDraft('r13:new',(p,),(),ClaimStatus.ENDORSED,None,'bounded input'),(w.select_input(actor)[0].observations[0].ref,)))
        m=w.memory_head(actor,'r13:new').ref
        process(w,actor,'r13:role','demonstrate_search',(m,))
        r=DevelopmentalWorld.restore(w.checkpoint()); self.assertEqual(r.checkpoint(),w.checkpoint())
        self.assertTrue(accounting(w)['passed'])
        self.assertEqual(summary['founder_state'],'withdrawn')

    def test_pending_language_reservation_blocks_content_without_changing_state(self):
        from hle.language_demo import acquire
        from hle.language_records import LanguageCommand,Learn
        item=Ref(Kind.ENTITY,'box',1); w=world(items=(item,))
        m=store(w,LEARNER,'seed',TRAINING); access=acquire(w,LEARNER,(item,),'actual:access')
        c=LanguageCommand('learn','learn',LEARNER,Learn('held',access),1); w.execute(c)
        self.assertEqual(w.language_job(LEARNER,'learn').outcome,WorkStatus.PARTIAL)
        before=w.checkpoint()
        with self.assertRaises(ValueError): w.execute(ContentCommand('p','p',LEARNER,'hold',(m,)))
        self.assertEqual(w.checkpoint(),before)
        r=DevelopmentalWorld.restore(before)
        for x in (w,r): x.execute(CancelSemantic('cancel','learn',LEARNER,'language','switch to content')); process(x,LEARNER,'p','hold',(m,))
        self.assertEqual(w.checkpoint(),r.checkpoint())

    def test_recursive_declared_dependencies_invalidate_without_deleting_history(self):
        _,tasks=task_panel(); w=world(tasks); memories,receipts=train(w)
        base=store(w,LEARNER,'base',TRAINING)
        child=store(w,LEARNER,'child',w.content(LEARNER,receipts['search']),(receipts['search'],),(base,))
        parent=store(w,LEARNER,'parent',w.content(LEARNER,receipts['search']),(receipts['search'],),(child,))
        bind(w,LEARNER,'capacity:search',SEARCH_CUE,parent)
        access=recall(w,LEARNER,'read',(SEARCH_CUE,))
        store(w,LEARNER,'base',TRAINING)
        with self.assertRaises(ValueError): w.retained_capacity(LEARNER,access,'search_rule')
        self.assertEqual(w.read_revision(LEARNER,parent).links,(child,))

    def test_personal_actions_exactly_continue_from_fresh_controller(self):
        w,summary=distinct_personal_histories()
        self.assertTrue(summary['actions_completed'] and summary['exact_continuation'])
        self.assertEqual([r['action'] for r in summary['actors']],['r2.inspect','r2.transfer'])
        self.assertTrue(accounting(w)['passed'])

    def test_existing_material_treatment_and_reownership_checkpoint(self):
        from hle.assessment_demo import world as old_world,false_account_fixture
        from hle.assessment_records import MaterialCommand
        from hle.demo import BOB
        old=old_world(); w=DevelopmentalWorld(old.config,old.profiles,old.policy,tuple(AgentPolicy(a) for a in old.config.actors))
        _,account,_=false_account_fixture(w)
        w.execute(MaterialCommand('generate',BOB,'intent','generate',account.ref))
        material=w._material_heads['3:bob:1:intent']
        w.execute(MaterialCommand('externalize',BOB,'intent','externalize',material.ref))
        material=w._material_heads['3:bob:1:intent']
        r=DevelopmentalWorld.restore(w.checkpoint())
        for x in (w,r):
            x.execute(MaterialCommand('express',BOB,'intent','express',material.ref))
            x.execute(MaterialCommand('reown',BOB,'intent','reown',material.ref))
            owned=x._material_heads['3:bob:1:intent']
            x.execute(MaterialCommand('renew',BOB,'intent','express',owned.ref))
            self.assertEqual(x._journal[-1].extra[0].outcome,'withheld_after_reownership')
        self.assertEqual(w.checkpoint(),r.checkpoint()); self.assertTrue(accounting(w)['passed'])

    def test_old_r4_guard_cannot_execute_after_capacity_withdrawal(self):
        item=Ref(Kind.ENTITY,'guard-item',1); w=world(items=(item,))
        exp,app=embodied_experience(w,item,'learn-guard',True)
        m=w.read_revision(LEARNER,exp); self.assertTrue(m.capabilities)
        bind(w,LEARNER,'guard-access',SEARCH_CUE,m.ref)
        access=recall(w,LEARNER,'guard-recall',(SEARCH_CUE,),relation='owned_by')
        theory=MetabolicCommand('theory','theory',LEARNER,TheorizeDraft(access,item,PARTNER))
        finish(w,theory); account=w.processing_record(LEARNER,w.processing_job(LEARNER,'theory').result)
        self.assertIsNotNone(account.guard)
        draft=WriteDraft('experience:learn-guard',m.content,m.links,ClaimStatus.RETRACTED,m.ref,'withdraw capability')
        finish(w,MemoryCommand('withdraw','withdraw',LEARNER,draft,(m.ref,)+m.links))
        cp=w.checkpoint()
        with self.assertRaises(ValueError): w.execute(MetabolicCommand('apply','apply',LEARNER,ApplyDraft(account.ref)))
        self.assertEqual(cp,w.checkpoint())
