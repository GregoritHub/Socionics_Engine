import unittest
from tools.verify_corrective_native import expected_keys, validate_keys


class NativeCoverageVerifierTests(unittest.TestCase):
    def test_duplicate_cannot_hide_missing_boundary(self):
        rows = [dict(setting=s, route=r, polarity=p, boundary=b)
                for s, r, p, b in sorted(expected_keys())]
        validate_keys(rows)
        rows[-1] = rows[0]
        with self.assertRaisesRegex(ValueError, 'required 192'):
            validate_keys(rows)

    def test_same_total_wrong_setting_fails(self):
        rows = [dict(setting=s, route=r, polarity=p, boundary=b)
                for s, r, p, b in sorted(expected_keys())]
        rows[0]['setting'] = 'cancelled-encounter-restart'
        with self.assertRaises(ValueError):
            validate_keys(rows)
