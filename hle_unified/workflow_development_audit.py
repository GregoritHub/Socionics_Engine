"""Bounded workflow Shell diagnostics reconstructed from committed history."""
from .workflow_interruption_audit import audit as inherited_audit
from .material import attrs
from .development_values import attrs as development_attrs
from .operation_audit import indexed
from .shell_audit import effects


def audit(transactions, access_text):
    txs=tuple(transactions)
    result=inherited_audit(txs,access_text)
    admitted={r['ref']:r for r in result['workflow_shell_rows']+result['workflow_interruption_rows']}
    versions={};patterns={};corrections=[];seen_targets={};rows=[]
    for tx in txs:
        for v in tx.versions:
            versions[v.ref]=v
            ns=v.ref.identity.namespace
            if ns=='u7.pattern':patterns[v.ref]=attrs(v)
            if ns=='u8.correction':corrections.append(development_attrs(v))
            if v.ref not in admitted:continue
            a=admitted[v.ref];d=attrs(v)
            if d['encounter'] is None:continue
            enc=attrs(versions[d['encounter']]);op=attrs(versions[d['operation']])
            related={p:pd for p,pd in patterns.items()
                if (pd['owner'],pd['context'],pd['cue'],pd['trigger'])==
                   (d['actor'],d['context'],d['cue'],enc.get('known.trigger'))}
            applied=indexed(enc,'pattern.')
            prior=[c for c in corrections if c['pattern'] in related]
            local=tuple(c['ref'] for c in prior if c['target']==d['target']
                and c['binding'] in indexed(op,'recalled.'))
            recurrence=None
            if a['deformed'] and prior:
                recurrence='same_target' if any(d['target'] in seen_targets.get(p,set()) for p in applied) else 'changed_target'
            defensive=tuple(p for p in applied if a['deformed'] and related[p]['origin_mode']=='generated')
            rows.append(dict(ref=v.ref,requested=a['requested'],target=d['target'],
                deformed=a['deformed'],completed=a['completed'],
                premature_translation=a.get('early_substitution',False),
                attempted_forced_placement=a.get('attempted_personal_placement',False),
                new_defensive_structure=defensive,
                patterns=tuple(related),origins=tuple(pd['origin'] for pd in related.values()),
                local_corrections=local,recurrence=recurrence,
                supported=a['completed'] and enc.get('known.approved') is True,
                demand=d['demand'],admission_spent=d['admission_spent'],movement_spent=a['movement_spent']))
            if a['deformed']:
                for p in applied:seen_targets.setdefault(p,set()).add(d['target'])
    signs=dict(premature_translation=any(r['premature_translation'] for r in rows),
        attempted_forced_placement=any(r['attempted_forced_placement'] for r in rows),
        new_defensive_structure=any(r['new_defensive_structure'] for r in rows),
        residual_fragmentation=any(r['recurrence'] for r in rows))
    result.update(workflow_development_rows=rows,workflow_diagnostic_signs=signs)
    return result


def require_scoped_correction(transactions,access_text,pattern,target):
    """A clearance claim needs an audited actual correction for this exact target."""
    txs=tuple(transactions);audit(txs,access_text)
    versions={v.ref:v for tx in txs for v in tx.versions}
    p=attrs(versions[pattern])
    if any(kind not in ('approval','obligation') for kind,_,_ in effects(p)):
        raise ValueError('unsupported clearance for this effect kind')
    found=[v.ref for v in versions.values() if v.ref.identity.namespace=='u8.correction'
        and attrs(v)['pattern']==pattern and attrs(v)['target']==target]
    if not found:raise ValueError('no actual exact-target correction')
    return found[-1]
