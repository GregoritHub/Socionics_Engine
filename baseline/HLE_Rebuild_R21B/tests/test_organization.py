from dataclasses import replace
import unittest
from unittest.mock import patch
from hle.organization import OrganizationWorld, terms_id, packet
from hle.organization_records import *
from hle.organization_demo import (world, prepared, propose, agree, org, send, perform,
    train, move, run_organization_demo, ACTORS, CARA, DARA)
from hle.language_demo import acquire, finish, deliver
from hle.language_records import Learn, Pattern
from hle.demo import ALICE, BOB, BOX, ROOM, request
from hle.contracts import WorkStatus, ActionRequest, Proposition, TimeScope, ClaimStatus
from hle.world_records import Attempt, Credit, INSPECT, TRANSFER, SEND, MessageDraft, RETAIN, MemoryDraft, Tick
from hle.socion_records import ReceiveCommand, ConfigureAgent, AgentPolicy
from hle.codec import loads,dumps
from .support import rules
from .reference_organization import consent,actions


def agreed(steps=('transfer',)):
    w=prepared(steps=steps); p=propose(w,ALICE,'p'); identity=agree(w,ALICE,p,'agree')
    return w,p,identity


def reviews(w,p):
    result={}
    for a in w._records[p].terms.members:
        source=p if a==ALICE else send(w,ALICE,p,a,'offer:'+a.key)
        access=acquire(w,a,(BOX,),'review:access:'+a.key)
        result[a]=org(w,a,ReviewTerms(source,access),'review:'+a.key)
    return result


def limited(w,actor,energy,time):
    wallet=w._wallets[actor]
    cfg=replace(w.config,wallets=tuple(replace(x,energy=x.energy-wallet.energy+energy,time=x.time-wallet.time+time)
        if x.actor==actor else x for x in w.config.wallets))
    clone=OrganizationWorld(cfg,w.profiles,w.policy,w.agents,w.organization_policies)
    for tx in w._journal[1:]: clone.execute(tx.command)
    assert clone._wallets[actor].energy==energy and clone._wallets[actor].time==time
    return clone


class OrganizationTests(unittest.TestCase):
    @rules('G01')
    def test_no_history_cannot_generate_finished_procedure(self):
        w=world(); a=acquire(w,ALICE,(BOX,),'a'); finish(w,ALICE,Learn('kept',a),'l')
        r=org(w,ALICE,Formulate(a),'p')
        self.assertEqual(w._records[r].status,'unresolved'); self.assertIsNone(w._records[r].terms)

    @rules('G01')
    def test_participant_elects_history_dependent_sequence_and_members(self):
        for steps in (('transfer',),('inspect','transfer'),('inspect','inspect','transfer')):
            w=prepared(steps=steps); p=propose(w,ALICE,'p'); t=w._records[p].terms
            self.assertEqual(t.steps,steps); self.assertEqual(t.members,(ALICE,BOB,CARA))
            self.assertEqual(t.meaning.patterns,(Pattern(0,1),))
            self.assertTrue(all(w._records[r].owner==ALICE for r in w._records[p].sources))

    @rules('G01')
    def test_opaque_labels_preserve_selected_behavior(self):
        terms=[]
        for token in ('kept','zqx'):
            w=prepared(token=token); p=propose(w,ALICE,'p'); terms.append(w._records[p].terms)
        self.assertEqual((terms[0].steps,terms[0].members),(terms[1].steps,terms[1].members))

    @rules('G01')
    def test_foreign_source_rejected_without_mutation(self):
        w=prepared(); access=acquire(w,ALICE,(BOX,),'a'); before=w.checkpoint()
        with self.assertRaises(ValueError): org(w,BOB,Formulate(access),'bad')
        self.assertEqual(w.checkpoint(),before)

    @rules('G01')
    def test_one_success_is_not_recurring_support(self):
        w=world()
        for a in (ALICE,BOB):
            access=acquire(w,a,(BOX,),a.key); finish(w,a,Learn('kept',access),'learn:'+a.key)
        train(w,ALICE,BOB,'once'); move(w,BOB,ALICE,'return')
        r=propose(w,ALICE,'p'); self.assertEqual(w._records[r].status,'unresolved')

    @rules('G02')
    def test_paid_reception_required(self):
        w=prepared(); p=propose(w,ALICE,'p'); access=acquire(w,BOB,(BOX,),'b')
        w.execute(w.send_organization(ALICE,p,BOB,'send'))
        obs=next(o.ref for o in w._journal[-1].observations if o.observer==BOB and o.source.kind==Kind.MESSAGE)
        with self.assertRaises(ValueError): org(w,BOB,ReviewTerms(obs,access),'bad')

    @rules('G02')
    def test_unknown_concept_requires_independent_acquisition(self):
        w=prepared(); p=propose(w,ALICE,'p')
        offer=send(w,ALICE,p,DARA,'offer'); access=acquire(w,DARA,(BOX,),'new')
        before=org(w,DARA,Join(offer,access),'before')
        self.assertEqual(w._records[before].status,'repair')
        definition=deliver(w,ALICE,w.lexeme(ALICE,'kept').ref,DARA,'definition')
        finish(w,DARA,Learn('kept',access,definition),'learn')
        after=org(w,DARA,Join(offer,access),'after')
        self.assertEqual(w._records[after].status,'accepted')
        self.assertIsNone(w.organization_state(DARA,w._records[p].terms.identity))

    @rules('G02')
    def test_missing_vote_cannot_activate(self):
        w=prepared(); p=propose(w,ALICE,'p'); rv=reviews(w,p)
        one=send(w,BOB,rv[BOB],ALICE,'vote')
        r=org(w,ALICE,Ratify(rv[ALICE],(one,)),'ratify')
        self.assertEqual(w._records[r].status,'unagreed'); self.assertFalse(consent(w._journal,ALICE,r))
        self.assertIsNone(w.organization_state(ALICE,w._records[p].terms.identity))

    @rules('G02')
    def test_duplicate_votes_do_not_fill_missing_seat(self):
        w=prepared(); p=propose(w,ALICE,'p'); rv=reviews(w,p)
        one=send(w,BOB,rv[BOB],ALICE,'vote'); two=send(w,BOB,rv[BOB],ALICE,'again')
        r=org(w,ALICE,Ratify(rv[ALICE],(one,two)),'ratify')
        self.assertEqual(w._records[r].status,'unagreed')

    @rules('G02')
    def test_mixed_terms_votes_do_not_agree(self):
        w=prepared(); p=propose(w,ALICE,'p'); rv=reviews(w,p)
        q=propose(w,ALICE,'other'); obs=send(w,ALICE,q,CARA,'other:offer')
        acc=acquire(w,CARA,(BOX,),'other:access'); cr=org(w,CARA,ReviewTerms(obs,acc),'other:review')
        votes=(send(w,BOB,rv[BOB],ALICE,'bv'),send(w,CARA,cr,ALICE,'cv'))
        r=org(w,ALICE,Ratify(rv[ALICE],votes),'ratify'); self.assertEqual(w._records[r].status,'unagreed')

    @rules('G02')
    def test_refusal_prevents_agreement(self):
        policies=tuple(OrganizationPolicy(a,max_action_cost=2 if a==BOB else 8) for a in ACTORS)
        w=prepared(steps=('inspect','transfer'),policies=policies); p=propose(w,ALICE,'p'); rv=reviews(w,p)
        self.assertEqual(w._records[rv[BOB]].status,'refused')
        votes=tuple(send(w,x,rv[x],ALICE,'vote:'+x.key) for x in (BOB,CARA))
        r=org(w,ALICE,Ratify(rv[ALICE],votes),'ratify'); self.assertEqual(w._records[r].status,'unagreed')

    @rules('G02')
    def test_all_votes_are_locally_checked(self):
        w,p,identity=agreed()
        for a in (ALICE,BOB,CARA):
            r=w.organization_state(a,identity)
            self.assertEqual(r.status,'active'); self.assertTrue(consent(w._journal,a,r.ref))
        self.assertIsNone(w.organization_state(DARA,identity))

    @rules('G02')
    def test_forged_packet_and_foreign_record_rejected(self):
        w=prepared(); p=propose(w,ALICE,'p'); before=w.checkpoint()
        with self.assertRaises(ValueError): w.send_organization(BOB,p,ALICE,'bad')
        fake=replace(packet(w._records[p]),sender=BOB,kind='review',status='accepted')
        prop=Proposition(BOB,'r9_wire',dumps(fake),ROOM,TimeScope(w.now,None))
        with self.assertRaises(ValueError): w.execute(Attempt('raw','raw',request(BOB,SEND,(ALICE,)),MessageDraft((prop,))))
        self.assertEqual(w.checkpoint(),before)

    @rules('G02')
    def test_channel_failure_does_not_grant_consent(self):
        w=prepared(); p=propose(w,ALICE,'p')
        # Recreate the identical pre-proposal history with one unavailable new link.
        cfg=replace(w.config,message_links=tuple(x for x in w.config.message_links if x!=(ALICE,DARA)))
        c=OrganizationWorld(cfg,w.profiles,w.policy,w.agents,w.organization_policies)
        for tx in w._journal[1:]: c.execute(tx.command)
        self.assertIsNone(send(c,ALICE,p,DARA,'blocked'))
        self.assertEqual(c._journal[-1].event.outcome,WorkStatus.FAILED)
        self.assertIsNone(c.organization_state(DARA,w._records[p].terms.identity))

    @rules('G03')
    def test_recurring_actual_transfers_and_physical_costs(self):
        w,p,identity=agreed(steps=('inspect','transfer'))
        for n,a in enumerate((ALICE,BOB,CARA)*2):
            r=perform(w,a,identity,'use:'+str(n)); self.assertEqual(w.organization_outcome(a,r),'fulfilled')
            trace=actions(w._journal,r)
            self.assertEqual([x[1] for x in trace],['r2.inspect','r2.transfer'])
            self.assertEqual(sum(x[4] for x in trace),3)
        self.assertEqual(w.truth.current_fact(BOX,'owned_by',ROOM).object,ALICE)

    @rules('G03')
    def test_wrong_holder_cannot_enact(self):
        w,p,identity=agreed(); r=perform(w,BOB,identity,'not-holder')
        self.assertEqual(w.organization_outcome(BOB,r),'refused'); self.assertFalse(actions(w._journal,r))

    @rules('G03')
    def test_hidden_world_change_does_not_leak_to_plan(self):
        w,p,identity=agreed(); acc=acquire(w,ALICE,(BOX,),'access')
        c=OrganizationWorld.restore(w.checkpoint()); move(c,ALICE,BOB,'hidden')
        for x in (w,c):
            with patch.object(type(x.truth),'check',side_effect=AssertionError('Truth check')), patch.object(type(x.truth),'current_fact',side_effect=AssertionError('Truth current')):
                r=org(x,ALICE,Perform(x.organization_state(ALICE,identity).ref,acc),'plan')
                self.assertEqual(x._records[r].status,'accepted')
            x.execute(x.next_organization_action(ALICE,r))
        self.assertEqual(w.organization_outcome(ALICE,r),'fulfilled')
        self.assertEqual(c.organization_outcome(ALICE,r),'failed')

    @rules('G03')
    def test_inspection_prevents_known_contradictory_transfer(self):
        w,p,identity=agreed(('inspect','transfer')); access=acquire(w,ALICE,(BOX,),'access')
        r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,access),'plan')
        move(w,ALICE,BOB,'hidden'); w.execute(w.next_organization_action(ALICE,r))
        self.assertEqual(w.organization_outcome(ALICE,r),'blocked'); self.assertIsNone(w.next_organization_action(ALICE,r))
        self.assertEqual(len(actions(w._journal,r)),1)
        d=org(w,ALICE,Dispute(r),'dispute'); self.assertEqual(w._records[d].status,'suspended')

    @rules('G03')
    def test_plan_action_tampering_rejected(self):
        w,p,identity=agreed(); access=acquire(w,ALICE,(BOX,),'access')
        r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,access),'plan'); cmd=w.next_organization_action(ALICE,r)
        before=w.checkpoint()
        with self.assertRaises(ValueError): w.execute(replace(cmd,action=replace(cmd.action,inputs=(BOX,CARA))))
        self.assertEqual(w.checkpoint(),before)

    @rules('G03')
    def test_changed_meaning_requires_repair(self):
        w,p,identity=agreed(); access=acquire(w,ALICE,(BOX,),'access')
        # Remove learned meaning through a supported lexicon revision with another
        # pattern (constructed by acquiring both ownership edges is covered in R8).
        old=w.lexeme(ALICE,'kept')
        from hle.language_records import Meaning
        changed=replace(old,meaning=Meaning('kept',(Pattern(0,1),Pattern(1,0)),2))
        # Unit boundary injection tests the guard, never counted as emergence.
        w._lexicon[(ALICE,'kept')]=changed
        r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,access),'plan')
        self.assertEqual(w._records[r].status,'repair')

    @rules('G04','G05')
    def test_complete_dispute_revision_succession_dissolution(self):
        w,s,c=run_organization_demo()
        self.assertEqual(s['without_alternative'],'unresolved')
        self.assertEqual(s['revised_steps'],('inspect','transfer'))
        self.assertEqual(s['successor_members'],['bob','cara','dara'])
        self.assertEqual(s['successor_outcomes'],['fulfilled']*6)
        self.assertEqual((s['founder_state'],s['remaining_member_state']),('withdrawn','dissolved'))
        self.assertEqual(s['generations'],[1,2,3])
        for tx in w._journal:
            if type(tx) is OrganizationTransaction:
                for r in tx.extra:
                    if r.kind=='agreement' and r.status=='active': self.assertTrue(consent(w._journal,r.owner,r.ref))

    @rules('G04')
    def test_dispute_requires_consequential_failure(self):
        w,p,identity=agreed(); r=perform(w,ALICE,identity,'good'); before=w.checkpoint()
        with self.assertRaises(ValueError): org(w,ALICE,Dispute(r),'fake')
        self.assertEqual(w.checkpoint(),before)

    @rules('G04')
    def test_uninformed_member_does_not_know_dispute(self):
        w,p,identity=agreed(); acc=acquire(w,ALICE,(BOX,),'a')
        r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,acc),'plan')
        move(w,ALICE,BOB,'intervene'); w.execute(w.next_organization_action(ALICE,r))
        d=org(w,ALICE,Dispute(r),'dispute')
        self.assertEqual(w.organization_state(BOB,identity).status,'active')
        obs=send(w,ALICE,d,BOB,'tell')
        org(w,BOB,Attend(w.organization_state(BOB,identity).ref,obs),'attend')
        self.assertEqual(w.organization_state(BOB,identity).status,'suspended')
        self.assertEqual(w.organization_state(CARA,identity).status,'active')
        pending=perform(w,BOB,identity,'suspended'); self.assertEqual(w._records[pending].status,'suspended')

    @rules('G05')
    def test_exit_cancels_outstanding_plan_and_blocks_old_command(self):
        w,p,identity=agreed(); acc=acquire(w,ALICE,(BOX,),'a')
        r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,acc),'plan')
        cmd=w.next_organization_action(ALICE,r)
        org(w,ALICE,Leave(w.organization_state(ALICE,identity).ref,'leave'),'exit')
        self.assertEqual(w.organization_outcome(ALICE,r),'cancelled')
        with self.assertRaises(ValueError): w.execute(cmd)

    @rules('G06')
    def test_partial_semantic_resume_and_idempotence(self):
        w=prepared(); a=acquire(w,ALICE,(BOX,),'a'); payload=Formulate(a)
        cmd=OrganizationCommand('start','proposal',ALICE,payload,1); w.execute(cmd)
        self.assertEqual(w.organization_job(ALICE,'proposal').outcome,WorkStatus.PARTIAL)
        cp=w.checkpoint(); w.execute(cmd); self.assertEqual(cp,w.checkpoint())
        clone=OrganizationWorld.restore(cp)
        for x in (w,clone): org(x,ALICE,payload,'proposal')
        self.assertEqual(w.checkpoint(),clone.checkpoint())

    @rules('G06')
    def test_changed_command_and_payload_rejected(self):
        w=prepared(); a=acquire(w,ALICE,(BOX,),'a'); cmd=OrganizationCommand('start','proposal',ALICE,Formulate(a),1)
        w.execute(cmd); before=w.checkpoint()
        with self.assertRaises(ValueError): w.execute(replace(cmd,work_limit=2))
        with self.assertRaises(ValueError): w.execute(replace(cmd,command_id='other',payload=Leave(a,'bad')))
        self.assertEqual(before,w.checkpoint())

    @rules('G06')
    def test_energy_time_and_zero_funding(self):
        base=prepared(); access=acquire(base,ALICE,(BOX,),'a')
        for energy,time in ((0,10),(1,100),(100,1)):
            w=limited(base,ALICE,energy,time)
            r=org(w,ALICE,Formulate(access),'partial')
            self.assertIsNone(r)
            j=w.organization_job(ALICE,'partial'); self.assertEqual(j.paid,min(energy,time))
            clone=OrganizationWorld.restore(w.checkpoint())
            for x in (w,clone):
                x.execute(Credit('fund',ALICE,100,100,'resume explicit resource-limited work'))
                self.assertIsNotNone(org(x,ALICE,Formulate(access),'partial'))
            self.assertEqual(w.checkpoint(),clone.checkpoint())

    @rules('G06')
    def test_partial_physical_action_resume(self):
        w,p,identity=agreed(); acc=acquire(w,ALICE,(BOX,),'a')
        r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,acc),'plan')
        w=limited(w,ALICE,1,20); w.execute(w.next_organization_action(ALICE,r))
        self.assertEqual(w.organization_outcome(ALICE,r),'pending')
        self.assertEqual(actions(w._journal,r)[-1][3],'partial')
        clone=OrganizationWorld.restore(w.checkpoint())
        for x in (w,clone):
            x.execute(Credit('fund',ALICE,1,0,'finish already funded transfer'))
            x.execute(x.next_organization_action(ALICE,r))
            self.assertEqual(x.organization_outcome(ALICE,r),'fulfilled')
        self.assertEqual(w.checkpoint(),clone.checkpoint())
        self.assertEqual(sum(x[4] for x in actions(w._journal,r)),2)

    @rules('G06')
    def test_leave_requires_cancel_before_changing_local_state(self):
        from hle.semantic_records import CancelSemantic
        w,p,identity=agreed(); acc=acquire(w,ALICE,(BOX,),'a'); state=w.organization_state(ALICE,identity).ref
        payload=Perform(state,acc); w.execute(OrganizationCommand('start','plan',ALICE,payload,1))
        before=w.checkpoint()
        with self.assertRaises(ValueError): org(w,ALICE,Leave(state,'leave before completed planning'),'exit')
        self.assertEqual(w.checkpoint(),before)
        w.execute(CancelSemantic('cancel','plan',ALICE,'organization','cancel uncompleted planning'))
        org(w,ALICE,Leave(state,'leave after cancellation'),'exit')
        self.assertEqual(w.organization_job(ALICE,'plan').outcome,WorkStatus.FAILED)
        self.assertEqual(w.organization_job(ALICE,'plan').paid,1)
        self.assertIsNone(w.organization_job(ALICE,'plan').result)
        self.assertEqual(w.organization_state(ALICE,identity).status,'withdrawn')

    @rules('G06')
    def test_lifecycle_checkpoints_and_continuation(self):
        w,s,checkpoints=run_organization_demo()
        for cp in checkpoints:
            clone=OrganizationWorld.restore(cp)
            self.assertEqual(clone.checkpoint(),cp)
            for tx in w._journal[len(clone._journal):]: clone.execute(tx.command)
            self.assertEqual(clone.checkpoint(),w.checkpoint())

    @rules('G06')
    def test_rehashed_semantic_tampering_rejected(self):
        w,p,identity=agreed(); cp=loads(w.checkpoint()); entries=list(cp.journal)
        i=next(i for i,tx in enumerate(entries) if type(tx) is OrganizationTransaction and tx.extra and tx.extra[0].kind=='review')
        tx=entries[i]; entries[i]=replace(tx,extra=(replace(tx.extra[0],status='refused'),))
        with self.assertRaises(ValueError): OrganizationWorld.restore(dumps(replace(cp,journal=tuple(entries))))

    @rules('G07')
    def test_inactive_ticks_do_not_visit_practice_candidates(self):
        w=prepared(); n=w.organization_candidate_visits
        for i in range(200): w.execute(Tick('inactive:'+str(i)))
        self.assertEqual(w.organization_candidate_visits,n)
        p=propose(w,ALICE,'p'); self.assertEqual(w.organization_candidate_visits-n,len(w.practices(ALICE)))

    @rules('G03')
    def test_stale_access_is_rejected_for_rule_use(self):
        w,p,identity=agreed(); access=acquire(w,ALICE,(BOX,),'a')
        old=w._records[w._records[access].hits[0].memory]
        w.execute(Attempt('revise','revise',request(ALICE,RETAIN),memory=MemoryDraft('a:item:0',old.content,ClaimStatus.ENDORSED,'revise retained view')))
        r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,access),'plan')
        self.assertEqual(w._records[r].status,'stale'); self.assertIsNone(w.next_organization_action(ALICE,r))

    @rules('G03')
    def test_unknown_and_ambiguous_access_do_not_grant_action(self):
        from hle.composition_records import FoldDraft,Part,UnfoldDraft
        from hle.composition_demo import complete
        for mode in ('unknown','ambiguous'):
            w,p,identity=agreed()
            content=() if mode=='unknown' else tuple(Proposition(BOX,'owned_by',a,ROOM,TimeScope(w.now,None)) for a in (ALICE,BOB))
            w.execute(Attempt('retain','retain',request(ALICE,RETAIN),memory=MemoryDraft('fixture',content,ClaimStatus.TENTATIVE,'declared incomplete or inconsistent belief fixture')))
            root=complete(w,FoldDraft('fixture',(Part('source',w.memory_head(ALICE,'fixture').ref,ROOM),)),'fold',ALICE).result
            access=complete(w,UnfoldDraft(root,ROOM,w.now),'access',ALICE).result
            r=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,access),'plan')
            self.assertEqual(w._records[r].status,mode); self.assertIsNone(w.next_organization_action(ALICE,r))

    @rules('G05')
    def test_removing_member_requires_locally_received_exit(self):
        w,p,identity=agreed()
        for n,a in enumerate((ALICE,BOB,CARA)*2): perform(w,a,identity,'use:'+str(n))
        perform(w,ALICE,identity,'handover-before-exit')
        ex=org(w,ALICE,Leave(w.organization_state(ALICE,identity).ref,'leave'),'leave')
        obs=send(w,ALICE,ex,BOB,'tell:bob')
        org(w,BOB,Attend(w.organization_state(BOB,identity).ref,obs),'attend:bob')
        p2=propose(w,BOB,'new',w.organization_state(BOB,identity).ref)
        offer=send(w,BOB,p2,CARA,'new:offer'); acc=acquire(w,CARA,(BOX,),'c:access')
        refused=org(w,CARA,ReviewTerms(offer,acc),'before:exit')
        self.assertEqual(w._records[refused].status,'refused')
        obs=send(w,ALICE,ex,CARA,'tell:cara')
        org(w,CARA,Attend(w.organization_state(CARA,identity).ref,obs),'attend:cara')
        accepted=org(w,CARA,ReviewTerms(offer,acc),'after:exit')
        self.assertEqual(w._records[accepted].status,'accepted')

    @rules('G02','G06')
    def test_old_review_cannot_reinstall_after_agreement(self):
        w=prepared(); p=propose(w,ALICE,'p'); rv=reviews(w,p)
        votes=tuple(send(w,x,rv[x],ALICE,'vote:'+x.key) for x in (BOB,CARA))
        a=org(w,ALICE,Ratify(rv[ALICE],votes),'ratify:1')
        r=org(w,ALICE,Ratify(rv[ALICE],votes),'ratify:2')
        self.assertEqual(w._records[r].status,'unagreed')
        self.assertEqual(w.organization_state(ALICE,w._records[p].terms.identity).ref,a)

    @rules('G07')
    def test_r9_gate_ids_registered_and_distinct_from_foundation(self):
        import json
        from pathlib import Path
        data=json.loads((Path(__file__).resolve().parents[1]/'docs/rules.json').read_text())
        by_id={x['id']:x for x in data['rules']}
        self.assertEqual(len(by_id),len(data['rules']))
        for n in range(1,8): self.assertIn('G0'+str(n),by_id)
        self.assertNotEqual(by_id['O01']['statement'],by_id['G01']['statement'])
