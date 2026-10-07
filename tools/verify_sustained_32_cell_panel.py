"""Independent FB5.5 raw verifier; no scheduler, selector, executor or fixtures."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]

from hle_unified.compact import unseal
from hle_unified.material import OperationStore, attrs
from hle_unified.selection_records import loads, dumps
from hle_unified.workflow_agenda_population_audit import audit_agenda_population, address
from hle_unified.workflow_selection_audit import audit as native_audit
from hle_unified.workflow_reference import decode
from hle_unified.records import Account
from hle_unified.crux_audit import _access


NAMES = ('Contemplate', 'Act', 'Commune', 'Integrate', 'Express', 'Embody',
         'Theorize', 'Understand', 'Apply', 'Organize', 'Share', 'Coordinate',
         'Identify', 'Mobilize', 'Institutionalize', 'Educate')
FACES = ('accumulation', 'expenditure')
CONSUMERS = ('Theorize', 'Theorize', 'Embody', 'Embody', 'Identify', 'Identify',
             'Apply', 'Apply', 'Embody', 'Embody', 'Theorize', 'Theorize',
             'Apply', 'Apply', 'Theorize', 'Theorize', 'Embody', 'Embody',
             'Apply', 'Apply', 'Identify', 'Identify', 'Identify', 'Identify',
             'Theorize', 'Theorize', 'Embody', 'Embody', 'Educate', 'Educate',
             'Identify', 'Identify')


def identity(path, expected=None):
    row = dict(file=path.name, bytes=path.stat().st_size,
               sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if expected is not None and row != expected:
        raise ValueError('raw file identity differs')
    return row


def load(path):
    state = loads(gzip.decompress(path.read_bytes()).decode())
    sealed = unseal(state['engine'], 'hle-full-crux-c7-workflow-selection-v4')
    transactions = OperationStore.restore(sealed['world']).journal()
    versions = {v.ref: v for tx in transactions for v in tx.versions}
    heads = {v.ref.identity: v for tx in transactions for v in tx.versions}
    times = {v.ref: tx.at.tick for tx in transactions for v in tx.versions}
    details, bindings = _access(sealed['access'], versions, times)
    return state, sealed, transactions, versions, heads, details, bindings


def semantic(ref, actor, versions, details, bindings):
    if ref.identity.namespace == 'u4.observation':
        value = {p.address.key: p.value for (owner, _), (p, _) in details.items()
                 if owner == actor and p.source == ref}
        required = {'event', 'outcome', 'context', 'primitive', 'actor', 'workflow_tick'}
        if not required <= set(value):
            raise ValueError('unpaid observation in credited semantics')
        return dict(value, kind='activity')
    if ref in bindings:
        binding = bindings[ref][0]
        return decode(binding.content[0].object)
    payloads = [p.value for (owner, _), (p, _) in details.items()
                if owner == actor and p.source == ref and p.address.key == 'payload']
    if len(payloads) != 1:
        raise ValueError('unpaid public content in credited semantics')
    return decode(payloads[0])


def child(heads, actor, key):
    return attrs(heads[address('u4.operation', actor, key).identity])


def verify(folder):
    declared_rows = json.loads((folder / 'rows.json').read_text())
    if len(declared_rows) != 32:
        raise ValueError('coverage row count differs')
    reports = []
    coverage = set()
    hidden_public = 0
    for cell, summary in enumerate(declared_rows):
        expected = (cell, NAMES[cell // 2], FACES[cell % 2], 'iee' if cell % 2 == 0 else 'sli')
        actual = (summary['cell'], summary['name'], summary['face'], summary['owner_type'])
        if actual != expected:
            raise ValueError('prospective panel row differs')
        witness_path = folder / summary['witness']['file']
        control_path = folder / summary['control']['file']
        identity(witness_path, summary['witness'])
        identity(control_path, summary['control'])
        w = load(witness_path)
        c = load(control_path)
        ws, we, wt, wv, wh, wd, wb = w
        cs, ce, ct, cv, ch, cd, cb = c
        wa = ws['agendas'][0]
        ca = cs['agendas'][0]
        wr = audit_agenda_population(wt, we['access'], ws)
        cr = audit_agenda_population(ct, ce['access'], cs)
        wn = native_audit(wt, we['access'])
        cn = native_audit(ct, ce['access'])
        target_recipe = 'workflow-' + summary['name'].lower() + '-' + summary['face'] + '-v1'
        consumer_recipe = 'workflow-' + CONSUMERS[cell].lower() + '-accumulation-v1'
        if [row['recipe'] for row in wn['selection_rows'][:2]] != [target_recipe, consumer_recipe]:
            raise ValueError('automatic target/consumer choice differs')
        if [row['recipe'] for row in cn['selection_rows']] != [target_recipe]:
            raise ValueError('control executed beyond target selection')
        if (wa['stage'], len(wa['results']), ca['stage'], len(ca['results'])) != (2, 2, 0, 0):
            raise ValueError('witness/control continuation differs')
        if ca['pending_result'] != wa['results'][0]:
            raise ValueError('withheld result identity differs')
        actor = wa['template']['actor']
        target_key = 'agenda:cell-' + str(cell) + ':auto:0:movement'
        wchild = child(wh, actor, target_key)
        cchild = child(ch, actor, target_key)
        if (wchild['status'], wchild['spent'], wchild.get('public.0'), wchild.get('binding'), wchild.get('result')) != (
                cchild['status'], cchild['spent'], cchild.get('public.0'), cchild.get('binding'), cchild.get('result')):
            raise ValueError('matched producer or cost differs')
        output = semantic(wa['results'][0], actor, wv, wd, wb)
        inputs = [semantic(slot['initial'], actor, wv, wd, wb) for slot in wa['goals'][0]['sources']]
        if output in inputs:
            raise ValueError('credited target lacks semantic delta')
        digest = hashlib.sha256(dumps(output).encode()).hexdigest()
        if digest != summary['target_semantic_sha256']:
            raise ValueError('semantic summary differs')
        terminal = address('c7w.output', actor, 'panel-terminal-' + str(cell))
        if terminal.identity not in wh:
            raise ValueError('terminal causal output missing')
        answer = decode(wh[terminal.identity].facet(Account).content[0].object)
        if answer.get('next_task') != summary['terminal_next_task'] or answer.get('next_task') is None:
            raise ValueError('terminal causal answer differs')
        if ca['pending_result'].identity.namespace == 'c7w.message':
            paid = [p for (owner, _), (p, _) in cd.items()
                    if owner == actor and p.source == ca['pending_result'] and p.address.key == 'payload']
            if paid:
                raise ValueError('withheld public result was delivered')
            hidden_public += 1
        coverage.add((summary['name'], summary['face']))
        reports.append(dict(cell=cell, target=target_recipe, consumer=consumer_recipe,
                            target_spent=wchild['spent'], witness_turns=ws['turn'],
                            control_turns=cs['turn'], witness_audit=wr['passed'],
                            control_audit=cr['passed']))
    if len(coverage) != 32 or hidden_public == 0:
        raise ValueError('coverage or hidden/delivered panel differs')

    special = json.loads((folder / 'special_cases.json').read_text())
    special_reports = {}
    for key, raw_identity in special.items():
        path = folder / raw_identity['file']
        identity(path, raw_identity)
        state, sealed, txs, *_ = load(path)
        report = audit_agenda_population(txs, sealed['access'], state)
        special_reports[key] = report
    if special_reports['fair']['peer_turns'] < 1:
        raise ValueError('peer-owned scheduled work missing')
    if special_reports['finite']['turns'] != 1:
        raise ValueError('finite turn boundary differs')
    exhausted_state = load(folder / special['exhausted']['file'])[0]
    failed_state = load(folder / special['failed']['file'])[0]
    if exhausted_state['agendas'][0]['halted'] != 'exhausted':
        raise ValueError('wallet exhaustion not retained')
    if failed_state['agendas'][0]['halted'] != 'native_cancelled':
        raise ValueError('cancelled work not retained')

    result = dict(passed=True, cells=len(coverage), witnesses=32, controls=32,
                  semantic_deltas=32, terminal_consequences=32,
                  matched_producer_costs=True, hidden_public_controls=hidden_public,
                  mixed_types=['iee', 'sli'], exact_restore=True,
                  participant_replay=False, reports=reports, special=special_reports)
    (folder / 'independent_verification.json').write_text(json.dumps(result, indent=2, default=str) + '\n')
    print('PASS independent 32/32 sustained coverage reconstruction', flush=True)
    return result


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
