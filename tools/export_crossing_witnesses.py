"""24 causal pairs with committed raw evidence and exact continuation."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from tests_c3.fixtures import *
from hle_unified.crossing_audit import audit
from hle_unified import codec
from hle_unified.operations import address

ANSWERS={
 'Express':('An intention obtains actual stock readiness or paid consumption.','Paid N/T content generates a physical command; the workshop law commits the event.','A later allocation uses observed readiness or actual remaining supply.'),
 'Share':('A personal cap enters shared understanding with independent receiver limits and assent.','An addressed offer and paid receiver answer are checked against the source; differences remain.','The receiver proposes or performs its own later participation at the understood cap.'),
 'Theorize':('An owned intention becomes a scoped uncertain allocation model.','A paid N transformation records a conditional formula, assumptions and a possible test.','A changed demand is evaluated from the generated model and can lead to actual consumption.'),
 'Embody':('An actual stock observation becomes an owned interpretation or decision policy.','The actor pays for the observation and T/N handoff into retention.','A later changed demand uses the observed limit in its own decision.'),
 'Coordinate':('Actual observed supply becomes jointly understood participation constraints.','A stock inspection is offered; the receiver answers and preserves its distinct capacity.','A later receiver proposal or performance uses the reconciled constraint.'),
 'Organize':('Observed limits become an explicit resource dependency model or governed arrangement.','Paid T work retains sample provenance and separates physical custody from inferred regularity.','A later demand is governed by the generated arrangement and current stock.'),
 'Identify':('Shared expectations gain an actor-owned interpretation or explicit stance.','Paid F work compares received shared content with the actor’s own cap and consent.','Its later choice retains qualification or refusal instead of overwriting assent.'),
 'Mobilize':('An accepted shared intention becomes actual readiness or consumption.','Paid S work makes an explicit command; each actor pays and can exercise its allowance once.','A later task uses actual readiness or remaining stock.'),
 'Institutionalize':('Shared practice becomes a draft rule or a ratified public rule.','A witnessed group practice supports a draft; two separate paid votes refer to that exact draft.','A draft supports assessment; ratification permits bounded voluntary governed performance.'),
 'Understand':('A generated system gains an actor-owned interpretation or decision policy.','Paid N work relates the conditional model to the actor’s own limits and stance.','A changed demand is answered from retained meaning, with no competence granted by possession.'),
 'Apply':('A generated model becomes a one-unit concrete trial or task execution.','Paid T work instantiates the model and native consumption preserves actual outcomes.','A later task uses remaining stock; a failed model or trial remains visible.'),
 'Educate':('A system enters jointly examined understanding with a receiver-owned answer and question.','Paid N/F work consumes an actual teaching offer and a separately paid learner reply.','The learner uses the learned constraint at a different demand; attendance grants no skill.')}

def write(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def pack(path,value): path.write_bytes(gzip.compress(value.encode(),mtime=0))

def witness(folder,name,face,control):
    folder.mkdir(parents=True,exist_ok=False)
    e=setup_c3(engine_type=Ablated if control else CrossingEngine)
    before={x:e.world.head(x.identity) for x in (SUPPLY,ref('bob-consumables'))}
    out=cell(e,name,face); rejection=None; report=None
    try: report=audit(e.world.journal(),e.access.checkpoint())
    except ValueError as exc:
        if not control: raise
        rejection=str(exc)
    if control and not rejection: raise AssertionError('control passed semantic audit')
    cp=e.checkpoint(); q=type(e).restore(cp); assert cp==q.checkpoint()
    d=e.job_status(ALICE,'case'); recipe=CROSSING_RECIPES[out['request'].recipe]
    refs=dict(inputs=out['inputs'],output=out['result'],downstream=out['downstream'],
        steps=tuple(address('c3.step',ALICE,'case',i) for i in range(len(recipe.steps))))
    if out.get('event'): refs['downstream_event']=out['event']
    changes=[]
    for ref_,old in before.items():
        new=e.world.head(ref_.identity)
        changes.append(dict(before=codec.encode(old.ref),after=codec.encode(new.ref),
            before_consumed=attrs(old)['consumed'],after_consumed=attrs(new)['consumed']))
    row=dict(route=name,polarity=face,control=control,terminal_status=d['status'],movement_spending=d['spent'],
        consequence=consequence(e,out),consumer_actor=out['consumer_actor'].key,
        what_changed=ANSWERS[name][0],how=ANSWERS[name][1],what_becomes_possible=ANSWERS[name][2],
        refs={k:codec.encode(v) for k,v in refs.items()},material_changes=changes,
        raw_audit_passed=report is not None,control_rejection=rejection,exact_restore=True,
        checkpoint_sha256=hashlib.sha256(cp.encode()).hexdigest())
    pack(folder/'engine.checkpoint.json.gz',cp); pack(folder/'transactions.json.gz',codec.dumps(e.world.journal()))
    pack(folder/'access.checkpoint.json.gz',e.access.checkpoint()); write(folder/'result.json',row)
    if report: write(folder/'audit.json',report)
    return row

def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c*/*.py'),Path(__file__)})
    write(args.out/'execution_source.json',{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths})
    rows=[]
    for name in PATHS:
        for face in FACES:
            key=name.lower()+'-'+face
            good=witness(args.out/key,name,face,False); bad=witness(args.out/(key+'-ablated'),name,face,True)
            assert good['movement_spending']==bad['movement_spending'] and good['consequence']!=bad['consequence']
            rows.extend((good,bad)); print(key+' causal pair passed',flush=True)
    write(args.out/'summary.json',dict(passed=True,cells=24,witnesses=48,matched_movement_costs=True,
        matching='Identical setup, actor type, main recipe, evidence, group, inputs, requested demand and paid progression. Only the last defining result is removed in the designated main case. Later work and spending may differ because the output differs.',rows=rows))

if __name__=='__main__': main()
