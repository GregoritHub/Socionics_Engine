import unittest
from dataclasses import replace
from .final_fixtures import *
from hle_unified.selection_records import dumps,loads
from hle_unified.material import attributes

class FinalSelectionTests(unittest.TestCase):
    def test_three_responsiveness_worlds_and_controls(self):
        worlds,pairs=responsiveness()
        self.assertEqual(len(pairs),3);self.assertEqual(len(worlds),9)
        self.assertEqual(sum(bad for _,_,bad in worlds),2)

    def test_capacity_checkpoint_continuation_and_paid_definition(self):
        e,r,_=capacity_base()
        with self.assertRaisesRegex(ValueError,'paid exact care procedure'):e.start('unread',replace(r,procedure=ref('unread-care-means')))
        self.assertFalse({'recipe','face','route','cell'} & set(WorkflowCapacitySelectionRequest.__dataclass_fields__))
        acquire_care(e,r);e.participate('partial',r,1);q=WorkflowFinalSelectionEngine.restore(e.checkpoint())
        self.assertEqual(e.checkpoint(),q.checkpoint())
        for i in range(8):self.assertEqual(e.participate('resume'+str(i),r),q.participate('resume'+str(i),r))
        self.assertEqual(e.checkpoint(),q.checkpoint());audit(q.world.journal(),q.access.checkpoint())
        self.assertEqual(q.job_status(ALICE,'auto:movement')['status'],'succeeded')

    def test_unearned_capacity_snapshot_rejected(self):
        e,r,_=capacity_base();finish(e,r);txs=[]
        for tx in e.world.journal():
            versions=[]
            for v in tx.versions:
                if v.ref.identity.namespace=='c7ws.snapshot':
                    z=loads(attrs(v)['payload']);z['acquired']=((r.procedure,r.context,r.demand),)
                    v=replace(v,attributes=attributes(dict(payload=dumps(z))))
                versions.append(v)
            txs.append(replace(tx,versions=tuple(versions)))
        with self.assertRaisesRegex(ValueError,'native care capacity'):audit(txs,e.access.checkpoint())
