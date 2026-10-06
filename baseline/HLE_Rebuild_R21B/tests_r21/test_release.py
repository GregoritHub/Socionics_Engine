import json,sys,unittest
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from r21_workloads import make_world,run_episode,bounded,BudgetStop,replay_witness,permutation,renewal_case
from r21_reference import resource_audit,renewal_audit
from r21_evidence import summarize
from hle.world_records import Credit,Tick
from hle.contracts import WorkStatus
from hle.clearance_demo import prepared,begin,challenge
from hle.individuation_demo import make_offer,do,command
from hle.concept_demo import fund_command


class ReleaseContracts(unittest.TestCase):
    def test_zero_budget_defers_without_awarding_development(self):
        w,meta=run_episode('sli',11,0)
        self.assertIsNotNone(meta['resource_stop']);self.assertFalse(meta['cleared'])
        self.assertEqual(w._capacities,{})
        r=resource_audit(w);self.assertTrue(r['passed']);self.assertEqual(r['unfinished_count'],1)
        self.assertEqual(next(iter(r['unfinished_jobs'].values()))['paid'],0)

    def test_exhausted_partial_work_is_preserved_and_exactly_replayed(self):
        w,meta=run_episode('sli',11,2)
        self.assertIsNotNone(meta['resource_stop'])
        r=resource_audit(w);self.assertTrue(r['passed']);self.assertGreater(r['unfinished_count'],0)
        self.assertEqual(replay_witness(w)._journal,w._journal)

    def test_credit_is_rejected_before_mutation(self):
        w,_=make_world('sli',11,10);before=tuple(w._journal)
        with bounded(w):
            with self.assertRaisesRegex(ValueError,'top-ups'):
                w.execute(Credit('forbidden',w.config.actors[0],100,100,'test'))
        self.assertEqual(tuple(w._journal),before)

    def test_resource_checker_detects_unexpected_credit(self):
        w,_=make_world('sli',11,10)
        w.execute(Credit('visible',w.config.actors[0],1,1,'test allocation'))
        self.assertFalse(resource_audit(w)['passed'])
        self.assertTrue(resource_audit(w,allow_credits=True)['passed'])

    def test_quiet_ticks_do_not_supply_a_horizon(self):
        w,_=make_world('sli',11,0)
        for n in range(100):w.execute(Tick('quiet:'+str(n)))
        result=renewal_audit(w,[])
        self.assertFalse(result['passed']);self.assertEqual(result['eligible'],0)

    def test_seed_changes_real_histories_and_menus(self):
        a,ha=make_world('sli',11,10);b,hb=make_world('sli',17,10);c,hc=make_world('sli',23,10)
        # Use one different history residue in addition to independent labels.
        d,hd=make_world('sli',12,10)
        self.assertNotEqual(len(a.config.entities),len(d.config.entities))
        self.assertNotEqual(a.config.actors,b.config.actors)
        self.assertNotEqual(permutation(11,'x')(tuple(range(12))),permutation(17,'x')(tuple(range(12))))

    def test_two_changes_are_real_demand_families(self):
        families=[renewal_case(11,n).split('.')[0] for n in range(100)]
        self.assertEqual(sum(a!=b for a,b in zip(families,families[1:])),2)
        self.assertEqual(len(set(families)),3)

    def test_failed_and_censored_episodes_stay_in_denominator(self):
        spec=json.loads((ROOT/'docs/r12/acceptance_v1.json').read_text())['evaluation']
        rows=[{'name':f'{t}:{s}:{r}','tim':t,'seed':s,'regime':r,'passed':False,'cleared':False,
            'eligible':0,'changes':0,'resource_stop':'exhausted'}
            for t in spec['types'] for s in spec['evaluation_seeds'] for r in spec['regimes']]
        full=summarize(rows);missing=summarize(rows[:-1])
        self.assertTrue(full['denominator_complete']);self.assertFalse(full['passed'])
        self.assertFalse(missing['denominator_complete'])
        self.assertEqual(full['regimes']['adequate']['executed'],160)
        altered=[dict(r) for r in rows];altered[-1]['seed']=42
        self.assertFalse(summarize(altered)['denominator_complete'])

class ExistingRuntimeCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=prepared()

    def test_no_allocation_option_has_no_credit(self):
        from hle.clearance_demo import clone
        w=clone(self.base);cut=len(w._journal)
        begin(w,allocate=False);challenge(w,'original',allocate=False)
        self.assertFalse(any(isinstance(t.command,Credit) for t in w._journal[cut:]))
        self.assertTrue(w.clearance_report()['rows'][0]['passed'])

    def test_time_slice_does_not_publish_unpaid_choice(self):
        from hle.clearance_demo import clone
        w=clone(self.base);f=make_offer(w,'sliced','si',held=True,all_traps=True)
        w.execute(f);do(w,f.key,f.partner,'menu')
        cmd=replace(command(w,f.key,f.learner,'choose'),work_limit=1)
        with bounded(w):
            event=w.execute(cmd)
            self.assertEqual(event.outcome,WorkStatus.PARTIAL)
            self.assertIsNone(w._circuit_orders[f.key].chosen)
            fund_command(w,replace(cmd,command_id=cmd.command_id+':resume',work_limit=256))
        self.assertIsNotNone(w._circuit_orders[f.key].chosen)
        # This compatibility fixture carries R18's historical allocation.
        self.assertTrue(resource_audit(w,allow_credits=True)['passed'])

if __name__=='__main__':unittest.main()
