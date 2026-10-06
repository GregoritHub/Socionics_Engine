"""Run the unmodified historical probe, then execute its sections separately.

Section execution retains each original assertion, records its failure, and
continues to later independent sections. It is not a passing modified probe.
"""
import ast
import contextlib
import hashlib
import io
import os
import subprocess
import sys
from pathlib import Path


def run(engine_root):
    src=Path(__file__).resolve().parents[1]/'sources/active_element_probe_original.py'
    env=os.environ.copy();env['PYTHONPATH']=str(engine_root)
    raw=subprocess.run([sys.executable,str(src)],cwd=engine_root,env=env,capture_output=True,text=True,timeout=60)
    tree=ast.parse(src.read_text())
    cuts=[i for i,node in enumerate(tree.body) if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
        and isinstance(node.value.func,ast.Name) and node.value.func.id=='hdr']
    g={'__file__':str(src),'__name__':'segmented_historical_probe'}
    exec(compile(ast.Module(tree.body[:cuts[0]],type_ignores=[]),str(src),'exec'),g)
    result=[]
    for n,start in enumerate(cuts):
        end=cuts[n+1] if n+1<len(cuts) else len(tree.body)-1
        log=io.StringIO();failure=None
        try:
            with contextlib.redirect_stdout(log):
                exec(compile(ast.Module(tree.body[start:end],type_ignores=[]),str(src),'exec'),g)
        except AssertionError as e:
            failure=str(e)
        except Exception as e:
            failure=type(e).__name__+': '+str(e)
        result.append({'probe':'P'+str(n+1),'old_assertion_passes':failure is None,
            'failure':failure,'stdout':log.getvalue()})
    return {'original_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
        'unmodified_exit_code':raw.returncode,'unmodified_stdout':raw.stdout,'unmodified_stderr':raw.stderr,
        'segmented':result,'after_training':g['after_training'],'after_organization':g['after_org'],
        'emitted_by_sender_type':g['emitted'],'reception_rows':g['rows']}
