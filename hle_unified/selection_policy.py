"""Pure bounded candidate construction. No world, executor or truth access.
The same outcome weights compete across all origins. These are proposals;
only the native executor can establish completion.
"""
from itertools import combinations, product, islice
from .selection_records import NAMES,FACES,dumps,demand_value
from .self_records import SELF_RECIPES
from .crossing_records import CROSSING_RECIPES
from .cognitive_routes import route

def proposals(s):
    r=s['request']; actor=r['actor']; need=demand_value(s['need']); items=s['items']
    kinds={}
    for x in items: kinds.setdefault(x['data'].get('kind'),[]).append(x)
    def ks(*names): return [x for n in names for x in kinds.get(n,[])]
    def one(*names): return ((x,) for x in ks(*names))
    def pairs(*names): return combinations(ks(*names),2)
    def social():
        g=s['group']
        return g is not None and g.get('context')==r['context'] and len(g.get('members',()))==2 and actor in g['members'] and r['peer'] in g['members']
    def exchange(name):
        domain={'Share':'intention','Coordinate':'observation','Educate':'model'}[name]
        sources=ks(domain,* (('rule',) if name=='Educate' else ()))
        for source in sources:
            for off in ks('offer'):
                o=off['data']
                if o.get('source')!=source['ref'] or o.get('speaker')!=actor or o.get('receiver')!=r['peer'] or o.get('group')!=r['group']: continue
                for rep in ks('reply'):
                    d=rep['data']
                    if d.get('offer')==off['ref'] and d.get('speaker')==r['peer'] and d.get('receiver')==actor and d.get('group')==r['group']:
                        yield source,off,rep
    def commune():
        for o in ks('offer'):
            if o['ref'].identity.namespace!='c2.message' or o['data'].get('speaker')!=actor or o['data'].get('group')!=r['group']: continue
            for p in ks('reply'):
                if p['data'].get('offer')==o['ref'] and p['data'].get('speaker')==r['peer'] and p['data'].get('group')==r['group']: yield o,p
    def institutional(face):
        if face=='accumulation':
            return ((a,b) for a,b in product(ks('shared'),ks('observation')) if b['data'].get('primitive')=='consume' and b['data'].get('outcome')=='succeeded')
        def votes():
            for x in ks('rule'):
                if x['data'].get('status')!='draft': continue
                rows=[v for v in ks('vote') if v['data'].get('draft')==x['ref'] and v['data'].get('group')==r['group']]
                for a,b in combinations(rows,2):
                    if {a['data'].get('speaker'),b['data'].get('speaker')}=={actor,r['peer']}: yield x,a,b
        return votes()
    output=[]
    for number,name in enumerate(NAMES):
        for face in FACES:
            key=name.lower()+'-'+face+'-v1'; rec=(SELF_RECIPES if name in ('Contemplate','Act','Commune','Integrate') else CROSSING_RECIPES)[key]
            groups=()
            if name=='Contemplate': groups=pairs('personal')
            elif name=='Integrate': groups=pairs('system')
            elif name=='Act': groups=((),)
            elif name=='Commune': groups=commune()
            elif name in ('Express','Theorize'): groups=one('intention')
            elif name in ('Embody','Organize'): groups=one('observation')
            elif name in ('Identify','Understand'): groups=product(ks('shared') if name=='Identify' else ks('model','rule'),ks('intention'))
            elif name in ('Apply','Mobilize'): groups=one('shared') if name=='Mobilize' else one('model','rule')
            elif name in ('Share','Coordinate','Educate'): groups=exchange(name)
            elif name=='Institutionalize': groups=institutional(face)
            ranked=[]; examined=0; deferred=False
            for bundle in islice(groups,r['alternatives']+1):
                if examined==r['alternatives']: deferred=True;break
                examined+=1; reason=None; inputs=tuple(x['ref'] for x in bundle)
                social_route=name in ('Share','Coordinate','Educate','Identify','Mobilize','Institutionalize','Commune') or any(x['data'].get('kind') in ('shared','rule') for x in bundle)
                if social_route and not social(): reason='missing_received_membership'
                if need['scope']=='condition' and name not in ('Contemplate','Act','Integrate'): reason='quantity_content_does_not_meet_condition_demand'
                if need['scope']=='quantity' and name in ('Contemplate','Act','Integrate'): reason='condition_content_does_not_meet_quantity_demand'
                # Commune is reciprocal resource content in both schema families.
                if name=='Commune' and need['scope']=='condition': reason='quantity_content_does_not_meet_condition_demand'
                stock=s['stock']; target=s['target']; tool=s['tool']; repair=s['repair_stock']
                if name=='Act':
                    inputs=(r['target'],r['tool'],r['repair_stock']) if face=='accumulation' else (r['target'],)
                    if face=='accumulation':
                        if not s['acquired']: reason='practice_not_acquired'
                        elif target.get('condition')!='damaged': reason='no_observed_repair_need'
                        elif not tool or tool.get('condition')!='serviceable' or not repair or repair.get('quantity',0)-repair.get('consumed',0)<1: reason='missing_observed_repair_resources'
                    elif target.get('condition')!='serviceable': reason='no_observed_usable_target'
                    if target.get('custodian')!=actor: reason='no_observed_custody'
                if name in ('Express','Apply','Mobilize'):
                    x=bundle[0]['data']
                    if not stock or stock.get('custodian')!=actor or stock.get('quantity',0)-stock.get('consumed',0)<1: reason='no_observed_owned_stock'
                    if not x.get('consent',True) or x['kind'] in ('shared','rule') and not x.get('authorized',False): reason='no_participant_authority'
                    if x.get('status')=='governed_arrangement' and x.get('authority')!=actor: reason='foreign_arrangement'
                    if name=='Apply' and face=='expenditure' and x.get('coupled') is False: reason='uncoupled_model_requires_trial'
                if name=='Organize' and (bundle[0]['data'].get('outcome')!='succeeded' or 'available' not in bundle[0]['data'] or face=='expenditure' and bundle[0]['data'].get('owner')!=actor): reason='insufficient_observed_stock_authority'
                rows=route(s['tim'],s['cursor'],rec.elements,rec.origin,rec.destination,face)
                effort=sum(sum(x['charges'])+x['content_units'] for x in rows)+rec.material_units+len(bundle)
                grounding=sum(2 if x['data'].get('kind')=='observation' else 1 if x['ref'].identity.namespace.startswith(('c2.','c3.','c4.')) else 0 for x in bundle)
                benefit=100*need['weights'][number%4]+(30 if (face=='expenditure')==need['commit'] else -30)
                benefit += 80 if need['collective'] and social_route else 0
                score=benefit+20*grounding-effort
                if need['weights'][number%4]==0: reason='no_demand_for_this_effect'
                if min(s['wallet'])<effort: reason='unaffordable_predicted_work'
                if any(z is None for z in inputs): reason='missing_material_role'
                row=dict(cell=number*2+FACES.index(face),recipe=key,name=name,origin=rec.origin,destination=rec.destination,face=face,
                    inputs=inputs,eligible=reason is None,reason=reason or 'accessible_content_serves_owned_demand',score=score,effort=effort,benefit=benefit,grounding=grounding)
                ranked.append(row)
            if ranked:
                ranked.sort(key=lambda x:(not x['eligible'],-x['score'],dumps(x['inputs']))); row=ranked[0]
            else:
                row=dict(cell=number*2+FACES.index(face),recipe=key,name=name,origin=rec.origin,destination=rec.destination,face=face,
                    inputs=(),eligible=False,reason='missing_accessible_content',score=None,effort=None,benefit=None,grounding=None)
            output.append(dict(row,examined=examined,deferred=deferred))
    transfers=[]
    local=ks('intention'); observations=[x for x in ks('observation') if x['data'].get('outcome')=='succeeded' and 'available' in x['data']]
    from .crux_composition_records import COMPOSITION_RECIPES
    rec=COMPOSITION_RECIPES['context-transfer-v1']; examined=0; deferred=False
    for bundle in islice(product(s['foreign'],local,observations),r['alternatives']+1):
        if examined==r['alternatives']:deferred=True;break
        examined+=1
        rows=route(s['tim'],s['cursor'],rec.elements,rec.origin,rec.destination,'accumulation')
        effort=sum(sum(x['charges'])+x['content_units'] for x in rows)+3
        benefit=100*need['weights'][3]+(-30 if need['commit'] else 30)+30
        reason=None
        if need['scope']!='quantity' or not need['weights'][3]:reason='no_demand_for_this_effect'
        if min(s['wallet'])<effort:reason='unaffordable_predicted_work'
        transfers.append(dict(cell=32,recipe=rec.key,name='Integrate',origin='ITS',destination='ITS',face='accumulation',
            inputs=tuple(x['ref'] for x in bundle),eligible=reason is None,reason=reason or 'accessible_content_serves_owned_demand',
            score=benefit+60-effort,effort=effort,benefit=benefit,grounding=3))
    if transfers:
        transfers.sort(key=lambda x:(not x['eligible'],-x['score'],dumps(x['inputs']))); row=transfers[0]
    else:row=dict(cell=32,recipe=rec.key,name='Integrate',origin='ITS',destination='ITS',face='accumulation',inputs=(),eligible=False,reason='missing_accessible_content',score=None,effort=None,benefit=None,grounding=None)
    output.append(dict(row,examined=examined,deferred=deferred))
    return output

def choose(rows):
    ready=[x for x in rows if x['eligible'] and x['score']>0]
    return min(ready,key=lambda x:(-x['score'],x['cell'],dumps(x['inputs']))) if ready else None
