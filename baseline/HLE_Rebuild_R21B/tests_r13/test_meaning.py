from dataclasses import replace
import unittest
from hle.development_demo import *
from hle.content_records import MeaningCommand, ContentCommand
from hle.memory_records import MemoryCommand, WriteDraft, ContextDraft
from hle.meaning_learning import read_meaning, allocate
from hle.cards import card


class MeaningTests(unittest.TestCase):
    def test_two_holons_same_cue_different_histories_change_actual_actions(self):
        left=tuple(Ref(Kind.ENTITY,'left:'+str(i),1) for i in range(4))
        right=tuple(Ref(Kind.ENTITY,'right:'+str(i),1) for i in range(4))
        w=world(items=left+right,owners={r:HELPER for r in right})
        for i in range(3):
            exp,app=embodied_experience(w,left[i],'left:'+str(i),True,LEARNER)
            publish_meaning(w,exp,app,'left:'+str(i),actor=LEARNER)
            exp,app=embodied_experience(w,right[i],'right:'+str(i),False,HELPER)
            publish_meaning(w,exp,app,'right:'+str(i),actor=HELPER)
        a=recall(w,LEARNER,'left:use',(MEANING_CUE,),relation='meaning.scene')
        b=recall(w,HELPER,'right:use',(MEANING_CUE,),relation='meaning.scene')
        self.assertTrue(w.contextual_meaning(LEARNER,a).check)
        self.assertFalse(w.contextual_meaning(HELPER,b).check)
        left_action=meaning_action(w,LEARNER,a,left[-1],PARTNER,'left:action')
        right_action=meaning_action(w,HELPER,b,right[-1],PARTNER,'right:action')
        self.assertEqual(left_action.action.operation,INSPECT)
        self.assertEqual(right_action.action.operation,TRANSFER)
        r=DevelopmentalWorld.restore(w.checkpoint())
        for x in (w,r):
            self.assertEqual(x.execute(left_action).outcome,WorkStatus.COMPLETED)
            self.assertEqual(x.execute(right_action).outcome,WorkStatus.COMPLETED)
        self.assertEqual(w.checkpoint(),r.checkpoint())
        self.assertEqual(w.truth.current_fact(right[-1],'owned_by',ROOM).object,PARTNER)

    def test_reversal_revises_owned_meaning_not_just_label(self):
        w,rows=meaning_history()
        self.assertEqual([r['check'] for r in rows],[True,True,True,True,False,False])
        self.assertEqual([r['revision'] for r in rows],list(range(1,7)))
        m=w.memory_head(LEARNER,'meaning:home')
        old=replace(m.ref,revision=1)
        self.assertTrue(read_meaning(w.read_revision(LEARNER,old),LEARNER).check)
        self.assertFalse(read_meaning(m,LEARNER).check)
        self.assertEqual(rows[-1]['selected_action'],'r2.transfer')
        self.assertEqual(DevelopmentalWorld.restore(w.checkpoint()).checkpoint(),w.checkpoint())

    def test_successful_transfer_does_not_mislearn_prior_unavailability(self):
        w,rows=meaning_history((False,))
        self.assertFalse(rows[0]['check']); self.assertEqual(rows[0]['samples'],[False])
        # Ownership changed after success, but the learned sample concerns the
        # original opportunity, not the recipient's post-transfer ownership.
        item=Ref(Kind.ENTITY,'experience-item:0',1)
        self.assertEqual(w.truth.current_fact(item,'owned_by',ROOM).object,PARTNER)

    def test_missing_publication_keeps_old_meaning_despite_new_experiences(self):
        items=tuple(Ref(Kind.ENTITY,'i:'+str(i),1) for i in range(6)); w=world(items=items)
        for i in range(3):
            exp,app=embodied_experience(w,items[i],str(i),False)
            publish_meaning(w,exp,app,'meaning:'+str(i))
        for i in range(3,6): embodied_experience(w,items[i],str(i),True)
        access=recall(w,LEARNER,'unpublished',(MEANING_CUE,),relation='meaning.scene')
        value=w.contextual_meaning(LEARNER,access)
        self.assertFalse(value.check); self.assertEqual(value.encounters,3)
        self.assertEqual(w.memory_head(LEARNER,'meaning:home').ref.revision,3)

    def test_card_label_does_not_supply_personal_meaning(self):
        values=[]
        for rank in (19,20,21):
            item=Ref(Kind.ENTITY,'item',1); w=world(items=(item,)); exp,app=embodied_experience(w,item,'e',True)
            cue=card('arcana:'+str(rank)).ref
            m=publish_meaning(w,exp,app,'m',cue=cue)
            access=recall(w,LEARNER,'meaning',(cue,),relation='meaning.scene')
            values.append(w.contextual_meaning(LEARNER,access).check)
        self.assertEqual(values,[True,True,True])

    def test_cue_allocation_uses_owned_history_not_fixed_phase(self):
        cues=tuple(card('arcana:'+str(x)).ref for x in (19,20,21))
        assignments={}
        for scene in ('a','b','c'):
            assignments[scene]=allocate(cues,assignments)
        self.assertEqual(tuple(assignments.values()),cues)
        reversed_cues=tuple(reversed(cues))
        self.assertEqual(allocate(reversed_cues,{}),cues[-1])

    def test_same_cue_in_different_contexts_keeps_different_meanings(self):
        items=tuple(Ref(Kind.ENTITY,'item:'+str(i),1) for i in range(2)); w=world(items=items)
        from hle.world import memory_key
        flags=[]
        for i,unavailable in enumerate((True,False)):
            key='scene:'+str(i)
            finish(w,MemoryCommand(key,key,LEARNER,ContextDraft(key,key)))
            ctx=Ref(Kind.CONTEXT,'memory-context:'+memory_key(LEARNER,key),1)
            exp,app=embodied_experience(w,items[i],str(i),unavailable)
            publish_meaning(w,exp,app,'m:'+str(i),scene=key,context=ctx)
            access=recall(w,LEARNER,'use:'+str(i),(MEANING_CUE,),ctx,'meaning.scene')
            flags.append(w.contextual_meaning(LEARNER,access).check)
        self.assertEqual(flags,[True,False])

    def pending(self):
        item=Ref(Kind.ENTITY,'item',1); w=world(items=(item,)); exp,app=embodied_experience(w,item,'e',True)
        a=recall(w,LEARNER,'access',(MEANING_CUE,),relation='meaning.scene')
        c=MeaningCommand('learn','learn',LEARNER,MEANING_CUE,ROOM,'home',exp,app,a,'meaning:home',work_limit=1)
        return w,c,exp,app

    def test_paid_meaning_job_and_partial_write_do_not_publish_early(self):
        w,c,exp,app=self.pending(); w.execute(c)
        self.assertIsNone(w.development_job(LEARNER,'learn').result)
        self.assertIsNone(w.memory_head(LEARNER,'meaning:home'))
        r=DevelopmentalWorld.restore(w.checkpoint())
        for x in (w,r): finish(x,c)
        self.assertEqual(w.checkpoint(),r.checkpoint())
        job=w.development_job(LEARNER,'learn'); draft=job.candidate
        basis=tuple(dict.fromkeys((job.result,exp)+draft.links))
        command=MemoryCommand('write','write',LEARNER,draft,basis,1)
        w.execute(command); self.assertIsNone(w.memory_head(LEARNER,'meaning:home'))
        r=DevelopmentalWorld.restore(w.checkpoint())
        for x in (w,r):
            finish(x,command)
            m=x.memory_head(LEARNER,'meaning:home')
            bind(x,LEARNER,'meaning:home',MEANING_CUE,m.ref,chunk=1)
        self.assertEqual(w.checkpoint(),r.checkpoint())

    def test_forged_learned_boolean_cannot_be_published(self):
        w,c,exp,app=self.pending(); finish(w,c); j=w.development_job(LEARNER,'learn')
        content=tuple(replace(p,object=not p.object) if p.relation=='meaning.check' else p for p in j.candidate.content)
        d=replace(j.candidate,content=content)
        before=w.checkpoint()
        with self.assertRaises(ValueError): w.execute(MemoryCommand('bad','bad',LEARNER,d,(j.result,exp)+d.links))
        self.assertEqual(w.checkpoint(),before)

    def test_mismatched_embodiment_and_foreign_evidence_rejected(self):
        w,c,exp,app=self.pending(); before=w.checkpoint()
        with self.assertRaises(ValueError): w.execute(replace(c,application=Ref(Kind.EVIDENCE,'unknown',1)))
        with self.assertRaises(ValueError): w.execute(replace(c,actor=HELPER))
        self.assertEqual(w.checkpoint(),before)

    def test_same_receipt_cannot_be_counted_as_repeated_experience(self):
        w,c,exp,app=self.pending()
        publish_meaning(w,exp,app,'publish')
        access=recall(w,LEARNER,'again',(MEANING_CUE,),relation='meaning.scene')
        old=w.contextual_meaning(LEARNER,access)
        with self.assertRaises(ValueError): w.execute(replace(c,access=access,expected=old.ref))

    def test_superseded_and_withdrawn_meaning_not_current(self):
        w,rows=meaning_history((True,False))
        old=Ref(Kind.MEMORY,w.memory_head(LEARNER,'meaning:home').ref.key,1)
        bind(w,LEARNER,'meaning:home',MEANING_CUE,old)
        stale=recall(w,LEARNER,'stale',(MEANING_CUE,),relation='meaning.scene')
        with self.assertRaises(ValueError): w.contextual_meaning(LEARNER,stale)
        m=w.memory_head(LEARNER,'meaning:home')
        d=WriteDraft('meaning:home',m.content,m.links,ClaimStatus.RETRACTED,m.ref,'withdraw without erasure')
        finish(w,MemoryCommand('withdraw','withdraw',LEARNER,d,(m.ref,)+m.links))
        bind(w,LEARNER,'meaning:home',MEANING_CUE,w.memory_head(LEARNER,'meaning:home').ref)
        a=recall(w,LEARNER,'withdrawn',(MEANING_CUE,),relation='meaning.scene')
        with self.assertRaises(ValueError): w.contextual_meaning(LEARNER,a)

    def test_meaning_partial_revision_detects_changed_binding(self):
        w,rows=meaning_history((True,))
        extra=Ref(Kind.ENTITY,'experience-item:1',1)
        exp,app=embodied_experience(w,extra,'next',False)
        a=recall(w,LEARNER,'recall:revision',(MEANING_CUE,),relation='meaning.scene')
        old=w.contextual_meaning(LEARNER,a)
        c=MeaningCommand('partial','partial',LEARNER,MEANING_CUE,ROOM,'home',exp,app,a,'meaning:home',old.ref,1)
        w.execute(c)
        bind(w,LEARNER,'meaning:home',MEANING_CUE,old.ref)
        e=w.execute(replace(c,command_id='continue'))
        self.assertEqual(e.outcome,WorkStatus.FAILED)
        self.assertEqual(w.memory_head(LEARNER,'meaning:home').ref,old.ref)
        self.assertIsNone(w.processing_state(LEARNER).busy)
