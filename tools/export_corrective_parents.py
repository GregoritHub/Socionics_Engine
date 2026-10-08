"""Fresh eight-scenario panel using preserved canonical/workflow fixtures."""
import json
import sys
import traceback
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from tests_c4 import fixtures as c4
from tests_u11.fixtures import work as collective_work
from tests_workflow_nesting_faces.fixtures import parent_world
from tools.evaluate_workflow_selection import manifest, save


def canonical(category):
    e = c4.setup()
    if category in ('normal', 'unsuccessful-child'):
        c4.nested(e, failed=category == 'unsuccessful-child')
        return e, 'case', 'cancelled-child' if category == 'unsuccessful-child' else 'normal'
    c4.family(e, c4.FAMILIES[1])
    q, r = c4.before_request(e, 'case-parent')
    q.start('begin-parent', r)
    q.advance('paid-parent', c4.ALICE, r.key, 100000)
    if category == 'membership-change':
        collective_work(q, 'leave-now', 'leave', actor=c4.BOB, focus=r.group)
    else:
        old = q.world.resolve(c4.ref('case-renew-b'))
        account = old.facet(c4.Account)
        value = c4.comp.decode(account.content[0].object)
        value['consent'] = False
        revised = c4.next_version(old, facets=(replace(account,
            content=(replace(account.content[0], object=c4.comp.encode(value)),)),))
        q.declare('withdraw', (revised,))
        c4.perform(q, c4.OperationRequest('retain-withdrawal', c4.BOB, 'bind', c4.ROOM,
            binding=revised.ref, evidence=c4.evidence(q, c4.BOB, c4.SAW)))
    q.commit('finish-parent', c4.ALICE, r.key)
    assert q.job_status(c4.ALICE, r.key)['failure'] == 'stale_dependency'
    return q, r.key, category


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    freeze = manifest()
    (out / 'source_freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    rows = []
    categories = ('normal', 'unsuccessful-child', 'membership-change', 'withdrawal')
    modes = dict(zip(categories, ('normal', 'failed-child', 'membership-change', 'participant-withdrawal')))
    try:
        for setting in ('canonical', 'workflow'):
            for category in categories:
                if setting == 'canonical':
                    e, key, native = canonical(category)
                else:
                    e, _ = parent_world(modes[category])
                    key, native = 'parent', modes[category]
                cp = e.checkpoint()
                restored = type(e).restore(cp)
                assert restored.checkpoint() == cp
                name = setting + '-' + native
                rows.append({'setting': setting, 'category': category, 'native_scenario': native,
                             'parent_key': key, 'world': save(out, name, e),
                             'restored': save(out, name + '-restored', restored)})
                (out / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')
                print('EXPORTED', name, flush=True)
        assert len(rows) == 8 and manifest() == freeze
        print('EXPORTED eight new parent scenarios; exact-restored copies are checks, not additional scenarios')
    except Exception:
        (out / 'failure.txt').write_text(traceback.format_exc())
        if 'e' in locals():
            save(out, 'failed-current-world', e)
        raise


if __name__ == '__main__':
    main(Path(sys.argv[1]))
