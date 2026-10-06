# HLE unified object engine — U12

U12 adds participant-generated institutional proposals, independently chosen responses, trial agreements, maintained public rules, public consequences, collective revision, succession, newcomer teaching and dissolution. It includes U1–U11 and the frozen R21B baseline.

Python 3.12 and the standard library are sufficient. From this directory, choose a fresh output path:

```sh
python tools/reproduce_u12.py --out /tmp/hle-u12-reproduction
python tools/inspect_u12.py /tmp/hle-u12-reproduction/u12_witnesses/complete_institution_history.checkpoint.json --actor bob --assess
```

Reproduction freezes the executable source manifest, then runs the U12 tests, raw witnesses and complete U11 predecessor reproduction as three independent processes with separate outputs. It checks source identity again when they finish. The inspector shows only the selected actor's received group and institution accounts; `--assess` adds a separate read-only audit of raw transactions.

Read `docs/HLE_Unified_U12_Report_v1.md`, `docs/U12_Architecture_and_Scope_v1.md`, `docs/U12_Development_Record.md`, `docs/U12_Source_Authority.json`, and `contracts/U12_Protocol_v1.json` for scope and actual results. Historical U1–U11 files remain available. The current roadmap and U12 progress ledger record completed and remaining milestones.

Institutions reference real groups and participant commitments. Their public revisions require exact current-member consent. U7 attribution can affect a proposal; U8 personal correction cannot erase its maintained public consequences. U9 search constructs the material procedure from received facts and acquired primitives; U11/U4 perform and observe the actual work. A newcomer learns the public rule separately from learning the skills needed to perform it. Exact U11 adoption is supported with `InstitutionEngine.adopt(existing_engine)`.

The harness supplies materials, goals, histories and opportunities. Concrete programs, authority proposals, responses, public rules and their revisions are runtime outputs within a finite engineering grammar. The institution governs a voluntary collective service; it adds no coercive material law. Unrestricted institution invention, general psychological validity, U13 efficiency, U14 release and R21C acceptance remain open.
