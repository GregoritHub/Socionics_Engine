# HLE Unified U6 v1

Bounded anticipation and continuing autonomy on the preserved U2–U5 native engine.

Python 3.12 and the standard library are sufficient. From this directory:

```sh
python tools/reproduce_u6.py --out /tmp/hle-u6-reproduction
python tools/inspect_u6.py /tmp/hle-u6-reproduction/u6_witnesses/workshop.completed.checkpoint.json --actor alice
```

Use a fresh reproduction output directory. The complete reproduction includes the inherited protected regressions and raw U2–U6 witnesses and takes several minutes. For the U6 demonstration alone:

```sh
python tools/u6_witness.py --out /tmp/hle-u6-workshop
```

`hle_unified/autonomy.py` extends `CognitiveEngine` with paid bounded forecasts, participant opportunities, exact result waiting, paid appraisal, investigation, requests, rest and stopping. `AutonomousEngine.adopt(existing_engine)` replays an existing U5 checkpoint exactly before any U6 configuration. `configure(command_id, AutonomyConfig(...))` declares an actor's standing demand; `step(command_id, actor)` supplies an opportunity. It cannot choose the actor's action or provide its result. Quiescent opportunities return `None` without charges or command-history growth.

The finite workshop driver supplies initial histories and authorized deliveries. It does not supply action order or outcome labels to the scheduler. Inspection and material effects still execute through the U4 paid lifecycle. Corrective integration still executes the U5 Fool's Memory–Model A–Crux circuit. Original R21B files and world contracts remain unchanged.

See `docs/U6_Design_and_Scope_v1.md`, the frozen `contracts/U6_Protocol_v1.json`, the milestone report, and the separately delivered evidence for scope and executed acceptance. This is a bounded development milestone, not U14 release acceptance or validation of psychological realism.
