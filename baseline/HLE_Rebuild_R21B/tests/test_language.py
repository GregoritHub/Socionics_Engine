from dataclasses import replace
import json
import unittest
from unittest.mock import patch
from hle.language_demo import world, acquire, finish, deliver, enact, run_language_demo
from hle.language import LanguageWorld, fingerprint
from hle.language_records import *
from hle.composition_demo import complete
from hle.composition_records import FoldDraft, Part, UnfoldDraft
from hle.contracts import ClaimStatus, Proposition, TimeScope, ActionRequest
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from hle.world_records import Attempt, Credit, RETAIN, TRANSFER, MemoryDraft, Wallet, MessageDraft, SEND
from hle.socion_records import ConfigureAgent, AgentPolicy, ReceiveCommand
from .support import rules


def pair(token='kept',items=(BOX,),cfg=None):
    w=world(cfg=cfg)
    a=acquire(w,ALICE,items,'a')
    b=acquire(w,BOB,(TOOL,) if items==(BOX,) else items,'b')
    lex=finish(w,ALICE,Learn(token,a),'learn').result
    obs=deliver(w,ALICE,lex,BOB,'teach')
    finish(w,BOB,Learn(token,b,obs),'adopt')
    return w,a,b,lex


def utter(w,b,mode='request',calls=None,actions=None,key='speech'):
    speech=Speech(mode,calls or (w.word(ALICE,'kept',(TOOL,BOB)),),
        actions or (Act('inspect',TOOL),Act('transfer',TOOL,ALICE)))
    u=finish(w,ALICE,Produce(speech),key+':produce').result
    obs=deliver(w,ALICE,u,BOB,key+':deliver')
    r=finish(w,BOB,Interpret(obs,b),key+':interpret').result
    return u,obs,r


class LanguageTests(unittest.TestCase):
    @rules('L01')
    def test_abstraction_preserves_repeated_entities(self):
        w=world(); access=acquire(w,ALICE,(BOX,TOOL),'both')
        r=finish(w,ALICE,Learn('two',access),'learn').result
        m=w.language_record(ALICE,r).meaning
        self.assertEqual(m.patterns,(Pattern(0,1),Pattern(2,3)))
        self.assertEqual(m.arity,4)

    @rules('L01')
    def test_composed_concept_uses_nested_structure(self):
        w=world(); a=acquire(w,ALICE,(BOX,TOOL),'both')
        root=w._records[a].query.root
        nested=complete(w,FoldDraft('nested',(Part('child',root,ROOM),)),'nested',ALICE).result
        access=complete(w,UnfoldDraft(nested,ROOM,w.now),'unfold',ALICE).result
        lex=finish(w,ALICE,Learn('combined',access),'learn').result
        self.assertEqual(len(w.language_record(ALICE,lex).meaning.patterns),2)

    @rules('L01')
    def test_foreign_access_rejected_without_charge(self):
        w=world(); a=acquire(w,ALICE,(BOX,),'a'); cp=w.checkpoint()
        with self.assertRaises(ValueError): finish(w,BOB,Learn('stolen',a),'bad')
        self.assertEqual(w.checkpoint(),cp)

    @rules('L01')
    def test_foreign_utterance_cannot_be_sent(self):
        w,a,b,l=pair()
        with self.assertRaises(ValueError): w.send_language(BOB,l,ALICE,'bad')

    @rules('L02')
    def test_unknown_then_repair_has_behavioral_consequence(self):
        w,s=run_language_demo()
        self.assertEqual((s['before_repair'],s['after_repair'],s['action_outcome']),('repair','accepted','fulfilled'))
        self.assertEqual(w._facts[(TOOL,'owned_by',ROOM)].object,ALICE)

    @rules('L02')
    def test_reception_is_required_before_acquisition(self):
        w=world(); a=acquire(w,ALICE,(BOX,),'a'); b=acquire(w,BOB,(TOOL,),'b')
        l=finish(w,ALICE,Learn('kept',a),'learn').result
        w.execute(w.send_language(ALICE,l,BOB,'send'))
        obs=w._journal[-1].observations[0].ref
        with self.assertRaises(ValueError): finish(w,BOB,Learn('kept',b,obs),'bad')

    @rules('L02')
    def test_mismatch_requires_explicit_repair_and_preserves_old_revision(self):
        w,a,b,l=pair(); old=w.lexeme(BOB,'kept')
        both=acquire(w,ALICE,(BOX,TOOL),'both')
        new=finish(w,ALICE,Learn('kept',both,expected=l),'revise').result
        msg=deliver(w,ALICE,new,BOB,'new:teach')
        failed=finish(w,BOB,Learn('kept',b,msg,old.ref),'mismatch').result
        self.assertEqual(w.language_record(BOB,failed).status,'repair')
        self.assertEqual(w.lexeme(BOB,'kept'),old)
        bb=acquire(w,BOB,(BOX,TOOL),'bob:both')
        fixed=finish(w,BOB,Learn('kept',bb,msg,old.ref),'fix').result
        self.assertEqual(fixed.revision,2)
        self.assertEqual(w.language_record(BOB,old.ref),old)
        u,obs,r=utter(w,bb,calls=(w.word(ALICE,'kept',(BOX,ALICE,TOOL,BOB)),))
        self.assertEqual(w.language_record(BOB,r).status,'accepted')

    @rules('L02')
    def test_old_message_does_not_silently_rebind(self):
        w,a,b,l=pair(); u,obs,r=utter(w,b)
        both=acquire(w,BOB,(BOX,TOOL),'both')
        finish(w,BOB,Learn('kept',both,expected=w.lexeme(BOB,'kept').ref),'revise')
        r2=finish(w,BOB,Interpret(obs,b),'retry').result
        self.assertEqual(w.language_record(BOB,r2).status,'repair')

    @rules('L03')
    def test_request_and_explanation_enact_held_out_item(self):
        for mode in ('request','explain'):
            with self.subTest(mode=mode):
                w,a,b,l=pair(); _,_,r=utter(w,b,mode)
                before=w._wallets[BOB]
                self.assertEqual(enact(w,BOB,r),'fulfilled')
                self.assertEqual(before.energy-w._wallets[BOB].energy,3)
                self.assertEqual([e.action for e in w._language_actions[r]],['r2.inspect','r2.transfer'])

    @rules('L03')
    def test_label_permutation_preserves_behavior(self):
        for token in ('kept','zqx','owned something'):
            w,a,b,l=pair(token)
            _,_,r=utter(w,b,calls=(w.word(ALICE,token,(TOOL,BOB)),))
            self.assertEqual(enact(w,BOB,r),'fulfilled')

    @rules('L03')
    def test_new_conjunction_and_action_order(self):
        w,a,b,l=pair(items=(BOX,TOOL))
        # Train combined concept, then compose duplicate instantiated calls and a
        # new order of actions. The grammar is supplied, the plan is not memorized.
        calls=(w.word(ALICE,'kept',(BOX,ALICE,TOOL,BOB)),)*2
        _,_,r=utter(w,b,calls=calls,actions=(Act('inspect',BOX),Act('inspect',TOOL),Act('transfer',TOOL,ALICE)))
        self.assertEqual(enact(w,BOB,r),'fulfilled')
        self.assertEqual(len(w._language_actions[r]),3)

    @rules('L03')
    def test_held_out_world_context(self):
        cfg=replace(config(5000,5000),context=Ref(Kind.CONTEXT,'garden',1))
        w,a,b,l=pair(cfg=cfg); _,_,r=utter(w,b)
        self.assertEqual(enact(w,BOB,r),'fulfilled')

    @rules('L04')
    def test_commitment_receipt_and_actual_fulfillment_separate(self):
        w,a,b,l=pair()
        # Speaker promises an action involving its own held-out retained object.
        aa=acquire(w,ALICE,(TOOL,),'alice:tool')
        speech=Speech('commit',(w.word(ALICE,'kept',(BOX,ALICE)),),(Act('transfer',BOX,BOB),))
        u=finish(w,ALICE,Produce(speech),'promise').result
        obs=deliver(w,ALICE,u,BOB,'promise:send')
        bb=acquire(w,BOB,(BOX,),'bob:box')
        r=finish(w,BOB,Interpret(obs,bb),'expect').result
        self.assertEqual(w.expectations(BOB),(r,))
        self.assertEqual(w.language_outcome(BOB,r),'expected')
        self.assertIsNone(w.next_language_action(BOB,r))
        i=finish(w,ALICE,Intend(u,a),'intend').result
        self.assertEqual(w.language_outcome(ALICE,i),'pending')
        self.assertEqual(enact(w,ALICE,i),'fulfilled')
        self.assertEqual(w.language_outcome(BOB,r),'expected') # private fulfillment not leaked
        self.assertEqual(w._facts[(BOX,'owned_by',ROOM)].object,BOB)

    @rules('L04')
    def test_unsent_commitment_cannot_enact(self):
        w,a,b,l=pair()
        u=finish(w,ALICE,Produce(Speech('commit',(w.word(ALICE,'kept',(BOX,ALICE)),),(Act('inspect',BOX),))),'u').result
        with self.assertRaises(ValueError): finish(w,ALICE,Intend(u,a),'intend')

    @rules('L04')
    def test_failed_action_is_not_fulfillment(self):
        w,a,b,l=pair(); _,_,r=utter(w,b)
        w.execute(Attempt('intervene','intervene',request(BOB,TRANSFER,(TOOL,ALICE))))
        self.assertEqual(enact(w,BOB,r),'failed')
        self.assertEqual(w._language_actions[r][-1].outcome,WorkStatus.FAILED)

    @rules('L05')
    def test_false_guard_refuses(self):
        w,a,b,l=pair(); _,_,r=utter(w,b,calls=(w.word(ALICE,'kept',(TOOL,ALICE)),))
        self.assertEqual(w.language_outcome(BOB,r),'refused')
        self.assertIsNone(w.next_language_action(BOB,r))

    @rules('L05')
    def test_missing_evidence_does_not_mean_false(self):
        w,a,b,l=pair(); _,_,r=utter(w,b,calls=(w.word(ALICE,'kept',(BOX,ALICE)),))
        self.assertEqual(w.language_outcome(BOB,r),'unknown')

    @rules('L05')
    def test_conflicting_evidence_blocks(self):
        w,a,b,l=pair()
        old=w._records[w._records[b].hits[0].memory]
        conflict=replace(old.content[0],object=ALICE)
        w.execute(Attempt('conflict','conflict',request(BOB,RETAIN),memory=MemoryDraft('conflict',(old.content[0],conflict),ClaimStatus.TENTATIVE,'counterexample')))
        mem=w.memory_head(BOB,'conflict')
        root=complete(w,FoldDraft('conflict',(Part('claim',mem.ref,ROOM),)),'cf',BOB).result
        bb=complete(w,UnfoldDraft(root,ROOM,w.now),'ca',BOB).result
        _,_,r=utter(w,bb)
        self.assertEqual(w.language_outcome(BOB,r),'ambiguous')

    @rules('L05')
    def test_stale_access_requires_revision(self):
        w,a,b,l=pair()
        old=w._records[w._records[b].hits[0].memory]
        w.execute(Attempt('revise','revise',request(BOB,RETAIN),memory=MemoryDraft('b:item:0',old.content,ClaimStatus.ENDORSED,'explicit revision')))
        _,_,r=utter(w,b)
        self.assertEqual(w.language_outcome(BOB,r),'stale')

    @rules('L05')
    def test_silent_policy_can_refuse(self):
        w,a,b,l=pair(); w.execute(ConfigureAgent('policy',AgentPolicy(BOB,response='silent'),'control'))
        _,_,r=utter(w,b)
        self.assertEqual(w.language_outcome(BOB,r),'refused')

    @rules('L05')
    def test_hidden_world_change_does_not_change_interpretation(self):
        base,a,b,l=pair(); _,obs,r=utter(base,b)
        changed=LanguageWorld.restore(base.checkpoint())
        changed.execute(Attempt('hidden','hidden',request(BOB,TRANSFER,(TOOL,ALICE))))
        for w in (base,changed):
            with patch.object(type(w.truth),'check',side_effect=AssertionError('Truth accessed')):
                r2=finish(w,BOB,Interpret(obs,b),'again').result
                self.assertEqual(w.language_outcome(BOB,r2),'pending')
        self.assertEqual(enact(base,BOB,r),'fulfilled')
        self.assertEqual(enact(changed,BOB,r),'failed')

    @rules('L05')
    def test_invalid_arity_is_retained_receiver_failure(self):
        w,a,b,l=pair()
        # Public send may contain malformed language: decoder must refuse it.
        call=replace(w.word(ALICE,'kept',(TOOL,BOB)),arguments=(TOOL,))
        speech=Speech('request',(call,),(Act('inspect',TOOL),))
        from hle.language import wire
        p=Proposition(ALICE,'r8_wire',wire(speech),ROOM,TimeScope(w.now,None))
        w.execute(Attempt('raw','raw',request(ALICE,SEND,(BOB,)),MessageDraft((p,))))
        obs=next(o.ref for o in w._journal[-1].observations if o.observer==BOB and o.source.kind==Kind.MESSAGE)
        w.execute(ReceiveCommand('recv','recv',BOB,obs))
        r=finish(w,BOB,Interpret(obs,b),'bad').result
        self.assertEqual(w.language_outcome(BOB,r),'invalid')

    @rules('L06')
    def test_partial_semantic_work_and_duplicate_commands(self):
        w=world(); a=acquire(w,ALICE,(BOX,),'a'); p=Learn('kept',a)
        cmd=LanguageCommand('one','learn',ALICE,p,1); w.execute(cmd)
        self.assertEqual(w.language_job(ALICE,'learn').outcome,WorkStatus.PARTIAL)
        cp=w.checkpoint(); w.execute(cmd); self.assertEqual(w.checkpoint(),cp)
        clone=LanguageWorld.restore(cp)
        for x in (w,clone): finish(x,ALICE,p,'learn')
        self.assertEqual(w.checkpoint(),clone.checkpoint())

    @rules('L06')
    def test_changed_continuation_rejected(self):
        w=world(); a=acquire(w,ALICE,(BOX,),'a')
        w.execute(LanguageCommand('one','learn',ALICE,Learn('kept',a),1))
        with self.assertRaises(ValueError): w.execute(LanguageCommand('two','learn',ALICE,Learn('other',a),1))

    @rules('L06')
    def test_independent_energy_and_time_shortages(self):
        for shortage in ('energy','time'):
            w=world(30,30); a=acquire(w,ALICE,(BOX,),'a')
            wallet=w._wallets[ALICE]
            # Config-sized fixture consumes remainder through an explicit costly
            # job rather than mutating the simulation's balances.
            remaining=getattr(wallet,shortage)
            from hle.world_records import INSPECT
            for n in range(remaining-1): w.execute(Attempt('burn'+str(n),'burn'+str(n),request(ALICE,INSPECT,(BOX,))))
            # Both initially equal; credit only the other resource to isolate shortage.
            w.execute(Credit('isolate',ALICE,100 if shortage=='time' else 0,100 if shortage=='energy' else 0,'independent resource control'))
            job=finish(w,ALICE,Learn('kept',a),'learn')
            self.assertEqual(job.outcome,WorkStatus.PARTIAL)
            w.execute(Credit('fund',ALICE,10 if shortage=='energy' else 0,10 if shortage=='time' else 0,'resume'))
            self.assertEqual(finish(w,ALICE,Learn('kept',a),'learn').outcome,WorkStatus.COMPLETED)

    @rules('L06')
    def test_every_demo_prefix_restores(self):
        w,_=run_language_demo()
        clone=world()
        for tx in w._journal[1:]:
            clone.execute(tx.command)
            self.assertEqual(LanguageWorld.restore(clone.checkpoint()).checkpoint(),clone.checkpoint())

    @rules('L06')
    def test_action_tampering_rejected(self):
        w,a,b,l=pair(); _,_,r=utter(w,b)
        cmd=w.next_language_action(BOB,r)
        with self.assertRaises(ValueError): w.execute(replace(cmd,action=replace(cmd.action,inputs=(BOX,))))

    @rules('L06')
    def test_rehashed_checkpoint_semantic_tampering_rejected(self):
        from hle.codec import dumps,loads
        w,_=run_language_demo(); cp=loads(w.checkpoint()); entries=list(cp.journal)
        index=next(i for i,t in enumerate(entries) if type(t) is LanguageTransaction and t.extra and type(t.extra[0]) is Interpretation)
        tx=entries[index]; entries[index]=replace(tx,extra=(replace(tx.extra[0],status='accepted'),))
        with self.assertRaises(ValueError): LanguageWorld.restore(dumps(replace(cp,journal=tuple(entries))))

    @rules('L07')
    def test_all_r7_behavior_still_available(self):
        from hle.socion_demo import run_socion_demo
        w,s=run_socion_demo()
        self.assertTrue(len(w._journal)>1)

    @rules('L05')
    def test_independent_journal_oracle_for_argument_controls(self):
        from .reference_language import guard
        for item in (BOX,TOOL):
            for owner in (ALICE,BOB):
                w,a,b,l=pair()
                _,_,r=utter(w,b,calls=(w.word(ALICE,'kept',(item,owner)),))
                result=w.language_record(BOB,r)
                self.assertEqual(result.status,guard(w._journal,BOB,result.speech,b))

    @rules('L06')
    def test_partial_action_resume_after_checkpoint(self):
        w,a,b,l=pair(cfg=config(200,200)); _,_,r=utter(w,b,actions=(Act('transfer',TOOL,ALICE),))
        # Spend the actor's remaining balance except one unit using inspection.
        from hle.world_records import INSPECT
        for n in range(w._wallets[BOB].energy-1):
            w.execute(Attempt('spend'+str(n),'spend'+str(n),request(BOB,INSPECT,(TOOL,))))
        w.execute(w.next_language_action(BOB,r))
        self.assertEqual(w._language_actions[r][-1].outcome,WorkStatus.PARTIAL)
        clone=LanguageWorld.restore(w.checkpoint())
        for x in (w,clone):
            x.execute(Credit('credit',BOB,1,1,'finish physical action'))
            self.assertEqual(enact(x,BOB,r),'fulfilled')
        self.assertEqual(w.checkpoint(),clone.checkpoint())

    @rules('L06')
    def test_competing_learning_requires_cancel_before_revision(self):
        from hle.semantic_records import CancelSemantic
        w,a,b,l=pair()
        payload=Learn('kept',a,expected=l)
        w.execute(LanguageCommand('start','pending',ALICE,payload,1))
        before=w.checkpoint()
        with self.assertRaises(ValueError): finish(w,ALICE,payload,'competing')
        self.assertEqual(w.checkpoint(),before)
        w.execute(CancelSemantic('cancel','pending',ALICE,'language','revise after cancellation'))
        finish(w,ALICE,payload,'competing')
        self.assertEqual(w.language_job(ALICE,'pending').outcome,WorkStatus.FAILED)
        self.assertEqual(w.language_job(ALICE,'pending').paid,1)
        self.assertIsNone(w.language_job(ALICE,'pending').result)
        self.assertEqual(w.lexeme(ALICE,'kept').ref.revision,l.revision+1)

    @rules('L02')
    def test_unavailable_channel_does_not_create_delivered_commitment(self):
        cfg=replace(config(5000,5000),message_links=())
        w=world(cfg=cfg); a=acquire(w,ALICE,(BOX,),'a')
        finish(w,ALICE,Learn('kept',a),'learn')
        u=finish(w,ALICE,Produce(Speech('commit',(w.word(ALICE,'kept',(BOX,ALICE)),),(Act('inspect',BOX),))),'u').result
        w.execute(w.send_language(ALICE,u,BOB,'send'))
        with self.assertRaises(ValueError): finish(w,ALICE,Intend(u,a),'intend')

    @rules('L03')
    def test_shared_owner_slot_generalizes(self):
        w=world(); w.execute(Attempt('transfer','transfer',request(BOB,TRANSFER,(TOOL,ALICE))))
        a=acquire(w,ALICE,(BOX,TOOL),'a'); b=acquire(w,BOB,(TOOL,BOX),'b')
        l=finish(w,ALICE,Learn('pair',a),'learn').result
        self.assertEqual(w.language_record(ALICE,l).meaning.patterns,(Pattern(0,1),Pattern(2,1)))
        msg=deliver(w,ALICE,l,BOB,'teach'); finish(w,BOB,Learn('pair',b,msg),'adopt')
        _,_,r=utter(w,b,calls=(w.word(ALICE,'pair',(TOOL,ALICE,BOX)),),actions=(Act('inspect',BOX),))
        self.assertEqual(enact(w,BOB,r),'fulfilled')

    @rules('L04')
    def test_commitment_physical_failure_preserves_expectation(self):
        w,a,b,l=pair()
        speech=Speech('commit',(w.word(ALICE,'kept',(BOX,ALICE)),),(Act('transfer',BOX,BOB),))
        u=finish(w,ALICE,Produce(speech),'u').result
        obs=deliver(w,ALICE,u,BOB,'send')
        bb=acquire(w,BOB,(BOX,),'bb')
        r=finish(w,BOB,Interpret(obs,bb),'expect').result
        i=finish(w,ALICE,Intend(u,a),'intend').result
        w.execute(Attempt('intervention','intervention',request(ALICE,TRANSFER,(BOX,BOB))))
        self.assertEqual(enact(w,ALICE,i),'failed')
        self.assertEqual(w.language_outcome(BOB,r),'expected')
        self.assertEqual(len(w._language_actions[i]),1)

    @rules('L05')
    def test_foreign_context_not_used_as_world_action_evidence(self):
        from hle.memory_records import MemoryCommand, ContextDraft, WriteDraft
        w=world()
        w.execute(MemoryCommand('context','context',BOB,ContextDraft('elsewhere','elsewhere')))
        ctx=w._journal[-1].contexts[0].ref
        p=Proposition(TOOL,'owned_by',BOB,ctx,TimeScope(w.now,None))
        w.execute(MemoryCommand('memory','memory',BOB,WriteDraft('other',(p,),(),ClaimStatus.ENDORSED,None,'other context'),
            based_on=(w.participant_input(BOB)[0].observations[0].ref,)))
        mem=w.memory_head(BOB,'other')
        root=complete(w,FoldDraft('other',(Part('claim',mem.ref,ctx),)),'fold:other',BOB).result
        access=complete(w,UnfoldDraft(root,ctx,w.now),'unfold:other',BOB).result
        with self.assertRaises(ValueError): finish(w,BOB,Learn('kept',access),'learn:other')
