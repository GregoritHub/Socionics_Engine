import hashlib
import json
from dataclasses import replace
from pathlib import Path
import unittest

from hle.codec import dumps, loads
from hle.composition import ComposedWorld
from hle.composition_demo import complete, compose, learned_world, run_composition_demo, use, world
from hle.composition_records import (AssessCompositions, CompositionCommand,
    CompositionRevision, DeclareCompositionTest, Expectation, FoldDraft, Part, UnfoldDraft)
from hle.contracts import ClaimStatus, EvidenceStatus as E, Kind, Moment, Proposition, Ref, TimeScope, WorkStatus
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, request
from hle.memory_records import ContextDraft, MemoryCommand, WriteDraft
from hle.metabolism_demo import finish, remember_initial
from hle.metabolism_records import ApplyDraft, EmbodyDraft, TheorizeDraft
from hle.socion_demo import demand, settle
from hle.world_records import Attempt, Correction, Credit, Tick, TRANSFER
from .reference_composition import reference_report
from .support import rules


def simple():
    w=world(); m=remember_initial(w)
    r=complete(w,FoldDraft('child',(Part('fact',m.ref,ROOM),)),'fold:child').result
    return w,m,r


def declare(w,root,key='t',context=ROOM,claims=None,required=(),budget=1000):
    if claims is None: claims=(Expectation(BOX,'owned_by',ALICE),)
    w.execute(DeclareCompositionTest('declare:'+key,key,root,context,claims,required,budget))
    return Ref(Kind.ASSESSMENT,'composition-test:'+key,1)


def assess(w,test):
    w.execute(AssessCompositions('assess:'+str(len(w._journal)),max(1,len(w.pending_compositions()))))
    return w.composition_report(test)


def revise(w,m,key='box',claim=None,attitude=ClaimStatus.ENDORSED):
    draft=WriteDraft(key,m.content if claim is None else (claim,),(),attitude,m.ref,'explicit new evidence revision')
    task='revise:'+str(len(w._journal))
    w.execute(MemoryCommand(task,task,m.owner,draft,(m.ref,)))
    return w.memory_head(m.owner,key)


def check_oracle(testcase,w,report):
    expected=reference_report(w.truth.journal(),w._composition_tests[report.test],report.at)
    for field,value in expected.items(): testcase.assertEqual(getattr(report,field),value,field)


class Composition(unittest.TestCase):
    @rules('Q01','Q03','Q04')
    def test_learned_nested_capacity_changes_held_out_action(self):
        base,lesson,tool=learned_world(); results=[]
        roots={include:compose(base,lesson,tool,include,str(include)+':') for include in (False,True)}
        wallets=[]
        for include in (False,True):
            w=ComposedWorld.restore(base.checkpoint()); root=roots[include];wallets.append(w.truth.wallet(BOB))
            test=declare(w,root,claims=(Expectation(TOOL,'owned_by',BOB),),required=('inspect_before_transfer',))
            access,account,app,retained=use(w,root)
            actions=[w._records[r].request.operation for r in w._records[app.result].enactments]
            results.append(actions)
            self.assertEqual(w._records[account.result].claim.object,BOB)
            self.assertEqual(w._records[account.result].guard is not None,include)
            self.assertEqual(bool(w._records[retained.result].capabilities),include)
            report=assess(w,test);check_oracle(self,w,report)
            self.assertEqual(report.usefulness,E.ESTABLISHED if include else E.FAILED)
        self.assertEqual([x.key for x in results[0]],['r2.transfer'])
        self.assertEqual([x.key for x in results[1]],['r2.inspect','r2.transfer'])
        self.assertEqual(wallets[0],wallets[1])

    @rules('Q01')
    def test_full_unfold_preserves_records_edges_roles_and_capability(self):
        w,lesson,tool=learned_world();root=compose(w,lesson,tool)
        result=complete(w,UnfoldDraft(root,None,w.now),'full').result
        access=w.composition_record(BOB,result); records=w.unfold_records(BOB,result)
        self.assertEqual(len(access.nodes),4);self.assertEqual(len(access.edges),3)
        self.assertIn(lesson,records);self.assertIn(tool,records)
        self.assertIn(w.processing_record(BOB,lesson.capabilities[0]),records)
        self.assertEqual(tuple(r.ref for r in records),access.nodes+access.capabilities)
        with self.assertRaises(ValueError):finish(w,TheorizeDraft(result,TOOL,ALICE),'invalid-full')

    @rules('Q01','Q02')
    def test_shared_dag_preserves_two_roles_but_reads_child_once(self):
        w,m,child=simple()
        root=complete(w,FoldDraft('shared',(Part('left',child,ROOM),Part('right',child,ROOM))),'shared').result
        job=complete(w,UnfoldDraft(root,ROOM,w.now),'unfold')
        r=w.composition_record(BOB,job.result)
        self.assertEqual(len(r.nodes),3);self.assertEqual(len(r.edges),3)
        self.assertEqual([e.part.role for e in r.edges],['left','right','fact'])
        self.assertEqual(job.completed,7)

    @rules('Q01','Q06')
    def test_depth_72_has_no_programmed_depth_ceiling(self):
        w,m,root=simple()
        for depth in range(72):root=complete(w,FoldDraft(str(depth),(Part('child',root,ROOM),)),'fold:'+str(depth)).result
        job=complete(w,UnfoldDraft(root,ROOM,w.now),'deep',limit=11)
        self.assertEqual(len(w._records[job.result].nodes),74)
        self.assertEqual(job.completed,148)

    @rules('Q01','Q02')
    def test_historical_unfold_survives_child_revision(self):
        w,m,root=simple();q=UnfoldDraft(root,ROOM,w.now)
        a=complete(w,q,'before').result
        newer=revise(w,m,claim=replace(m.content[0],object=BOB))
        b=complete(w,q,'after').result
        self.assertEqual(w.unfold_records(BOB,a),w.unfold_records(BOB,b))
        self.assertNotIn(newer,w.unfold_records(BOB,b))

    @rules('Q01','Q06')
    def test_fold_roundtrip_can_reassemble_exact_parts(self):
        w,m,root=simple();original=w.composition_record(BOB,root)
        access=complete(w,UnfoldDraft(root,None,w.now),'all').result
        recovered=next(r for r in w.unfold_records(BOB,access) if r.ref==root)
        new=complete(w,FoldDraft('copy',recovered.parts),'copy').result
        self.assertEqual(w.composition_record(BOB,new).parts,original.parts)
        self.assertNotEqual(new,root)

    @rules('Q01','Q02')
    def test_foreign_unresolved_and_wrong_context_references_reject_atomically(self):
        w,m,root=simple()
        for actor,p in [(ALICE,FoldDraft('foreign',(Part('x',m.ref,ROOM),))),
                        (ALICE,UnfoldDraft(root,ROOM,w.now)),
                        (BOB,FoldDraft('missing',(Part('x',replace(m.ref,revision=99),ROOM),))),
                        (BOB,FoldDraft('context',(Part('x',m.ref,Ref(Kind.CONTEXT,'missing',1)),))),
                        (BOB,UnfoldDraft(root,ROOM,Moment(99999,0)))]:
            before=w.checkpoint()
            with self.assertRaises(ValueError):w.execute(CompositionCommand('bad','bad',actor,p))
            self.assertEqual(w.checkpoint(),before)

    @rules('Q01')
    def test_forward_self_reference_rejects_but_past_revision_can_be_constituent(self):
        w,m,root=simple();before=w.checkpoint()
        with self.assertRaises(ValueError):complete(w,FoldDraft('child',(Part('cycle',replace(root,revision=2),ROOM),),root),'bad')
        self.assertEqual(w.checkpoint(),before)
        newer=complete(w,FoldDraft('child',(Part('previous',root,ROOM),),root),'old-self').result
        a=complete(w,UnfoldDraft(newer,ROOM,w.now),'unfold').result
        self.assertEqual(len(w._records[a].nodes),3)

    @rules('Q01')
    def test_duplicate_role_context_and_empty_composition_reject(self):
        w,m,root=simple();p=Part('same',m.ref,ROOM)
        with self.assertRaises(ValueError):FoldDraft('empty',())
        with self.assertRaises(ValueError):FoldDraft('duplicate',(p,p))

    @rules('Q02','Q05')
    def test_same_child_in_different_contexts_filters_without_relabeling(self):
        w,m,_=simple()
        w.execute(MemoryCommand('ctx','ctx',BOB,ContextDraft('other','other scenario')))
        other=Ref(Kind.CONTEXT,'memory-context:3:bob:1:other',1)
        p=replace(m.content[0],context=other,object=BOB)
        w.execute(MemoryCommand('other-m','other-m',BOB,WriteDraft('other',(p,),(),ClaimStatus.ENDORSED,None,'context fixture'),(m.ref,)))
        n=w.memory_head(BOB,'other')
        shared=complete(w,FoldDraft('shared',(Part('fact',m.ref,ROOM),Part('fact',n.ref,other))),'fold:shared').result
        root=complete(w,FoldDraft('contexts',(Part('shared',shared,ROOM),Part('shared',shared,other))),'fold:contexts').result
        tests=[declare(w,root,'room'),declare(w,root,'other',other,(Expectation(BOX,'owned_by',BOB),))]
        for context,expected in ((ROOM,m),(other,n)):
            access=complete(w,UnfoldDraft(root,context,w.now),'access:'+context.key).result
            self.assertEqual(w._records[access].hits[0].memory,expected.ref)
            self.assertEqual(w.read_revision(BOB,expected.ref).content[0].context,context)
        a=assess(w,tests[0]);b=w.composition_report(tests[1]);check_oracle(self,w,a);check_oracle(self,w,b)
        revise(w,n,'other',replace(p,object=ALICE))
        self.assertEqual(w.pending_compositions(),(tests[1],))
        self.assertTrue(w.composition_report_is_current(a))

    @rules('Q02','Q04')
    def test_empty_context_is_missing_evidence_not_success(self):
        w,m,root=simple()
        w.execute(MemoryCommand('ctx','ctx',BOB,ContextDraft('empty','empty')))
        context=Ref(Kind.CONTEXT,'memory-context:3:bob:1:empty',1)
        t=declare(w,root,context=context)
        r=assess(w,t)
        self.assertEqual((r.agreement,r.cross_level,r.identity,r.factual),(E.UNASSESSED,)*4)

    @rules('Q03','Q04')
    def test_factual_truth_does_not_leak_into_access_or_account(self):
        w,m,root=simple();event=w.execute(Attempt('give','give',request(ALICE,TRANSFER,(BOX,BOB))))
        a=ComposedWorld.restore(w.checkpoint());b=ComposedWorld.restore(w.checkpoint())
        a.execute(Correction('hidden',event.ref,ALICE,'hidden matched intervention'));b.execute(Tick('time'))
        for c in (a,b):
            access=complete(c,UnfoldDraft(root,ROOM,c.now),'access')
            finish(c,TheorizeDraft(access.result,BOX,ALICE),'account')
        self.assertEqual(a.processing_record(BOB,a.processing_job(BOB,'account').result),b.processing_record(BOB,b.processing_job(BOB,'account').result))

    @rules('Q04')
    def test_cross_level_counterexample_has_intact_lower_identity(self):
        w,m,root=simple();t=declare(w,root,claims=(Expectation(BOX,'owned_by',BOB),))
        complete(w,UnfoldDraft(root,ROOM,w.now),'access');r=assess(w,t)
        self.assertEqual((r.identity,r.freshness,r.factual),(E.ESTABLISHED,)*3)
        self.assertEqual((r.agreement,r.cross_level),(E.FAILED,)*2);check_oracle(self,w,r)

    @rules('Q04')
    def test_equal_time_conflict_is_not_resolved_by_order(self):
        for reverse in (False,True):
            w,m,root=simple();p=replace(m.content[0],object=BOB)
            w.execute(MemoryCommand('conflict','conflict',BOB,WriteDraft('conflict',(p,),(),ClaimStatus.ENDORSED,None,'counterexample'),(m.ref,)))
            n=w.memory_head(BOB,'conflict');parts=(Part('a',m.ref,ROOM),Part('b',n.ref,ROOM))
            root=complete(w,FoldDraft('conflicted',parts[::-1] if reverse else parts),'fold:conflict').result
            t=declare(w,root);r=assess(w,t)
            self.assertEqual(r.agreement,E.FAILED)
            access=complete(w,UnfoldDraft(root,ROOM,w.now),'access').result
            account=finish(w,TheorizeDraft(access,BOX,ALICE),'theorize')
            self.assertIsNone(w._records[account.result].claim)

    @rules('Q04')
    def test_missing_tested_use_and_general_closure_stay_unassessed(self):
        w,m,root=simple();r=assess(w,declare(w,root))
        self.assertEqual((r.identity,r.path,r.usefulness,r.closure),(E.UNASSESSED,)*4)

    @rules('Q04')
    def test_endpoint_capacity_success_does_not_erase_cost_failure(self):
        w,lesson,tool=learned_world();root=compose(w,lesson,tool)
        t=declare(w,root,claims=(),required=('inspect_before_transfer',),budget=1)
        use(w,root);r=assess(w,t)
        self.assertEqual(r.usefulness,E.ESTABLISHED);self.assertEqual(r.path,E.FAILED)
        check_oracle(self,w,r)

    @rules('Q04','Q05')
    def test_failed_use_stays_in_family_after_later_success(self):
        w,lesson,tool=learned_world();root=compose(w,lesson,tool)
        t=declare(w,root,claims=(),required=('inspect_before_transfer',))
        # BOX belongs to Alice, so Bob can inspect but cannot complete transfer.
        use(w,root,'no-transfer',BOX);first=assess(w,t)
        self.assertEqual(first.usefulness,E.FAILED)
        use(w,root,'works',TOOL);second=assess(w,t)
        self.assertEqual(second.usefulness,E.FAILED);self.assertEqual(len(second.uses),2)
        self.assertEqual(w._records[first.ref],first);check_oracle(self,w,second)

    @rules('Q04','Q05')
    def test_definition_change_preserves_prior_failed_test(self):
        w,m,root=simple();bad=declare(w,root,'bad',claims=(Expectation(BOX,'owned_by',BOB),))
        prior=assess(w,bad);good=declare(w,root,'good');now=assess(w,good)
        self.assertEqual(prior.agreement,E.FAILED);self.assertEqual(now.agreement,E.ESTABLISHED)
        self.assertEqual(w._records[prior.ref],prior)
        with self.assertRaises(ValueError):declare(w,root,'bad')

    @rules('Q05')
    def test_child_revision_invalidates_ancestors_and_requires_explicit_refresh(self):
        w,m,child=simple();root=complete(w,FoldDraft('parent',(Part('child',child,ROOM),)),'parent').result
        t=declare(w,root);old=assess(w,t)
        newer=revise(w,m,claim=replace(m.content[0],object=BOB))
        self.assertFalse(w.composition_report_is_current(old));self.assertEqual(w.pending_compositions(),(t,))
        r=assess(w,t);self.assertIn(m.ref,r.stale);self.assertEqual(r.cross_level,E.FAILED);check_oracle(self,w,r)
        child2=complete(w,FoldDraft('child',(Part('fact',newer.ref,ROOM),),child),'child2').result
        self.assertEqual(assess(w,t).cross_level,E.FAILED)
        root2=complete(w,FoldDraft('parent',(Part('child',child2,ROOM),),root),'parent2').result
        t2=declare(w,root2,'updated',claims=(Expectation(BOX,'owned_by',BOB),));r2=assess(w,t2)
        self.assertEqual(r2.cross_level,E.ESTABLISHED);self.assertEqual(r2.factual,E.FAILED)

    @rules('Q05')
    def test_world_change_invalidates_factual_report_without_rewriting_child(self):
        w,m,root=simple();t=declare(w,root);old=assess(w,t)
        w.execute(Attempt('give','give',request(ALICE,TRANSFER,(BOX,BOB))))
        self.assertFalse(w.composition_report_is_current(old))
        r=assess(w,t);self.assertEqual(r.factual,E.FAILED);self.assertEqual(r.cross_level,E.ESTABLISHED)
        check_oracle(self,w,r)

    @rules('Q02','Q05')
    def test_scope_boundary_invalidates_selected_claim(self):
        w,m,root=simple();end=Moment(w.now.tick+12,0)
        newer=revise(w,m,claim=replace(m.content[0],scope=TimeScope(Moment(0,0),end)))
        root=complete(w,FoldDraft('scoped',(Part('fact',newer.ref,ROOM),)),'scoped').result
        t=declare(w,root);a=assess(w,t)
        while w.now<end:w.execute(Tick('tick:'+str(w.now.tick)))
        self.assertFalse(w.composition_report_is_current(a))
        b=assess(w,t);self.assertEqual(b.agreement,E.UNASSESSED);check_oracle(self,w,b)

    @rules('Q05')
    def test_no_journal_or_unrelated_test_scan_on_invalidation(self):
        w,m,root=simple();t=declare(w,root)
        tool=remember_initial(w,'tool',TOOL)
        u=complete(w,FoldDraft('unrelated',(Part('tool',tool.ref,ROOM),)),'unrelated').result
        other=declare(w,u,'unrelated',claims=(Expectation(TOOL,'owned_by',BOB),));assess(w,t)
        untouched=w.composition_report(other)
        class NoIteration(list):
            def __iter__(self):raise AssertionError('runtime scanned journal')
        class NoScan(dict):
            def __iter__(self):raise AssertionError('runtime scanned all tests')
            def values(self):raise AssertionError('runtime scanned all tests')
            def items(self):raise AssertionError('runtime scanned all tests')
        w._journal=NoIteration(w._journal);w._composition_tests=NoScan(w._composition_tests)
        before=w.invalidation_visits;revise(w,m)
        self.assertEqual(w.pending_compositions(),(t,));self.assertEqual(w.invalidation_visits-before,2)
        assess(w,t);self.assertTrue(w.composition_report_is_current(untouched))

    @rules('Q05','Q06')
    def test_assessment_limit_and_queue_restore_exactly(self):
        w,m,root=simple();a=declare(w,root,'a');b=declare(w,root,'b')
        w.execute(AssessCompositions('one',1));self.assertEqual(len(w.pending_compositions()),1)
        clone=ComposedWorld.restore(w.checkpoint())
        for c in (w,clone):c.execute(AssessCompositions('two',1))
        self.assertEqual(w.checkpoint(),clone.checkpoint());self.assertFalse(w.pending_compositions())

    @rules('Q06')
    def test_partial_unfold_preserves_exact_paid_frontier_and_charges(self):
        w,m,root=simple();before=w._spent[BOB];p=UnfoldDraft(root,ROOM,w.now)
        w.execute(CompositionCommand('first','access',BOB,p,1));job=w.composition_job(BOB,'access')
        self.assertIsNone(job.result);self.assertEqual(job.node_paid,1);self.assertFalse(job.nodes)
        clone=ComposedWorld.restore(w.checkpoint())
        for c in (w,clone):c.execute(CompositionCommand('finish','access',BOB,p,100))
        self.assertEqual(w._spent[BOB]-before,4);self.assertEqual(w.checkpoint(),clone.checkpoint())

    @rules('Q06')
    def test_independent_energy_time_shortage_and_refill(self):
        for energy,time in ((0,10),(10,0),(1,10),(10,1)):
            w,m,root=simple()
            # Spend down through explicit paid operations; no direct wallet mutation.
            balance=w.truth.wallet(BOB)
            # A new world with an adjusted genesis is replayed only up to this same small preparation.
            required=5000-balance.energy
            c=world(required+energy,required+time);m2=remember_initial(c)
            r2=complete(c,FoldDraft('child',(Part('fact',m2.ref,ROOM),)),'fold:child').result
            p=UnfoldDraft(r2,ROOM,c.now)
            c.execute(CompositionCommand('access:0','access',BOB,p))
            job=c.composition_job(BOB,'access');self.assertIsNone(job.result)
            self.assertEqual(job.completed,min(energy,time))
            clone=ComposedWorld.restore(c.checkpoint())
            for q in (c,clone):
                q.execute(Credit('refill',BOB,10,10,'explicit resource control'))
                q.execute(CompositionCommand('access:1','access',BOB,p))
                self.assertEqual(q.composition_job(BOB,'access').completed,4)
            self.assertEqual(c.checkpoint(),clone.checkpoint())

    @rules('Q06')
    def test_duplicate_command_is_idempotent_and_changed_resume_rejects(self):
        w,m,root=simple();p=UnfoldDraft(root,ROOM,w.now);cmd=CompositionCommand('a','a',BOB,p,1)
        w.execute(cmd);before=w.checkpoint();w.execute(cmd);self.assertEqual(before,w.checkpoint())
        for bad in (replace(cmd,payload=replace(p,context=None)),replace(cmd,command_id='b',payload=replace(p,context=None))):
            with self.assertRaises(ValueError):w.execute(bad)
            self.assertEqual(before,w.checkpoint())

    @rules('Q06')
    def test_competing_fold_revision_fails_after_paid_work(self):
        w,m,root=simple();parts=(Part('changed',m.ref,ROOM),);p=FoldDraft('child',parts,root)
        w.execute(CompositionCommand('partial','slow',BOB,p,1));before=w._spent[BOB]
        newer=complete(w,p,'winner').result
        w.execute(CompositionCommand('resume','slow',BOB,p,10))
        self.assertEqual(w.composition_job(BOB,'slow').outcome,WorkStatus.FAILED)
        self.assertEqual(w.composition_head(BOB,'child').ref,newer)
        self.assertEqual(w._spent[BOB]-before,3)

    @rules('Q06')
    def test_historical_access_continuation_does_not_retarget_new_child(self):
        w,m,root=simple();p=UnfoldDraft(root,ROOM,w.now)
        w.execute(CompositionCommand('first','access',BOB,p,2))
        revised=revise(w,m,claim=replace(m.content[0],object=BOB))
        w.execute(CompositionCommand('last','access',BOB,p,100))
        r=w._records[w.composition_job(BOB,'access').result]
        self.assertEqual(r.hits[0].memory,m.ref);self.assertNotIn(revised.ref,r.nodes)

    @rules('Q06')
    def test_every_demo_prefix_restores_and_reproduces_next_transaction(self):
        w,_=run_composition_demo();cp=loads(w.checkpoint())
        for n in range(1,len(cp.journal)):
            c=ComposedWorld.restore(dumps(replace(cp,journal=cp.journal[:n])))
            c.execute(cp.journal[n].command)
            self.assertEqual(c._journal[-1],cp.journal[n])
        self.assertEqual(ComposedWorld.restore(w.checkpoint()).checkpoint(),w.checkpoint())

    @rules('Q06')
    def test_rehashed_semantic_tampering_and_duplicate_journal_reject(self):
        w,m,root=simple();cp=loads(w.checkpoint());tx=cp.journal[-1]
        node=tx.extra[0];bad=replace(node,parts=(replace(node.parts[0],role='silently changed'),))
        changed=replace(cp,journal=cp.journal[:-1]+(replace(tx,extra=(bad,)),))
        with self.assertRaises(ValueError):ComposedWorld.restore(dumps(changed))
        with self.assertRaises(ValueError):ComposedWorld.restore(dumps(replace(cp,journal=cp.journal+(tx,))))

    @rules('Q03','Q06')
    def test_partial_crux_use_after_unfold_continues_exactly(self):
        w,lesson,tool=learned_world();root=compose(w,lesson,tool)
        access=complete(w,UnfoldDraft(root,ROOM,w.now),'access').result
        from hle.metabolism_records import MetabolicCommand
        p=TheorizeDraft(access,TOOL,ALICE)
        w.execute(MetabolicCommand('t0','t',BOB,p,1));c=ComposedWorld.restore(w.checkpoint())
        for candidate in (w,c):
            candidate.execute(MetabolicCommand('t1','t',BOB,p,200))
            app=finish(candidate,ApplyDraft(candidate.processing_job(BOB,'t').result),'app')
            finish(candidate,EmbodyDraft(app.result,'retained'),'embody')
        self.assertEqual(w.checkpoint(),c.checkpoint())

    @rules('Q03','Q07')
    def test_r6_policy_exchange_still_runs_in_composed_world(self):
        w=world();settle(w)
        first=demand(w,'out',ALICE,BOX,BOB);second=demand(w,'back',BOB,BOX,ALICE)
        self.assertIsNotNone(first);self.assertIsNotNone(second)
        self.assertEqual(w.truth.current_fact(BOX,'owned_by',ROOM).object,ALICE)
        self.assertEqual(ComposedWorld.restore(w.checkpoint()).checkpoint(),w.checkpoint())

    @rules('Q07')
    def test_inherited_runtime_tests_and_references_unchanged(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'docs/inherited_R6_sha256.json').read_text())
        # R11 factors the unchanged funded-hop rule into processing.route_active.
        # Historical hashes stay intact; the changes are audited in docs/r11/inherited_changes.md.
        exceptions={'hle/codec.py','hle/__init__.py','hle/__main__.py',
                    'hle/processing.py','hle/metabolism.py','hle/socion.py'}
        for name,digest in manifest.items():
            if name not in exceptions:self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest,name)

    @rules('Q04','Q07')
    def test_evaluator_reports_are_not_participant_records(self):
        w,m,root=simple();before=w.select_input(BOB)[0]
        r=assess(w,declare(w,root));after=w.select_input(BOB)[0]
        self.assertEqual(before.observations,after.observations)
        self.assertEqual(before.own_memories,after.own_memories)
        self.assertNotIn(r.ref,w._known[BOB])
        with self.assertRaises(ValueError):w.composition_record(BOB,r.ref)

    @rules('Q01','Q02')
    def test_retracted_memory_preserves_structure_but_supplies_no_claim(self):
        w,m,root=simple();m2=revise(w,m,attitude=ClaimStatus.RETRACTED)
        r=complete(w,FoldDraft('retracted',(Part('fact',m2.ref,ROOM),)),'new').result
        t=declare(w,r);report=assess(w,t);self.assertEqual(report.agreement,E.UNASSESSED)
        access=complete(w,UnfoldDraft(r,ROOM,w.now),'access').result
        account=finish(w,TheorizeDraft(access,BOX,ALICE),'account')
        self.assertIsNone(w._records[account.result].claim)

    @rules('Q04','Q05')
    def test_every_demo_report_matches_offline_reconstruction(self):
        w,_=run_composition_demo()
        for tx in w.truth.journal():
            for r in getattr(tx,'extra',()):
                if type(r).__name__=='CompositionReport':check_oracle(self,w,r)

    @rules('Q04')
    def test_assessment_declared_after_access_cannot_claim_prior_use(self):
        w,lesson,tool=learned_world();root=compose(w,lesson,tool)
        use(w,root)
        t=declare(w,root,claims=(),required=('inspect_before_transfer',))
        r=assess(w,t)
        self.assertEqual(r.accesses,());self.assertEqual(r.uses,())
        self.assertEqual(r.usefulness,E.UNASSESSED)

    @rules('Q06')
    def test_tampered_unfold_and_report_reject_even_with_new_checksum(self):
        w,m,root=simple();declare(w,root)
        complete(w,UnfoldDraft(root,ROOM,w.now),'access');assess(w,Ref(Kind.ASSESSMENT,'composition-test:t',1))
        cp=loads(w.checkpoint())
        for typ in ('UnfoldResult','CompositionReport'):
            i=next(i for i,t in enumerate(cp.journal) if any(type(r).__name__==typ for r in getattr(t,'extra',())))
            tx=cp.journal[i];r=tx.extra[0]
            bad=replace(r,nodes=r.nodes[:-1]) if typ=='UnfoldResult' else replace(r,agreement=E.FAILED)
            altered=replace(cp,journal=cp.journal[:i]+(replace(tx,extra=(bad,)),)+cp.journal[i+1:])
            with self.assertRaises(ValueError):ComposedWorld.restore(dumps(altered))

    @rules('Q04')
    def test_greater_budget_has_own_identity_without_erasing_failed_path(self):
        w,lesson,tool=learned_world();root=compose(w,lesson,tool)
        low=declare(w,root,'low',claims=(),required=('inspect_before_transfer',),budget=1)
        high=declare(w,root,'high',claims=(),required=('inspect_before_transfer',),budget=1000)
        use(w,root);a=assess(w,low);b=w.composition_report(high)
        self.assertEqual(a.path,E.FAILED);self.assertEqual(b.path,E.ESTABLISHED)
        self.assertEqual(a.uses,b.uses);self.assertEqual(a.usefulness,b.usefulness)


if __name__=='__main__':unittest.main()
