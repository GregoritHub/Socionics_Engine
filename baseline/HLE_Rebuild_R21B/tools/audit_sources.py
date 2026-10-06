#!/usr/bin/env python3
"""Static 5.2.1 inventory and import audit; never imports legacy code.

Includes implicit package initializer edges. Dynamic imports and Erlang remote
calls are recorded separately; this is not a proof of arbitrary runtime reach.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]


def digest(data):return hashlib.sha256(data).hexdigest()


def audit(archive):
    with ZipFile(archive) as z:
        files={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
    inventory=[{"path":name,"bytes":len(data),"sha256":digest(data)} for name,data in sorted(files.items())]
    modules={}
    for name,data in files.items():
        if not name.endswith(".py"):continue
        path=PurePosixPath(name).relative_to("clean").with_suffix("")
        parts=list(path.parts)
        if parts[-1]=="__init__":parts.pop()
        modules[".".join(parts)]=(name,ast.parse(data.decode("utf-8"),filename=name))
    graph={name:set() for name in modules}
    external={name:set() for name in modules}
    dynamic=[]

    def link(source,target):
        if target in modules:graph[source].add(target)
        elif target:external[source].add(target)
        for i in range(1,len(target.split('.'))):
            parent='.'.join(target.split('.')[:i])
            if parent in modules:graph[source].add(parent)

    for module,(path,tree) in modules.items():
        is_package=path.endswith("/__init__.py")
        package=module if is_package else module.rpartition('.')[0]
        for i in range(1,len(module.split('.'))):link(module,'.'.join(module.split('.')[:i]))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                for alias in node.names:link(module,alias.name)
            elif isinstance(node,ast.ImportFrom):
                if node.level:
                    parts=package.split('.') if package else []
                    base='.'.join(parts[:len(parts)-node.level+1])
                    target='.'.join(p for p in (base,node.module) if p)
                else:target=node.module or ''
                link(module,target)
                for alias in node.names:
                    child=target+'.'+alias.name if target else alias.name
                    if child in modules:link(module,child)
            elif isinstance(node,ast.Call):
                fn=ast.unparse(node.func)
                if fn in ('__import__','importlib.import_module','exec','eval') or 'spec_from_file_location' in fn:
                    dynamic.append({"module":module,"line":node.lineno,"call":fn})

    def closure(start):
        seen=set();pending=[start]
        while pending:
            current=pending.pop()
            if current in seen:continue
            seen.add(current);pending.extend(graph.get(current,()))
        return sorted(seen)

    candidates=('pyref.core','algebra.perspective','algebra.content','algebra.facets',
                'algebra.kepinski','algebra.archetype','crux.perspectives','crux.typemap',
                'metabolism.exchange','fools_memory.schema','fools_memory.retrieve',
                'metabolism.tick','holon_tower.altitude')
    erlang=[]
    for path,data in files.items():
        if path.endswith('.erl'):
            text=data.decode('utf-8')
            erlang.append({"path":path,"module":re.search(r'-module\(([^)]+)\)',text).group(1),
                           "remote_modules":sorted(set(re.findall(r'\b([a-z][a-z0-9_]*)\s*:',text)))})
    decisions=[]
    for module,(path,_) in sorted(modules.items()):
        if module=='pyref.core':decision='selective rewrite of source-supported finite operations; no import of monolith'
        elif module=='crux.perspectives':decision='selective rewrite of formal grammar; preserve source claim grades'
        elif module=='metabolism.exchange':decision='rewrite element-preserving seat transfer only; relation names and dynamics excluded'
        else:decision='not ported in R1; retained in original archive for audit only'
        decisions.append({"module":module,"path":path,"decision":decision})
    return {"archive_sha256":digest(Path(archive).read_bytes()),"inventory":inventory,
            "python_module_count":len(modules),"erlang_module_count":len(erlang),
            "import_graph":{k:sorted(v) for k,v in sorted(graph.items())},
            "nonlocal_imports":{k:sorted(v) for k,v in sorted(external.items()) if v},
            "candidate_closures":{c:closure(c) for c in candidates},
            "dynamic_import_sites":dynamic,"erlang_static_remote_calls":erlang,
            "decisions":decisions,
            "scope":"AST conservative local closure including package initializers; no legacy execution; Erlang remote calls are lexical audit only"}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    result=audit(ROOT/'reference/originals/HolonicLivingEngine5_2_1_canon.zip')
    (args.output/'legacy_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    manifest=[]
    for path in sorted((ROOT/'reference/originals').iterdir()):
        manifest.append({"packaged_path":str(path.relative_to(ROOT)),"sha256":digest(path.read_bytes()),"bytes":path.stat().st_size})
    (args.output/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({"files":len(result['inventory']),"python_modules":result['python_module_count'],
                      "erlang_modules":result['erlang_module_count'],"dynamic_import_sites":result['dynamic_import_sites'],
                      "candidate_closure_sizes":{k:len(v) for k,v in result['candidate_closures'].items()}}))


if __name__=='__main__':main()
