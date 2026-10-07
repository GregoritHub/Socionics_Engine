import unittest
from dataclasses import replace
from .social_fixtures import *
from tools.verify_workflow_selection import audit,extent
from hle_unified.workflow_audit import audit as native_audit

class SocialSelectionTests(unittest.TestCase):
    def test_all_32_cells_and_matched_controls(self):
        for name in ALL_NAMES:
            for face in FACES:
                with self.subTest(name=name,face=face):
                    e,r,b=social_fixture(name,face);q,s,_=social_fixture(name,face,WithheldSocial)
                    d=finish(e,r);c=finish(q,s)
                    self.assertEqual(d['recipe'],'workflow-'+name.lower()+'-'+face+'-v1')
                    self.assertIsNone(d['failure']);self.assertIsNotNone(d['child'])
                    self.assertEqual(d['spent'],c['spent']);self.assertIsNone(c['child'])
                    self.assertIsNotNone(consume(e,r,b)['consequence']['next_task'])
                    self.assertNotEqual(social_query(e,r,name),social_query(q,s,name))
                    self.assertEqual(audit(e.world.journal(),e.access.checkpoint())['workflow_selections'],1)
                    native_audit(q.world.journal(),q.access.checkpoint(),extent_check=extent,extended_flags=('c7ws',))
                    with self.assertRaisesRegex(ValueError,'choice withheld'):audit(q.world.journal(),q.access.checkpoint())

    def test_missing_scope_and_exchange_cannot_create_social_applicability(self):
        for name in SOCIAL_NAMES:
            e,r,_=social_fixture(name,'accumulation')
            rows,_=e._workflow_policy(e.workflow_selection_view(replace(r,group=None)))
            self.assertFalse(any(x['eligible'] for x in rows if x['recipe'].startswith('workflow-'+name.lower()+'-')))
            if name in ('Share','Coordinate','Educate'):
                rows,_=e._workflow_policy(e.workflow_selection_view(replace(r,accessible=r.accessible[:-1])))
                self.assertFalse(any(x['eligible'] for x in rows if x['recipe'].startswith('workflow-'+name.lower()+'-')))
            rows,_=e._workflow_policy(e.workflow_selection_view(replace(r,peer=WRITER)))
            self.assertFalse(any(x['eligible'] for x in rows if x['recipe'].startswith('workflow-'+name.lower()+'-')))

    def test_duplicate_delivery_cannot_supply_distinct_member_practice(self):
        e,r,b=social_fixture('Institutionalize','accumulation')
        observed,_=e._read_workflow(e.participant_view(ALICE),r.accessible[1],b['request'])
        duplicate=receive(e,observed['event'],ALICE,'duplicate-practice-reading')
        rows,_=e._workflow_policy(e.workflow_selection_view(replace(r,accessible=(*r.accessible,duplicate))))
        self.assertFalse(next(x for x in rows if x['recipe']=='workflow-institutionalize-accumulation-v1')['eligible'])

    def test_teaching_retains_paid_uptake_without_practiced_skill(self):
        e,r,b=social_fixture('Educate','expenditure');before=e.participant_view(BOB).snapshot.acquired
        finish(e,r);consume(e,r,b);job=e.job_status(ALICE,'auto:movement');out=data(e,job['public.0'],BOB)
        self.assertTrue(out['understood']);self.assertFalse(out['competence'])
        self.assertEqual(before,e.participant_view(BOB).snapshot.acquired)
        audit(e.world.journal(),e.access.checkpoint())

    def test_social_checkpoint_and_composite_intermediates(self):
        for boundary in (1,100000):
            e,r,_=social_fixture('Institutionalize','expenditure');e.participate('partial',r,boundary)
            q=WorkflowSocialSelectionEngine.restore(e.checkpoint());self.assertEqual(e.checkpoint(),q.checkpoint())
            for i in range(8):self.assertEqual(e.participate('resume'+str(i),r),q.participate('resume'+str(i),r))
            self.assertEqual(e.checkpoint(),q.checkpoint());job=q.job_status(ALICE,'auto:movement')
            self.assertEqual(job['route_count'],2);self.assertEqual(job['steps_completed'],2)
            audit(q.world.journal(),q.access.checkpoint())
