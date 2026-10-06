import unittest
from copy import deepcopy
from .fixtures import population
from hle_unified.population_audit import audit_population
from hle_unified.selection_records import loads

class PopulationAuditTests(unittest.TestCase):
    def test_raw_schedule_and_tampered_charge(self):
        p,_=population(17,2,2,32);p.run(2000)
        d=loads(p.checkpoint());tx=p.engine.world.journal()
        self.assertTrue(audit_population(tx,d)['passed'])
        bad=deepcopy(d);a,b=bad['events'][0]['charged'];bad['events'][0]['charged']=(a+1,b)
        with self.assertRaises(ValueError):audit_population(tx,bad)
    def test_fabricated_completion_and_actor_order_rejected(self):
        p,_=population(43,2,1,100000);p.run(100)
        d=loads(p.checkpoint());tx=p.engine.world.journal()
        bad=deepcopy(d);bad['events'][0]['actor']=bad['requests'][1]['actor']
        with self.assertRaises(ValueError):audit_population(tx,bad)
        bad=deepcopy(d)
        row=next(x for x in bad['events'] if x.get('native_status')=='succeeded');row['native_status']='failed'
        with self.assertRaises(ValueError):audit_population(tx,bad)
