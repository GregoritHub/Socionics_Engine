"""Raw active workflow interruption reconstruction. No executor or selector import."""
from .workflow_shell_audit import audit as inherited_audit
from .workflow_records import WORKFLOW_RECIPES
from .workflow_reference import decode
from .selection_records import loads
from .material import attrs
from .operation_audit import indexed
from .records import Account, Occurrence, Proposition, TimeScope

def audit(transactions,access_text):
    txs=tuple(transactions);result=inherited_audit(txs,access_text)
    versions={v.ref:v for tx in txs for v in tx.versions}
    times={v.ref:tx.at.tick for tx in txs for v in tx.versions}
    moments={v.ref:tx.at for tx in txs for v in tx.versions}
    heads={v.ref.identity:v for tx in txs for v in tx.versions}
    requests={v.ref:v for v in versions.values() if v.ref.identity.namespace=='c7shi.request'}
    rows=[];children=set();used=set()
    for v in versions.values():
        if v.ref.identity.namespace!='c7shi.admission':continue
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
        if d['phase']!='after_first_step' or d['owner']!=d['actor'] or req['owner']!=req['actor']:
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
        late=decision is not None and decision['base_route']==route and not allowed
        if child is not None:
            if not (allowed or late) or child in children or times[child]>=times[v.ref]:raise ValueError('workflow Shell unearned child')
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
            if late and (h['steps_completed']>1 or h['status'] in ('ready','succeeded')):
                raise ValueError('workflow interruption escaped first boundary')
            completed=h['status']=='succeeded';output=(h.get('binding') or h.get('result')) if completed else None;spent=h['spent']
        elif (allowed or late) and d['failure'] is None:raise ValueError('workflow Shell permitted child absent')
        deformed=decision is not None and decision['base_route']==route and decision['route']!=route
        rows.append(dict(ref=v.ref,requested=m['recipe'],deformed=deformed,admitted=allowed,
            completed=completed,child=child,output=output,foreclosure=False,early_substitution=False,attempted_personal_placement=False,
            admission_spent=d['admission_spent'],movement_spent=spent,
            reason=None if decision is None else decision['reason']))
    for ref,v in requests.items():
        r=attrs(v);job=attrs(heads[r['operation'].identity])
        if job['status'] in ('succeeded','failed') and ref not in used:
            raise ValueError('workflow Shell completed gate lacks admission')
    by_ref={row['ref']:row for row in rows}
    for v in versions.values():
        if v.ref.identity.namespace!='c7shi.interruption':continue
        d=attrs(v);a=by_ref[d['admission']];ad=attrs(versions[d['admission']])
        job=attrs(versions[d['operation']]);step=attrs(versions[d['intermediate']])
        enc=attrs(versions[d['encounter']])
        if d['encounter']!=ad['encounter'] or d['operation'].identity!=ad['child'].identity:
            raise ValueError('workflow interruption lost admitted lineage')
        if not a['deformed'] or job['status']!='cancelled' or job['steps_completed']!=1 or times[d['operation']]>=times[v.ref]:
            raise ValueError('workflow interruption lacks actual first-step cancellation')
        boundary=job['recall_units']+sum(indexed(job,'route.0.charges.'))+job['route.0.content_units']
        if job['last_step']!=d['intermediate'] or d['spent']!=job['spent'] or job['spent']!=boundary or d['original_obligation_met'] is not False:
            raise ValueError('workflow interruption lost paid intermediate or spending')
        if job.get('binding') is not None or job.get('public.0') is not None:
            raise ValueError('workflow interruption fabricated retained or material result')
        cancellation=versions.get(job.get('result'))
        if cancellation is None or cancellation.ref.identity.namespace!='u4.event' or cancellation.occurrence!=Occurrence.ACTUAL_EVENT:
            raise ValueError('workflow interruption lacks actual cancellation receipt')
        cd=attrs(cancellation);prior=versions[d['operation']].previous
        prior_job=attrs(versions[prior])
        # Cancellation changes no material. Native provenance is the prior job
        # followed by its exact ordered inputs, deduplicated without reordering.
        sources=tuple(dict.fromkeys((prior,)+indexed(prior_job,'input.')))
        at=moments[d['operation']]
        expected_account=Account(prior,
            (Proposition(prior,'outcome','cancelled',prior_job['context'],TimeScope(at,None)),),
            at,None,sources)
        if (cd['outcome']!='cancelled' or cd['operation']!=prior or cd['event']!=cancellation.ref
            or cancellation.facet(Account)!=expected_account
            or times[cancellation.ref]!=times[d['operation']]
            or any(cd[k]!=job[k] for k in ('actor','context','primitive'))
            or indexed(cd,'participant.')!=indexed(prior_job,'participant.')
            or any(k in cd for k in ('target','stock','relation','owner','custodian','wear','condition','available','consumed','relation_status'))):
            raise ValueError('workflow cancellation receipt claims completion or changed material')
        if d['replacement']!=attrs(versions[ad['operation']]).get('binding') or d['actual_intent']!=enc['route']:
            raise ValueError('workflow interruption replacement is not retained attribution')
        if d['requested_destination']!=job['destination'] or d['requested_polarity']!=job['polarity'] or d['actual_result_perspective']!='I':
            raise ValueError('workflow interruption changed endpoint or polarity')
        if d['intermediate'].identity.namespace!='c7w.step' or step['index']!=0 or step['operation'].identity!=d['operation'].identity:
            raise ValueError('workflow interruption has wrong first semantic step')
        a.update(early_substitution=True,attempted_personal_placement=job['destination']!='I',
            intermediate=d['intermediate'],replacement=d['replacement'])
    for a in rows:
        if a['deformed'] and a['child'] is not None and attrs(heads[a['child'].identity])['status']=='cancelled' and not a['early_substitution']:
            raise ValueError('workflow cancellation lacks interruption record')
    result.update(workflow_interruption_admissions=len(rows),workflow_interruption_rows=rows,
        workflow_interruption_deformed=sum(r['deformed'] for r in rows),
        workflow_interruption_completed=sum(r['completed'] for r in rows))
    return result
