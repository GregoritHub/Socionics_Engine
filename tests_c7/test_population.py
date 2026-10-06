import unittest
from dataclasses import replace
from .fixtures import population,ALICE,BOB
from hle_unified.population import Population
from hle_unified.selection_audit import audit

class PopulationTests(unittest.TestCase):
    def test_midpaid_resume_exact(self):
        p,_=population(17,2,3,17)
        p.run(7);q=Population.restore(p.checkpoint())
        self.assertEqual(p.checkpoint(),q.checkpoint())
        self.assertTrue(p.run(2000)['done']);self.assertTrue(q.run(2000)['done'])
        self.assertEqual(p.checkpoint(),q.checkpoint())
        self.assertTrue(audit(p.engine.world.journal(),p.engine.access.checkpoint())['passed'])
    def test_round_robin_never_starves_a_runnable_actor(self):
        p,_=population(43,3,2,16);p.run(9)
        actors=[x['actor'] for x in p.events]
        self.assertEqual(len(set(actors)),3)
        self.assertEqual(actors[:3],actors[3:6]);self.assertEqual(actors[:3],actors[6:9])
    def test_finite_horizon_and_history_retention(self):
        p,_=population(89,2,3,100000)
        before=len(p.engine.world.journal());self.assertTrue(p.run(200)['done'])
        self.assertEqual(p.counts,[3,3]);self.assertTrue(any(x.get('native_status')=='succeeded' for x in p.events));self.assertGreater(len(p.engine.world.journal()),before)
        self.assertIsNone(p.step())
        self.assertTrue(all(x['charged'][0]>=0 for x in p.events))
    def test_foreign_demand_and_duplicate_actor_rejected(self):
        p,_=population(17,2,1)
        with self.assertRaises(ValueError):Population(p.engine,(p.requests[0],p.requests[0]))
        with self.assertRaises(ValueError):Population(p.engine,(replace(p.requests[0],demand=p.requests[1].demand),))
    def test_turn_limit_preserves_unfinished_work(self):
        p,_=population(17,2,24,1);self.assertTrue(p.run(2)['pending'])
        self.assertEqual(p.counts,[0,0]);self.assertEqual(p.turn,2)
        self.assertEqual(p.checkpoint(),Population.restore(p.checkpoint()).checkpoint())
    def test_exhaustion_is_retained_and_terminates(self):
        p,_=population(17,2,100,32,budget=3000);p.run(10000)
        self.assertTrue(p.done);self.assertIn('exhausted',p.stopped)
        for i,status in enumerate(p.stopped):
            if status=='exhausted':self.assertEqual(p.engine.wallet(p.requests[i].actor)['energy'],0)
        self.assertTrue(audit(p.engine.world.journal(),p.engine.access.checkpoint())['passed'])

    def test_repeated_retained_content_stops_without_claiming_capacity(self):
        p,_=population(17,2,24,32,repeat_limit=2);p.run(2000)
        self.assertTrue(p.done);self.assertEqual(p.stopped,['unchanged_retained_result']*2)
        self.assertTrue(all(n<24 for n in p.counts))
        self.assertEqual(p.checkpoint(),Population.restore(p.checkpoint()).checkpoint())
        from hle_unified.population_audit import audit_population
        from hle_unified.selection_records import loads
        self.assertTrue(audit_population(p.engine.world.journal(),loads(p.checkpoint()))['passed'])

    def test_actual_material_feedback_is_delivered_and_paid(self):
        from tests_c6.fixtures import fixture
        from hle_unified.selection_records import loads
        from hle_unified.population_audit import audit_population
        e,r=fixture('Express','expenditure')
        p=Population(e,(r,),episodes=1,quantum=16,repeat_limit=None)
        self.assertTrue(p.run(1000)['done'])
        self.assertTrue(any(x['status']=='feedback_succeeded' for x in p.events))
        self.assertTrue(any(x['status'].startswith('feedback_') and x['charged'][0]>0 for x in p.events))
        self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['passed'])
        self.assertTrue(audit_population(e.world.journal(),loads(p.checkpoint()))['passed'])
