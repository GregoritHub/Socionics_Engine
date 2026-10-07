"""Raw workflow Shell reconstruction. No executor, selector or scheduler import."""
from .workflow_selection_audit import audit as inherited_audit
from .workflow_records import WORKFLOW_RECIPES
from .workflow_reference import decode
from .selection_records import loads
from .material import attrs
from .operation_audit import indexed

def audit(transactions,access_text):
    txs=tuple(transactions);result=inherited_audit(txs,access_text)
    versions={v.ref:v for tx in txs for v in tx.versions}
    times={v.ref:tx.at.tick for tx in txs for v in tx.versions}
    heads={v.ref.identity:v for tx in txs for v in tx.versions}
    requests={v.ref:v for v in versions.values() if v.ref.identity.namespace=='c7sh.request'}
    rows=[];children=set();used=set()
    for v in versions.values():
        if v.ref.identity.namespace!='c7sh.admission':continue
        d=attrs(v);req=attrs(requests[d['request']]);m=loads(req['workflow'])
        op=attrs(versions[d['operation']]);recipe=WORKFLOW_RECIPES[d['requested_recipe']]
        route=d['requested_recipe'].removeprefix('workflow-')
        if not recipe.main or req['recipe']!=d['requested_recipe'] or m['recipe']!=req['recipe']:
            raise ValueError('workflow Shell requested recipe differs')
        if req['operation'].identity!=d['operation'].identity or times[d['request']]>=times[d['operation']] or d['request'] in used:
            raise ValueError('workflow Shell original obligation missing or reused')
        used.add(d['request'])
        if (d['origin'],d['destination'],d['polarity'])!=(recipe.origin,recipe.destination,recipe.polarity):
            raise ValueError('workflow Shell intended endpoint differs')
        if not op.get('u7') or op['status'] not in ('succeeded','failed') or times[d['operation']]>=times[v.ref]:
            raise ValueError('workflow Shell admission not paid and committed')
        if d['phase']!='admission' or d['owner']!=d['actor'] or req['owner']!=req['actor']:
            raise ValueError('workflow Shell owner or phase differs')
        for k in ('actor','target','context','cue','carrier','bearer','demand'):
            if req[k]!=d[k] or d[k]!=op[k]:raise ValueError('workflow Shell lost role or scope')
        if req['phase']!=d['phase'] or any(m[k]!=req[k] for k in ('actor','target','context','cue','key')):
            raise ValueError('workflow Shell original workflow differs')
        if d['admission_spent']!=op['spent'] or d['movement_complete'] is not False or d['pending_obligation']!=recipe.destination:
            raise ValueError('workflow Shell admission is not completion')
        enc=d['encounter'];decision=None if enc is None else attrs(versions[enc])
        if op['requested_route']!=route or op.get('encounter')!=enc:
            raise ValueError('workflow Shell encounter lineage differs')
        allowed=decision is not None and decision['route']==route
        if d['admitted']!=allowed or d['actual_intent']!=(None if decision is None else decision['route']):
            raise ValueError('workflow Shell admission disagrees with paid encounter')
        if d['actual_result_perspective']!='I':raise ValueError('workflow Shell admission fabricated destination')
        child=d['child'];completed=False;output=None;spent=0
        if child is not None:
            if not allowed or child in children or times[child]>=times[v.ref]:raise ValueError('workflow Shell unearned child')
            children.add(child);c=attrs(versions[child]);h=attrs(heads[child.identity])
            if not c.get('c7w') or c['recipe_key']!=m['recipe'] or any(c[k]!=d[k] for k in ('actor','context','cue','origin','destination','polarity')):
                raise ValueError('workflow Shell child changed contract')
            if c['key']!=m['key'] or c['content_target']!=m['target'] or indexed(c,'source.')!=m['inputs']:
                raise ValueError('workflow Shell child lost exact content')
            if (c['requested_stock'],c['requested_relation'],c['peer'],c['group'],c['query_clock'],decode(c['query_completed'])['done'])!=(m['stock'],m['relation'],m['peer'],m['group'],m['clock'],m['completed']):
                raise ValueError('workflow Shell child changed material, social or query roles')
            count=c['request_evidence_count']
            if tuple((c['evidence.delivery.'+str(i)],c['evidence.key.'+str(i)]) for i in range(count))!=m['evidence']:
                raise ValueError('workflow Shell child changed paid evidence')
            if m['elements'] and tuple(c['route.'+str(i)+'.element'] for i in range(c['route_count']))!=m['elements']:
                raise ValueError('workflow Shell changed supplied element path')
            completed=h['status']=='succeeded';output=h.get('binding') or h.get('result');spent=h['spent']
        elif allowed and d['failure'] is None:raise ValueError('workflow Shell permitted child absent')
        deformed=decision is not None and decision['base_route']==route and decision['route']!=route
        rows.append(dict(ref=v.ref,requested=m['recipe'],deformed=deformed,admitted=allowed,
            completed=completed,child=child,output=output,foreclosure=deformed,
            admission_spent=d['admission_spent'],movement_spent=spent,
            reason=None if decision is None else decision['reason']))
    for ref,v in requests.items():
        r=attrs(v);job=attrs(heads[r['operation'].identity])
        if job['status'] in ('succeeded','failed') and ref not in used:
            raise ValueError('workflow Shell completed gate lacks admission')
    result.update(workflow_shell_admissions=len(rows),workflow_shell_rows=rows,
        workflow_shell_deformed=sum(r['deformed'] for r in rows),
        workflow_shell_completed=sum(r['completed'] for r in rows))
    return result
