"""Matched participant negotiation episodes; no release holdouts are used."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'baseline/HLE_Rebuild_R21B'
sys.dont_write_bytecode=True


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('reference','candidate'),required=True)
    p.add_argument('--domain',choices=('tool','pump'),required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.parent.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(ROOT/'reference_u12' if args.mode=='reference' else ROOT),str(BASE)]
    from tests_u12 import fixtures as f
    from hle_unified.institution_audit import audit
    from hle_unified import codec
    protocol=json.loads((ROOT/'contracts/U13_Interaction_Protocol_v1.json').read_text())
    samples=[]
    for batch in range(protocol['warmup_runs']+protocol['measured_runs']):
        gc.collect();start=time.perf_counter()
        e,d=f.active12(domain=args.domain)
        rule=d['institution']
        _,consequence=f.op12(e,'dense-delay','apply',actor=f.BOB,focus=rule['ref'],slots=f.slots12(e,f.BOB,args.domain),domain=args.domain)
        dispute=f.op12(e,'dense-dispute','dispute',actor=f.BOB,focus=consequence['ref'],domain=args.domain)[0]
        f.correct12(e,f.ALICE,'alice-correct',domain=args.domain)
        proposal=f.propose12(e,rule,'dense-review',intent='review',support=dispute['ref'],domain=args.domain)
        votes=f.vote12(e,proposal,'dense-review-votes',domain=args.domain)
        for vote in votes:f.expose12(e,f.ALICE,vote['ref'])
        f.op12(e,'dense-rejected-review','ratify',focus=proposal['ref'],expect=False,domain=args.domain)
        f.correct12(e,f.BOB,'bob-correct',domain=args.domain)
        counter=f.op12(e,'dense-counter','counter',actor=f.BOB,focus=proposal['ref'],slots=f.slots12(e,f.BOB,args.domain),domain=args.domain)[0]
        f.vote12(e,counter,'dense-counter-votes',domain=args.domain)
        revised=f.ratify12(e,counter,'dense-collective-revision',actor=f.BOB)
        run,practice=f.practice12(e,revised,'dense-corrected-work',actor=f.BOB,domain=args.domain)
        elapsed=time.perf_counter()-start
        t=time.perf_counter();report=audit(e.world.journal());evaluation=time.perf_counter()-t
        cp=e.checkpoint()
        protected={'checkpoint':hashlib.sha256(cp.encode()).hexdigest(),
            'transactions':hashlib.sha256(codec.dumps(e.world.journal()).encode()).hexdigest(),
            'views':[hashlib.sha256(e.participant_view(a).bytes().encode()).hexdigest() for a in (f.ALICE,f.BOB,f.EVE)],
            'charged_energy':report['charged_energy'],'charged_time':report['charged_time'],
            'transactions_count':report['transactions'],'operation_attempts':report['operation_attempts'],
            'refused_revision_status':e.job_status(f.ALICE,'dense-rejected-review')['status'],
            'final_gate':revised['gate'],'real_work_status':run['status']}
        checks={'audit':report['passed'],'refusal_preserved':protected['refused_revision_status']=='failed',
                'public_revision':revised['gate']=='self_check','actual_paid_work':run['status']=='succeeded',
                'delayed_public_bearer':consequence['bearer']==f.BOB}
        samples.append({'batch':batch,'warmup':batch<protocol['warmup_runs'],
                        'episode_seconds':elapsed,'offline_evaluation_seconds':evaluation,
                        'protected':protected,'checks':checks})
        if batch==protocol['warmup_runs']+protocol['measured_runs']-1:
            (args.out.parent/'final.checkpoint.json').write_text(cp)
            (args.out.parent/'final.audit.json').write_text(json.dumps(report,indent=2)+'\n')
        del e,d,cp;gc.collect()
        print(json.dumps({'batch':batch,'seconds':elapsed,'checks':checks}),flush=True)
    result={'schema':'hle-u13-interaction-measurement-v1','mode':args.mode,'domain':args.domain,
        'samples':samples,'median_episode_seconds':statistics.median(x['episode_seconds'] for x in samples if not x['warmup']),
        'passed':all(all(x['checks'].values()) for x in samples),
        'scope':protocol['timing_scope']}
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
