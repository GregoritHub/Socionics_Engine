from dataclasses import replace
import unittest
from hle.codec import loads,dumps
from hle.contracts import WorkStatus, ClaimStatus, Kind
from hle.crux import Perspective
from hle.language import LanguageWorld
from hle.language_records import LanguageCommand, Learn, Produce, Speech, Act, Intend
from hle.language_demo import world, acquire, finish, deliver, enact
from hle.organization_records import OrganizationCommand, Formulate, Perform
from hle.organization_demo import run_organization_demo, org
from hle.semantic_records import CancelSemantic
from hle.semantic import TARGETS, semantic_route
from hle.metabolism_records import MetabolicCommand, TheorizeDraft, UnderstandDraft, ProcessingPolicy
from hle.metabolism_demo import remember_initial, retrieve, finish as metabolic_finish
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, request
from hle.socion_records import ReceiveCommand
from hle.world_records import Attempt, INSPECT, RETAIN, TRANSFER, MemoryDraft, Credit
from tools.r11_oracle import check_world, reconstruct, EXPECTED
from tests.reference_processing import route_oracle
from tests.test_organization import agreed

DONE=(WorkStatus.COMPLETED,WorkStatus.FAILED)


class SemanticRoutingTests(unittest.TestCase):
    def test_full_organization_and_commitment_cover_every_mapping(self):
        w,summary,_=run_organization_demo()
        seen={tx.job.route.operation for tx in w._journal if getattr(getattr(tx,'job',None),'route',None)}
        self.assertEqual(seen,set(TARGETS)-{'Intend'})
        diag=check_world(w)
        self.assertGreater(diag['counts']['activation_changes'],0)
        self.assertGreater(len(diag['emitted_elements']),2)
        w=world(); access=acquire(w,ALICE,(BOX,),'a')
        finish(w,ALICE,Learn('kept',access),'learn')
        u=finish(w,ALICE,Produce(Speech('commit',(w.word(ALICE,'kept',(BOX,ALICE)),),
            (Act('transfer',BOX,BOB),))),'produce').result
        deliver(w,ALICE,u,BOB,'send')
        self.assertEqual(w.processing_state(ALICE).active,'fe')
        job=finish(w,ALICE,Intend(u,access),'intend')
        self.assertEqual(w.processing_state(ALICE).active,'fi')
        self.assertEqual(enact(w,ALICE,job.result),'fulfilled')
        self.assertEqual(w._facts[(BOX,'owned_by',ROOM)].object,BOB)
        check_world(w)

    def test_all_operation_routes_match_independent_positional_oracle(self):
        from hle.model_a import TYPES,ELEMENT
        w,_,_=run_organization_demo()
        payloads={type(tx.job.command.payload).__name__:tx.job.command.payload
            for tx in w._journal if getattr(getattr(tx,'job',None),'route',None)}
        payloads['Intend']=Intend(next(iter(w._lexicon.values())).ref,next(iter(w._lexicon.values())).access)
        profile=w.profiles[0]; state=w.processing_state(profile.owner)
        for tim in TYPES:
            for start in ELEMENT:
                for typed,prices in ((True,True),(True,False),(False,True),(False,False)):
                    for name,p in payloads.items():
                        route=semantic_route(replace(profile,tim=tim),replace(state,active=start),
                            'language' if name in ('Learn','Produce','Interpret','Intend') else 'organization',
                            p,3,ProcessingPolicy(typed,prices))
                        target,expense=EXPECTED[name]
                        q=route.plan
                        self.assertEqual((q.path,q.positions,q.support_position,q.support_index,q.hop_units,q.content_units),
                            route_oracle(tim,start,target,expense,3,typed,prices))

    def test_every_funded_hop_and_content_prefix_restore_and_continue(self):
        base=world(); access=acquire(base,ALICE,(BOX,),'a'); prefix=base.checkpoint()
        command=LanguageCommand('first','learn',ALICE,Learn('kept',access),1)
        base.execute(command); total=base.language_job(ALICE,'learn').required
        for n in range(1,total):
            w=LanguageWorld.restore(prefix)
            w.execute(replace(command,work_limit=n))
            self.assertIsNone(w.lexeme(ALICE,'kept')); self.assertIsNone(w.language_job(ALICE,'learn').result)
            check_world(w); cp=w.checkpoint(); clone=LanguageWorld.restore(cp)
            self.assertEqual(clone.checkpoint(),cp)
            for x in (w,clone): finish(x,ALICE,command.payload,'learn')
            self.assertEqual(w.checkpoint(),clone.checkpoint())
            self.assertEqual(w.language_job(ALICE,'learn').paid,total)
            self.assertEqual(w.processing_state(ALICE).active,'ti')

    def test_zero_energy_or_time_keeps_no_output_and_exact_paid_progress(self):
        base=world(); access=acquire(base,ALICE,(BOX,),'a')
        for energy,time in ((0,5),(5,0)):
            wallet=base._wallets[ALICE]
            cfg=replace(base.config,wallets=tuple(replace(x,energy=x.energy-wallet.energy+energy,
                time=x.time-wallet.time+time) if x.actor==ALICE else x for x in base.config.wallets))
            w=LanguageWorld(cfg,base.profiles,base.policy,base.agents)
            for tx in base._journal[1:]: w.execute(tx.command)
            finish(w,ALICE,Learn('kept',access),'limited')
            self.assertEqual(w.language_job(ALICE,'limited').paid,0)
            self.assertIsNone(w.lexeme(ALICE,'kept')); check_world(w)
            clone=LanguageWorld.restore(w.checkpoint())
            for x in (w,clone):
                x.execute(Credit('credit',ALICE,100,100,'explicit test resources'))
                finish(x,ALICE,Learn('kept',access),'limited')
            self.assertEqual(w.checkpoint(),clone.checkpoint())

    def test_retry_idempotence_and_cancel_preserve_paid_cost_active_and_history(self):
        w=world(); access=acquire(w,ALICE,(BOX,),'a')
        cmd=LanguageCommand('start','learn',ALICE,Learn('kept',access),2)
        w.execute(cmd); cp=w.checkpoint(); w.execute(cmd); self.assertEqual(cp,w.checkpoint())
        with self.assertRaises(ValueError): w.execute(replace(cmd,work_limit=3))
        state=w.processing_state(ALICE); balance=w._wallets[ALICE]
        cancel=CancelSemantic('cancel','learn',ALICE,'language','choose another task')
        w.execute(cancel)
        self.assertEqual(w._wallets[ALICE],balance)
        self.assertEqual(w.processing_state(ALICE).active,state.active)
        self.assertIsNone(w.processing_state(ALICE).busy)
        self.assertEqual(w.language_job(ALICE,'learn').paid,2)
        self.assertIsNone(w.lexeme(ALICE,'kept'))
        cp=w.checkpoint(); w.execute(cancel); self.assertEqual(cp,w.checkpoint())
        with self.assertRaises(ValueError): w.execute(replace(cmd,command_id='terminal'))
        clone=LanguageWorld.restore(cp)
        for x in (w,clone): finish(x,ALICE,cmd.payload,'replacement')
        self.assertEqual(w.checkpoint(),clone.checkpoint()); check_world(w)

    def test_stale_language_evidence_fails_releases_and_preserves_prior_lexeme(self):
        w=world(); access=acquire(w,ALICE,(BOX,),'a')
        old=finish(w,ALICE,Learn('kept',access),'initial').result
        cmd=LanguageCommand('start','learn',ALICE,Learn('kept',access,expected=old),1)
        w.execute(cmd)
        memory=w.read_revision(ALICE,w._records[access].hits[0].memory)
        w.execute(Attempt('revise','revise',request(ALICE,RETAIN),memory=MemoryDraft(
            'a:item:0',memory.content,ClaimStatus.ENDORSED,'new local revision')))
        e=w.execute(replace(cmd,command_id='resume',work_limit=64))
        self.assertEqual(e.outcome,WorkStatus.FAILED); self.assertEqual(w.lexeme(ALICE,'kept').ref,old)
        self.assertIsNone(w.processing_state(ALICE).busy); self.assertEqual(w.language_job(ALICE,'learn').paid,1)
        check_world(w)

    def test_invalidated_produce_fails_instead_of_stranding_processing(self):
        from hle.socion_records import ConfigureAgent,AgentPolicy
        w=world(); access=acquire(w,ALICE,(BOX,),'a')
        finish(w,ALICE,Learn('kept',access),'initial')
        # _prepare raises when an owned required record becomes unavailable; a
        # test double covers this error path, leaving the real indexes untouched.
        from unittest.mock import patch
        cmd=LanguageCommand('start','learn',ALICE,Learn('new',access),1)
        w.execute(cmd)
        with patch.object(w,'_prepare',side_effect=ValueError('access no longer admissible')):
            event=w.execute(replace(cmd,command_id='resume'))
        self.assertEqual(event.outcome,WorkStatus.FAILED)
        self.assertIsNone(w.processing_state(ALICE).busy)
        self.assertEqual(w.language_job(ALICE,'learn').paid,1)

    def test_stale_organization_evidence_cannot_install_partial_plan(self):
        w,p,identity=agreed(); access=acquire(w,ALICE,(BOX,),'a')
        payload=Perform(w.organization_state(ALICE,identity).ref,access)
        cmd=OrganizationCommand('start','perform',ALICE,payload,1); w.execute(cmd)
        old=w.read_revision(ALICE,w._records[access].hits[0].memory)
        w.execute(Attempt('revise','revise',request(ALICE,RETAIN),memory=MemoryDraft(
            'a:item:0',old.content,ClaimStatus.ENDORSED,'new access required')))
        w.execute(replace(cmd,command_id='resume'))
        self.assertEqual(w.organization_job(ALICE,'perform').outcome,WorkStatus.FAILED)
        self.assertIsNone(w.organization_job(ALICE,'perform').result)
        self.assertFalse(w._organization_pending); self.assertFalse(w._semantic_owners); check_world(w)

    def test_cross_family_identical_task_names_are_exclusive_and_other_actor_runs(self):
        w,p,identity=agreed(); access=acquire(w,ALICE,(BOX,),'a')
        cmd=LanguageCommand('start','same',ALICE,Learn('another',access),1); w.execute(cmd)
        before=w.checkpoint()
        with self.assertRaises(ValueError): w.execute(OrganizationCommand('org','same',ALICE,Formulate(access),1))
        self.assertEqual(w.checkpoint(),before)
        other=acquire(w,BOB,(BOX,),'b')
        w.execute(OrganizationCommand('bob:org','same',BOB,Formulate(other),10000))
        self.assertEqual(w._semantic_owners[ALICE],('language','same'))
        finish(w,ALICE,cmd.payload,'same')
        w.execute(OrganizationCommand('org','same',ALICE,Formulate(access),1))
        with self.assertRaises(ValueError): w.execute(LanguageCommand('other','same',ALICE,Learn('another2',access),1))
        w.execute(OrganizationCommand('alice:org:finish','same',ALICE,Formulate(access),10000)); check_world(w)

    def test_r4_r6_r8_r9_share_one_state_without_free_perspective_reset(self):
        w,p,identity=agreed(); access=acquire(w,BOB,(BOX,),'b')
        # An explicit R3 recall gives R4 a permitted account source.
        from hle.metabolism_demo import associate,CUE
        memory=w.read_revision(BOB,w._records[access].hits[0].memory)
        associate(w,memory,'r4-cue'); recall=retrieve(w,'r4-recall')
        draft=TheorizeDraft(recall,BOX,ALICE)
        w.execute(MetabolicCommand('r4:start','r4',BOB,draft,1))
        with self.assertRaises(ValueError): finish(w,BOB,Learn('new',access),'blocked')
        with self.assertRaises(ValueError): org(w,BOB,Formulate(access),'blocked-org')
        metabolic_finish(w,draft,'r4',work_limit=64)
        self.assertEqual(w.processing_state(BOB).perspective,Perspective.ITS)
        with self.assertRaises(ValueError): finish(w,BOB,Learn('new',access),'blocked')
        account=w.processing_job(BOB,'r4').result
        metabolic_finish(w,UnderstandDraft(account,'returned'),'r4-return')
        self.assertEqual(w.processing_state(BOB).perspective,Perspective.I)
        w.execute(LanguageCommand('language:start','shared',BOB,Learn('new',access),1))
        # Deliberately collide with the rendered busy string: family ownership wins.
        with self.assertRaises(ValueError): w.execute(MetabolicCommand('r4:collision','semantic:language:shared',BOB,draft,1))
        w.execute(w.send_language(ALICE,w.lexeme(ALICE,'kept').ref,BOB,'teaching'))
        obs=next(o.ref for o in w._journal[-1].observations if o.observer==BOB)
        receive=ReceiveCommand('receive:start','shared',BOB,obs,1)
        with self.assertRaises(ValueError): w.execute(receive)
        finish(w,BOB,Learn('new',access),'shared')
        w.execute(receive)
        with self.assertRaises(ValueError): finish(w,BOB,Learn('third',access),'blocked-reception')
        with self.assertRaises(ValueError): org(w,BOB,Formulate(access),'blocked-org-reception')
        with self.assertRaises(ValueError): w.execute(MetabolicCommand('r4:receive','another',BOB,draft,1))
        w.execute(replace(receive,command_id='receive:finish',work_limit=1000))
        org(w,BOB,Formulate(access),'organization-after'); check_world(w)
        cp=w.checkpoint(); from hle.organization import OrganizationWorld
        self.assertEqual(OrganizationWorld.restore(cp).checkpoint(),cp)

    def test_hidden_ownership_does_not_change_local_learning_route_or_output(self):
        from hle.world_records import Tick
        base=world(); access=acquire(base,ALICE,(BOX,),'a'); cp=base.checkpoint()
        a=LanguageWorld.restore(cp); b=LanguageWorld.restore(cp)
        a.execute(Attempt('hidden','hidden',request(ALICE,TRANSFER,(BOX,BOB))))
        b.execute(Tick('hidden'))
        for w in (a,b): finish(w,ALICE,Learn('kept',access),'learn')
        self.assertEqual(a.language_job(ALICE,'learn'),b.language_job(ALICE,'learn'))
        self.assertEqual(a.processing_state(ALICE),b.processing_state(ALICE))

    def test_route_state_and_progress_tampering_rejected_after_rehash(self):
        w=world(); access=acquire(w,ALICE,(BOX,),'a')
        w.execute(LanguageCommand('partial','learn',ALICE,Learn('kept',access),1))
        cp=loads(w.checkpoint()); tx=cp.journal[-1]
        plan=tx.job.route.plan
        variants=(replace(tx,state=replace(tx.state,active='si' if tx.state.active!='si' else 'ni')),
            replace(tx,job=replace(tx.job,paid=tx.job.paid+1)),
            replace(tx,job=replace(tx.job,route=replace(tx.job.route,plan=replace(plan,content_units=plan.content_units+1)))),
            replace(tx,job=replace(tx.job,route=replace(tx.job.route,start_state=tx.state.ref))))
        for changed in variants:
            with self.assertRaises(ValueError): LanguageWorld.restore(dumps(replace(cp,journal=cp.journal[:-1]+(changed,))))
        with self.assertRaises(AssertionError): reconstruct(w.profiles,w.policy,w.semantic_policy,cp.journal[:-1]+(variants[0],))

    def test_legacy_live_schema_is_explicitly_rejected(self):
        w=world(); cp=loads(w.checkpoint())
        with self.assertRaisesRegex(ValueError,'unsupported'): LanguageWorld.restore(dumps(replace(cp,schema='hle-r8-v1')))
