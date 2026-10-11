"""Independent raw-checkpoint verifier. No engine, candidate policy or fixture imports."""
from pathlib import Path
import json,gzip,hashlib
from independent_wire import raw_versions,values,canonical
R=Path(__file__).resolve().parent
J=lambda p:json.loads(p.read_text())
count=0;ledgers=[];results=[]
for folder in sorted((R/'attempt_02').glob('*/*')):
    prof=J(folder/'profile.json')
    for path in sorted(folder.glob('*.json.gz')):
        text=gzip.open(path,'rt').read();report=J(path.with_suffix(''))
        assert hashlib.sha256(text.encode()).hexdigest()==report['sha256']
        rows=[(v['ref']['identity']['namespace'],values(v)) for v in raw_versions(text)]
        responses=[d for ns,d in rows if ns=='u8.response'];practices=[d for ns,d in rows if ns=='u8.practice']
        name=path.name[:-8]
        if name in ('mixed','novel3'):
            d=responses[-1];expected=name=='mixed' and prof['load']=='unfamiliar'
            assert d['completed_demand']==expected
            assert [d[f'row.{i}.route'] for i in range(3)]==(['engage']*3 if expected else ['engage','engage','wait'] if name=='mixed' else ['wait']*3)
        if name.endswith('-old'):
            expected=not(name=='observed-old' and prof['fresh']=='fresh_pattern')
            assert report['accepted']==expected
            if not expected:assert report['unchanged']
        if name=='observed-fresh':assert report['accepted']
        # Independently reconstruct recertification cutoffs from paid job recall and practices.
        jobs={canonical(d['ref']) if 'ref' in d else '':d for ns,d in []}
        versions=list(raw_versions(text));byref={canonical(v['ref']):values(v) for v in versions}
        for ns,d in rows:
            if ns!='u8.treatment' or d['kind']!='reownership':continue
            job=byref[canonical(d['operation'])]
            if 'experimental_fresh_rule' not in job:continue
            rule=job['experimental_fresh_rule'];seq={canonical(x['event']):i for i,x in enumerate(responses)}
            recalled=[v for k,v in job.items() if k.startswith('recalled.')]
            before=[x for x in practices if x['binding'] in recalled]
            expected_scan=len(before)+sum(1 for x in responses if seq[canonical(x['event'])]<=max((seq[canonical(y['event'])] for y in before),default=-1))
            # Scan cost is checked against available history at job creation, below via transaction prefix.
            if rule=='historical':continue
            cutoff=-1
            for ex in before:
                x=byref[canonical(ex['response'])]
                residual=any(x[f'row.{i}.patterns'] and x[f'row.{i}.route']!=x[f'row.{i}.base_route'] for i in range(x['load']))
                if not x['completed_demand'] and not x['supported'] and residual and (rule=='fresh_pattern' or x['load']<=2):cutoff=max(cutoff,seq[canonical(x['event'])])
            assert all(seq[canonical(byref[canonical(ref)]['event'])]>cutoff for ref in d['returns'])
        seenresp=[];seenpractice=[]
        for ns,d in rows:
            if ns=='u8.response':seenresp.append(d)
            if ns=='u8.practice':seenpractice.append(d)
            if d.get('record_type')=='operation' and d.get('u8') and d.get('purpose')=='reown' and d.get('experimental_fresh_rule','historical')!='historical':
                assert d['experimental_scan_units']==len(seenresp)+len([x for x in seenpractice if x['pattern']==d['pattern']])
        if name.startswith('supported-'):
            x=responses[-1];required=name=='supported-True';assert x['completed_demand'] and x['supported']
            assert x['row.0.known.approval_required']==required
            assert x['row.0.patterns']
            assert not practices[-1]['independent']
            ledgers.append({'profile':folder.parent.name,'type':folder.name,'actual_required':required,'broad_candidate_increment':1,'contingent_candidate_increment':int(not required),'response':x['ref'],'observation':practices[-1]['observation'],'meaning':'observed support evidence; no reinforcement state changed'})
        count+=1;results.append({'profile':folder.parent.name,'type':folder.name,'case':name,'accepted':report.get('accepted'),'completed':report.get('response',{}).get('completed_demand')})
# Exact full native checkpoints, including costs, for baseline mode.
equalities=0
for tim in ('iee','sli'):
    for p in (R/'attempt_02/reference'/tim).glob('*.json.gz'):
        assert gzip.open(p,'rb').read()==gzip.open(R/'attempt_02/total-historical'/tim/p.name,'rb').read();equalities+=1
assert count==98, ('incomplete matrix',count)
assert equalities==14
(R/'audit.json').write_text(json.dumps({'passed':True,'native_checkpoints':count,'baseline_exact_equalities':equalities,'results':results,'maintenance_evidence':ledgers},indent=2))
print('PASS',count,'checkpoints;',equalities,'exact baseline comparisons')
