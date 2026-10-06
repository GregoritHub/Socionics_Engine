import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from u14_support import raw_accounting
from tests_u4 import fixtures as f
from inspect_u14 import inspect,write_html,load_engine


class Accounting(unittest.TestCase):
    def test_own_budget_reconstructed_and_forged_debit_rejected(self):
        e=f.setup(); f.perform(e,f.repair(e))
        audit=raw_accounting(e.world.journal())
        self.assertEqual(audit['total_charged'],200-e.wallet(f.ALICE)['energy'])
        txs=list(e.world.journal());found=False
        for i,tx in enumerate(txs):
            versions=[]
            for v in tx.versions:
                d=f.attrs(v)
                if not found and d.get('record_type')=='wallet' and v.previous:
                    v=replace(v,attributes=f.attributes({**d,'energy':d['energy']+1}));found=True
                versions.append(v)
            txs[i]=replace(tx,versions=tuple(versions))
        self.assertTrue(found)
        with self.assertRaisesRegex(ValueError,'debit'):raw_accounting(txs)

    def test_budget_reallocation_cannot_hide_spending(self):
        e=f.setup();txs=list(e.world.journal())
        for i,tx in enumerate(txs):
            versions=[]
            for v in tx.versions:
                d=f.attrs(v)
                if d.get('record_type')=='wallet' and v.previous:
                    v=replace(v,attributes=f.attributes({**d,'initial_energy':d['initial_energy']+1}))
                versions.append(v)
            txs[i]=replace(tx,versions=tuple(versions))
        with self.assertRaisesRegex(ValueError,'allocation'):raw_accounting(txs)


class Inspector(unittest.TestCase):
    def test_actor_export_excludes_unseen_material(self):
        from tests_u6.fixtures import setup6
        a=setup6(hidden_kit_wear=0);b=setup6(hidden_kit_wear=10)
        self.assertEqual(inspect(a),inspect(b))
        with self.assertRaisesRegex(ValueError,'evaluator'):inspect(a,object_name='workshop:kit')

    def test_exact_historical_revision_and_no_mutation(self):
        from tests_u6.fixtures import setup6
        e=setup6();before=e.checkpoint()
        result=inspect(e,assess=True,object_name='workshop:kit',revision=1)
        self.assertEqual(len(result['offline_evaluator']['object_history']),1)
        self.assertEqual(e.checkpoint(),before)

    def test_complete_export_serializes_wallet_and_evaluator(self):
        import json
        from tests_u6.fixtures import setup6
        e=setup6()
        for assess in (False,True):
            data=inspect(e,assess=assess)
            self.assertEqual(json.loads(json.dumps(data)),data)
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'inspector.html';write_html(p,data)
                self.assertIn('Workshop inspector',p.read_text())

    def test_html_cannot_execute_record_text(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'inspector.html';write_html(p,{'actor':'</script><script>alert(1)</script>'})
            text=p.read_text()
            self.assertNotIn('</script><script>alert(1)</script>',text)
            self.assertIn('\\u003c/script',text)

    def test_gzip_checkpoint_restores_with_same_actor_export(self):
        from tests_u6.fixtures import setup6
        from u14_support import save_gzip
        e=setup6()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cp.json.gz';save_gzip(p,e.checkpoint())
            self.assertEqual(inspect(e),inspect(load_engine(p)))


class PanelValidation(unittest.TestCase):
    def check_rejected(self,cases,reason):
        import json
        from run_u14 import main
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'protocol.json';p.write_text(json.dumps({'panels':{'autonomy':cases}}))
            with patch.object(sys,'argv',['run_u14','--panel','autonomy','--development',str(p),'--out',str(Path(d)/'out')]):
                with self.assertRaisesRegex(ValueError,reason):main()
            self.assertFalse((Path(d)/'out/summary.json').exists())

    def test_empty_panel_is_not_a_pass(self):self.check_rejected([],'empty panel')

    def test_duplicate_cases_are_not_independent_evidence(self):
        self.check_rejected([{'id':'same'},{'id':'same'}],'duplicate case')
