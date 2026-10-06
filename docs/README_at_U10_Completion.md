# HLE unified object engine — U10

U10 adds grounded workshop communication, separate speaker intentions and receiver interpretations, paid vocabulary learning, generated questions, observed counterexamples, retained meaning repair, practical responses and explicit commitments. It includes all earlier milestones and the frozen R21B baseline.

Use Python 3.12 and the standard library. From this directory, choose a fresh output path:

```sh
python tools/reproduce_u10.py --out /tmp/hle-u10-reproduction
python tools/inspect_u10.py /tmp/hle-u10-reproduction/u10_witnesses/grounded_meaning_and_repair.checkpoint.json --actor bob --assess
```

The reproduction command runs the U10 tests and raw witnesses, then the complete U9 predecessor panel. The inspector restores the history before showing actor-owned language state; `--assess` adds a separate offline audit.

Read `docs/HLE_Unified_U10_Report_v1.md`, `docs/U10_Architecture_and_Scope_v1.md`, `docs/U10_Source_Authority.json`, `docs/U10_Development_Record.md`, and `contracts/U10_Protocol_v1.json`. The report records actual gate results. This is a finite typed workshop language, not unrestricted natural-language learning. Teaching opportunities and access are scheduled; the runtime derives questions, interpretations, hypotheses and learned distinctions.

U11–U14 and R21C release acceptance remain open. Earlier milestone documents and source manifests keep their historical meaning. The source package preserves their files and the frozen baseline, with inherited audit extensions explicitly listed in the U10 manifest.
