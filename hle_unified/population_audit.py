"""Reconstruct population costs and output claims from raw committed records.

No selector, scheduler or executor import. Native postconditions remain the
independent C1-C6 audit's responsibility. This validates the new summary layer.
"""
import re
from .material import attrs
from .operations import address


def audit_population(transactions, state):
    schema=state.get('schema')
    if schema=='hle-c7-population-v2':
        requests=state['requests'];request_types=['SelectionRequest']*len(requests)
    elif schema=='hle-c7-workflow-population-v3':
        encoded=state['requests']
        if (not encoded or any(set(r)!={'request_type','fields'} for r in encoded)
            or any(r['request_type'] not in ('SelectionRequest','WorkflowSelectionRequest','WorkflowCapacitySelectionRequest') for r in encoded)
            or not any(r['request_type']!='SelectionRequest' for r in encoded)):
            raise ValueError('invalid workflow population request registry')
        requests=[r['fields'] for r in encoded];request_types=[r['request_type'] for r in encoded]
    else:raise ValueError('unsupported population schema')
    versions={};heads={};charges={};turn_wallets={}
    for tx in transactions:
        match=re.match(r'^u4:c7-turn:(\d+):',tx.key)
        turn=int(match[1])+1 if match else None
        for v in tx.versions:
            d=attrs(v)
            if d.get('record_type')=='wallet' and turn is not None:
                before=attrs(versions[v.previous])
                key=(turn,d['actor'])
                prior=charges.get(key,(0,0))
                delta=tuple(before[k]-d[k] for k in ('energy','time'))
                if any(x<0 for x in delta):raise ValueError('population replenished resources')
                charges[key]=tuple(a+b for a,b in zip(prior,delta))
            versions[v.ref]=v;heads[v.ref.identity]=v
    actors=[r['actor'] for r in requests]
    signatures=[None]*len(actors);repeats=[0]*len(actors)
    counts=[0]*len(actors);stops=[None]*len(actors);cursor=0;total=0;complete=0
    successful_recipes={};repeated_outputs=0
    for number,row in enumerate(state['events'],1):
        runnable=[(cursor+i)%len(actors) for i in range(len(actors))
                  if stops[(cursor+i)%len(actors)] is None and counts[(cursor+i)%len(actors)]<state['episodes']]
        if not runnable:raise ValueError('events after horizon')
        index=runnable[0];actor=actors[index];cursor=(index+1)%len(actors)
        if row['turn']!=number or row['actor']!=actor or row['episode']!=counts[index]:
            raise ValueError('population fairness or episode continuity differs')
        charged=charges.pop((number,actor),(0,0))
        if row['charged']!=charged:raise ValueError('population charge differs from committed wallets')
        total+=charged[0]
        status=row['status']
        if status=='exhausted':
            wallet=[attrs(v) for v in heads.values() if attrs(v).get('record_type')=='wallet' and attrs(v).get('actor')==actor]
            if not wallet or min(wallet[0][k] for k in ('energy','time'))!=0:raise ValueError('false exhaustion')
            stops[index]='exhausted'
        elif status=='episode_complete':
            decision_namespace='c6.decision' if request_types[index]=='SelectionRequest' else 'c7ws.decision'
            if row['decision'].identity.namespace!=decision_namespace or row['decision'] not in versions:
                raise ValueError('wrong population decision family')
            d=attrs(versions[row['decision']])
            if (d['recipe'],d['failure'])!=(row['recipe'],row['failure']):raise ValueError('false decision summary')
            child_id=address('u4.operation',actor,row['key']+':movement').identity
            child=attrs(heads[child_id]) if child_id in heads else None
            if child:
                if row.get('native_status')!=child['status'] or row.get('output')!=(child.get('binding') or child.get('result')):
                    raise ValueError('false native completion summary')
                complete+=child['status']=='succeeded'
                if child['status']=='succeeded' and d['recipe'] is not None:
                    successful_recipes[d['recipe']]=successful_recipes.get(d['recipe'],0)+1
            elif 'native_status' in row:raise ValueError('invented native child')
            feedback=bool(child and child.get('result') and child.get('primitive') in ('inspect','consume','use','repair','care','damage'))
            if not feedback:
                counts[index]+=1
                if child and child['status']=='succeeded' and child.get('binding') and not any(k.startswith('public.') for k in child):
                    from .records import Account
                    account=versions[child['binding']].facet(Account)
                    signature=(actor,child['context'],child['content_target'],tuple((p.relation,p.object) for p in account.content))
                    same=signature==signatures[index]
                    repeats[index]=repeats[index]+1 if same else 1
                    repeated_outputs+=int(same)
                    signatures[index]=signature
                    if state['repeat_limit'] is not None and repeats[index]>=state['repeat_limit']:
                        if row.get('stop')!='unchanged_retained_result':raise ValueError('missing repetition stop')
                        stops[index]='unchanged_retained_result'
                    elif 'stop' in row:raise ValueError('unsupported repetition stop')
        elif status.startswith('feedback_'):
            if status in ('feedback_succeeded','feedback_failed','feedback_cancelled'):counts[index]+=1
        elif status not in ('working','blocked_by_other_work'):raise ValueError('unknown population state')
    if charges:raise ValueError('unreported population work')
    if signatures!=state['signatures'] or repeats!=state['repeats']:raise ValueError('retained-result repetition count differs')
    if counts!=state['counts'] or stops!=state['stopped'] or cursor!=state['cursor'] or len(state['events'])!=state['turn']:
        raise ValueError('population final counters differ')
    return dict(passed=True,turns=state['turn'],modeled_energy=total,native_completions=complete,
        successful_recipes=successful_recipes,repeated_outputs=repeated_outputs)
