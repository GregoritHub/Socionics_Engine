"""Eight causal pairs, raw evidence, and compact three-question views."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_c2.fixtures import *
from tests_c2.test_self_routes import NAMES,FACES,make,consequence
from hle_unified.self_audit import audit
from hle_unified import codec
from hle_unified.operations import address


def write(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def pack(path,value): path.write_bytes(gzip.compress(value.encode(),mtime=0))


def witness(out,name,face,control=False):
    out.mkdir(parents=True,exist_ok=False)
    e=make(name,face,engine_type=Ablated if control else SelfRouteEngine)
    before={x: e.world.head(x.identity) for x in (SAW,STOCK,KIT,CARE,ref('bob-consumables'))}
    result=cell(e,name,face)
    report=None; rejection=None
    try: report=audit(e.world.journal(),e.access.checkpoint())
    except ValueError as exc:
        rejection=str(exc)
        if not control: raise
    if control and rejection is None: raise AssertionError('ablation passed ordinary acceptance')
    cp=e.checkpoint(); restored=type(e).restore(cp)
    assert cp==restored.checkpoint()
    d=e.job_status(ALICE,'case')
    refs={'inputs':tuple(result['inputs']),'output':d.get('binding') or d['result'],
          'downstream':result['downstream'], 'steps':tuple(address('c2.step',ALICE,'case',i) for i in range(2))}
    if result.get('event'): refs['downstream_event']=result['event']
    if result.get('follow_event'): refs['follow_event']=result['follow_event']
    changes=[]
    for old,v in before.items():
        after=e.world.head(old.identity)
        if v!=after: changes.append(dict(before=codec.encode(v.ref),after=codec.encode(after.ref),
            before_attributes=codec.encode(tuple(sorted(attrs(v).items()))),after_attributes=codec.encode(tuple(sorted(attrs(after).items())))))
    answers={
       'Contemplate':('Owned meanings become differentiated uncertainty or a retained attention policy.','A paid intermediate comparison/rehearsal is consumed by retention.','The downstream decision selects inspection; the ablation selects use.'),
       'Act':('Repair restores a damaged tool, or use increases its wear.','A generated command is committed under the native material law, with separate material work.','A later use, or a later care operation, succeeds; the ablation leaves its precondition unsatisfied.'),
       'Commune':('The group relationship gains a shared cap, preserved differing positions, and explicit assent status.','Two paid offers/replies are read, compared and retained; the receiver separately reads the result.','The receiver proposes or consumes two units instead of the ablated four.'),
       'Integrate':('Two scoped interfaces gain an explicit dependency graph, conflicts, external requirements, and optional coupling.','Paid reconciliation produces the graph consumed by a separate retained model/organization.','The consumer predicts a previously unconnected outcome; expenditure executes repair then use.')}
    a=answers[name]
    row=dict(route=name,polarity=face,control=control,terminal_status=d['status'],movement_spending=d['spent'],
        consequence=codec.encode(consequence(e,result,name)),what_changed=a[0],how=a[1],what_becomes_possible=a[2],
        raw_audit_passed=report is not None,control_rejection=rejection,exact_restore=True,
        refs={k:codec.encode(v) for k,v in refs.items()},material_changes=changes,
        checkpoint_sha256=hashlib.sha256(cp.encode()).hexdigest())
    pack(out/'engine.checkpoint.json.gz',cp);pack(out/'transactions.json.gz',codec.dumps(e.world.journal()))
    pack(out/'access.checkpoint.json.gz',e.access.checkpoint());write(out/'result.json',row)
    if report: write(out/'audit.json',report)
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c2/*.py'),Path(__file__)})
    write(a.out/'execution_source.json',{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths})
    rows=[]
    for name in NAMES:
        for face in FACES:
            key=name.lower()+'-'+face
            good=witness(a.out/key,name,face);bad=witness(a.out/(key+'-ablated'),name,face,True)
            assert good['movement_spending']==bad['movement_spending']
            assert good['consequence']!=bad['consequence']
            rows.extend((good,bad));print(key+' causal pair passed',flush=True)
    write(a.out/'summary.json',dict(passed=True,cells=8,witnesses=16,matched_movement_costs=True,
        matching='Same setup, type, inputs, target and recipe; defining semantic result removed or bypassed. Core self-movement spending is matched; downstream work can differ as a consequence.',rows=rows))

if __name__=='__main__': main()
