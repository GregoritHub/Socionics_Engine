import copy
import json
import tempfile
import unittest
from pathlib import Path
from tools.run_corrective_release import ROOT, PROTOCOL, validate_protocol
from tools.verify_corrective_release import check_methods
from tools.build_corrective_ledger import historical_inventory, native_mapping


class ReleasePreparationTests(unittest.TestCase):
    def test_missing_inherited_job_rejected(self):
        protocol = json.loads(PROTOCOL.read_text())
        validate_protocol(protocol)
        changed = copy.deepcopy(protocol)
        changed['jobs'][0]['argv'][1] = 'tools/omitted_inherited.py'
        with self.assertRaisesRegex(AssertionError, 'inherited job'):
            validate_protocol(changed)

    def test_duplicate_method_rejected(self):
        ids = json.loads((ROOT / 'contracts/C7_Corrective_Method_Inventory_v1.json').read_text())['method_ids']
        check_methods(ids, ids)
        duplicate = ids[:-1] + [ids[0]]
        with self.assertRaisesRegex(AssertionError, 'duplicate or missing'):
            check_methods(duplicate, ids)

    def test_missing_historical_bytes_block_mapping(self):
        # A missing sentinel tests refusal only; it is never passed as evidence.
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                historical_inventory(Path(folder), [('negative-control', 'absent', '0'*64, 1)])

    def test_cross_cell_native_mapping_rejected(self):
        rows = [dict(setting='canonical', route='Act', polarity='accumulation', boundary=i) for i in range(3)]
        self.assertEqual(len(native_mapping(rows, 'canonical', 'Act', 'accumulation')), 3)
        rows[-1]['route'] = 'Contemplate'
        with self.assertRaisesRegex(AssertionError, 'native cell mapping'):
            native_mapping(rows, 'canonical', 'Act', 'accumulation')
