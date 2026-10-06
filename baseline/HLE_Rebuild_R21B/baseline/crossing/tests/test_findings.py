"""Checks for the distinctions on which the reported conclusions depend."""
import gzip
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Findings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={}
        for release in ('r10','r11'):
            path=ROOT/'results'/(release+'.json')
            if path.exists():
                content=path.read_text()
            else:
                with gzip.open(path.with_suffix('.json.gz'),'rt',encoding='utf-8') as stream:
                    content=stream.read()
            cls.data[release]=json.loads(content)

    def test_exact_historical_probe_detects_r11_change(self):
        self.assertEqual(self.data['r10']['active_probe']['unmodified_exit_code'],0)
        self.assertNotEqual(self.data['r11']['active_probe']['unmodified_exit_code'],0)
        self.assertIn('R8/R9 now move',self.data['r11']['active_probe']['unmodified_stderr'])

    def test_completed_produce_has_one_element_for_all_sender_types(self):
        for release,element in [('r10','ne'),('r11','fe')]:
            rows=self.data[release]['study_b']['empirical']
            self.assertEqual(len(rows),256)
            self.assertEqual({x['element'] for x in rows},{element})
            for receiver in {x['receiver'] for x in rows}:
                self.assertEqual(len({x['read_units'] for x in rows if x['receiver']==receiver}),1)

    def test_history_control_changes_reception_with_identical_packet(self):
        for r in ('r10','r11'):
            b=self.data[r]['study_b']
            self.assertEqual([x['utterance_sha256'] for x in b['empirical']],
                [x['utterance_sha256'] for x in b['history_control']])
            changed=sum(x['read_units']!=y['read_units'] for x,y in zip(b['empirical'],b['history_control']))
            if r=='r10':self.assertEqual(changed,0)
            else:self.assertGreater(changed,0)

    def test_routes_change_cost_without_changing_ample_policy_outcomes(self):
        a=self.data['r10']['study_a']['cases'];b=self.data['r11']['study_a']['cases']
        keys=['stop_round','box_owner','fulfilled_organization_runs','fulfilled_transfers_to_extractor','delivered_replies']
        for x,y in zip(a,b):
            for key in keys:self.assertEqual(x[key],y[key],(x['policy'],key))
            self.assertNotEqual(x['assay_spent'],y['assay_spent'])

    def test_q4_member_costs_match_quiet_baseline(self):
        for d in self.data.values():
            a=d['study_a'];q4=a['cases'][3];quiet=a['quiet_baseline']
            for actor in ('alice','bob','cara'):
                self.assertEqual(q4['assay_spent'][actor],quiet['assay_spent'][actor])
            self.assertGreater(q4['assay_spent']['dara'],0)

    def test_stopping_is_controlled_by_supplied_patience(self):
        for d in self.data.values():
            for c in d['study_a']['stop_sensitivity']:
                self.assertEqual(c['stop_round'],c['patience'])
                self.assertEqual(c['attempt_count'],3*c['patience'])

    def test_all_coverage_subsets_are_observed(self):
        for d in self.data.values():
            rows=d['study_a']['coverage_subsets'];self.assertEqual(len(rows),8)
            for c in rows:
                if len(c['covered'])==3:self.assertEqual(c['stop_round'],2)
                else:self.assertIsNone(c['stop_round'])

    def test_restoration_requires_new_consent_but_not_six_extra_runs(self):
        for d in self.data.values():
            a=d['study_a']
            for r in [a['cases'][3]['restoration'],a['restoration_without_extra_practice']]:
                self.assertTrue(r['no_seat_before']);self.assertTrue(r['no_seat_after_attend'])
                self.assertEqual(r['unearned_formulation_status'],'unresolved')
                self.assertEqual(r['members'],['alice','bob','cara','dara'])
                self.assertTrue(all(x['outcome']=='fulfilled' for x in r['new_runs']))
                self.assertTrue(all(v>0 for v in r['successor_agreement_spent'].values()))
            self.assertEqual(a['restoration_without_extra_practice']['practice_outcomes'],[])

    def test_budget_limited_unfinished_output_is_unpublished(self):
        rows=self.data['r11']['study_b']['twenty_unit_opportunity']
        self.assertTrue(any(x['required']>20 for x in rows))
        self.assertTrue(any(x['required']<=20 for x in rows))
        for x in rows:
            self.assertEqual(x['has_published_utterance'],x['paid']==x['required'])

    def test_extractor_type_changes_cost_not_ample_extraction(self):
        rows=self.data['r11']['study_a']['extractor_full_q1']
        self.assertEqual(len(rows),16)
        self.assertEqual(len({x['fulfilled_transfers_to_extractor'] for x in rows}),1)
        self.assertGreater(len({x['assay_spent']['dara'] for x in rows}),1)


if __name__=='__main__':unittest.main()
