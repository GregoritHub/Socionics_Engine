"""Prospectively fixed longitudinal Shell histories and boundary cases."""
from dataclasses import replace

from tests_workflow_interruption.fixtures import *
from tests_workflow_shell import fixtures as shell
from tests_c7_workflow.fixtures import setup_workflow
from hle_unified.workflow_longitudinal_shell_audit import audit, compare_correction_control
from hle_unified.shell_records import PatternPolicy, Effect


def setup_typed(tim='iee', *, budget=200000, generate=True):
    e = setup_workflow(tim, engine_type=WorkflowInterruptionEngine, budget=budget)
    e.declare('workflow-shell-anchors', (definition(dev.TRIGGER, 'Entrusted workflow opportunity'),
        definition(dev.OTHER_TRIGGER, 'Distinct workflow opportunity')))
    for ref_ in (dev.TRIGGER, dev.OTHER_TRIGGER, ObjectRef(EVE, 1), SAW2):
        if ref_ not in e.access._known_refs(ALICE):
            show(e, ALICE, ref_)
    e.configure_patterns('workflow-shell-policy', PatternPolicy(ALICE, generate=generate))
    return e


def prepared_typed(tim='iee', *, budget=200000, effect='approval', with_pattern=True):
    e = setup_typed(tim, budget=budget, generate=effect == 'approval')
    p = None
    if with_pattern:
        if effect == 'approval':
            p = dev.generated(e)
        else:
            dev.supply8(e, 'pattern-origin')
            p = e._patterns[dev.inject(e, Effect(effect, 'theorize-accumulation-v1',
                -1 if effect == 'salience' else 1))]
    out = prepare(e, 'Theorize', 'accumulation')
    dev.supply8(e, 'current-neutral', target=out['request'].target)
    return e, p, out


def run(e, out, key):
    q = dict(out, request=replace(out['request'], key=key))
    return finish(e, q, key + '-gate')


def _changed(e, prefix):
    own = authored(e, prefix + '-intent', target=LOAN)
    request_ = request(e, prefix, 'Theorize', 'accumulation', (own,), target=LOAN)
    dev.supply8(e, prefix + '-facts', target=LOAN)
    return dict(request=request_, inputs=(own,), extra={})


def _off_target_sequence(e, out, worlds=None, prefix='history'):
    p = e.pattern_view(ALICE)[0]
    dev.release8(e, prefix + '-off-target-release', p, target=SAW2)
    if worlds is not None: worlds['03-off-target-correction'] = type(e).restore(e.checkpoint())
    _, later = run(e, out, prefix + '-same-recurrence')
    assert later == 'unavailable'
    if worlds is not None: worlds['04-same-target-recurrence'] = type(e).restore(e.checkpoint())
    changed = _changed(e, prefix + '-changed')
    _, later = run(e, changed, prefix + '-changed-recurrence')
    assert later == 'unavailable'
    if worlds is not None: worlds['05-changed-target-recurrence'] = type(e).restore(e.checkpoint())
    dev.release8(e, prefix + '-exact-release', p, target=out['request'].target)
    _, later = run(e, out, prefix + '-corrected')
    assert later == 'handover'
    if worlds is not None: worlds['06-exact-correction-and-use'] = type(e).restore(e.checkpoint())
    dev.supply8(e, prefix + '-changed-again', target=LOAN)
    _, later = run(e, changed, prefix + '-changed-residual')
    assert later == 'unavailable'
    if worlds is not None: worlds['07-changed-target-residual'] = type(e).restore(e.checkpoint())
    return e


def longitudinal(tim='iee', worlds=None):
    worlds = {} if worlds is None else worlds
    e, p, out = prepared_typed(tim)
    _, later = run(e, out, 'initial')
    assert later == 'unavailable'
    interrupted = e.checkpoint()
    worlds['01-initial-interruption'] = type(e).restore(interrupted)

    witness = type(e).restore(interrupted)
    wp = witness.pattern_view(ALICE)[0]
    dev.release8(witness, 'witness-exact-release', wp, target=out['request'].target)
    _, later = run(witness, out, 'witness-corrected')
    assert later == 'handover'
    worlds['02-exact-correction-witness'] = witness

    original = type(e).restore(interrupted)
    _off_target_sequence(original, out, worlds)
    restored = type(e).restore(interrupted)
    _off_target_sequence(restored, out)
    assert original.checkpoint() == restored.checkpoint()
    worlds['08-restored-final'] = restored

    witness_report = audit(witness.world.journal(), witness.access.checkpoint())
    control_report = audit(worlds['04-same-target-recurrence'].world.journal(),
                           worlds['04-same-target-recurrence'].access.checkpoint())
    comparison = compare_correction_control(witness_report, control_report, out['request'].target)
    assert comparison['terminal'] == 'handover'
    return worlds, dict(type=tim, target=out['request'].target, comparison=comparison,
                        restore_equal=True)


def undeformed(tim='iee'):
    e, _, out = prepared_typed(tim, with_pattern=False)
    _, later = run(e, out, 'undeformed')
    assert later == 'handover'
    return e


def unsupported_longitudinal(effect, worlds=None):
    worlds = {} if worlds is None else worlds
    e, p, out = prepared_typed('iee', effect=effect)
    before = e.checkpoint()
    worlds['before'] = type(e).restore(before)
    r = dev.request8(e, 'unsupported-release', 'release', p, (out['request'].target,))
    try:
        e.start('unsupported-release:start', r)
    except ValueError as exc:
        error = str(exc)
        assert error == 'unsupported, incomplete or scaffolded local correction'
    else:
        raise AssertionError('unsupported correction was permitted')
    assert e.checkpoint() == before
    worlds['after'] = type(e).restore(e.checkpoint())
    _, later = run(e, out, 'unsupported-still-interrupted')
    assert later == 'unavailable'
    worlds['still-interrupted'] = e
    return worlds, dict(effect=effect, error=error, checkpoint_unchanged=True)


def exhaustion():
    ample, _, out = prepared_typed('iee')
    run(ample, out, 'exhaust-initial')
    p = ample.pattern_view(ALICE)[0]
    dev.supply8(ample, 'exhaust-release-facts', target=out['request'].target)
    r = dev.request8(ample, 'exhaust-release', 'release', p, (out['request'].target,))
    ample.start('exhaust-release:start', r)
    required = ample.job_status(ALICE, r.key)['required']
    prefix = 200000 - ample.wallet(ALICE)['energy']
    budget = prefix + required - 1

    e, _, out = prepared_typed('iee', budget=budget)
    run(e, out, 'exhaust-initial')
    p = e.pattern_view(ALICE)[0]
    dev.supply8(e, 'exhaust-release-facts', target=out['request'].target)
    r = dev.request8(e, 'exhaust-release', 'release', p, (out['request'].target,))
    e.start('exhaust-release:start', r)
    e.advance('exhaust-release:advance', ALICE, r.key, 1000000)
    d = e.job_status(ALICE, r.key)
    assert e.wallet(ALICE)['energy'] == 0 and d['status'] == 'partial'
    assert d['completed'] == d['required'] - 1 and not any(
        v.ref.identity.namespace == 'u8.correction' for tx in e.world.journal() for v in tx.versions)
    return e, dict(initial_budget=budget, prefix=prefix, required=required,
                   spent=d['spent'], completed=d['completed'])


def failed_work():
    """Paid work cancelled after its first correction quantum; prior history survives."""
    e, _, out = prepared_typed('iee')
    run(e, out, 'failed-initial')
    p = e.pattern_view(ALICE)[0]
    dev.supply8(e, 'failed-release-facts', target=out['request'].target)
    r = dev.request8(e, 'failed-release', 'release', p, (out['request'].target,))
    e.start('failed-release:start', r)
    e.advance('failed-release:advance', ALICE, r.key, 1)
    before = e.job_status(ALICE, r.key)
    e.cancel('failed-release:cancel', ALICE, r.key)
    after = e.job_status(ALICE, r.key)
    assert before['spent'] == after['spent'] == 1 and after['status'] == 'cancelled'
    assert not any(v.ref.identity.namespace == 'u8.correction' for tx in e.world.journal() for v in tx.versions)
    return e, dict(spent=after['spent'], status=after['status'], failure='cancelled_paid_work')
