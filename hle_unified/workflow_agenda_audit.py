"""Independent agenda provenance and payment reconstruction from committed worlds."""
import re
from hashlib import sha256
from . import codec
from .records import ObjectId, ObjectRef, Account
from .material import attrs
from .selection_records import loads
from .workflow_selection_audit import audit as native_audit
from .workflow_reference import decode
from .crux_audit import _access


def address(namespace, *parts):
    return ObjectRef(ObjectId(namespace, sha256(codec.canonical([codec.encode(x) for x in parts]).encode()).hexdigest()), 1)


def audit_agenda(transactions, access, state):
    if (type(state['quantum']) is not int or state['quantum'] < 1
            or not 1 <= len(state['goals']) <= 8
            or not 0 <= state['stage'] <= len(state['goals'])):
        raise ValueError('invalid finite agenda bounds')
    for i, g in enumerate(state['goals']):
        if (set(g) != {'need','sources','companion','own_stance','peer_stance'}
                or g['companion'] not in ('none','exchange','votes') or not 1 <= len(g['sources']) <= 8):
            raise ValueError('invalid supplied goal')
        for slot in g['sources']:
            if (set(slot) not in ({'initial'},{'result'}) or ('result' in slot
                    and (type(slot['result']) is not int or not 0 <= slot['result'] < i))):
                raise ValueError('invalid prior-result slot')
    native = native_audit(transactions, access)
    versions = {}; heads = {}; charges = {}
    for tx in transactions:
        match = re.match(r'^u4:agenda-turn:(\d+):', tx.key)
        step = int(match[1]) if match else None
        for v in tx.versions:
            d = attrs(v)
            if step is not None and d.get('record_type') == 'wallet':
                old = attrs(versions[v.previous]); key = (step, d['actor'])
                delta = tuple(old[k]-d[k] for k in ('energy','time'))
                if any(n < 0 for n in delta): raise ValueError('agenda replenishment')
                charges[key] = tuple(a+b for a,b in zip(charges.get(key,(0,0)),delta))
            versions[v.ref] = v; heads[v.ref.identity] = v
    if len(state['events']) != state['steps']: raise ValueError('agenda step count differs')
    total = 0
    for i, row in enumerate(state['events']):
        if row['step'] != i: raise ValueError('agenda step order differs')
        for actor, energy, time in row['charged']:
            if (energy,time) != charges.pop((i,actor),(0,0)): raise ValueError('agenda charge differs')
            total += energy
    if charges: raise ValueError('unreported agenda charges')
    template = state['template']; actor = template['actor']; actual_results = []
    for i, goal in enumerate(state['goals']):
        key = 'agenda:'+template['key']+':'+str(i)
        snapshot = address('c7ws.snapshot', actor, key)
        if snapshot not in versions: break
        source_refs = []
        for slot in goal['sources']:
            if 'initial' in slot: source_refs.append(slot['initial'])
            elif slot['result'] < len(actual_results): source_refs.append(actual_results[slot['result']])
            else: raise ValueError('selection preceded generated source')
        inputs = tuple(source_refs)
        if goal['companion'] == 'exchange':
            inputs = (source_refs[0], address('c7w.message',actor,key+':offer'),
                      address('c7w.message',template['peer'],key+':reply'))
        elif goal['companion'] == 'votes':
            inputs = (source_refs[0], address('c7w.message',actor,key+':own-vote'),
                      address('c7w.message',template['peer'],key+':peer-vote'))
        expected = dict(template,key=key,demand=goal['need'],accessible=inputs)
        request = loads(attrs(versions[snapshot])['payload'])['request']
        if request != expected: raise ValueError('agenda input or supplied need differs')
        child_id = address('u4.operation',actor,key+':movement').identity
        child = attrs(heads[child_id]) if child_id in heads else None
        if not child or child['status'] != 'succeeded': break
        result = child.get('public.0') or child.get('binding')
        if result is None:
            observations = [v for v in versions.values() if v.ref.identity.namespace=='u4.observation'
                            and v.facet(Account).sources == (child['result'],)]
            if len(observations) != 1: raise ValueError('exact material observation missing')
            result = observations[0].ref
        actual_results.append(result)
    if state['stage'] != len(state['results']) or state['results'] != actual_results[:state['stage']]:
        raise ValueError('agenda retained result provenance differs')
    if state['pending_result'] is not None and (state['stage'] >= len(actual_results)
            or state['pending_result'] != actual_results[state['stage']]):
        raise ValueError('agenda pending result differs')
    times = {v.ref:tx.at.tick for tx in transactions for v in tx.versions}
    details, bindings = _access(access, versions, times)
    for result in state['results']:
        if result.identity.namespace == 'c7w.output':
            if result not in bindings or bindings[result][0].actor != actor:
                raise ValueError('unpaid owned agenda result')
        else:
            read = {p.address.key for (owner, _), (p, _) in details.items()
                    if owner == actor and p.source == result}
            required = {'payload'} if result.identity.namespace == 'c7w.message' else {'event','outcome','context','primitive','actor','workflow_tick','condition','wear','custodian'}
            if not required <= read: raise ValueError('agenda result advanced before paid reading')
    validate_pending(state, versions)
    return dict(passed=True, completed_goals=state['stage'], modeled_energy=total,
                main_selections=native['workflow_selections'], native=native)


def validate_pending(state, versions):
    """Pending commands must belong to the declared goal and communication scope."""
    actions = list(state['queue']) + ([] if state['active'] is None else [state['active']])
    if not actions: return
    if state['stage'] >= len(state['goals']): raise ValueError('commands beyond goal horizon')
    g = state['goals'][state['stage']]; t = state['template']; a = t['actor']; peer = t['peer']
    key = 'agenda:'+t['key']+':'+str(state['stage'])
    sources = tuple(s['initial'] if 'initial' in s else state['results'][s['result']] for s in g['sources'])
    offer = address('c7w.message',a,key+':offer'); reply = address('c7w.message',peer,key+':reply') if peer else None
    votes = (address('c7w.message',a,key+':own-vote'),address('c7w.message',peer,key+':peer-vote')) if peer else ()
    inputs = (sources[0],offer,reply) if g['companion']=='exchange' else (sources[0],*votes) if g['companion']=='votes' else sources
    for action in actions:
        kind=action['kind']; suffix=action['key'][len(key):]
        if not action['key'].startswith(key) or action['actor'] not in (a,peer):
            raise ValueError('pending command leaves supplied goal')
        if kind=='main':
            expected=dict(kind='main',key=key,actor=a,inputs=inputs,need=g['need'])
        elif kind=='aux':
            if suffix==':offer' and g['companion']=='exchange':
                v=versions[sources[0]]
                if sources[0].identity.namespace=='u4.observation': source_kind='activity'
                elif sources[0].identity.namespace=='c7w.message': source_kind=decode(attrs(v)['payload'])['kind']
                else: source_kind=decode(v.facet(Account).content[0].object)['kind']
                domain={'intention':'personal','personal':'personal','activity':'activity','shared':'shared','system':'system','rule':'system'}[source_kind]
                expected=dict(kind='aux',key=key+suffix,actor=a,recipe='workflow-offer-'+domain+'-v1',inputs=(sources[0],g['own_stance']))
            elif suffix==':reply' and g['companion']=='exchange':
                expected=dict(kind='aux',key=key+suffix,actor=peer,recipe='workflow-reply-v1',inputs=(offer,g['peer_stance']))
            elif suffix in (':own-vote',':peer-vote') and g['companion']=='votes':
                own=suffix==':own-vote'
                expected=dict(kind='aux',key=key+suffix,actor=a if own else peer,recipe='workflow-vote-v1',inputs=(sources[0],g['own_stance' if own else 'peer_stance']))
            else: raise ValueError('unsupported pending auxiliary')
        elif kind=='public':
            choices={':own-offer-read':(a,offer),':peer-offer-read':(peer,offer),':reply-read':(a,reply)} if g['companion']=='exchange' else {}
            if g['companion']=='votes': choices={':peer-draft-read':(peer,sources[0]),':own-vote-read':(a,votes[0]),':peer-vote-read':(a,votes[1])}
            if state['pending_result'] is not None: choices[':result-read']=(a,state['pending_result'])
            if suffix not in choices: raise ValueError('unsupported pending public read')
            actor,ref=choices[suffix];expected=dict(kind='public',key=key+suffix,actor=actor,ref=ref)
        elif kind=='event':
            if suffix!=':result-read' or state['pending_result'] is None: raise ValueError('unscoped pending event read')
            if address('u4.observation',action['delivery'],a) != state['pending_result']:
                raise ValueError('pending event delivery differs')
            expected=dict(kind='event',key=key+suffix,actor=a,delivery=action['delivery'])
        else: raise ValueError('unknown pending command kind')
        if action != expected: raise ValueError('pending command differs from supplied goal')
