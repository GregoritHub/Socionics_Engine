"""Independent C6 reconstruction. Imports no participant selector or executor.

Uses committed access receipts, declarative recipes and shared Model A geometry.
Candidate joins and ranking are recomputed here, independently of runtime policy.
"""
from itertools import product,combinations,islice
from .selection_records import NAMES,FACES,loads,dumps,demand_value
from .self_records import SELF_RECIPES
from .crossing_records import CROSSING_RECIPES
from .crux_composition_records import COMPOSITION_RECIPES
from .crux_shell_audit import audit as native_audit
from .crux_composition_audit import extent as native_extent
from .crux_audit import _access
from .crossing_audit import decode
from .material import attrs
from .operations import indexed
from .cognitive_routes import route


def extent(d):
    if not d.get('c6'):return native_extent(d)
    if d['required']!=1+d['scanned']+d['foreign_count']+33+d['evaluated'] or d['route_prepare']!=d['required'] or d['route_execute']!=0:
        raise ValueError('selection work extent differs')


def reference(s,cell):
    r=s['request'];a=r['actor'];d=s['need'];by={x['ref']:x for x in s['items']}
    def subset(k):return [x for name in k for x in s['items'] if x['data'].get('kind')==name]
    n=NAMES[cell//2] if cell<32 else 'Transfer';f=FACES[cell%2] if cell<32 else FACES[0]
    key=n.lower()+'-'+f+'-v1' if cell<32 else 'context-transfer-v1'
    recipe=({**SELF_RECIPES,**CROSSING_RECIPES,**({'context-transfer-v1':COMPOSITION_RECIPES['context-transfer-v1']})})[key]
    if n in ('Contemplate','Integrate'):it=combinations(subset(('personal',) if n=='Contemplate' else ('system',)),2)
    elif n=='Act':it=((),)
    elif n in ('Express','Theorize'):it=((x,) for x in subset(('intention',)))
    elif n in ('Embody','Organize'):it=((x,) for x in subset(('observation',)))
    elif n in ('Apply','Mobilize'):it=((x,) for x in subset(('shared',) if n=='Mobilize' else ('model','rule')))
    elif n in ('Identify','Understand'):it=product(subset(('shared',) if n=='Identify' else ('model','rule')),subset(('intention',)))
    elif n=='Commune':
        it=((x,y) for x,y in product(subset(('offer',)),subset(('reply',))) if x['ref'].identity.namespace=='c2.message' and x['data'].get('speaker')==a and x['data'].get('group')==r['group'] and y['data'].get('offer')==x['ref'] and y['data'].get('speaker')==r['peer'] and y['data'].get('group')==r['group'])
    elif n in ('Share','Coordinate','Educate'):
        source={'Share':('intention',),'Coordinate':('observation',),'Educate':('model','rule')}[n]
        it=((x,y,z) for x,y,z in product(subset(source),subset(('offer',)),subset(('reply',))) if
            (y['data'].get('source'),y['data'].get('speaker'),y['data'].get('receiver'),y['data'].get('group'))==(x['ref'],a,r['peer'],r['group']) and
            (z['data'].get('offer'),z['data'].get('speaker'),z['data'].get('receiver'),z['data'].get('group'))==(y['ref'],r['peer'],a,r['group']))
    elif n=='Institutionalize' and f=='accumulation':
        it=((x,y) for x,y in product(subset(('shared',)),subset(('observation',))) if y['data'].get('primitive')=='consume' and y['data'].get('outcome')=='succeeded')
    elif n=='Institutionalize':
        it=((x,y,z) for x in subset(('rule',)) for y,z in combinations(subset(('vote',)),2) if x['data'].get('status')=='draft' and y['data'].get('draft')==z['data'].get('draft')==x['ref'] and y['data'].get('group')==z['data'].get('group')==r['group'] and {y['data'].get('speaker'),z['data'].get('speaker')}=={a,r['peer']})
    else:
        it=product(s['foreign'],subset(('intention',)),[x for x in subset(('observation',)) if x['data'].get('outcome')=='succeeded' and 'available' in x['data']])
    batches=list(islice(it,r['alternatives']+1));deferred=len(batches)>r['alternatives'];batches=batches[:r['alternatives']];candidates=[]
    for bundle in batches:
        refs=tuple(x['ref'] for x in bundle);good=True
        social=n in ('Share','Coordinate','Educate','Identify','Mobilize','Institutionalize','Commune') or any(x['data'].get('kind') in ('shared','rule') for x in bundle)
        if social:
            g=s['group'];good=bool(g and g.get('context')==r['context'] and len(g.get('members',()))==2 and a in g['members'] and r['peer'] in g['members'])
        condition=n in ('Contemplate','Act','Integrate')
        good=good and (d['scope']=='condition')==condition
        if n=='Act':
            t=s['target'];good=good and t.get('custodian')==a
            if f=='accumulation':
                refs=(r['target'],r['tool'],r['repair_stock']);tool=s['tool'];stock=s['repair_stock']
                good=good and bool(s['acquired']) and t.get('condition')=='damaged' and bool(tool) and tool.get('condition')=='serviceable' and bool(stock) and stock.get('quantity',0)-stock.get('consumed',0)>=1
            else:refs=(r['target'],);good=good and t.get('condition')=='serviceable'
        if n in ('Express','Apply','Mobilize'):
            x=bundle[0]['data'];st=s['stock']
            good=good and bool(st) and st.get('custodian')==a and st.get('quantity',0)-st.get('consumed',0)>=1 and x.get('consent',True)
            if x['kind'] in ('shared','rule'):good=good and x.get('authorized',False)
            if x.get('status')=='governed_arrangement':good=good and x.get('authority')==a
            if n=='Apply' and f=='expenditure':good=good and x.get('coupled') is not False
        if n=='Organize':
            x=bundle[0]['data'];good=good and x.get('outcome')=='succeeded' and 'available' in x and (f!='expenditure' or x.get('owner')==a)
        routes=route(s['tim'],s['cursor'],recipe.elements,recipe.origin,recipe.destination,f)
        effort=sum(sum(x['charges'])+x['content_units'] for x in routes)+recipe.material_units+len(bundle)
        grounding=sum(2 if x['data'].get('kind')=='observation' else int(x['ref'].identity.namespace.startswith(('c2.','c3.','c4.'))) for x in bundle)
        destination=(cell//2)%4 if cell<32 else 3
        benefit=100*d['weights'][destination]+(30 if (f=='expenditure')==d['commit'] else -30)+80*int(d['collective'] and social)
        if n=='Transfer':benefit+=30;grounding=3
        good=bool(good and d['weights'][destination]>0 and min(s['wallet'])>=effort and all(x is not None for x in refs))
        candidates.append(dict(inputs=refs,eligible=good,benefit=benefit,grounding=grounding,effort=effort,score=benefit+20*grounding-effort))
    best=min(candidates,key=lambda x:(not x['eligible'],-x['score'],dumps(x['inputs']))) if candidates else dict(inputs=(),eligible=False,benefit=None,grounding=None,effort=None,score=None)
    return dict(best,examined=len(batches),deferred=deferred,recipe=key,origin=recipe.origin,destination=recipe.destination,face=f)


def audit(transactions,access_text,*,extent_check=extent,extended_flags=()):
    txs=tuple(transactions);report=native_audit(txs,access_text,extent_check=extent_check,extended_flags=('c6',*extended_flags))
    versions={v.ref:v for t in txs for v in t.versions};times={v.ref:t.at.tick for t in txs for v in t.versions}
    details,bindings=_access(access_text,versions,times);rows=[];snapshots={}
    for v in versions.values():
        if v.ref.identity.namespace!='c6.snapshot':continue
        s=loads(attrs(v)['payload']);r=s['request'];a=r['actor'];at=times[v.ref]
        own={ref:b for ref,(b,t) in bindings.items() if t<at and b.actor==a}
        b=own.get(r['demand'])
        if b is None or b.context!=r['context'] or b.target.identity!=r['target'].identity or b.cue!=r['cue'] or len(b.content)!=1 or b.content[0].relation!='c6.need' or demand_value(decode(b.content[0].object))!=s['need']:raise ValueError('forged or foreign owned demand')
        ps=[p for (actor,_),(p,t) in details.items() if actor==a and t<at]
        def known(ref):return {p.address.key:p.value for p in ps if p.source==ref}
        for key in ('target','stock','tool','repair_stock'):
            if known(r[key])!=s[key]:raise ValueError('hidden or altered material field')
        g=known(r['group']).get('payload');g=decode(g) if g else None
        if g!=s['group']:raise ValueError('unreceived shared membership')
        expected=[];foreign=[];scanned=0
        for b in own.values():
            if b.cue!=r['cue'] or b.target.identity!=r['target'].identity or b.endorsement.value in ('retracted','disputed'):continue
            if b.context!=r['context']:
                if len(b.content)==1 and b.content[0].relation in ('c3.data','c4.data'):
                    z=decode(b.content[0].object)
                    if z.get('kind')=='model':foreign.append(dict(ref=b.ref,data=z,binding=True))
                continue
            scanned+=1
            if len(b.content)==1 and b.content[0].relation in ('c2.data','c3.data','c4.data'):expected.append(dict(ref=b.ref,data=decode(b.content[0].object),binding=True))
        for p in ps:
            if p.address.key=='payload' and p.source.identity.namespace in ('c2.message','c3.message','c4.message'):
                z=decode(p.value)
                if z.get('target',r['target']).identity==r['target'].identity and z.get('context',r['context'])==r['context']:
                    scanned+=1;expected.append(dict(ref=p.source,data=z,binding=False))
            if p.address.key=='event' and p.source.identity.namespace=='u4.observation':
                z=known(p.source);target=z.get('target') or z.get('stock')
                if z.get('context')==r['context'] and z.get('actor')==a and target is not None and (r['stock'] is None or target.identity==r['stock'].identity):
                    scanned+=1;expected.append(dict(ref=p.source,data=dict(z,kind='observation'),binding=False))
        expected=sorted({x['ref']:x for x in expected}.values(),key=lambda x:dumps(x['ref']));foreign.sort(key=lambda x:dumps(x['ref']))
        if (expected[:r['limit']],foreign[:r['limit']],len(expected),len(foreign),scanned)!=(s['items'],s['foreign'],s['total_items'],s['foreign_total'],s['scanned']):raise ValueError('omitted, borrowed or fabricated accessible content')
        expected_acquired=[]
        for value in versions.values():
            rd=attrs(value)
            if value.ref.identity.namespace=='u4.receipt' and times[value.ref]<at and rd.get('actor')==a and rd.get('operation')=='acquire':
                inputs=indexed(rd,'input.')
                if inputs==(r['procedure'],r['context']):expected_acquired.append((r['procedure'],r['context'],value.ref))
        if tuple(expected_acquired)!=s['acquired']:raise ValueError('omitted or fabricated acquired capacity')
        for proc,context,receipt in s['acquired']:
            rd=attrs(versions[receipt])
            if times[receipt]>=at or rd['actor']!=a or rd['operation']!='acquire' or proc!=r['procedure'] or context!=r['context'] or proc not in indexed(rd,'input.'):raise ValueError('unearned acquired capacity')
        wallets=[attrs(x) for x in versions.values() if times[x.ref]<at and attrs(x).get('record_type')=='wallet' and attrs(x).get('actor')==a]
        if not wallets or (wallets[-1]['energy'],wallets[-1]['time'])!=s['wallet']:raise ValueError('selection budget differs from actual wallet')
        if attrs(versions[s['profile']])['tim']!=s['tim']:raise ValueError('false participant frame')
        snapshots[v.ref]=s
    for v in versions.values():
        if v.ref.identity.namespace!='c6.decision':continue
        d=attrs(v);job=attrs(versions[d['operation']]);s=snapshots[d['snapshot']];ballot=loads(attrs(versions[d['candidates']])['payload'])
        if len(ballot)!=33 or {x['cell'] for x in ballot}!=set(range(33)):raise ValueError('missing candidate cell')
        for candidate in ballot:
            expected=reference(s,candidate['cell'])
            if any(candidate[k]!=value for k,value in expected.items()):raise ValueError('candidate contract/rank differs: '+str(candidate['cell']))
        eligible=[x for x in ballot if x['eligible'] and x['score']>0]
        winner=min(eligible,key=lambda x:(-x['score'],x['cell'],dumps(x['inputs']))) if eligible else None
        if d['selected']!=(winner['cell'] if winner else None) or d['recipe']!=(winner['recipe'] if winner else None):raise ValueError('not the accountable best evaluated option')
        if job['spent']!=job['required'] or d['spent']!=job['spent'] or d['completion_claim'] is not False:raise ValueError('unpaid or falsely completed selection')
        if d['admission'] is not None:
            child=attrs(versions[d['admission']]);route_key='integrate-accumulation-v1' if d['recipe']=='context-transfer-v1' else d['recipe']
            if job['status']!='succeeded' or child['actor']!=s['request']['actor'] or child['requested_route']!=route_key or times[d['admission']]<=times[d['operation']]:raise ValueError('launch does not follow paid choice')
        rows.append(dict(decision=v.ref,recipe=d['recipe'],status=d['status'],failure=d['failure'],spent=d['spent'],candidate_count=len(ballot),eligible=len(eligible)))
    report.update(c6_selections=len(rows),c6_rows=rows)
    return report
