# HLE Id/Identity developmental coupling probe v1

This experiment connects a provisional three-phase recurrence to the existing
R11 processing and memory engine. Sun forms an account, Judgement applies it,
and World embodies the consequences and publishes paid memory bindings. The
next circuit can recall those consequences and a learned checking capability.
These phase meanings are experimental choices; the source manual does not
derive this mapping.

Read `docs/Report.md` for the executed results and `docs/Progress.md` for the
current stepwise status. The unchanged runtime is in `hle/`; all new controller
and evaluation code is isolated in `devprobe/`. The original documents are in
`reference/`. This is an experimental controller, not a replacement R11 release.

## Run

Python 3.12 or later; standard library only. From this directory:

```bash
python3 -m unittest devprobe.test_engine -v
python3 -m devprobe.run
python3 -m devprobe.audit
```

The panel has 360 main trajectories and 32 type/routing controls. It replaces
generated result files with one verified complete final ledger. There is no
parameter fitting or favorable-seed selection. Selected checkpoints are replayed
both by the developmental controller and independently by R11's engine loader.

## Evidence

- `docs/acceptance.json`: the predeclared mapping, conditions, controls and gates.
- `evidence/trials.jsonl`: every run, completed circuit, cost, action, assessment,
  retained capability and pending stage.
- `evidence/aggregates.json` and `evidence/summary.json`: aggregate results.
- `evidence/checkpoints/`: exact compressed controller and engine histories.
- `evidence/tests.log`: execution and continuation tests.
- `evidence/artifact_audit.json`: independent completeness, billing, action
  precondition and capability-provenance checks.
- `evidence/runtime_identity.json`: byte identity of all 42 R11 runtime modules.

The acceptance declaration was hashed before implementation and evaluation:

`d0e663ed14101adf289554af30f6c0862b6b9f0212d7edc0854dac1d1e980e81`

## Scope

The controller supplies goals, timing and phase order. R4 itself infers accounts,
performs actions, observes errors and instantiates its existing generic checking
procedure during Embody. The controller does not insert capability objects or
give Truth/assessment verdicts to the participant. R5 independently evaluates
the resulting histories; it does not drive the participant with evaluator data.

The three-phase order repeats three times per nine-step outer lap. Compared with
the previous read-only probe, an outer step now means one completed developmental
phase, rather than three completed read queries. Card rank, fold, Model A seat,
Crux perspective and current developmental phase remain distinct.

The outer counter groups completed phases; it supplies no additional Ego or
Super-Ego content transformation. Consequently the experiment can establish
whether the paid feedback loop works within the supplied grammar, but cannot
identify unique psychological meanings or prove that 3:1 is optimal. The exact
generic-loop control checks this boundary explicitly.

The fixed checking grammar, finite ownership world and externally supplied
demands are unchanged R11 assumptions. General Shell generation/clearance,
unrestricted developmental complexity and language/organizational recurrence
are not demonstrated by this experiment.
