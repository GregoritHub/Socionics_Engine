# HLE unified engine — U2 common versioned object structure

U2 adds immutable versioned objects, exact definition bindings, addressable relations, optional capabilities, explicit occurrence categories, material lineage, and lossless legacy adapters. The frozen R21B implementation remains unchanged.

**Progress: 2/14 milestones complete. Twelve remain. Next: U3 — compact particulars and situated access.**

Read `docs/U2_Report_v1.md` for completion evidence and limits. `docs/U2_Architecture_and_Compatibility_v1.md` specifies the implemented semantics and authority boundary.

## Package contents

| Path | Purpose |
| --- | --- |
| `hle_unified/records.py` | Immutable common identities, object roles, optional state, occurrences, relations, lineage and transactions. |
| `hle_unified/store.py` | Exact revision lookup, atomic journal, writer checks, structural material operations, validated replay. |
| `hle_unified/codec.py` | Independent allowlisted U2 JSON format. |
| `hle_unified/legacy.py` | Lossless field-by-field adapters and read-only legacy runtime views. |
| `tests_u2/` | Eight required acceptance cases and 23 further controls/comparisons, including 216 matched action sequences. |
| `contracts/U2_Protocol_v1.json` | U2 scope and acceptance panel, declared before implementation. |
| `contracts/Legacy_Adapter_Scope_v1.json` | Exact supported legacy wire tags and fields, including inherited fields. |
| `tools/reproduce_u2.py` | Reproduce U2 tests, selected legacy regressions, source checks and raw witnesses. |
| `tools/u2_witness.py` | Generate inspectable native and legacy checkpoint witnesses. |
| `baseline/HLE_Rebuild_R21B/` | All 3,044 frozen original baseline members and unchanged runtime modules. |
| `contracts/`, `docs/`, `tools/` | Retained U1 contracts, evidence reports, migration map and reproduction tools, plus the U2 additions. |

## Reproduce U2

Use Python 3.12 and its standard library. From this package's root:

    python tools/reproduce_u2.py --out /tmp/hle-u2-reproduction

Choose a new output directory. The command writes per-stage logs and per-test results, verifies the frozen baseline before and after execution, and checks that the U2 execution source remains unchanged. It runs 31 U2 tests plus 71 distinct applicable legacy regressions, rather than rerunning the entire historical release evaluation. Failed stages remain in the output and cause a nonzero result.

To run only the U2 tests:

    python tools/evaluate_u2.py --stage u2 --out /tmp/hle-u2-tests

To generate the inspectable object and checkpoint witnesses:

    python tools/u2_witness.py --out /tmp/hle-u2-witness

For direct imports or interactive development, put this package and its frozen baseline on the Python path:

    PYTHONPATH=baseline/HLE_Rebuild_R21B:. python -m unittest tests_u2.test_acceptance -v

The namespace deliberately reuses baseline `Record`, time and status definitions. There are no external Python dependencies. U1 reproduction commands remain available; the old README is preserved as `docs/U1_README.md`.

## Scope of this milestone

The native store is an object/history service. It is not yet the generalized participant-access or paid-operation runtime. Native material primitives demonstrate structural ownership and conservation; existing participant effects and spending continue through the legacy writer. Procedure descriptions and group membership alone do not grant physical abilities, personal learning, or collective capacity.

Legacy views cannot be written into native storage. Checkpoint recovery preserves canonical legacy text, and continued execution uses the appropriate existing runtime. New U3 participant views, U4 paid operations, later integrated developmental mechanisms, U13 efficiency acceptance and U14 release evaluation remain to be implemented.
