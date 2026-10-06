import unittest
from copy import deepcopy
from dataclasses import replace
from .fixtures import *
from hle_unified.selection_audit import audit
from hle_unified.selection_policy import choose,proposals
from hle_unified.selection_records import dumps
from hle_unified.compact import seal,unseal

class SelectionTests(unittest.TestCase):
    def test_all_32_automatic_cells_have_native_consumers_and_raw_audit(self):
        for name in NAMES:
            for face in FACES:
                with self.subTest(name=name,face=face):
                    e,r,d,later=witness(name,face)
                    self.assertEqual(audit(e.world.journal(),e.access.checkpoint())['c6_selections'],1)
                    self.assertFalse(d['completion_claim']);self.assertTrue(later.get('ref'))
    def test_goal_contract_refuses_route_instructions(self):
        from hle_unified.selection_records import demand_value
        with self.assertRaises(ValueError):demand_value(dict(kind='need',route='Theorize'))
        self.assertNotIn('recipe',SelectionRequest.__dataclass_fields__)
    def test_unpaid_selection_cannot_launch(self):
        e,r=fixture('Theorize','accumulation');e.start('start',r)
        with self.assertRaises(ValueError):e.commit('unpaid',ALICE,r.key)
        self.assertNotIn((ALICE,r.key+':movement'),e._jobs)
    def test_partial_selection_and_child_resume_exactly(self):
        for name,face in [('Theorize','expenditure'),('Commune','expenditure'),('Act','accumulation'),('Institutionalize','expenditure')]:
            for boundary in (0,1,2):
                with self.subTest(name=name,boundary=boundary):
                    e,r=fixture(name,face)
                    for i in range(boundary):e.participate('initial-'+str(i),r)
                    e.participate('partial',r,1);restored=SelectionEngine.restore(e.checkpoint())
                    for i in range(8):
                        a=e.participate('continue-'+str(i),r,1000000);b=restored.participate('continue-'+str(i),r,1000000)
                        self.assertEqual(a,b)
                        if a is None:break
                    self.assertEqual(e.checkpoint(),restored.checkpoint())
                    self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])
    def test_cancelled_selection_keeps_spending_and_no_child(self):
        e,r=fixture('Theorize','accumulation');e.start('start',r);e.advance('partial',ALICE,r.key,2);e.cancel('cancel',ALICE,r.key)
        self.assertEqual(e.job_status(ALICE,r.key)['spent'],2);self.assertNotIn((ALICE,r.key+':admission'),e._jobs)
        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])
    def test_exhaustion_retains_partial_work_without_launch(self):
        from hle_unified.compact import ValuePool
        from hle_unified.selection_records import registry
        from hle_unified import codec
        e,r=fixture('Theorize','accumulation')
        raw=unseal(e.checkpoint(),e.SCHEMA);original=OperationStore.restore(raw['initial']);initial=OperationStore()
        spent=200000-e.wallet(ALICE)['energy'];budget=spent+2
        for tx in original.journal():
            vs=[]
            for v in tx.versions:
                d=attrs(v)
                if d.get('record_type')=='wallet' and d.get('actor')==ALICE:
                    v=replace(v,attributes=attributes(dict(d,energy=budget,time=budget,initial_energy=budget,initial_time=budget)))
                vs.append(v)
            initial.create(tx.key,tx.writer,tuple(vs))
        low=SelectionEngine(initial,codec.decode(raw['law']));pool=ValuePool(registry());pool.load_nodes(raw['nodes'])
        for token in raw['commands']:
            command,expected=pool.get(pool.import_token(token));self.assertEqual(low._execute(command),expected)
        low.start('select',r);low.advance('exhaust',ALICE,r.key,1000000)
        self.assertEqual(low.wallet(ALICE)['energy'],0);self.assertEqual(low.job_status(ALICE,r.key)['status'],'partial')
        self.assertEqual(low.job_status(ALICE,r.key)['spent'],2);self.assertNotIn((ALICE,r.key+':admission'),low._jobs)
        self.assertEqual(low.checkpoint(),SelectionEngine.restore(low.checkpoint()).checkpoint())
        self.assertTrue(audit(low.world.journal(),low.access.checkpoint())['passed'])
    def test_pending_delivery_does_not_become_processed_evidence(self):
        e,r=fixture('Theorize','accumulation')
        event=perform(e,OperationRequest('not-received',ALICE,'inspect',ROOM,target=SUPPLY,evidence=evidence(e,ALICE,SUPPLY)),limit=100000)
        e.start('select',r);e.advance('paid',ALICE,r.key,1000000)
        e.deliver_event('pending',event,ALICE)
        e.commit('commit',ALICE,r.key)
        decision=attrs(e.world.resolve(address('c6.decision',ALICE,r.key)))
        self.assertIsNone(decision['failure']);self.assertIsNotNone(decision['admission'])
    def test_hidden_material_change_does_not_change_predelivery_selection(self):
        e,r=fixture('Express','expenditure');before=e.selection_view(r);wanted=choose(proposals(before))
        # Simulator-only lawful change; participant receives no observation.
        perform(e,OperationRequest('undelivered-consumption',ALICE,'consume',ROOM,stock=SUPPLY,amount=4,evidence=evidence(e,ALICE,SUPPLY)),limit=100000)
        after=e.selection_view(r);self.assertEqual(before['stock'],after['stock']);self.assertEqual(before['items'],after['items']);self.assertEqual(wanted,choose(proposals(after)))
    def test_new_owned_observation_changes_competing_route(self):
        e,r=fixture('Understand','expenditure');prior=choose(proposals(e.selection_view(r)))
        self.assertEqual(prior['name'],'Understand')
        inspect(e,'new-experience');later=choose(proposals(e.selection_view(r)))
        self.assertEqual(later['name'],'Embody')
        self.assertNotEqual(prior['inputs'],later['inputs'])
    def test_actual_acquired_repair_enables_held_out_target(self):
        e=setup(generate=False,engine_type=SelectionEngine);dev.supply8(e,'neutral')
        for obj in (SAW,KIT,STOCK):expose(e,ALICE,obj)
        demand=need(e,'repair-need',weights=(0,10,0,0),scope='condition')
        r=SelectionRequest('learned',ALICE,ROOM,CUE5,SAW,demand,tool=KIT,repair_stock=STOCK,procedure=REPAIR,peer=BOB)
        self.assertIsNone(choose(proposals(e.selection_view(r))))
        training(e);chosen=choose(proposals(e.selection_view(r)));self.assertEqual(chosen['recipe'],'act-accumulation-v1')
        e,d=finish_selection(e,r);self.assertEqual(e.job_status(ALICE,r.key+':movement')['status'],'succeeded')
        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])
    def test_context_transfer_uses_local_limits_without_importing_authority(self):
        for cap in (1,4):
            e,r,d,out,later,source,obs=transfer_witness(cap)
            self.assertEqual(d['recipe'],'context-transfer-v1');self.assertEqual(later['amount'],cap)
            self.assertEqual(out['source_context'],ROOM);self.assertIsNone(out['authority']);self.assertFalse(out['competence'])
            self.assertIn(obs,out['local_evidence']);self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])
    def test_context_transfer_absent_without_actual_local_evidence(self):
        e,r,d,out,later,source,obs=transfer_witness(1,False)
        self.assertEqual(d['recipe'],'theorize-accumulation-v1');self.assertNotIn('source_context',out)
    def test_other_context_does_not_inherit_practiced_skill(self):
        e,r,_,_=transfer_fixture();training(e)
        s=e.selection_view(replace(r,procedure=REPAIR));self.assertEqual(s['acquired'],())
    def test_foreign_demand_cannot_select_for_actor(self):
        e,r=fixture('Theorize','accumulation');b=need(e,'bob-need',actor=BOB)
        with self.assertRaises(ValueError):e.start('foreign',replace(r,demand=b))
    def test_labels_and_candidate_order_do_not_determine_choice(self):
        e,r=fixture('Share','expenditure');rows=proposals(e.selection_view(r));w=choose(rows)
        other=[dict(x,name='renamed',recipe='label-only') for x in reversed(rows)]
        z=choose(other);self.assertEqual((z['cell'],z['inputs'],z['score']),(w['cell'],w['inputs'],w['score']))
    def test_search_budget_discloses_deferred_alternatives(self):
        e,r=fixture('Theorize','accumulation')
        for i in range(6):seed_intent(e,'more-'+str(i),cap=i+1)
        rows=proposals(e.selection_view(replace(r,alternatives=2)))
        self.assertTrue(any(x['deferred'] for x in rows));self.assertTrue(all(x['examined']<=2 for x in rows))
    def test_automatic_selection_does_not_bypass_shell(self):
        e,r=fixture('Theorize','accumulation',generate=True);dev.generated(e);dev.supply8(e,'new-neutral')
        e,d=finish_selection(e,r);job=e.job_status(ALICE,r.key+':movement')
        self.assertEqual(job['status'],'cancelled');self.assertEqual(job['steps_completed'],1)
        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])
    def test_raw_auditor_rejects_choice_and_input_tampering(self):
        e,r,d,l=witness('Theorize','accumulation');txs=e.world.journal()
        def corrupted(namespace,fn):
            return tuple(replace(t,versions=tuple(replace(v,attributes=attributes(fn(attrs(v)))) if v.ref.identity.namespace==namespace else v for v in t.versions)) for t in txs)
        with self.assertRaises(ValueError):audit(corrupted('c6.decision',lambda d:dict(d,selected=0)),e.access.checkpoint())
        def corrupt(d):
            s=loads(d['payload']);s['stock']['quantity']=999;return dict(payload=dumps(s))
        with self.assertRaises(ValueError):audit(corrupted('c6.snapshot',corrupt),e.access.checkpoint())
        def score(d):
            rows=loads(d['payload']);rows[6]['score']+=1;return dict(payload=dumps(rows))
        with self.assertRaises(ValueError):audit(corrupted('c6.candidates',score),e.access.checkpoint())
    def test_c5_upgrade_preserves_exact_world_and_access(self):
        old=setup(generate=False);new=SelectionEngine.from_c5(old.checkpoint())
        self.assertEqual(old.world.checkpoint(),new.world.checkpoint());self.assertEqual(old.access.checkpoint(),new.access.checkpoint())
