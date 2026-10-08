import unittest
from pathlib import Path
from tools.verify_longitudinal_shell import read, forge_recurrent_status, require_rejection


class CorrectiveLongitudinalTests(unittest.TestCase):
    def test_real_forgery_rejected_and_accepting_auditor_fails(self):
        p = Path(__file__).resolve().parents[1] / 'evidence/FB5.6/attempt4/matrix/iee-04-same-target-recurrence.json.gz'
        raw, txs, _, _ = read(p)
        forged = forge_recurrent_status(txs, raw['access'])
        self.assertTrue(require_rejection(forged, raw['access']))
        calls = []
        def accepting(t, a):
            calls.append((t, a))
            return {'passed': True}
        with self.assertRaisesRegex(AssertionError, 'accepted by auditor'):
            require_rejection(forged, raw['access'], accepting)
        self.assertEqual(calls, [(forged, raw['access'])])

    def test_preparation_cannot_count_as_auditor_rejection(self):
        calls = []
        def accepting(t, a):
            calls.append(True)
        with self.assertRaises(AssertionError):
            require_rejection((), '', accepting)
        self.assertEqual(calls, [True])
