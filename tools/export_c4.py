"""Export C4 causal pairs and valid blocked outcomes with raw reconstruction."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_c4.fixtures import *
from hle_unified import codec

ANSWERS={
 FAMILIES[0]:("The participant retains a limit of two after a four-unit concrete use.","The generated model controls paid Apply; its actual received outcome supplies Embody.","A changed demand selects two; the altered-model control selects five."),
 FAMILIES[1]:("An earlier shared cap of two becomes a renewed cap of one, retaining unequal positions.","A new offer addresses the exact shared prior; an independently paid reply feeds Commune and then Identify.","The participant selects one at the later demand; removing the renewal selects two."),
 FAMILIES[2]:("Observed supply becomes a shared limit of two and then two units of actual participation.","The exact Coordinate output authorizes Mobilize; actual consumption leaves four.","Later work observes four remaining, versus five under the altered shared limit."),
 FAMILIES[3]:("A ratified rule is understood by a receiver with its own larger limit.","Exact votes establish the rule; its generated content is offered and answered in the same group before Educate.","The learner proposes two units on a changed demand; altering the rule changes that answer to one."),
 FAMILIES[4]:("Two observed limits, six and two, become one conjunctive system retaining both sources.","Separate Organize outputs enter paid Integrate; Apply consumes the generated combined constraint.","Actual use leaves four units; omitting the tighter constraint leaves two."),
 "parent":("A model is eligible for release only after its declared children have succeeded.","Paid parent processing reconstructs exact child outcomes and a distinct-operation spending set.","The released model selects three; a matched blocked-parent control selects zero."),
 "context":("A model with cap five is qualified to cap one in a different context.","Explicit transfer combines the source hypothesis with an owned local intention and an actual local stock observation.","A changed demand selects one; omitting the local qualification selects four.")}

def write(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def pack(p,s): p.write_bytes(gzip.compress(s.encode(),mtime=0))
def source_manifest():
    paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c*/*.py'),Path(__file__),ROOT/'contracts/C4_Protocol_v1.json'})
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def witness(folder,name,control=False,failed=False):
    folder.mkdir(parents=True,exist_ok=False)
    e=setup(engine_type=Ablated if control else CruxCompositionEngine)
    before=sum(e.wallet(a)['energy'] for a in (ALICE,BOB,EVE))
    out=nested(e,failed=failed) if name=='parent' else context_case(e) if name=='context' else family(e,name)
    error=None; report=None
    try: report=audit(e.world.journal(),e.access.checkpoint())
    except ValueError as exc:
        if not control: raise
        error=str(exc)
    if control and not error: raise AssertionError('control unexpectedly passed')
    cp=e.checkpoint(); assert type(e).restore(cp).checkpoint()==cp
    focus=e.job_status(ALICE,'case')
    refs=dict(decision=out['decision'],parent=out.get('parent'),
              children=tuple((c.operation,c.output) for c in out.get('children',())))
    displayed=[]
    for c in out.get('children',()):
        jd=attrs(e.world.resolve(c.operation))
        try: value=read_data(e,c.output)
        except (KeyError,ValueError): value=dict(attrs(e.world.resolve(c.output)),kind='observation')
        displayed.append(dict(operation=codec.encode(c.operation),output=codec.encode(c.output),
            route=jd['movement'],polarity=jd['polarity'],status=jd['status'],spent=jd['spent'],content=codec.encode(tuple(sorted(value.items())))))
    parent=read_data(e,out['parent']) if out.get('parent') else None
    row=dict(name=name,control=control,failed_child=failed,outcome=out['outcome'],focus_spent=focus['spent'],
        active_modeled_work=before-sum(e.wallet(a)['energy'] for a in (ALICE,BOB,EVE)),
        what_changed=ANSWERS[name][0],how=ANSWERS[name][1],later_use=ANSWERS[name][2],
        refs={k:codec.encode(v) for k,v in refs.items()},children=displayed,
        parent=None if parent is None else codec.encode(tuple(sorted(parent.items()))),
        parent_complete=None if parent is None else parent['complete'],
        supply_consumed=attrs(e.world.head(SUPPLY.identity))['consumed'],
        raw_audit_passed=report is not None,control_rejection=error,exact_restore=True,
        checkpoint_sha256=hashlib.sha256(cp.encode()).hexdigest())
    pack(folder/'engine.checkpoint.json.gz',cp); pack(folder/'transactions.json.gz',codec.dumps(e.world.journal()))
    pack(folder/'access.checkpoint.json.gz',e.access.checkpoint()); write(folder/'result.json',row)
    if report: write(folder/'audit.json',report)
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False); manifest=source_manifest();write(a.out/'execution_source.json',manifest)
    rows=[]
    for i,name in enumerate((*FAMILIES,'parent','context')):
        good=witness(a.out/f'{i+1:02d}-healthy',name)
        bad=witness(a.out/f'{i+1:02d}-control',name,True)
        assert good['focus_spent']==bad['focus_spent'] and good['outcome']!=bad['outcome']
        rows.extend((good,bad)); print(name+' matched causal pair passed',flush=True)
    blocked=witness(a.out/'08-cancelled-child','parent',failed=True)
    assert not blocked['parent_complete'] and blocked['outcome']==0 and blocked['raw_audit_passed']
    unchanged=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==sha for f,sha in manifest.items())
    write(a.out/'summary.json',dict(passed=unchanged,source_unchanged=unchanged,causal_pairs=7,witnesses=15,
        matching='Identical initial world, input content, resources, participants, recipe and paid focus work. Intervene only at the final defining focus step. Consequent downstream work may differ.',rows=rows,blocked=blocked))
    if not unchanged: raise SystemExit(1)

if __name__=='__main__': main()
