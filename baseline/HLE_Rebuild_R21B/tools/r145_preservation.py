"""Explicit evolution of byte-preservation assertions, not behavioral gates."""
import json,hashlib

def verify_changed(root,name):
    rows=json.loads((root/'docs/r145/Source_Changes_R145.json').read_text())['changed']
    row=next(r for r in rows if r['path']==name)
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==row['after'],name
    assert hashlib.sha256((root/'reference/r14_preserved'/name).read_bytes()).hexdigest()==row['before'],name
