"""Produce actual R13 run evidence; distinguish the still-unexecuted R14–R21 gates."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hle.development_evaluation import *
from hle.model_a import TYPES,stack
from hle import content_operators as ops
from tests_r13.test_roles import specimens,run_role


def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(p)


def save_checkpoint(out,name,w):
    data=w.checkpoint().encode();p=out/(name+'.json.gz');p.write_bytes(gzip.compress(data,mtime=0))
    return {'file':p.name,'sha256_uncompressed':hashlib.sha256(data).hexdigest(),'bytes_uncompressed':len(data),'events':len(w._journal),'accounting':accounting(w)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r13/panels');args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    controls=[]; checkpoints=[]
    expected={'both_retained':12,'no_instruction':3,'help_only':3,'search_only':3,'boundary_only':3,'both_without_return':0}
    for condition,n in expected.items():
        w,row=crossing(condition);row['expected']=n;row['passed']=row['successes']==n and row['helper_units_after_training']==0
        row['accounting']=accounting(w);controls.append(row)
        if condition in ('both_retained','help_only'): checkpoints.append(save_checkpoint(out,condition,w))
    types=[]
    for tim in TYPES:
        w,row=crossing(tim=tim);row['passed']=row['successes']==12 and row['helper_units_after_training']==0;row['accounting']=accounting(w);types.append(row)
    role_rows=[]
    for tim in TYPES:
        w=world(tim=tim);fixed=stack(tim)
        for ie in ('ne','si','fi','te','ni','se','ti','fe'):
            output,data=run_role(w,ie,'role:'+ie)
            if w.content(LEARNER,output)!=data: raise AssertionError('owned result differs')
            role_rows.append({'tim':tim,'aspect':ie,'output':data,'active':w.processing_state(LEARNER).active,'fixed_stack_unchanged':stack(tim)==fixed,'passed':data['valid'] and w.processing_state(LEARNER).active==ie})
        accounting(w)
    mw,personal=distinct_personal_histories();checkpoints.append(save_checkpoint(out,'two_personal_histories',mw))
    rw,revisions=meaning_history();checkpoints.append(save_checkpoint(out,'meaning_revisions',rw))
    trace=continuation_trace();continuation=all_prefix_continuation(trace);checkpoints.append(save_checkpoint(out,'partial_continuation_trace',trace))
    write(out/'crossing_controls.json',controls);write(out/'all_type_crossing.json',types);write(out/'eight_role_panel.json',role_rows)
    write(out/'personal_histories.json',personal);write(out/'meaning_revisions.json',revisions);write(out/'continuation.json',continuation);write(out/'checkpoints.json',checkpoints)
    result={'schema':'hle-r13-behavior-panels-v1','crossing_controls':{r['condition']:r['successes'] for r in controls},
        'all_type_crossing':{'types':len(types),'held_out_demands':12*len(types),'successful_returns':sum(r['successes'] for r in types)},
        'eight_role_cases':len(role_rows),'two_personal_histories':personal,'continuation':continuation,
        'passed':all(r['passed'] for r in controls+types+role_rows) and personal['actions_completed'] and personal['exact_continuation'] and continuation['passed'],
        'scope':'Harness-supplied demands and training. R13 integration only; not R18 individuation, R19 clearance or R21 sustained evaluation.',
        'future_480_r21_cases_executed':0}
    write(out/'summary.json',result);print(json.dumps(result))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
