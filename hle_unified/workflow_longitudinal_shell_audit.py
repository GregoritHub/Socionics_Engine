"""Independent longitudinal workflow Shell reconstruction from committed records."""
from .workflow_development_audit import audit as inherited_audit
from .development_values import attrs as development_attrs
from .material import attrs
from .operation_audit import indexed
from .workflow_audit import payload


def audit(transactions, access_text):
    """Add longitudinal facts without importing an executor, selector or fixture."""
    txs = tuple(transactions)
    result = inherited_audit(txs, access_text)
    versions = {v.ref: v for tx in txs for v in tx.versions}
    heads = {v.ref.identity: v for tx in txs for v in tx.versions}
    patterns = []
    corrections = []
    failed_corrections = []
    consumers = []
    cancelled = []
    for v in versions.values():
        namespace = v.ref.identity.namespace
        data = attrs(v)
        if namespace == 'u7.pattern':
            patterns.append(dict(ref=v.ref, origin=data['origin'], origin_mode=data['origin_mode'],
                                 effects=tuple((data[k], data[k.replace('.kind', '.route')],
                                                data[k.replace('.kind', '.amount')])
                                               for k in sorted(data) if k.startswith('effect.') and k.endswith('.kind'))))
        elif namespace == 'u8.correction':
            row = development_attrs(v)
            operation = attrs(heads[row['operation'].identity])
            corrections.append(dict(ref=v.ref, pattern=row['pattern'], target=row['target'],
                                    origin=row['origin'], binding=row['binding'],
                                    required=operation['required'], spent=operation['spent'],
                                    status=operation['status']))
        elif namespace == 'u4.operation':
            if data.get('u8') and data.get('purpose') == 'release' and data['status'] == 'failed':
                failed_corrections.append(dict(ref=v.ref, pattern=data['pattern'], target=data['target'],
                                               required=data['required'], spent=data['spent'],
                                               failure=data['failure']))
            if data.get('c7w') and data['status'] == 'succeeded' and data.get('key', '').endswith('-consumer'):
                binding = data.get('binding') or data.get('result')
                consumers.append(dict(ref=v.ref, key=data['key'], spent=data['spent'], binding=binding,
                                      next_task=payload(versions[binding])['next_task']))
            if data.get('c7w') and data['status'] == 'cancelled':
                cancelled.append(dict(ref=v.ref, spent=data['spent'], steps_completed=data['steps_completed'],
                                      first_step=data.get('last_step'), inputs=indexed(data, 'input.')))
    shell_rows = result['workflow_development_rows']
    result.update(
        longitudinal_patterns=patterns,
        longitudinal_originals=tuple(dict.fromkeys(p['origin'] for p in patterns)),
        longitudinal_corrections=corrections,
        longitudinal_failed_corrections=failed_corrections,
        longitudinal_consumers=consumers,
        longitudinal_cancelled=cancelled,
        longitudinal_recurrence_same=sum(r['recurrence'] == 'same_target' for r in shell_rows),
        longitudinal_recurrence_changed=sum(r['recurrence'] == 'changed_target' for r in shell_rows),
        longitudinal_retained_intermediates=tuple(r['intermediate'] for r in
            result['workflow_interruption_rows'] if r.get('early_substitution')),
    )
    return result


def compare_correction_control(witness, control, target):
    """Reconstruct the exact-target result against an equal-cost off-target result."""
    wc = [r for r in witness['longitudinal_corrections'] if r['target'] == target]
    cc = [r for r in control['longitudinal_corrections'] if r['target'] != target]
    if len(wc) != 1 or len(cc) != 1:
        raise ValueError('one exact-target and one off-target correction required')
    if (wc[0]['required'], wc[0]['spent']) != (cc[0]['required'], cc[0]['spent']):
        raise ValueError('correction control cost differs')
    if not witness['longitudinal_consumers'] or control['longitudinal_consumers']:
        raise ValueError('correction control did not change the terminal consequence')
    return dict(target=target, witness=wc[0], control=cc[0],
                terminal=witness['longitudinal_consumers'][-1]['next_task'])
