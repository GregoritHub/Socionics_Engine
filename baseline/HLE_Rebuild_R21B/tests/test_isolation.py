import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from .support import rules

ROOT=Path(__file__).resolve().parents[1]


class Isolation(unittest.TestCase):
    @rules("E10")
    def test_runtime_imports_only_explicit_stdlib_or_new_modules(self):
        allowed={"__future__","bisect","dataclasses","enum","functools","hashlib","itertools","json","types","typing"}
        for path in (ROOT/"hle").glob("*.py"):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    self.assertTrue(all(n.name.split('.')[0] in allowed for n in node.names),str(path))
                if isinstance(node,ast.ImportFrom):
                    self.assertTrue(node.level==1 or node.module.split('.')[0] in allowed,str(path))
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                    self.assertNotIn(node.func.id,{"eval","exec","__import__","open"})

    @rules("E10")
    def test_new_runtime_imports_in_clean_interpreter_without_reference_tree(self):
        # Copy only the runtime modules: no old source, tests, or sources.
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(ROOT/"hle",Path(tmp)/"hle",ignore=shutil.ignore_patterns("__pycache__"))
            code="""import sys,json
sys.path.insert(0,sys.argv[1])
import hle
assert not any(n.startswith(('hle.model_a','hle.contracts')) for n in sys.modules)
from hle import gf2,model_a,relations,crux,contracts,ports,world,world_records,codec
from hle.demo import run_demo
assert run_demo()[1]['continuation_identical']
assert model_a.stack('iee')[3]=='ti'
assert len(relations.all_relations())==16
assert len(crux.movements())==32
for n in sys.modules:
    assert n.split('.')[0] not in ('pyref','algebra','crux','fools_memory','holon_tower','metabolism','demand','intention')
print(json.dumps({'independent_import':'passed','model_a_types':len(model_a.TYPES),'routes':len(crux.routes())}))
"""
            result=subprocess.run([sys.executable,"-I","-c",code,tmp],cwd=tmp,
                                  text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)["independent_import"],"passed")

    @rules("E11")
    def test_every_test_points_to_registered_rules(self):
        from . import test_math,test_crux,test_contracts,test_world
        registry=json.loads((ROOT/"docs/rules.json").read_text())
        ids={r["id"] for r in registry["rules"]}
        self.assertEqual(len(ids),len(registry["rules"]))
        for module in (test_math,test_crux,test_contracts,test_world,sys.modules[__name__]):
            for cls in vars(module).values():
                if isinstance(cls,type) and issubclass(cls,unittest.TestCase):
                    for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                        links=getattr(getattr(cls,name),"rule_ids",())
                        self.assertTrue(links,f"missing rule link for {cls.__name__}.{name}")
                        self.assertTrue(set(links)<=ids)
