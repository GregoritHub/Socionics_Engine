from dataclasses import replace
import unittest
from hle.development_demo import *
from hle.content_operators import ASPECT, TARGET, transform, validate
from hle.model_a import TYPES, stack
from hle.content_records import ContentCommand


def specimens():
    return {
        'ne':{'kind':'alternatives','task':'x','offered':['a','b','c'],'permitted':['b','c']},
        'si':{'kind':'condition','task':'x','value':4,'low':2,'high':6,'observed_at':7,'now':7,'budget':4,'cost':3},
        'fi':{'kind':'consent','task':'x','partner':PARTNER.key,'offered':['a','b'],'accepts':['b'],'consented':True},
        'te':{'kind':'means','task':'x','rows':[{'id':'a','cost':2,'authorized':True,'ready':True},{'id':'b','cost':3,'authorized':True,'ready':True}], 'budget':2},
        'ni':{'kind':'temporal','task':'x','nodes':['b','a','c'],'edges':[['a','b'],['b','c']],'ready_at':[['a',2],['b',3],['c',5]],'now':1},
        'se':{'kind':'commitments','task':'x','rows':[{'id':'a','cost':3,'authorized':True,'ready':True},{'id':'b','cost':3,'authorized':True,'ready':True}], 'budget':3},
        'ti':{'kind':'distinctions','task':'x','assertions':[['owner','alice'],['owner','alice'],['context','here']]},
        'fe':{'kind':'shared_request','task':'x','required':[PARTNER.key,SECOND.key]},
    }


def run_role(w,ie,key='role'):
    b=specimens()[ie]
    if ie=='fi':
        m=store(w,PARTNER,key+':input',b); source=send(w,PARTNER,m,LEARNER,key+':consent'); sources=(source,)
    else:
        m=store(w,LEARNER,key+':input',b); sources=(m,)
    if ie=='fe':
        for actor in (PARTNER,SECOND):
            a=store(w,actor,key+':ack',{'kind':'acknowledgment','task':'x','sender':actor.key,'accepted':True})
            sources+=(send(w,actor,a,LEARNER,key+':send:'+actor.key),)
    ref=process(w,LEARNER,key,'content_'+ie,sources)
    return ref,w.content(LEARNER,ref)


class RoleTests(unittest.TestCase):
    def test_all_eight_executable_roles_have_independent_expected_outputs(self):
        expected={'ne':['b','c'],'si':[],'fi':['b'],'te':['a'],'ni':['a','b','c'],'se':['a'],'ti':['context','owner'],'fe':[PARTNER.key,SECOND.key]}
        w=world()
        for ie,items in expected.items():
            r,b=run_role(w,ie,ie)
            self.assertEqual(b['items'],items); self.assertTrue(b['valid']); self.assertEqual(ASPECT[b['kind']],ie)
            self.assertEqual(w.processing_state(LEARNER).active,ie)
            self.assertGreater(w.development_job(LEARNER,ie).paid,0)
        self.assertEqual(w.content(LEARNER,w.development_job(LEARNER,'ni').result)['schedule'],[['a',2],['b',3],['c',5]])

    def test_every_tim_complementary_pair_is_executable_without_changing_structure(self):
        for tim in TYPES:
            w=world(tim=tim); fixed=stack(tim)
            for ie in fixed[4:6]:
                r,b=run_role(w,ie,ie)
                self.assertTrue(b['valid']); self.assertEqual(w.processing_state(LEARNER).active,ie)
            self.assertEqual(stack(w._profiles[LEARNER].tim),fixed)

    def test_condition_requires_bounds_freshness_and_budget(self):
        b=specimens()['si']
        for change in ({'value':9},{'observed_at':6},{'budget':2}):
            out,_=transform('content_si',[dict(b,**change)]); self.assertFalse(out['valid'])

    def test_permissions_and_resource_bounds_constrain_actual_choices(self):
        for ie in ('te','se'):
            b=specimens()[ie]
            for field in ('authorized','ready'):
                rows=[dict(r,**{field:False}) for r in b['rows']]
                result,_=transform('content_'+ie,[dict(b,rows=rows)])
                self.assertEqual(result['items'],[]); self.assertFalse(result['valid'])
            result,_=transform('content_'+ie,[dict(b,budget=0)])
            self.assertFalse(result['valid']); self.assertEqual(result['spent'],0)

    def test_temporal_delay_changes_predictions_and_cycle_is_not_success(self):
        b=specimens()['ni']; old,_=transform('content_ni',[b])
        delayed=dict(b,ready_at=[['a',9],['b',3],['c',5]])
        new,_=transform('content_ni',[delayed])
        self.assertEqual(new['schedule'],[['a',9],['b',10],['c',11]])
        self.assertNotEqual(new['schedule'],old['schedule'])
        cycle=dict(b,edges=b['edges']+[['c','a']]); out,_=transform('content_ni',[cycle])
        self.assertFalse(out['valid']); self.assertEqual(out['items'],[])

    def test_contradiction_is_not_consistent_reasoning(self):
        b=specimens()['ti']; out,_=transform('content_ti',[dict(b,assertions=b['assertions']+[['owner','bob']])])
        self.assertFalse(out['valid']); self.assertNotIn('owner',out['items'])

    def test_missing_and_withdrawn_specific_consent_do_not_authorize(self):
        w=world(); b=specimens()['fi']; b['consented']=False
        m=store(w,PARTNER,'no',b); o=send(w,PARTNER,m,LEARNER,'no:send')
        r=process(w,LEARNER,'fi','content_fi',(o,)); self.assertFalse(w.content(LEARNER,r)['valid'])
        fake=store(w,LEARNER,'fake',dict(b,consented=True))
        with self.assertRaises(ValueError): process(w,LEARNER,'forged','content_fi',(fake,))

    def test_superseded_received_consent_cannot_be_reused(self):
        w=world(); b=specimens()['fi']
        m=store(w,PARTNER,'yes',b); yes=send(w,PARTNER,m,LEARNER,'yes:send')
        m=store(w,PARTNER,'no',dict(b,consented=False)); no=send(w,PARTNER,m,LEARNER,'no:send')
        with self.assertRaises(ValueError): process(w,LEARNER,'obsolete','content_fi',(yes,))
        r=process(w,LEARNER,'current','content_fi',(no,)); self.assertFalse(w.content(LEARNER,r)['valid'])

    def test_shared_result_needs_all_real_receiver_responses(self):
        w=world(); req=store(w,LEARNER,'req',specimens()['fe'])
        r=process(w,LEARNER,'empty','content_fe',(req,)); self.assertFalse(w.content(LEARNER,r)['valid'])
        a=store(w,PARTNER,'ack',{'kind':'acknowledgment','task':'x','sender':PARTNER.key,'accepted':True})
        o=send(w,PARTNER,a,LEARNER,'ack:send')
        r=process(w,LEARNER,'one','content_fe',(req,o)); self.assertFalse(w.content(LEARNER,r)['valid'])
        with self.assertRaises(ValueError): process(w,LEARNER,'foreign','content_fe',(req,a))

    def test_forged_ack_sender_and_duplicate_response_rejected(self):
        w=world(); req=store(w,LEARNER,'req',specimens()['fe'])
        forged=store(w,PARTNER,'forged',{'kind':'acknowledgment','task':'x','sender':SECOND.key,'accepted':True})
        with self.assertRaises(ValueError): send(w,PARTNER,forged,LEARNER,'forge')
        a=store(w,PARTNER,'ack',{'kind':'acknowledgment','task':'x','sender':PARTNER.key,'accepted':True})
        o=send(w,PARTNER,a,LEARNER,'one'); another=send(w,PARTNER,a,LEARNER,'two')
        with self.assertRaises(ValueError): process(w,LEARNER,'double','content_fe',(req,o,another))

    def test_te_selected_means_has_actual_world_consequence(self):
        item=Ref(Kind.ENTITY,'parcel',1); w=world(items=(item,))
        b={'kind':'means','task':'dispatch','rows':[{'id':item.key,'cost':2,'authorized':True,'ready':True}], 'budget':2}
        src=store(w,LEARNER,'means',b); ref=process(w,LEARNER,'select','content_te',(src,))
        selected=w.content(LEARNER,ref)['items']; self.assertEqual(selected,[item.key])
        e=w.execute(Attempt('enact','enact',ActionRequest(LEARNER,TRANSFER,(Ref(Kind.ENTITY,selected[0],1),PARTNER),(ref,))))
        self.assertEqual(e.outcome,WorkStatus.COMPLETED)
        self.assertEqual(w.truth.current_fact(item,'owned_by',ROOM).object,PARTNER)

    def test_original_32_content_identity_pairs_survive_activity_and_copy(self):
        matched=0
        for tim in TYPES:
            for family in ('search','boundary'):
                rows=[]
                for activity in ('hold','infer_'+family):
                    w=world(tim=tim); t=store(w,HELPER,'training',TRAINING)
                    demo=process(w,HELPER,'demo','demonstrate_'+family,(t,))
                    process(w,HELPER,'activity',activity,(demo,))
                    active=w.processing_state(HELPER).active
                    obs=send(w,HELPER,demo,LEARNER,'send')
                    n=w._notice_by_observation[(LEARNER,obs)]; p=w._receptions[(LEARNER,'send:receive')]
                    rows.append((w.content(LEARNER,obs),n.element,p.landing_position,p.plan.required,active))
                self.assertEqual(rows[0][:4],rows[1][:4]); self.assertNotEqual(rows[0][4],rows[1][4]); matched+=1
        self.assertEqual(matched,32)

    def test_all_eight_result_aspects_survive_send_after_unrelated_work(self):
        for ie in specimens():
            w=world(); result,body=run_role(w,ie)
            t=store(w,LEARNER,'unrelated',TRAINING); process(w,LEARNER,'hold','hold',(t,))
            o=send(w,LEARNER,result,HELPER,'relay')
            n=w._notice_by_observation[(HELPER,o)]
            self.assertEqual(n.element,ie); self.assertEqual(w.content(HELPER,o),body)
