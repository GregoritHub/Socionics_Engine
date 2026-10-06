# HLE: content, retained capacity, and the Malice Matrix

## Current experiment: retained capacity after help ends

The current task is executable: keep content distinct from the activity used to
produce it, then test retained complementary capacity and a consequential return.
The function graph has no primitive horizontal connection. A route alone cannot
satisfy the test.

In a small SLI learning task, retaining both alternative-search and
partner-constraint rules gives **12/12 successful held-out returns** after help
ends. Help without retention, either rule alone, and no instruction each give
3/12. Correct plans without action fail the return criterion; a quiet period
remains unassessed. These elected task operators are narrow stand-ins for Ne
and Fi, with an actual paid inspection/transfer as the practical return.

Across all 16 receiver types, 32 paired checks also preserve the aspect and
reception cost of identical content after different sender activities. This
separates content from R11's fixed activity targets. Full individuation and Shell
clearance remain unassessed; this is a finite procedural-learning prototype.

```bash
python run_crossing.py
python -m unittest discover -s tests -p test_crossing.py -v
```

Read the [current report](docs/retained_crossing.md),
[protocol](crossing_protocol.json), and [complete results](results/crossing.json.gz).
No original historical study scripts are needed for this run.

## Earlier Malice Matrix policy and attention experiment

A completed policy and attention experiment on HLE R11, with R10 as a controlled baseline. The repository contains the executable study, pinned engines, results, and a report. The findings concern the declared simulation policies and engine costs.

Source: @unicorn.lo, *The Malice Matrix: Game-Theoretic Containment of Systemic Defection* (supplied undated manuscript).

## R11 results

Across twelve rounds, three organization members face repeated requests from an outside extractor. Member costs combine Alice, Bob and Cara; setup is accounted for separately. Each energy debit has an equal time debit.

| Supplied response policy | Member cost | Extractor cost | Organization runs completed | Final box owner | Extractor stops |
| --- | ---: | ---: | ---: | --- | --- |
| Q1: explain and yield | 2170 | 578 | 0 of 12 | Extractor | No |
| Q2: Alice filters; others respond | 1507 | 554 | 1 of 12 | Extractor | No |
| Q3: reply and refuse transfer | 2192 | 578 | 12 of 12 | Alice | No |
| Q4: all filter | 239 | 86 | 12 of 12 | Alice | Round 2 |

- All eight refusal subsets were evaluated. Any member who follows the yielding policy permits a transfer; complete refusal prevents it. The stopping rule and free boundary filters are supplied experiment controls.
- Every completed R11 `Produce` emits Fe. Production costs vary by sender type, from 6 to 29 units in this fixture. Reception of the resulting request costs 2–11 units across receiver types and is constant across senders at each fixed receiver state.
- Sending the same retained utterance after another paid `Learn` changes R11 emission to Ti and changes reception cost in all 256 type pairs. Sender activity therefore matters to attention costs.
- The analytical design with both actors initially at their leading seats has a mean reception cost of 9 in both releases. It does not provide a universal tariff for named relations during actual activity.
- Readmission requires a paid new agreement. The already prepared organization can admit the fourth member without six additional practice runs.

R10 and R11 agree on the four policies' physical outcomes under ample resources, while their work costs differ. These finite results do not establish human type rankings, malicious intent, emotional retaliation, or learned extinction. Q3 implements a paid reply followed by refusal; the stopping controller counts delivered replies and fulfilled transfers.

The [working note](docs/HLE_Malice_Matrix_R11_Working_Note_v1.md) gives the methods, detailed costs and interpretation limits. A [Word copy](docs/HLE_Malice_Matrix_R11_Working_Note_v1.docx) is included. [protocol.json](protocol.json) specifies the experiment, and [results](results/) contains the complete result data as compressed JSON, including stage costs and processing states.

## Re-run the policy and attention study

Python 3.12 or later, standard library only, from the repository root:

```bash
python verify_sources.py
python run_studies.py --out results
python -m unittest discover -s tests -v
```

The runner executes releases in separate processes and writes `results/r10.json` and `results/r11.json`. Tests use these freshly generated files when present, otherwise the included `.json.gz` snapshots. The snapshots decompress to the exact verified JSON; their uncompressed hashes are in [results/validation.json](results/validation.json).

Validation used Python 3.12.14: 1,216 simulation cases, 4,096 independent route-cost checks, 4,096 element-preservation checks, and all 10 study checks passed. A repeated complete execution produced byte-identical results. All 353 tests from the full R11 release also passed; their [execution log](results/r11_full_release_tests.log) is included. This repository supplies the study checks and runtimes; the full upstream test suite belongs to the original release.

## Sources and license

R11 release 1.1.0 manifest SHA-256:

`2457e439f3f1526f9d181a7b78def98e8a77593c440d29e2cbb7ec24c5e103d3`

R10 release 1.0.0 manifest SHA-256:

`2150b59e364bf1e4e1ee67f2979b3d8bc997e6006870da5fb54f330583212f8a`

All 82 vendored runtime modules match their upstream manifest entries. The 42 R11 modules also match the supplied holon-meaning probe runtime. [sources/provenance.json](sources/provenance.json) records the pins and source hashes.

The MIT license covers the new study code and writing, as scoped in [LICENSE](LICENSE). Existing engine and probe files retain their upstream status; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The source paper is cited but is not redistributed.
