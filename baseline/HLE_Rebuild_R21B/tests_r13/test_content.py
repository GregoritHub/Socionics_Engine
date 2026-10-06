from dataclasses import replace
import json
import unittest
from hle import codec
from hle.development_demo import *
from hle.developmental import unpack
from hle.content_records import ContentCommand, CancelDevelopment, WIRE
from hle.memory_records import MemoryCommand, WriteDraft, ContextDraft, BindDraft, RecallQuery
from hle.world_records import Credit, Tick, INSPECT
from hle.contracts import ClaimStatus, MemoryRevision


class ContentTests(unittest.TestCase):
    def setup_capacity(self):
        _,ts=task_panel(); w=world(ts); retained,receipts=train(w)
        task=store(w,PARTNER,'task',ts[0]); obs=send(w,PARTNER,task,LEARNER,'task:send')
        access=recall(w,LEARNER,'access',(SEARCH_CUE,))
        return w,retained,receipts,obs,access

    def atomic(self,w,fn):
        before=w.checkpoint()
        with self.assertRaises(ValueError): fn()
        self.assertEqual(w.checkpoint(),before)

    def test_retained_crossing(self):
        w,data=crossing()
        self.assertEqual(data['successes'],12); self.assertEqual(data['helper_units_after_training'],0)
        self.assertTrue(all(not t['accepted_return'] for t in data['before']))
        self.assertTrue(all(t['options']==task['offered'] for t,task in zip(data['after'],task_panel()[1])))

    def test_unretained_and_partial_retention_controls(self):
        expected={'no_instruction':3,'help_only':3,'search_only':3,'boundary_only':3,'both_without_return':0}
        for condition,n in expected.items():
            with self.subTest(condition=condition):
                _,r=crossing(condition); self.assertEqual(r['successes'],n)

    def test_raw_receipt_cannot_execute_capacity(self):
        w,mem,rec,obs,acc=self.setup_capacity()
        self.atomic(w,lambda: w.execute(ContentCommand('x','x',LEARNER,'search',(obs,rec['search']))))

    def test_explicit_memory_address_cannot_bypass_paid_recall(self):
        w,mem,rec,obs,acc=self.setup_capacity()
        self.atomic(w,lambda:w.execute(ContentCommand('x','x',LEARNER,'search',(obs,mem['search']))))

    def test_unpaid_and_foreign_recall_rejected(self):
        w,mem,rec,obs,acc=self.setup_capacity()
        fake=Ref(Kind.EVIDENCE,'unpaid',1)
        self.atomic(w,lambda:w.execute(ContentCommand('x','x',LEARNER,'search',(obs,),fake)))
        foreign=recall(w,HELPER,'foreign',(SEARCH_CUE,))
        self.atomic(w,lambda:w.execute(ContentCommand('x','x',LEARNER,'search',(obs,),foreign)))

    def test_superseded_capacity_rejected_with_old_binding(self):
        w,mem,rec,obs,acc=self.setup_capacity()
        newer=store(w,LEARNER,'capacity:search',w.content(LEARNER,rec['search']),(rec['search'],))
        self.assertEqual(newer.revision,2)
        self.atomic(w,lambda:w.execute(ContentCommand('x','x',LEARNER,'search',(obs,),acc)))
        self.assertEqual(w.read_revision(LEARNER,mem['search']).ref,mem['search'])

    def test_retracted_and_disputed_capacity_rejected(self):
        for attitude in (ClaimStatus.RETRACTED,ClaimStatus.DISPUTED):
            w,mem,rec,obs,acc=self.setup_capacity()
            old=w.read_revision(LEARNER,mem['search'])
            d=WriteDraft('capacity:search',old.content,old.links,attitude,old.ref,'withdrawal preserves historical content')
            finish(w,MemoryCommand('withdraw','withdraw',LEARNER,d,(old.ref,)))
            fresh=w.memory_head(LEARNER,'capacity:search')
            bind(w,LEARNER,'capacity:search',SEARCH_CUE,fresh.ref)
            a=recall(w,LEARNER,'withdrawn',(SEARCH_CUE,))
            self.atomic(w,lambda:w.execute(ContentCommand('x','x',LEARNER,'search',(obs,),a)))

    def test_stale_binding_and_pending_invalidation(self):
        w,mem,rec,obs,acc=self.setup_capacity()
        cmd=ContentCommand('start','pending',LEARNER,'search',(obs,),acc,1)
        w.execute(cmd); job=w.development_job(LEARNER,'pending'); self.assertIsNone(job.result)
        bind(w,LEARNER,'capacity:search',SEARCH_CUE,mem['search'])
        e=w.execute(replace(cmd,command_id='resume'))
        self.assertEqual(e.outcome,WorkStatus.FAILED)
        self.assertIsNone(w.development_job(LEARNER,'pending').result)
        self.assertEqual(w.development_job(LEARNER,'pending').paid,job.paid)
        self.assertIsNone(w.processing_state(LEARNER).busy)

    def test_changed_context_retrieves_same_rule_through_new_paid_binding(self):
        w,mem,rec,obs,acc=self.setup_capacity()
        finish(w,MemoryCommand('scene','scene',LEARNER,ContextDraft('new_scene','new participant context')))
        ctx=w.memory_job(LEARNER,'scene').result
        # Context writes publish their result through the same MemoryJob.
        if ctx is None: ctx=Ref(Kind.CONTEXT,'memory-context:'+__import__('hle.world',fromlist=['memory_key']).memory_key(LEARNER,'new_scene'),1)
        bind(w,LEARNER,'new_scene:search',SEARCH_CUE,mem['search'],ctx)
        fresh=recall(w,LEARNER,'new_scene:recall',(SEARCH_CUE,),ctx)
        r=process(w,LEARNER,'new_scene:search','search',(obs,),fresh)
        self.assertEqual(w.content(LEARNER,r)['items'],task_panel()[1][0]['offered'])
        self.assertEqual(w.recall_result(LEARNER,fresh).hits[0].memory,mem['search'])
        c=w.retained_capacity(LEARNER,fresh,'search_rule')
        self.assertEqual(c.context,ctx); self.assertTrue(c.acquisition_work)

    def test_facts_do_not_gain_cross_context_applicability(self):
        w=world(items=(Ref(Kind.ENTITY,'box',1),))
        o=w.select_input(LEARNER)[0].observations[0]
        p=next(p for p in o.content if p.relation=='owned_by')
        finish(w,MemoryCommand('fact','fact',LEARNER,WriteDraft('fact',(p,),(),ClaimStatus.ENDORSED,None,'observed'),(o.ref,)))
        finish(w,MemoryCommand('ctx','ctx',LEARNER,ContextDraft('ctx','other')))
        from hle.world import memory_key
        ctx=Ref(Kind.CONTEXT,'memory-context:'+memory_key(LEARNER,'ctx'),1)
        bind(w,LEARNER,'wrong_context',SEARCH_CUE,w.memory_head(LEARNER,'fact').ref,ctx)
        a=recall(w,LEARNER,'facts',(SEARCH_CUE,),ctx,'owned_by')
        self.assertFalse(w.recall_result(LEARNER,a).hits)

    def test_declared_capacity_dependency_invalidates(self):
        w,mem,rec,obs,acc=self.setup_capacity()
        base=store(w,LEARNER,'dependency',TRAINING)
        cap=store(w,LEARNER,'dependent',w.content(LEARNER,rec['search']),(rec['search'],),(base,))
        bind(w,LEARNER,'capacity:search',SEARCH_CUE,cap)
        access=recall(w,LEARNER,'dependent:recall',(SEARCH_CUE,))
        store(w,LEARNER,'dependency',TRAINING)
        self.atomic(w,lambda:w.execute(ContentCommand('use','use',LEARNER,'search',(obs,),access)))

    def test_fabricated_inference_and_hold_laundering_rejected(self):
        w=world(); body={'kind':'search_rule','program':'all'}
        self.atomic(w,lambda:store(w,LEARNER,'fake',body))
        _,receipts=train(w,())
        copied=process(w,LEARNER,'copy','hold',(receipts['search'],))
        self.atomic(w,lambda:store(w,LEARNER,'fake',body,(copied,)))

    def test_partial_job_does_not_publish_and_retry_does_not_recharge(self):
        w=world(); t=store(w,LEARNER,'training',TRAINING)
        c=ContentCommand('start','job',LEARNER,'demonstrate_search',(t,),work_limit=1)
        e=w.execute(c); before=w.checkpoint(); self.assertEqual(e.outcome,WorkStatus.PARTIAL)
        self.assertIsNone(w.development_job(LEARNER,'job').result)
        self.assertFalse(w._journal[-1].observations)
        self.assertEqual(w.execute(c),e); self.assertEqual(w.checkpoint(),before)
        finish(w,c); j=w.development_job(LEARNER,'job')
        self.assertEqual(j.paid,j.plan.required)
        debits=w._development_debits[(LEARNER,'job')]
        self.assertEqual(sum(w._records[r].completed_units for r in debits),j.plan.required)

    def test_changed_continuation_rejected_atomically(self):
        w=world(); t=store(w,LEARNER,'training',TRAINING)
        c=ContentCommand('start','job',LEARNER,'demonstrate_search',(t,),work_limit=1); w.execute(c)
        self.atomic(w,lambda:w.execute(replace(c,command_id='other',operator='demonstrate_boundary')))
        self.atomic(w,lambda:w.execute(replace(c,operator='hold')))

    def test_content_blocks_language_organization_and_actions(self):
        from hle.language_records import LanguageCommand,Learn
        from hle.organization_records import OrganizationCommand,Formulate
        w=world(items=(Ref(Kind.ENTITY,'box',1),)); t=store(w,LEARNER,'training',TRAINING)
        c=ContentCommand('start','job',LEARNER,'demonstrate_search',(t,),work_limit=1); w.execute(c)
        self.atomic(w,lambda:w.execute(Attempt('inspect','inspect',ActionRequest(LEARNER,INSPECT,(Ref(Kind.ENTITY,'box',1),),()))))
        # Shared SemanticRouting rejects the reserved R13 cursor before preparing payload.
        access=Ref(Kind.EVIDENCE,'not-yet-access',1)
        self.atomic(w,lambda:w.execute(LanguageCommand('learn','learn',LEARNER,Learn('x',access))))
        self.atomic(w,lambda:w.execute(OrganizationCommand('form','form',LEARNER,Formulate(access))))

    def test_cancel_preserves_debits_and_releases_processing(self):
        w=world(); t=store(w,LEARNER,'training',TRAINING)
        c=ContentCommand('start','job',LEARNER,'demonstrate_search',(t,),work_limit=1); w.execute(c)
        paid=w.development_job(LEARNER,'job').paid
        e=w.execute(CancelDevelopment('cancel','job',LEARNER,'changed intention'))
        self.assertEqual(e.outcome,WorkStatus.FAILED); self.assertEqual(w.development_job(LEARNER,'job').paid,paid)
        self.assertIsNone(w.processing_state(LEARNER).busy)
        self.assertIsNotNone(process(w,LEARNER,'other','hold',(t,)))

    def test_resource_deferral_and_replenished_resume(self):
        w=world(energy=3); t=store(w,LEARNER,'training',TRAINING)
        c=ContentCommand('start','job',LEARNER,'demonstrate_search',(t,),work_limit=64); w.execute(c)
        j=w.development_job(LEARNER,'job'); self.assertEqual(j.paid,1); self.assertIsNone(j.result)
        cp=w.checkpoint(); r=DevelopmentalWorld.restore(cp)
        for x in (w,r):
            x.execute(Credit('fund',LEARNER,100,100,'declared resumption resource'))
            x.execute(replace(c,command_id='resume'))
        self.assertEqual(w.checkpoint(),r.checkpoint()); self.assertEqual(w.development_job(LEARNER,'job').outcome,WorkStatus.COMPLETED)

    def test_schema_mutable_bool_and_unknown_version_rejected(self):
        for kw in ({'sources':[]},{'work_limit':True},{'schema_version':2}):
            with self.assertRaises(ValueError): ContentCommand('x','x',LEARNER,'hold',(),**kw) if 'sources' not in kw else ContentCommand('x','x',LEARNER,'hold',kw['sources'])

    def test_wire_rejects_tampering_and_unknown_prose(self):
        body={'kind':'search_rule','program':'all'}; env=json.loads(pack(body)); env['body']['program']='first'
        with self.assertRaises(ValueError): unpack(json.dumps(env))
        with self.assertRaises(ValueError): pack({'kind':'free_prose','text':'anything'})
        with self.assertRaises(ValueError): pack(dict(body,altitude=4))
        with self.assertRaises(ValueError): unpack('{"body":{},"body":{}}')

    def test_foreign_content_rejected(self):
        w=world(); m=store(w,HELPER,'training',TRAINING)
        self.atomic(w,lambda:w.execute(ContentCommand('x','x',LEARNER,'hold',(m,))))

    def test_message_requires_paid_reception(self):
        w=world(); m=store(w,HELPER,'training',TRAINING); o=send(w,HELPER,m,LEARNER,'send',receive=False)
        self.atomic(w,lambda:w.execute(ContentCommand('x','x',LEARNER,'hold',(o,))))
        finish(w,ReceiveCommand('read','read',LEARNER,o))
        self.assertIsNotNone(process(w,LEARNER,'x','hold',(o,)))

    def test_participant_status_cannot_read_unfunded_candidate(self):
        w=world(energy=2); source=store(w,LEARNER,'seed',TRAINING)
        w.execute(ContentCommand('p','p',LEARNER,'demonstrate_search',(source,)))
        j=w.development_job(LEARNER,'p')
        self.assertEqual(j.paid,0); self.assertEqual(j.candidate,'unpublished'); self.assertIsNone(j.result)
        self.assertFalse(w._journal[-1].observations)
        w.execute(Credit('fund',LEARNER,100,100,'pay for result'))
        finish(w,replace(j.command,command_id='resume'))
        done=w.development_job(LEARNER,'p')
        self.assertNotEqual(done.candidate,'unpublished'); self.assertEqual(done.paid,done.plan.required)
