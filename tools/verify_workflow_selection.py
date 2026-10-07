"""Independent reconstruction from raw transactions and paid access receipts.

No participant policy or executor imports. Shared recipe tables and Model A
geometry are specifications; bundle joins and ranking are reconstructed here.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from itertools import permutations
from hle_unified.workflow_audit import audit as native_audit, extent as native_extent
from hle_unified.workflow_reference import decode, check_authored, schedule, answer
from hle_unified.workflow_records import WORKFLOW_RECIPES
from hle_unified.workflow_selection_records import demand_value, dumps, loads
from hle_unified.crux_audit import _access
from hle_unified.material import attrs
from hle_unified.operation_audit import indexed
from hle_unified.cognitive_routes import route

CELLS = (0, 1, 10, 11, 20, 21, 30, 31)

def extent(d):
    if not d.get('c7ws'): return native_extent(d)
    total = 1 + d['scanned'] + d['candidate_count'] + d['evaluated']
    if d['required'] != total or d['route_prepare'] != total or d['route_execute'] != 0:
        raise ValueError('unpaid workflow comparison extent')

def policy_cells(s):
    policy=s.get('policy','c7-workflow-selection-v1')
    if policy=='c7-workflow-selection-v1':return CELLS
    if policy=='c7-workflow-selection-v2':return tuple(i for i in range(32) if i//2 in (0,1,3,4,5,7,10,12,13,15))
    raise ValueError('unknown candidate policy')

def reference(s):
    r=s['request']; a=r['actor']; candidates=[]
    names=('Contemplate','Express','Share','Theorize','Embody','Act','Coordinate','Organize','Identify','Mobilize','Commune','Institutionalize','Understand','Apply','Educate','Integrate')
    cells=policy_cells(s)
    for cell in cells:
        n=names[cell//2]; f=('accumulation','expenditure')[cell%2]
        recipe=WORKFLOW_RECIPES['workflow-'+n.lower()+'-'+f+'-v1']
        size={'Contemplate':2,'Act':1,'Commune':3,'Integrate':2,'Express':1,'Theorize':1,'Embody':1,'Understand':2,'Apply':1,'Organize':0}[n]; bundles=[]
        for bundle in permutations(s['items'],size):
            ks=tuple(x['data']['kind'] for x in bundle)
            if n=='Contemplate' and not (set(ks)<={'intention','stance'} and dumps(bundle[0]['ref'])<dumps(bundle[1]['ref'])):continue
            if n=='Integrate' and not (ks==('system','system') and dumps(bundle[0]['ref'])<dumps(bundle[1]['ref'])):continue
            if n=='Act' and ks!=('activity',):continue
            if n=='Commune' and not (ks==('shared','offer','reply') and bundle[1]['data'].get('source')==bundle[0]['ref'] and bundle[2]['data'].get('offer')==bundle[1]['ref']):continue
            if n=='Express' and ks!=('intention',):continue
            if n=='Theorize' and ks[0] not in ('intention','personal'):continue
            if n=='Embody' and ks!=('activity',):continue
            if n=='Apply' and ks[0] not in ('system','rule'):continue
            if n=='Understand' and not (ks[0] in ('system','rule') and ks[1] in ('intention','stance')):continue
            if n=='Organize':continue
            bundles.append(bundle)
        if n=='Organize':
            observations=tuple(v for v in s['items'] if v['data']['kind']=='activity')
            bundles=[observations] if observations else []
        effort=recipe.material_units+sum(sum(x['charges'])+x['content_units'] for x in route(s['tim'],s['cursor'],recipe.elements,recipe.origin,recipe.destination,f))
        options=[]
        for bundle in bundles[:r['alternatives']]:
            good=len({t[0] for x in bundle for t in x['data'].get('tasks',())})<=8
            if n=='Act':
                x=bundle[0]['data']; t=s['target']
                good=x.get('target')==r['target'] and t.get('custodian')==a and r['peer'] is not None
                good=good and (t.get('owner')==a if f=='expenditure' else t.get('owner')==r['peer'] and r['relation'] is not None and bool(s['relation']))
            if n=='Commune':
                x,o,q=(v['data'] for v in bundle);g=s['group'];ms=() if not g else g.get('members',())
                good=(bool(g) and g.get('context')==r['context'] and len(ms)==2 and set(ms)=={a,r['peer']}
                    and x.get('group')==r['group'] and set(x.get('participants',()))==set(ms)
                    and o.get('speaker')==a and o.get('receiver')==r['peer'] and q.get('speaker')==r['peer'] and q.get('receiver')==a
                    and o.get('group')==r['group'] and q.get('group')==r['group'] and o.get('tasks')==x['tasks']
                    and all(t[5] in ms for v in (x,o,q) for t in v.get('tasks',())))
            if n in ('Express','Theorize','Embody','Organize','Understand','Apply'):
                good=good and crossing_reference(s,n,f,bundle)
            priority=s['need']['priorities'][('I','IT','WE','ITS').index(recipe.destination)]
            options.append(dict(cell=cell,recipe=recipe.key,inputs=tuple(x['ref'] for x in bundle),eligible=bool(good and priority),
                priority=priority,preference=int(s['need']['externalize']==(f=='expenditure')),effort=effort))
        def order(x):return (-x['priority'],-x['preference'],x['effort'],x['cell'],dumps(x['inputs']))
        best=min(options,key=lambda x:(not x['eligible'],*order(x))) if options else dict(cell=cell,recipe=recipe.key,inputs=(),eligible=False,
            priority=s['need']['priorities'][('I','IT','WE','ITS').index(recipe.destination)],preference=int(s['need']['externalize']==(f=='expenditure')),effort=effort)
        candidates.append(dict(best,examined=min(len(bundles),r['alternatives']),deferred=len(bundles)>r['alternatives']))
    cost=1+len(s['items'])+len(cells)+sum(x['examined'] for x in candidates)
    for row in candidates:row['eligible']=row['eligible'] and min(s['wallet'])>=cost+row['effort']
    winner=min((x for x in candidates if x['eligible']),key=order,default=None)
    return candidates,winner

def crossing_reference(s,name,face,bundle):
    actor=s['request']['actor'];r=s['request'];values=tuple(v['data'] for v in bundle);source=values[0]
    group=s['group']
    if source['kind']=='rule' or group is not None:
        if not group or group.get('context')!=r['context']:return False
        members=group.get('members',())
        if len(members)!=2 or set(members)!={actor,r['peer']}:return False
        if any(task[5] not in members for value in values for task in value.get('tasks',())):return False
        if source['kind']=='rule' and (source.get('group')!=r['group'] or set(source.get('participants',()))!=set(members)):return False
    if name=='Organize':
        events=[v['event'] for v in values]
        return len(set(events))==len(events) and not any(v['outcome']!='succeeded' or (face=='expenditure' and v.get('owner')!=actor) for v in values)
    if name not in ('Apply','Express'):return True
    allowed=source.get('consent',True)
    if name=='Apply' and source['kind']=='rule':allowed=source.get('authorized',False)
    elif name=='Apply' and source.get('authority') is not None:allowed=allowed and source['authority']==actor
    if not allowed:return False
    if face=='accumulation':return True
    task=answer(schedule((source,)),(),0)
    if not task or task[1]!='care' or task[5]!=actor:return False
    target,stock=s['target'],s['stock']
    return bool(r['stock'] is not None and stock and target.get('custodian')==actor
        and target.get('condition')=='serviceable' and target.get('wear',0)>0
        and stock.get('owner')==stock.get('custodian')==actor)

def audit(transactions,access_text):
    txs=tuple(transactions)
    report=native_audit(txs,access_text,extent_check=extent,extended_flags=('c7ws',))
    versions={v.ref:v for tx in txs for v in tx.versions}; times={v.ref:tx.at.tick for tx in txs for v in tx.versions}
    details,bindings=_access(access_text,versions,times); snapshots={}; decisions=[]; starts={}; ends={}
    for tx in txs:
        for v in tx.versions:
            d=attrs(v)
            if d.get('c7ws'):
                starts.setdefault(v.ref.identity,(v,d));ends[v.ref.identity]=(v,d)
            if v.ref.identity.namespace!='c7ws.snapshot':continue
            s=loads(d['payload']);r=s['request'];a=r['actor'];at=tx.at.tick
            paid=[p for (actor,_),(p,t) in details.items() if actor==a and t<at]
            owned={ref:b for ref,(b,t) in bindings.items() if b.actor==a and t<at}
            b=owned.get(r['demand'])
            if (b is None or (b.context,b.cue,b.target.identity)!=(r['context'],r['cue'],r['target'].identity)
                or b.endorsement.value in ('retracted','disputed') or len(b.content)!=1 or b.content[0].relation!='c7ws.need'
                or b.content[0].subject!=b.target or b.content[0].context!=r['context'] or demand_value(decode(b.content[0].object))!=s['need']):
                raise ValueError('forged or foreign outcome demand')
            def known(ref):return {p.address.key:p.value for p in paid if p.source==ref}
            for k in ('target','stock','relation'):
                if known(r[k])!=s[k]:raise ValueError('hidden or altered material input')
            g=known(r['group']).get('payload')
            if (decode(g) if g else None)!=s['group']:raise ValueError('unpaid group')
            ev=tuple((p.address.delivery,p.address.key) for p in paid if p.source==r['target'])
            if s['evidence']!=ev or not ev:raise ValueError('unpaid target evidence')
            expected=[]
            for ref in sorted(r['accessible'],key=dumps):
                if ref in owned:
                    b=owned[ref]
                    if ((b.context,b.cue,b.target.identity)!=(r['context'],r['cue'],r['target'].identity) or len(b.content)!=1
                        or b.content[0].relation!='c7w.data' or b.content[0].subject!=b.target or b.content[0].context!=r['context']
                        or b.endorsement.value in ('retracted','disputed')):raise ValueError('foreign or withdrawn accessible content')
                    value=decode(b.content[0].object);addresses=tuple((x.delivery,x.key) for x in b.particulars)
                    if ref.identity.namespace!='c7w.output':check_authored(value)
                elif ref.identity.namespace=='c7w.message':
                    ps=[p for p in paid if p.source==ref and p.address.key=='payload'];md=attrs(versions[ref])
                    if len(ps)!=1 or a not in indexed(md,'audience.') or md['context']!=r['context']:raise ValueError('unreceived addressed message')
                    value=decode(ps[0].value);addresses=tuple((p.address.delivery,p.address.key) for p in ps)
                    if value['target'].identity!=r['target'].identity:raise ValueError('wrong message target')
                elif ref.identity.namespace=='u4.observation':
                    value=dict(known(ref),kind='activity');addresses=tuple((p.address.delivery,p.address.key) for p in paid if p.source==ref)
                    if not {'event','outcome','context','primitive','actor','workflow_tick'}<=set(value) or value['context']!=r['context'] or value.get('target',r['target']).identity!=r['target'].identity:
                        raise ValueError('unpaid actual observation')
                else:raise ValueError('unpaid content')
                expected.append(dict(ref=ref,data=value,evidence=addresses))
            if expected!=s['items']:raise ValueError('fabricated accessible snapshot')
            profile=attrs(versions[s['profile']])
            if profile['actor']!=a or profile['tim']!=s['tim']:raise ValueError('wrong type frame')
            cursor=profile['initial_active'];wallet=None
            for prev in txs:
                if prev.at.tick>=at:break
                for obj in prev.versions:
                    z=attrs(obj)
                    if z.get('actor')!=a:continue
                    if z.get('record_type')=='wallet':wallet=(z['energy'],z['time'])
                    if 'route_count' in z and z.get('completed',0)>0:
                        left=max(0,z['completed']-z['recall_units']);cursor=z['active_start'];stop=False
                        for i in range(z['route_count']):
                            for j,charge in enumerate(indexed(z,f'route.{i}.charges.')):
                                if left<charge:stop=True;break
                                left-=charge;cursor=z[f'route.{i}.path.{j+1}']
                            if stop:break
                            if left<z[f'route.{i}.content_units']:break
                            left-=z[f'route.{i}.content_units'];cursor=z[f'route.{i}.element']
            if wallet!=s['wallet'] or cursor!=s['cursor']:raise ValueError('false wallet or paid cursor')
            snapshots[v.ref]=s
    for v in versions.values():
        if v.ref.identity.namespace!='c7ws.decision':continue
        d=attrs(v);s=snapshots[d['snapshot']];job=attrs(versions[d['operation']]);r=s['request']
        ballot=loads(attrs(versions[d['candidates']])['payload']);expected,winner=reference(s)
        if len(ballot)!=len(expected) or [x['cell'] for x in ballot]!=list(policy_cells(s)):raise ValueError('missing candidate cells')
        if any(any(x[k]!=value for k,value in y.items()) for x,y in zip(ballot,expected)):raise ValueError('candidate contract or rank differs')
        first=starts[d['operation'].identity][1]
        if first['policy']!=s.get('policy','c7-workflow-selection-v1'):raise ValueError('policy marker differs')
        if (first['snapshot'],first['candidates'],first['actor'],first['context'],first['input.0'])!=(d['snapshot'],d['candidates'],r['actor'],r['context'],r['demand']):raise ValueError('comparison source substitution')
        if (job['scanned'],job['candidate_count'],job['evaluated'])!=(len(s['items']),len(expected),sum(x['examined'] for x in expected)):raise ValueError('comparison counts differ')
        if job['spent']!=job['required'] or d['spent']!=job['spent'] or d['completion_claim'] is not False:raise ValueError('unpaid or false completion')
        if (d['selected'],d['recipe'])!=((winner['cell'],winner['recipe']) if winner else (None,None)):raise ValueError('not the best evaluated choice')
        ad=attrs(versions[d['admission']])
        if (ad['operation'],ad['child'],ad['failure'],ad['completion_claim'])!=(d['operation'],d['child'],d['failure'],False):raise ValueError('admission differs')
        if winner and job['status']=='succeeded' and d['child'] is None and d['failure'] is None:raise ValueError('choice withheld after paid comparison')
        if d['child'] is not None:
            child=attrs(versions[d['child']])
            if (job['status']!='succeeded' or winner is None or times[d['child']]<=times[d['operation']]
                or (child['actor'],child['context'],child['cue'],child['content_target'],child['recipe_key'],indexed(child,'source.'))!=
                    (r['actor'],r['context'],r['cue'],r['target'],winner['recipe'],winner['inputs'])
                or (child['requested_stock'],child['requested_relation'],child['peer'],child['group'])!=(r['stock'],r['relation'],r['peer'],r['group'])):
                raise ValueError('native child bypasses accountable choice')
        decisions.append(dict(selected=d['selected'],recipe=d['recipe'],child=d['child'],spent=d['spent'],status=d['status']))
    for ident,(v,d) in ends.items():
        if d['status'] in ('succeeded','failed') and not any(attrs(x).get('operation')==v.ref for x in versions.values() if x.ref.identity.namespace=='c7ws.decision'):
            raise ValueError('missing choice decision')
    report.update(workflow_selections=len(decisions),selection_rows=decisions)
    return report

def verify(folder, cases=8):
    import gzip, hashlib, json
    from hle_unified.compact import unseal
    from hle_unified.material import OperationStore
    rows=[]
    for path in sorted(folder.glob('*.json.gz')):
        text=gzip.decompress(path.read_bytes()).decode();schema=json.loads(text)['schema']
        if schema not in ('hle-full-crux-c7-workflow-selection-v1','hle-full-crux-c7-workflow-selection-v2'):raise ValueError('unknown selection schema')
        raw=unseal(text,schema)
        world=OperationStore.restore(raw['world']);control=path.name.endswith('-control.json.gz')
        native_audit(world.journal(),raw['access'],extent_check=extent,extended_flags=('c7ws',))
        rejection=None
        try:result=audit(world.journal(),raw['access'])
        except ValueError as exc:
            rejection=str(exc)
            if not control or 'choice withheld' not in rejection:raise
        else:
            if control:raise AssertionError('withheld choice passed')
            assert result['workflow_selections']==1
        rows.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),control=control,rejection=rejection))
    assert len(rows)==2*cases and sum(r['control'] for r in rows)==cases
    (folder/'independent_verification.json').write_text(json.dumps(dict(passed=True,worlds=2*cases,controls_rejected=cases,participant_replay=False,rows=rows),indent=2)+'\n')
    print(f'Independent raw reconstruction: {cases} ordinary worlds passed; {cases} controls rejected',flush=True)

if __name__=='__main__':verify(Path(sys.argv[1]),int(sys.argv[2]) if len(sys.argv)>2 else 8)
