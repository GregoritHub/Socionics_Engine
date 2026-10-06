"""Source-binding transfer: received meaning must change an existing choice."""
import unittest
from tests_c3.fixtures import *
from hle.model_a import TYPES
from hle_unified.crossing_audit import audit

class PriorOnly(CrossingEngine):
    """Keep the receiver's prior cap while ignoring the received constraint."""
    def _semantic_step(self,name,p,previous):
        result=super()._semantic_step(name,p,previous)
        if p.get('c3') and p['request'].key=='case' and name.startswith('realize:'):
            kind,target,values=result; d=cross.decode(values['payload'])
            d['cap']=p['data'][2]['own_cap']
            return kind,target,{'payload':cross.encode(d)}
        return result


def transfer(e,name,face):
    own=seed_intent(e,'learner-prior',cap=5,actor=BOB)
    before=work(e,req(e,'before-learning','use-personal-v1',(own,),actor=BOB,stock=ref('bob-consumables'),demand=4))
    if name=='Share': source=seed_intent(e,'source-intent',cap=1); domain='personal'
    elif name=='Coordinate': source=inspect(e,'source-event'); domain='observation'
    else: source=model(e,'source-theory',cap=2); domain='system'
    g=join(e,group(e,'transfer-group'),key='transfer-join')
    for actor in (ALICE,BOB): expose_group(e,actor,g['ref'])
    work(e,req(e,'transfer-offer','offer-'+domain+'-v1',(source,),peer=BOB,group=g['ref'],demand=1))
    offer=e.job_status(ALICE,'transfer-offer')['public.0']
    for actor in (ALICE,BOB): expose(e,actor,offer)
    work(e,req(e,'transfer-reply','reply-v1',(offer,own),actor=BOB,peer=ALICE,group=g['ref']))
    reply=e.job_status(BOB,'transfer-reply')['public.0']; expose(e,ALICE,reply)
    work(e,req(e,'case',name.lower()+'-'+face+'-v1',(source,offer,reply),peer=BOB,group=g['ref']))
    shared_result=e.job_status(ALICE,'case')['public.0']; expose(e,BOB,shared_result)
    after=work(e,req(e,'after-learning','use-shared-v1',(shared_result,),actor=BOB,peer=ALICE,
        group=g['ref'],stock=ref('bob-consumables'),demand=4))
    event=None
    if data(e,after,BOB)['action']=='consume': event=enact(e,after,'learner-participates',actor=BOB)
    return dict(before=before,after=after,event=event,source=source,offer=offer,reply=reply,shared=shared_result,prior=own)


class SourceTransferTests(unittest.TestCase):
    def test_received_source_changes_existing_choice_all_types_and_faces(self):
        for tim in TYPES:
            for name in ('Share','Coordinate','Educate'):
                for face in FACES:
                    with self.subTest(tim=tim,route=name,face=face):
                        e=setup_c3(tim,quantity=1); out=transfer(e,name,face)
                        self.assertEqual(data(e,out['before'],BOB)['amount'],4)
                        self.assertEqual(data(e,out['after'],BOB)['amount'],2 if name=='Educate' else 1)
                        self.assertEqual(data(e,out['prior'],BOB)['cap'],5)
                        self.assertEqual(out['event'] is not None,face=='expenditure')
                        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])

    def test_source_binding_transfer_controls_and_continuation(self):
        for name in ('Share','Coordinate','Educate'):
            for face in FACES:
                e=setup_c3(quantity=1); out=transfer(e,name,face)
                q=setup_c3(quantity=1,engine_type=PriorOnly); other=transfer(q,name,face)
                self.assertEqual(e.job_status(ALICE,'case')['spent'],q.job_status(ALICE,'case')['spent'])
                self.assertNotEqual(data(e,out['after'],BOB)['amount'],data(q,other['after'],BOB)['amount'])
                self.assertEqual(data(q,other['after'],BOB)['amount'],4)
                with self.assertRaises(ValueError): audit(q.world.journal(),q.access.checkpoint())
                for branch in (e,q): self.assertEqual(type(branch).restore(branch.checkpoint()).checkpoint(),branch.checkpoint())
