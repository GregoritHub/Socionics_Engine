import unittest
from dataclasses import replace

from .fixtures import *
from hle_unified.material import attributes


class LongitudinalShellTests(unittest.TestCase):
    def test_two_type_histories_have_scoped_causal_controls_and_exact_restore(self):
        for tim in ('iee', 'sli'):
            with self.subTest(tim=tim):
                worlds, row = longitudinal(tim)
                self.assertEqual(len(worlds), 8)
                self.assertEqual(worlds['07-changed-target-residual'].checkpoint(),
                                 worlds['08-restored-final'].checkpoint())
                final = audit(worlds['07-changed-target-residual'].world.journal(),
                              worlds['07-changed-target-residual'].access.checkpoint())
                self.assertGreaterEqual(final['longitudinal_recurrence_same'], 1)
                self.assertGreaterEqual(final['longitudinal_recurrence_changed'], 1)
                self.assertEqual(len(final['longitudinal_originals']), 1)
                self.assertTrue(final['longitudinal_retained_intermediates'])
                self.assertEqual(row['comparison']['terminal'], 'handover')

    def test_no_pattern_controls_complete_for_both_types(self):
        for tim in ('iee', 'sli'):
            with self.subTest(tim=tim):
                e = undeformed(tim)
                report = audit(e.world.journal(), e.access.checkpoint())
                self.assertEqual(report['workflow_interruption_deformed'], 0)
                self.assertEqual(report['longitudinal_consumers'][-1]['next_task'], 'handover')

    def test_exhaustion_and_cancelled_paid_work_preserve_history(self):
        e, row = exhaustion()
        report = audit(e.world.journal(), e.access.checkpoint())
        self.assertEqual(e.wallet(ALICE)['energy'], 0)
        self.assertTrue(report['longitudinal_retained_intermediates'])
        self.assertEqual(row['completed'], row['required'] - 1)
        e, row = failed_work()
        report = audit(e.world.journal(), e.access.checkpoint())
        self.assertEqual(row['status'], 'cancelled')
        self.assertTrue(report['longitudinal_retained_intermediates'])

    def test_three_unsupported_clearances_are_byte_stable_and_recur(self):
        for effect in ('forecast', 'salience', 'exclude_route'):
            with self.subTest(effect=effect):
                worlds, row = unsupported_longitudinal(effect)
                self.assertEqual(worlds['before'].checkpoint(), worlds['after'].checkpoint())
                report = audit(worlds['still-interrupted'].world.journal(),
                               worlds['still-interrupted'].access.checkpoint())
                self.assertEqual(report['workflow_interruption_deformed'], 1)
                self.assertEqual(row['error'], 'unsupported, incomplete or scaffolded local correction')

    def test_original_material_and_restore_tampers_are_rejected(self):
        worlds, _ = longitudinal('iee')
        e = worlds['07-changed-target-residual']
        txs = list(e.world.journal())
        changed = False
        forged = []
        for tx in txs:
            versions = []
            for v in tx.versions:
                if not changed and v.ref.identity.namespace == 'u7.pattern':
                    d = dict(attrs(v)); d['origin'] = SAW2
                    v = replace(v, attributes=attributes(d)); changed = True
                versions.append(v)
            forged.append(replace(tx, versions=tuple(versions)))
        self.assertTrue(changed)
        with self.assertRaises(ValueError):
            audit(forged, e.access.checkpoint())

