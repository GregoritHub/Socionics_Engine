"""Independent raw admission validator. No executor, policy or selector import.

C4 validates native semantic postconditions and situated access. U8 reconstructs
formation, effective scoped correction, practice, recurrence and reownership.
This layer checks that a paid intention launches only its declared movement.
"""
from .crux_composition_audit import audit as content_audit, extent
from .development_audit import audit as development_audit
from .self_records import SELF_RECIPES
from .crux_composition_records import COMPOSITION_RECIPES
from .crossing_records import CROSSING_RECIPES
from .material import attrs
from .operations import indexed


def audit(transactions,access_text,*,extent_check=extent,extended_flags=()):
    txs=tuple(transactions)
    result=content_audit(txs,access_text,extent_check=extent_check,extended_flags=extended_flags)
    result.update(development_audit(txs,extent_check=extent_check,extended_flags=('c1','c2','c3','c4',*extended_flags)))
    versions={v.ref:v for tx in txs for v in tx.versions};times={v.ref:tx.at.tick for tx in txs for v in tx.versions}
    heads={v.ref.identity:v for tx in txs for v in tx.versions}
    receipts=[];children=set()
    for tx in txs:
        for v in tx.versions:
            if v.ref.identity.namespace!='c5.admission': continue
            d=attrs(v); op=attrs(versions[d['operation']]); enc=d['encounter']
            request=attrs(versions[d['request']])
            if times[d['request']]>=times[d['operation']] or request['recipe']!=d['requested_recipe']:
                raise ValueError('original request missing or rewritten')
            if any(request[k]!=d[k] for k in ('actor','target','context','cue','carrier','bearer','demand','phase')):
                raise ValueError('request roles changed')
            recipe=(COMPOSITION_RECIPES if d['requested_recipe']=='context-transfer-v1' else SELF_RECIPES if op['requested_route'].split('-')[0] in ('contemplate','act','commune','integrate') else CROSSING_RECIPES)[d['requested_recipe']]
            if (d['origin'],d['destination'],d['polarity'])!=(recipe.origin,recipe.destination,recipe.polarity): raise ValueError('false requested endpoint')
            if not op.get('u7') or op['status'] not in ('succeeded','failed') or times[d['operation']]>=tx.at.tick: raise ValueError('uncommitted admission')
            if d['admission_spent']!=op['spent'] or d['movement_complete'] is not False or d['pending_obligation']!=recipe.destination: raise ValueError('admission is not completion')
            for k in ('actor','target','context','cue','carrier','bearer','demand'):
                if d[k]!=op[k]: raise ValueError('lost admission role or scope')
            shell_route='integrate-accumulation-v1' if d['requested_recipe']=='context-transfer-v1' else d['requested_recipe']
            if op['requested_route']!=shell_route: raise ValueError('changed requested movement')
            decision=None if enc is None else attrs(versions[enc])
            allowed=decision is not None and decision['route']==shell_route
            if d['actual_result_perspective']!='I': raise ValueError('admission fabricated a destination result')
            if d['admitted']!=allowed or d['actual_intent']!=(None if decision is None else decision['route']): raise ValueError('admission disagrees with paid encounter')
            child=d['child']; complete=False; later=None
            late=(d['phase']=='after_first_step' and decision is not None and decision['base_route']==shell_route and not allowed)
            if child is not None:
                if not (allowed or late) or child in children or times[child]>=tx.at.tick: raise ValueError('unearned or duplicate child')
                children.add(child); c=attrs(versions[child]); h=attrs(heads[child.identity])
                if any(c[k]!=d[k] for k in ('actor','context','cue','origin','destination','polarity')) or c['recipe_key']!=d['requested_recipe'] or c.get('content_target',c.get('target'))!=d['target']:
                    raise ValueError('child changed scope or contract')
                if indexed(c,'source.')!=indexed(request,'input.') or c['key']!=request['key']:
                    raise ValueError('child lost requested content')
                if late and (h['steps_completed']>1 or h['status'] in ('ready','succeeded')):
                    raise ValueError('deformed continuation escaped its first-step boundary')
                complete=h['status']=='succeeded';later=h.get('binding') or h.get('result')
            elif (allowed or late) and d['failure'] is None: raise ValueError('lost allowed child without failure')
            deformed=decision is not None and decision['base_route']==shell_route and decision['route']!=decision['base_route']
            receipts.append(dict(ref=v.ref,requested=d['requested_recipe'],deformed=deformed,admitted=allowed,
                completed=complete,child=child,output=later,admission_spent=d['admission_spent'],
                # Simulation observables only. An attempted placement is never
                # accepted as realization of the requested destination.
                foreclosure=deformed and d['phase']=='admission',
                early_substitution=False,attempted_personal_placement=False,
                actual_result_perspective=d['actual_result_perspective']))
    by_ref={x['ref']:x for x in receipts}
    for v in versions.values():
        if v.ref.identity.namespace!='c5.interruption': continue
        d=attrs(v);a=by_ref[d['admission']];ad=attrs(versions[d['admission']]);job=attrs(versions[d['operation']])
        enc=attrs(versions[d['encounter']]);step=attrs(versions[d['intermediate']])
        if d['encounter']!=ad['encounter'] or d['operation'].identity!=ad['child'].identity:
            raise ValueError('interruption changed its admitted lineage')
        if not a['deformed'] or ad['phase']!='after_first_step' or job['status']!='cancelled' or job['steps_completed']!=1:
            raise ValueError('unearned active interruption')
        if job['last_step']!=d['intermediate'] or d['spent']!=job['spent'] or d['original_obligation_met'] is not False:
            raise ValueError('lost partial work or false completion')
        if d['replacement']!=attrs(versions[ad['operation']]).get('binding') or d['actual_intent']!=enc['route']:
            raise ValueError('replacement is not the actual retained attribution')
        if d['requested_destination']!=job['destination'] or d['requested_polarity']!=job['polarity'] or d['actual_result_perspective']!='I':
            raise ValueError('interruption erased original destination or polarity')
        if step['index']!=0 or step['operation'].identity!=d['operation'].identity:
            raise ValueError('wrong intermediate operation')
        a.update(early_substitution=True,attempted_personal_placement=job['destination']!='I',intermediate=d['intermediate'],replacement=d['replacement'])
    result.update(c5_admissions=len(receipts),c5_admitted=sum(x['admitted'] for x in receipts),
        c5_deformed=sum(x['deformed'] for x in receipts),c5_completed=sum(x['completed'] for x in receipts),c5_rows=receipts)
    return result
