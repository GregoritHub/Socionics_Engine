import unittest
from tools.verify_corrective_parents import validate_keys, reject, CATEGORIES


class ParentVerifierTests(unittest.TestCase):
    def test_duplicate_scenario_does_not_supply_eight_worlds(self):
        rows = [dict(setting=s, category=c) for s in ('canonical', 'workflow') for c in CATEGORIES]
        validate_keys(rows)
        rows[-1] = rows[0]
        with self.assertRaises(ValueError):
            validate_keys(rows)

    def test_accepting_auditor_cannot_count_forged_parent_rejection(self):
        calls = []
        def accepting(t, a):
            calls.append((t, a))
            return {'passed': True}
        with self.assertRaisesRegex(AssertionError, 'accepted by ordinary auditor'):
            reject((), 'unchanged-access', accepting)
        self.assertEqual(calls, [((), 'unchanged-access')])
