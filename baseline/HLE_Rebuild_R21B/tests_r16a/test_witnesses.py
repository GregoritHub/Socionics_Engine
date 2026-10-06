import unittest
from dataclasses import replace
from itertools import product

from hle.contracts import Ref, Kind
from hle.crux import Perspective as P
from hle.development_structure import observe_trajectory, LensContent, QUOTIENTS
from hle.shell_records import SIGNS
from hle.shell_fixtures import fixture
from hle.shell_assessment import (assess_engagement, JointShellAssessment, OIGAccumulator,
                                  projected_path, opportunity_status)


class FiveWitnesses(unittest.TestCase):
    def assess(self, sign, positive=True, **changes):
        return assess_engagement(replace(fixture(sign, positive), **changes))['signs'][sign]

    def test_each_sign_has_its_own_positive_and_control(self):
        for sign in SIGNS:
            with self.subTest(sign=sign):
                positive, ordinary = JointShellAssessment(), JointShellAssessment()
                for i in range(3):
                    positive.append(fixture(sign, True, i)); ordinary.append(fixture(sign, False, i))
                self.assertEqual(positive.report()['signs'][sign]['status'], 'established_in_window')
                self.assertNotIn(ordinary.report()['signs'][sign]['status'], ('candidate', 'established_in_window'))
                self.assertEqual(positive.report()['scope'][4], 'fixture')

    def test_repeated_placement_does_not_become_all_five_signs(self):
        joint = JointShellAssessment()
        for i in range(5): joint.append(fixture('forced_placement', index=i))
        self.assertEqual([s for s, r in joint.report()['signs'].items() if r['status'] == 'established_in_window'], ['forced_placement'])

    def test_premature_requires_held_material(self):
        t = fixture('premature_translation')
        self.assertEqual(self.assess('premature_translation', operations=t.operations[1:])['observation'], 'negative')

    def test_premature_requires_consequential_use(self):
        t = fixture('premature_translation')
        self.assertEqual(self.assess('premature_translation', operations=t.operations[:-1])['observation'], 'negative')

    def test_premature_unknown_prerequisite_stays_unassessed(self):
        self.assertEqual(self.assess('premature_translation', prerequisites=())['observation'], 'unassessed')

    def test_placement_requires_later_maintenance(self):
        t = fixture('forced_placement')
        self.assertEqual(self.assess('forced_placement', operations=t.operations[:-1])['observation'], 'negative')

    def test_structure_requires_comparable_increase(self):
        t = fixture('new_defensive_structure')
        for inc in (replace(t.increase, after=t.increase.before),
                    replace(t.increase, after_scope='changed resource envelope')):
            self.assertEqual(self.assess('new_defensive_structure', increase=inc)['observation'], 'negative')
        self.assertEqual(self.assess('new_defensive_structure', increase=None)['observation'], 'unassessed')

    def test_foreign_structure_already_at_origin_is_not_new(self):
        t = fixture('new_defensive_structure'); p = replace(t.parts[1], created=t.start)
        self.assertEqual(self.assess('new_defensive_structure', parts=(t.parts[0], p), initial_structures=(p.ref,))['observation'], 'negative')

    def test_unused_new_structure_is_not_defensive(self):
        t = fixture('new_defensive_structure')
        self.assertEqual(self.assess('new_defensive_structure', operations=t.operations[:-1])['observation'], 'negative')

    def test_residual_requires_two_distinct_parts_acting_in_one_scope(self):
        t = fixture('residual_fragmentation'); left, right = t.operations[-2:]
        r = replace(right, inputs=left.inputs)
        self.assertEqual(self.assess('residual_fragmentation', operations=t.operations[:-1]+(r,))['observation'], 'negative')
        other = replace(right.claims[0], occasion=Ref(Kind.EVENT, 'another-loan', 1))
        r = replace(right, claims=(other,))
        self.assertEqual(self.assess('residual_fragmentation', operations=t.operations[:-1]+(r,))['observation'], 'negative')

    def test_open_unfinished_work_is_not_residual_fragmentation(self):
        result = self.assess('residual_fragmentation', False)
        self.assertEqual(result['observation'], 'negative'); self.assertIn('unresolved', result['reason'])

    def test_foreclosure_requires_an_identified_maintaining_operation(self):
        t = fixture('foreclosure')
        self.assertEqual(self.assess('foreclosure', operations=t.operations[:-1])['observation'], 'unassessed')

    def test_foreclosure_requires_noncurrent_movement(self):
        t = fixture('foreclosure'); o = t.opportunity
        self.assertEqual(self.assess('foreclosure', opportunity=replace(o, required_movement=o.current_movement))['observation'], 'negative')
        self.assertEqual(self.assess('foreclosure', opportunity=replace(o, required_movement=None))['observation'], 'unassessed')

    def test_actual_start_defeats_prevented_initiation_claim(self):
        t = fixture('foreclosure')
        op = replace(t.operations[-1], event=Ref(Kind.EVENT, 'actual-start', 1), tick=t.end,
                     name='start', movements=(t.opportunity.required_movement,))
        self.assertEqual(self.assess('foreclosure', operations=t.operations+(op,))['observation'], 'negative')

    def test_same_oig_can_mean_rest_or_foreclosure(self):
        a, b = (assess_engagement(fixture('foreclosure', flag)) for flag in (True, False))
        self.assertEqual(a['oig'], b['oig'])
        self.assertEqual(a['signs']['foreclosure']['observation'], 'positive')
        self.assertEqual(b['opportunity'], 'no_demand')

    def test_missing_delivery_interpretation_capacity_and_cost_stay_unknown(self):
        for sign in SIGNS:
            t = fixture(sign); o = t.opportunity
            variants = (replace(t, evidence=()),
                        replace(t, evidence=(replace(t.evidence[0], interpreted=None, interpretation=None),)),
                        replace(t, opportunity=replace(o, capacity_evidence=())),
                        replace(t, opportunity=replace(o, required_units=None)),
                        replace(t, opportunity=replace(o, available_operators=())))
            for v in variants:
                self.assertEqual(assess_engagement(v)['signs'][sign]['observation'], 'unassessed')

    def test_exhaustion_refusal_delay_and_open_jobs_are_not_defense(self):
        for sign in SIGNS:
            t = fixture(sign); o = t.opportunity
            variants = (replace(t, opportunity=replace(o, energy=0)),
                        replace(t, opportunity=replace(o, time=0)),
                        replace(t, opportunity=replace(o, selected=False)),
                        replace(t, opportunity=replace(o, refusal_evidence=(t.evidence[0].ref,))),
                        replace(t, closed=False))
            for v in variants:
                self.assertEqual(assess_engagement(v)['signs'][sign]['observation'], 'unassessed')

    def test_wrong_referent_or_context_with_same_graph_cannot_match(self):
        t = fixture('forced_placement'); e = t.evidence[0]; c = e.claims[0]
        for altered in (replace(c, subject=Ref(Kind.ENTITY, 'other-person', 1)),
                        replace(c, context=Ref(Kind.CONTEXT, 'other-context', 1)),
                        replace(c, occasion=Ref(Kind.EVENT, 'other-occasion', 1))):
            report = assess_engagement(replace(t, evidence=(replace(e, claims=(altered,)),)))
            self.assertEqual(report['signs']['forced_placement']['observation'], 'unassessed')

    def test_conflicting_usable_evidence_is_not_silently_resolved(self):
        t = fixture('forced_placement'); e = t.evidence[0]
        rival = replace(e, ref=Ref(Kind.OBSERVATION, 'rival', 1), claims=(replace(e.claims[0], value='true'),))
        self.assertEqual(assess_engagement(replace(t, evidence=(e, rival)))['opportunity'], 'no_unambiguous_scoped_constraint')

    def test_late_interpretation_cannot_retroactively_condemn_an_action(self):
        t = fixture('forced_placement'); e = replace(t.evidence[0], interpreted=t.end)
        self.assertEqual(self.assess('forced_placement', evidence=(e,))['observation'], 'unassessed')
        self.assertEqual(self.assess('forced_placement', opportunity=replace(t.opportunity, engaged_at=None))['observation'], 'unassessed')
        with self.assertRaises(ValueError): replace(t, opportunity=replace(t.opportunity, engaged_at=t.end+1))

    def test_unpaid_or_movementless_operations_do_not_prove_a_sign(self):
        for sign in SIGNS:
            t = fixture(sign)
            for operations in (tuple(replace(o, units=0, work=()) for o in t.operations),
                               tuple(replace(o, movements=()) for o in t.operations)):
                self.assertNotEqual(assess_engagement(replace(t, operations=operations))['signs'][sign]['observation'], 'positive')

    def test_no_shell_or_phase_field_can_set_a_verdict(self):
        with self.assertRaises(TypeError): replace(fixture('foreclosure'), shell=True)
        with self.assertRaises(TypeError): replace(fixture('foreclosure'), phase='integrated')

    def test_foreign_and_future_evidence_rejected(self):
        t = fixture('forced_placement'); e = t.evidence[0]
        with self.assertRaises(ValueError): replace(t, evidence=(replace(e, owner=Ref(Kind.ENTITY, 'stranger', 1)),))
        with self.assertRaises(ValueError): replace(t, evidence=(replace(e, interpreted=t.end+1),))

    def test_future_parts_and_duplicate_events_rejected(self):
        t = fixture('forced_placement')
        with self.assertRaises(ValueError): replace(t, parts=(replace(t.parts[0], created=t.end+1),)+t.parts[1:])
        with self.assertRaises(ValueError): replace(t, operations=t.operations+(t.operations[-1],))

    def test_boolean_threshold_and_mutable_records_rejected(self):
        with self.assertRaises(ValueError): JointShellAssessment(True)
        with self.assertRaises(ValueError): replace(fixture('forced_placement'), measured=['forced_placement'])

    def test_duplicate_engagement_does_not_count_as_recurrence(self):
        a = JointShellAssessment(); t = fixture('forced_placement'); a.append(t)
        with self.assertRaises(ValueError): a.append(t)
        self.assertEqual(a.report()['signs']['forced_placement']['positive'], 1)

    def test_separate_material_context_type_and_execution_kind_do_not_pool(self):
        a = JointShellAssessment(); a.append(fixture('forced_placement'))
        t = fixture('forced_placement', index=1)
        for variant in (replace(t, tim='sli'), replace(t, execution_kind='runtime'),
                        replace(t, context=Ref(Kind.CONTEXT, 'elsewhere', 1))):
            with self.assertRaises(ValueError): a.append(variant)

    def test_threshold_sensitivity_counts_engagements_not_ticks(self):
        for threshold in (2, 3, 5):
            a = JointShellAssessment(threshold)
            for i in range(5):
                a.append(fixture('forced_placement', index=i*1000))
                self.assertEqual(a.report()['signs']['forced_placement']['status'],
                    'candidate' if i+1 < threshold else 'established_in_window')

    def test_later_negative_preserves_qualified_history_without_clearance(self):
        a = JointShellAssessment()
        for i in range(3): a.append(fixture('forced_placement', index=i))
        a.append(fixture('forced_placement', False, 4))
        r = a.report()
        self.assertEqual(r['signs']['forced_placement']['status'], 'established_in_window')
        self.assertTrue(r['clearance'].startswith('unassessed'))

    def test_correct_endpoint_does_not_override_path_evidence(self):
        a = JointShellAssessment(); a.append(fixture('forced_placement'))
        self.assertEqual(a.report()['engagements'][0]['endpoint'], 'correct')
        self.assertEqual(a.report()['coherence'], 'failed_in_window')

    def test_nonzero_cancellation_is_not_a_shell(self):
        t = fixture('premature_translation', False)
        ops = tuple(replace(o, domains=(P.I,) if i in (0, len(t.operations)-1) else (P.WE,)) for i,o in enumerate(t.operations))
        r = assess_engagement(replace(t, operations=ops))
        self.assertTrue(r['oig']['K']); self.assertEqual(r['signs']['premature_translation']['observation'], 'negative')

    def test_all_twelve_incremental_quotients_match_independent_reference(self):
        for tim, sign, flag in product(('iee', 'sli', 'eie', 'lsi'), SIGNS, (True, False)):
            t = replace(fixture(sign, flag), tim=tim); path = projected_path(t)
            inc = OIGAccumulator(tim)
            for n, content in enumerate(path, 1):
                inc.append(content)
                self.assertEqual(inc.result(), observe_trajectory(tim, path[:n]))
                self.assertEqual(inc.visits, 12*n)

    def test_oig_recurrence_partitions_preserve_positions_without_pair_expansion(self):
        t = fixture('foreclosure'); point = projected_path(t)[0]; a = OIGAccumulator(t.tim)
        for _ in range(1000): a.append(point)
        r = a.result(); self.assertFalse(r['V']); self.assertFalse(r['K'])
        self.assertEqual(r['R'][('dom','unpaired')], (tuple(range(1000)),))
        self.assertEqual(a.visits, 12000)

    def test_oig_scope_cannot_change_mid_path(self):
        t = fixture('foreclosure'); c = projected_path(t)[0]; a = OIGAccumulator(t.tim); a.append(c)
        with self.assertRaises(ValueError): a.append(replace(c, context=Ref(Kind.CONTEXT, 'new', 1)))
        with self.assertRaises(ValueError): replace(t, protocol=replace(t.protocol, revision=2))


if __name__ == '__main__': unittest.main()
