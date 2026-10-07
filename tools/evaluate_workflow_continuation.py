"""FB5.3 frozen one-chain panel; no cell-wide development claim."""
import gzip, hashlib, json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'baseline/HLE_Rebuild_R21B')]
from tests_workflow_continuation.fixtures import chain, WithheldHandoff, WorkflowContinuation, query_personal


def manifest():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.rglob('*')) if p.is_file() and '.git' not in p.parts
            and '__pycache__' not in p.parts and 'evidence' not in p.parts
            and (p.suffix == '.py' or p.relative_to(ROOT).parts[0] == 'contracts')}


def save(folder, key, p):
    path = folder / (key + '.json.gz')
    path.write_bytes(gzip.compress(p.checkpoint().encode(), mtime=0))
    return dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main(folder):
    folder.mkdir(parents=True, exist_ok=False)
    freeze = manifest(); (folder / 'source_freeze.json').write_text(json.dumps(freeze, indent=2)+'\n')
    rows = []; current = None
    try:
        current = chain(); current.run(1000); query_personal(current)
        rows.append(dict(case='generated-chain', **save(folder, 'generated-chain', current)))
        current = chain(cls=WithheldHandoff); current.run(1000)
        rows.append(dict(case='withheld-generated-handoff', **save(folder, 'withheld-generated-handoff', current)))
        for boundary in ('comparison', 'feedback'):
            current = chain()
            if boundary == 'comparison': current.run(1)
            else:
                for _ in range(1000):
                    current.step()
                    if current.feedback[0] is not None: break
                assert current.feedback[0] is not None
            save(folder, 'interrupted-'+boundary, current)
            restored = WorkflowContinuation.restore(current.checkpoint())
            current.run(1000); restored.run(1000)
            assert current.checkpoint() == restored.checkpoint()
            rows.append(dict(case='restore-'+boundary, exact_restore=True,
                             **save(folder, 'restore-'+boundary, restored)))
        current = chain(); assert current.run(1)['pending']
        rows.append(dict(case='finite-turn-budget', **save(folder, 'finite-turn-budget', current)))
        current = chain(budget=90); current.run(1000)
        assert current.stopped == ['exhausted']
        rows.append(dict(case='exhausted-wallet', **save(folder, 'exhausted-wallet', current)))
        (folder / 'rows.json').write_text(json.dumps(rows, indent=2)+'\n')
        assert manifest() == freeze
        (folder / 'summary.json').write_text(json.dumps(dict(passed=True, source_unchanged=True,
            cases=len(rows), claim='One bounded generated-content chain only; independent verification required.'),indent=2)+'\n')
    except Exception:
        (folder / 'failure.txt').write_text(traceback.format_exc())
        if current is not None: save(folder, 'failed-current', current)
        raise
    print('PASS', len(rows), 'frozen cases', flush=True)

if __name__ == '__main__': main(Path(sys.argv[1]))
