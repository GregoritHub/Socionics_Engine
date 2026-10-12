import gzip,json,unittest
from pathlib import Path
from dataclasses import replace
from hle.model_a import TYPES,element_at
from hle_unified.energy import payment
from hle_unified.energy_audit import cumulative_energy
from hle_unified.material import attrs,attributes
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine as Engine
from tests_workflow_selection.final_fixtures import final_fixture,finish,audit
from .fixtures import factory

class EnergyTests(unittest.TestCase):
    def test_table_all_types_positions_offsets_and_quanta(self):
        times=(1,2,3,4,4,3,2,1);energy=(1,1,3,3,2,4,4,2)
        for tim in TYPES:
            for seat in range(1,9):
                for size in (1,3):
                    t=times[seat-1]*size;en=energy[seat-1]*size
                    d={'tim':tim,'route_count':1,'recall_units':2,'required':2+t+2,'completed':0,
                       'route.0.element':element_at(tim,seat),'route.0.content_units':t}
                    w={'energy':100,'time':100};total=0
                    for at in range(d['required']):
                        d['completed']=at
                        paid,cost=payment(d,w,1)
                        self.assertEqual(paid,1)
                        self.assertEqual(cost,1 if at<2 or at>=2+t else en if at==2 else 0)
                        self.assertEqual(cost,cumulative_energy(d,at+1)-cumulative_energy(d,at))
                        w['energy']-=cost;w['time']-=paid;total+=cost
                    self.assertEqual(total,4+en)
                    d['completed']=0
                    self.assertEqual(payment(d,{'energy':100,'time':100},100),(d['required'],4+en))
                    d['completed']=2
                    self.assertEqual(payment(d,{'energy':en-1,'time':100},1),(0,0))
                    self.assertEqual(payment(d,{'energy':en,'time':0},1),(0,0))
                    if t>1:
                        d['completed']=3
                        self.assertEqual(payment(d,{'energy':0,'time':100},100),(t-1,0))

    def test_creation_identity_legacy_bytes_and_checkpoint(self):
        default,r,_=final_fixture('Contemplate','accumulation')
        explicit,s,_=final_fixture('Contemplate','accumulation',factory('legacy-r4'))
        self.assertEqual(default.checkpoint(),explicit.checkpoint())
        self.assertEqual(default.resource_model,'legacy-r4')
        with self.assertRaises(AttributeError):default.resource_model='grade-v1'
        with self.assertRaises(ValueError):Engine.create(default.world,default.law,resource_model='grade-v1')
        grade,q,_=final_fixture('Contemplate','accumulation',factory('grade-v1'))
        finish(grade,q)
        restored=Engine.restore(grade.checkpoint())
        self.assertEqual(restored.resource_model,'grade-v1')
        self.assertEqual(restored.checkpoint(),grade.checkpoint())
        result=audit(grade.world.journal(),grade.access.checkpoint())
        self.assertNotEqual(result['charged_energy'],result['charged_time'])

    def test_preextension_legacy_checkpoint_bytes_and_audit(self):
        root=Path(__file__).resolve().parents[1]/'evidence/FB7.1/legacy-checkpoint'
        text=gzip.decompress((root/'partial.json.gz').read_bytes()).decode()
        e=Engine.restore(text)
        self.assertEqual(e.checkpoint(),text)
        self.assertEqual(audit(e.world.journal(),e.access.checkpoint()),json.loads((root/'audit.json').read_text()))

    def test_every_time_boundary_resume_and_cancellation(self):
        e,r,_=final_fixture('Contemplate','accumulation',factory('grade-v1'))
        finish(e,r)
        base,s,_=final_fixture('Contemplate','accumulation',factory('grade-v1'))
        base.start('start',s)
        # Selection first, then native child; exact replay at each paid offset.
        i=0
        for key in (s.key,s.key+':movement'):
            while base.job_status(s.actor,key)['status']!='ready':
                base.advance('pay-'+str(i),s.actor,key,1);i+=1
                restored=Engine.restore(base.checkpoint())
                self.assertEqual(restored.checkpoint(),base.checkpoint())
            base.commit('commit-'+key,s.actor,key)
        audit(base.world.journal(),base.access.checkpoint())
        cancelled,t,_=final_fixture('Contemplate','accumulation',factory('grade-v1'))
        cancelled.start('start',t);cancelled.advance('pay',t.actor,t.key,1)
        before=cancelled.wallet(t.actor)
        cancelled.cancel('cancel',t.actor,t.key)
        self.assertEqual(cancelled.wallet(t.actor),before)
        audit(cancelled.world.journal(),cancelled.access.checkpoint())

    def test_forged_energy_model_type_and_refund_rejected(self):
        e,r,_=final_fixture('Contemplate','accumulation',factory('grade-v1'));finish(e,r)
        txs=e.world.journal()
        for kind in ('energy','model','tim'):
            changed=[];done=False
            for tx in txs:
                versions=[]
                for v in tx.versions:
                    d=attrs(v)
                    if not done and ((kind in ('energy','model') and d.get('record_type')=='wallet' and v.ref.revision>1)
                                     or (kind=='tim' and 'route_count' in d)):
                        if kind=='energy':d['energy']+=1
                        elif kind=='model':d.pop('resource_model')
                        else:d['tim']='sli' if d['tim']!='sli' else 'iee'
                        v=replace(v,attributes=attributes(d));done=True
                    versions.append(v)
                changed.append(replace(tx,versions=tuple(versions)))
            self.assertTrue(done)
            with self.assertRaises(ValueError):audit(tuple(changed),e.access.checkpoint())

    def test_actual_prepaid_exhaustion_and_cancel_preserve_energy(self):
        from hle_unified.energy_audit import blocks
        e,r,_=final_fixture('Contemplate','accumulation',factory('grade-v1'))
        e.start('comparison',r);e.advance('compare-pay',r.actor,r.key,10000);e.commit('compare-commit',r.actor,r.key)
        key=r.key+':movement';d=e.job_status(r.actor,key)
        first=next(b for b in blocks(d) if b[2] is not None)
        used=200000-e.wallet(r.actor)['energy']
        exact=used+first[0]+first[2]
        q,s,_=final_fixture('Contemplate','accumulation',factory('grade-v1',energy=exact))
        q.start('comparison',s);q.advance('compare-pay',s.actor,s.key,10000);q.commit('compare-commit',s.actor,s.key)
        q.advance('paid-entry',s.actor,key,first[0]+1)
        self.assertEqual(q.wallet(s.actor)['energy'],0)
        if first[1]>first[0]+1:
            self.assertFalse(q.resource_exhausted(s.actor,key))
            q.advance('finish-prepaid',s.actor,key,100000)
        self.assertEqual(q.job_status(s.actor,key)['completed'],first[1])
        self.assertTrue(q.resource_exhausted(s.actor,key))
        restored=Engine.restore(q.checkpoint());self.assertEqual(restored.checkpoint(),q.checkpoint())
        before=q.wallet(s.actor);q.cancel('cancel-prepaid',s.actor,key)
        self.assertEqual(before,q.wallet(s.actor));audit(q.world.journal(),q.access.checkpoint())

    def test_ample_raw_outputs_and_time_match(self):
        from hle_unified.records import Account
        worlds=[]
        for model in ('legacy-r4','grade-v1'):
            e,r,_=final_fixture('Contemplate','accumulation',factory(model));finish(e,r);worlds.append(e)
        def protected(e):
            return tuple(v for tx in e.world.journal() for v in tx.versions
                         if attrs(v).get('record_type')=='operation' or v.facet(Account) is not None)
        self.assertEqual(protected(worlds[0]),protected(worlds[1]))
        from hle_unified.compact import unseal
        access=[unseal(e.access.checkpoint(),e.access.SCHEMA) for e in worlds]
        # Each access envelope embeds the entire world, including intended
        # energy/model differences. Access nodes and events must still match.
        self.assertEqual(access[0]['nodes'],access[1]['nodes'])
        self.assertEqual(access[0]['events'],access[1]['events'])
