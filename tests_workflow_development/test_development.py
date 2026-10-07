import unittest
from dataclasses import replace
from .fixtures import *
from hle_unified.material import attributes


class WorkflowDevelopmentTests(unittest.TestCase):
    def test_original_material_correction_and_same_changed_recurrence(self):
        worlds=history();e=worlds['07-withdrawal-recurrence']
        report=audit(e.world.journal(),e.access.checkpoint())
        self.assertTrue(all(report['workflow_diagnostic_signs'].values()))
        rows=report['workflow_development_rows']
        self.assertEqual([r['completed'] for r in rows],[False,False,False,True,False,True,False])
        self.assertEqual(rows[1]['recurrence'],'same_target');self.assertEqual(rows[2]['recurrence'],'changed_target')
        p=e.pattern_view(ALICE)[0]
        require_scoped_correction(e.world.journal(),e.access.checkpoint(),p.ref,DEVICE)
        with self.assertRaisesRegex(ValueError,'no actual exact-target correction'):
            require_scoped_correction(e.world.journal(),e.access.checkpoint(),p.ref,LOAN)

    def test_supported_work_and_withdrawal_do_not_award_capacity(self):
        worlds=history()
        for key in ('06-supported-without-capacity','07-withdrawal-recurrence'):
            e=worlds[key];r=audit(e.world.journal(),e.access.checkpoint())['workflow_development_rows'][-1]
            self.assertEqual(r['supported'],key.startswith('06'))
            self.assertFalse(any(v.ref.identity.namespace=='u8.capacity' for tx in e.world.journal() for v in tx.versions))
        self.assertTrue(r['premature_translation']);self.assertFalse(r['completed'])

    def test_three_unsupported_clearances_refuse_without_changing_world(self):
        for kind in ('forecast','salience','exclude_route'):
            with self.subTest(effect=kind):
                worlds,row=unsupported(kind)
                self.assertEqual(worlds['before'].checkpoint(),worlds['after'].checkpoint())
                e=worlds['still-interrupted'];p=e.pattern_view(ALICE)[0]
                with self.assertRaisesRegex(ValueError,'unsupported clearance'):
                    require_scoped_correction(e.world.journal(),e.access.checkpoint(),p.ref,DEVICE)
                self.assertTrue(audit(e.world.journal(),e.access.checkpoint())['workflow_development_rows'][-1]['premature_translation'])

    def test_forged_correction_scope_and_origin_are_rejected(self):
        e=history()['04-exact-correction-and-native-use'];audit(e.world.journal(),e.access.checkpoint())
        for field,value in (('target',LOAN),('origin',DEVICE)):
            txs=[replace(tx,versions=tuple(replace(v,attributes=attributes(dict(attrs(v),**{field:value})))
                if v.ref.identity.namespace=='u8.correction' and attrs(v)['target']==DEVICE else v for v in tx.versions)) for tx in e.world.journal()]
            with self.subTest(field=field),self.assertRaises(ValueError):audit(txs,e.access.checkpoint())
