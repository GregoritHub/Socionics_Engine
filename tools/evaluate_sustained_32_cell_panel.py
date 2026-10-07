"""Execute the prospectively frozen FB5.5 32-cell sustained panel."""
import gzip
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]

from hle_unified.selection_records import dumps
from tests_workflow_sustained_panel.fixtures import *
from tools.evaluate_workflow_continuation import manifest


def save(folder, key, population):
    path = folder / (key + '.json.gz')
    path.write_bytes(gzip.compress(population.checkpoint().encode(), mtime=0))
    return dict(file=path.name, bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def producer(population, cell):
    agenda = population.agendas[0]
    actor = agenda.template['actor']
    key = 'agenda:cell-' + str(cell) + ':auto:0:movement'
    job = population.engine.job_status(actor, key)
    return dict(status=job['status'], spent=job['spent'], result=str(job.get('public.0') or job.get('binding') or job.get('result')))


def main(folder):
    folder.mkdir(parents=True, exist_ok=False)
    freeze = manifest()
    (folder / 'source_freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    rows = []
    current = None
    try:
        for cell in range(32):
            witness, declared = sustained_cell(cell)
            current = witness
            outcome = witness.run()
            if not outcome['done']:
                raise AssertionError('witness did not complete: ' + str(declared))
            agenda = witness.agendas[0]
            template = WorkflowSelectionRequest(**agenda.template)
            target_value = semantic_value(witness.engine, template, agenda.results[0])
            input_values = [semantic_value(witness.engine, template, ref) for ref in declared['initial']]
            if target_value in input_values:
                raise AssertionError('target lacks semantic delta: ' + str(declared))
            answer = terminal_consequence(witness, 'panel-terminal-' + str(cell))
            if answer is None:
                raise AssertionError('terminal consequence unavailable: ' + str(declared))
            witness_raw = save(folder, 'cell-%02d-witness' % cell, witness)

            control, _ = sustained_cell(cell)
            current = control
            run_withheld(control)
            if terminal_consequence(control) is not None:
                raise AssertionError('withheld control gained terminal consequence')
            control_raw = save(folder, 'cell-%02d-withheld' % cell, control)
            witness_producer = producer(witness, cell)
            control_producer = producer(control, cell)
            if witness_producer != control_producer or agenda.results[0] != control.agendas[0].pending_result:
                raise AssertionError('matched producer differs: ' + str(declared))
            row = dict(declared, target_semantic_sha256=digest(target_value),
                       input_semantic_sha256=[digest(value) for value in input_values],
                       terminal_next_task=answer.get('next_task'), producer=witness_producer,
                       witness=witness_raw, control=control_raw)
            rows.append(row)
            (folder / 'rows.json').write_text(json.dumps(rows, indent=2, default=str) + '\n')
            print('PASS cell', cell, declared['name'], declared['face'], flush=True)

        fair = fair_social_pair()
        current = fair
        if not fair.run()['done']:
            raise AssertionError('fair social pair did not complete')
        fair_raw = save(folder, 'fair-social-pair', fair)

        interrupted, _ = sustained_cell(29)
        interrupted.run(13)
        interrupted_raw = save(folder, 'restore-interrupted', interrupted)
        restored = FairWorkflowAgendaPopulation.restore(interrupted.checkpoint())
        restored.run()
        uninterrupted, _ = sustained_cell(29)
        uninterrupted.run()
        if restored.checkpoint() != uninterrupted.checkpoint():
            raise AssertionError('restored continuation differs')
        restored_raw = save(folder, 'restore-final', restored)

        finite, _ = sustained_cell(0)
        finite.max_turns = 1
        if finite.run()['done']:
            raise AssertionError('finite turn case completed')
        finite_raw = save(folder, 'finite-turn-pending', finite)

        exhausted, _ = sustained_cell(0, budget=100)
        exhausted.run()
        if exhausted.agendas[0].halted != 'exhausted':
            raise AssertionError('finite wallet did not exhaust')
        exhausted_raw = save(folder, 'wallet-exhaustion', exhausted)

        failed, _ = sustained_cell(0)
        actor = failed.agendas[0].template['actor']
        movement = 'agenda:cell-0:auto:0:movement'
        for _ in range(100):
            failed.step()
            if (actor, movement) in failed.engine._jobs:
                job = failed.engine.job_status(actor, movement)
                if job['status'] not in ('succeeded', 'failed', 'cancelled') and job['spent'] > 0:
                    break
        failed.engine.cancel('panel-authored-cancellation', actor, movement)
        failed.run()
        if failed.agendas[0].halted != 'native_cancelled':
            raise AssertionError('cancelled native child was not retained')
        failed_raw = save(folder, 'cancelled-native-child', failed)

        special = dict(fair=fair_raw, interrupted=interrupted_raw, restored=restored_raw,
                       finite=finite_raw, exhausted=exhausted_raw, failed=failed_raw)
        (folder / 'special_cases.json').write_text(json.dumps(special, indent=2) + '\n')
        unchanged = manifest() == freeze
        summary = dict(passed=unchanged, source_unchanged=unchanged, cells=32, faces=32,
                       witnesses=32, matched_controls=32, types=['iee', 'sli'],
                       target_native_completions=32, consumer_native_completions=32,
                       terminal_consequences=32, fair_social_pair=True, exact_restore=True,
                       finite_pending=True, wallet_exhaustion=True, cancelled_work=True)
        (folder / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        if not unchanged:
            raise AssertionError('executed source changed')
        print('PASS 32/32 sustained cells and 32 matched controls', flush=True)
    except Exception:
        (folder / 'failure.txt').write_text(traceback.format_exc())
        if current is not None:
            save(folder, 'failed-current', current)
        raise


if __name__ == '__main__':
    main(Path(sys.argv[1]))
