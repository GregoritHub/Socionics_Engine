import unittest
from dataclasses import replace
from hle_unified.conditioning_audit import completed_use,observations
from hle_unified.energy_audit import blocks
from hle_unified.material import attrs,attributes
from tests_workflow_selection.final_fixtures import final_fixture
from .fixtures import factory

class ConditioningTests(unittest.TestCase):
    def test_completed_boundary_partial_cancel_and_empty_ties(self):
        e,r,_=final_fixture('Contemplate','accumulation',factory('grade-v1'))
        initial=[]
        for tx in e.world.journal():
            if any(attrs(v).get('record_type')=='operation' for v in tx.versions):break
            initial.append(tx)
        for row in observations(initial):
            self.assertEqual(set(row['cells_with_greatest_load']),set('DCNH'))
            self.assertEqual(sum(row['counts'].values()),0)
        e.start('comparison',r);e.advance('comparison-pay',r.actor,r.key,10000);e.commit('comparison-commit',r.actor,r.key)
        key=r.key+':movement';d=e.job_status(r.actor,key)
        start,end,price,element=next(b for b in blocks(d) if b[3] is not None)
        before=completed_use(e.world.journal())[1][r.actor].copy()
        e.advance('before-boundary',r.actor,key,end-1)
        self.assertEqual(completed_use(e.world.journal())[1][r.actor],before)
        e.advance('at-boundary',r.actor,key,1)
        after=completed_use(e.world.journal())[1][r.actor]
        self.assertEqual({k:after[k]-before[k] for k in before},{k:int(k==element) for k in before})
        e.cancel('cancel',r.actor,key)
        self.assertEqual(completed_use(e.world.journal())[1][r.actor],after)

    def test_unpaid_forged_completion_and_missing_wallet_rejected(self):
        e,r,_=final_fixture('Contemplate','accumulation',factory('grade-v1'))
        e.start('start',r);e.advance('pay',r.actor,r.key,1)
        txs=e.world.journal();last=txs[-1]
        for kind in ('omit','refund','completion'):
            versions=[]
            for v in last.versions:
                d=attrs(v)
                if d.get('record_type')=='wallet':
                    if kind=='omit':continue
                    if kind=='refund':d['energy']+=1
                if d.get('record_type')=='operation' and kind=='completion':d['completed']+=1;d['spent']+=1
                versions.append(replace(v,attributes=attributes(d)))
            with self.assertRaises(ValueError):completed_use(txs[:-1]+(replace(last,versions=tuple(versions)),))
