#!/usr/bin/env python3
"""Reproduce R7 controls and descriptive profiles on the tested source."""
import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.codec import encode
from hle.composition import ComposedWorld
from hle.composition_demo import complete,compose,learned_world,run_composition_demo,use
from hle.composition_records import AssessCompositions,FoldDraft,Part,UnfoldDraft
from hle.contracts import EvidenceStatus as E
from hle.demo import ALICE,BOB,BOX,TOOL,ROOM
from hle.metabolism_demo import remember_initial
from hle.world_records import Tick
from tests.test_composition import assess,declare,revise,simple
from tests.reference_composition import reference_report


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def export(w,path,summary):
    path.mkdir(parents=True,exist_ok=True)
    (path/'checkpoint.json').write_text(w.checkpoint()+'\n')
    (path/'journal.jsonl').write_text(''.join(json.dumps(encode(t),sort_keys=True)+'\n' for t in w.truth.journal()))
    write(path/'summary.json',summary)
    reports=list(w._composition_reports.values())
    write(path/'reports.json',[encode(r) for r in reports])
    for r in reports:
        expected=reference_report(w.truth.journal(),w._composition_tests[r.test],r.at)
        assert all(getattr(r,k)==v for k,v in expected.items()),r.ref


def controls(out):
    w,s=run_composition_demo();export(w,out/'integrated',s)
    w,lesson,tool=learned_world()
    roots={b:compose(w,lesson,tool,b,str(b)+':') for b in (False,True)}
    cp=w.checkpoint(); rows=[]
    for enabled in (False,True):
        c=ComposedWorld.restore(cp);wallet=c.truth.wallet(BOB)
        t=declare(c,roots[enabled],claims=(),required=('inspect_before_transfer',))
        access,account,app,retained=use(c,roots[enabled]);report=assess(c,t)
        actions=[c._records[r].request.operation.key for r in c._records[app.result].enactments]
        row={'lesson_in_selected_root':enabled,'starting_energy':wallet.energy,'starting_time':wallet.time,
            'root':encode(roots[enabled]),'actions':actions,'access_units':access.completed,
            'use_units':report.uses[0].units,'capacity':report.capacity.value,'usefulness':report.usefulness.value}
        rows.append(row);export(c,out/('lesson_'+str(enabled).lower()),row)
    assert rows[0]['starting_energy']==rows[1]['starting_energy']
    assert rows[0]['actions']==['r2.transfer'] and rows[1]['actions']==['r2.inspect','r2.transfer']
    write(out/'matched_capacity.json',rows)
    c,m,child=simple();root=complete(c,FoldDraft('parent',(Part('child',child,ROOM),)),'parent').result
    t=declare(c,root);complete(c,UnfoldDraft(root,ROOM,c.now),'access');before=assess(c,t)
    n=revise(c,m);pending=[encode(r) for r in c.pending_compositions()];after=assess(c,t)
    assert before.cross_level==E.ESTABLISHED and after.cross_level==E.FAILED and after.identity==E.ESTABLISHED
    export(c,out/'child_revision',{'pending_after_revision':pending,'before':encode(before),'after':encode(after),
        'new_child':encode(n.ref),'historical_child':encode(m.ref)})
    from hle.composition_records import Expectation
    c,m,root=simple();t=declare(c,root,claims=(Expectation(BOX,'owned_by',BOB),))
    complete(c,UnfoldDraft(root,ROOM,c.now),'access');r=assess(c,t)
    assert r.identity==E.ESTABLISHED and r.cross_level==E.FAILED
    export(c,out/'counterexample',{'identity':r.identity.value,'cross_level':r.cross_level.value,'factual':r.factual.value})
    # Budget is a separate declared test over the same subsequent access and use.
    c,lesson,tool=learned_world();root=compose(c,lesson,tool)
    low=declare(c,root,'low',claims=(),required=('inspect_before_transfer',),budget=1)
    high=declare(c,root,'high',claims=(),required=('inspect_before_transfer',),budget=1000)
    use(c,root);a=assess(c,low);b=c.composition_report(high)
    assert a.path==E.FAILED and b.path==E.ESTABLISHED and a.usefulness==b.usefulness==E.ESTABLISHED
    export(c,out/'path_control',{'low':encode(a),'high':encode(b)})
    return s


def profile():
    rows=[]
    for ticks,unrelated in ((0,0),(2000,0),(0,100),(2000,100)):
        w,m,root=simple();t=declare(w,root)
        if unrelated:
            tool=remember_initial(w,'tool',TOOL)
            for i in range(unrelated):
                r=complete(w,FoldDraft('unrelated:'+str(i),(Part('tool',tool.ref,ROOM),)),'unrelated:'+str(i)).result
                from hle.composition_records import Expectation
                declare(w,r,'other:'+str(i),claims=(Expectation(TOOL,'owned_by',BOB),))
        assess(w,t)
        for i in range(ticks):w.execute(Tick('inactive:'+str(i)))
        samples=[];visits=[];paid=[];invalidations=[]
        for i in range(7):
            before=w.composition_visits;energy=w._spent[BOB];iv=w.invalidation_visits;start=time.perf_counter_ns()
            # Historical access + a new child revision and one affected report.
            complete(w,UnfoldDraft(root,ROOM,w.now),'profile:'+str(i))
            m=revise(w,m)
            w.execute(AssessCompositions('drain:'+str(i),1))
            elapsed=(time.perf_counter_ns()-start)/1e6
            if i:
                samples.append(elapsed);visits.append(w.composition_visits-before)
                paid.append(w._spent[BOB]-energy);invalidations.append(w.invalidation_visits-iv)
            assert not w.pending_compositions()
        start=time.perf_counter_ns();cp=w.checkpoint();save=(time.perf_counter_ns()-start)/1e6
        start=time.perf_counter_ns();clone=ComposedWorld.restore(cp);replay=(time.perf_counter_ns()-start)/1e6
        assert clone.checkpoint()==cp and set(visits)=={1} and set(paid)=={6} and set(invalidations)=={2}
        rows.append({'inactive_ticks':ticks,'unrelated_tests':unrelated,'samples_ms':samples,
            'median_ms':statistics.median(samples),'assessment_visits':visits,'invalidation_key_visits':invalidations,
            'paid_units':paid,'checkpoint_bytes':len(cp.encode()),'save_ms':save,'replay_ms':replay})
    return rows


def depth_profile():
    rows=[]
    for depth in (1,8,32,72):
        w,m,root=simple()
        for i in range(depth-1):root=complete(w,FoldDraft('level:'+str(i),(Part('child',root,ROOM),)),'level:'+str(i)).result
        start=time.perf_counter_ns();job=complete(w,UnfoldDraft(root,ROOM,w.now),'access');ms=(time.perf_counter_ns()-start)/1e6
        result=w._records[job.result]
        assert len(result.nodes)==depth+1 and len(result.edges)==depth and job.completed==2*(depth+1)
        rows.append({'composition_depth':depth,'unique_nodes':len(result.nodes),'edges':len(result.edges),
            'paid_units':job.completed,'unfold_ms':ms})
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--tests',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    tests=json.loads(args.tests.read_text());assert tests['successful']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for d in ('hle','tests','tools','docs') for p in sorted((ROOT/d).rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts}
    for name,value in hashes.items():
        if name.startswith(('hle/','tests/')):assert tests['source_hashes'].get(name)==value,name
    preserved=json.loads((ROOT/'docs/inherited_R6_sha256.json').read_text());exceptions={'hle/__init__.py','hle/__main__.py','hle/codec.py'}
    for name,value in preserved.items():
        if name not in exceptions:assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value,name
    inherited=[t for t in tests['tests'] if not t['test'].startswith('tests.test_composition.')]
    assert len(inherited)==219 and all(x['status']=='passed' for x in inherited)
    write(args.output/'source_preservation.json',{'passed':True,'inherited_tests':219,'allowed_extensions':sorted(exceptions),
        'preserved_files':len(preserved)-len(exceptions),'hashes':preserved})
    s=controls(args.output);print('Behavioral controls and independent journal comparisons passed',flush=True)
    write(args.output/'profile.json',profile());write(args.output/'depth_profile.json',depth_profile())
    print('Descriptive history and depth profiles completed',flush=True)
    seeds=[]
    code="import sys,hashlib;sys.path.insert(0,sys.argv[1]);from hle.composition_demo import run_composition_demo;print(hashlib.sha256(run_composition_demo()[0].checkpoint().encode()).hexdigest())"
    for seed in (0,1,2):
        q=subprocess.run([sys.executable,'-c',code,str(ROOT)],env={**os.environ,'PYTHONHASHSEED':str(seed)},capture_output=True,text=True,check=True)
        seeds.append({'seed':seed,'digest':q.stdout.strip()})
    assert len({x['digest'] for x in seeds})==1
    write(args.output/'hash_seed_controls.json',seeds)
    gates=json.loads((ROOT/'docs/acceptance_plan_R7.json').read_text())
    write(args.output/'acceptance_panel.json',{'law':gates['law'],'gates':[{**g,'status':'passed',
        'tests':[t['test'] for t in tests['tests'] if g['id'] in t['rules']]} for g in gates['gates']]})
    write(args.output/'environment.json',{'python':sys.version,'platform':platform.platform(),'command':sys.argv,
        'cpu':next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),'unknown'),
        'source_hashes':hashes})
    write(args.output/'summary.json',{'demo':s,'tests_run':tests['tests_run'],'all_controls_passed':True,
        'general_composition_closure':'unassessed','R10_efficiency_gate':'open'})
    print(json.dumps({'tests':tests['tests_run'],'controls':'passed'}))


if __name__=='__main__':main()
