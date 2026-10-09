# Socionics Research Lab

A Python research simulation for studying how situated participants interpret information, choose and pay for work, act on a shared world, coordinate, and retain changes from experience. Socionics supplies part of its formal vocabulary: Model A organizes processing, the **Crux** classifies transformations between four perspectives, and **Shells** model persistent distortions of encounter and action.

The lab makes these ideas inspectable through finite scenarios, exact histories, independent auditors and matched controls. It does not establish that its mechanisms describe people.

**Current status: Release 1.0 accepted; milestone C7 complete, 7/7.** The [final decision](evidence/Corrective6/Delivery_Decision.json) records the corrected full evaluation and verified clean delivery. Historical held releases remain in the repository. Model G and axis/DCNH formula tables are implemented as read-only structure; energy/conditioning dynamics and Phase 7 are not implemented or authorized.

Quick slides:

https://claude.ai/artifact/QcnbsZcZyEMpkaDb3uMSjc#

Fun Stuff: The Price of a Day

https://claude.ai/artifact/1rK8AfUWHNKuUEdGJbgPVd

## Start here

| Your question | Read |
| --- | --- |
| Can I run a small example? | [Verified first run](docs/research/First_Run.md) |
| What can it actually do? | [Capabilities, code and evidence](docs/research/Capabilities.md) |
| What do the concepts mean? | [Conceptual guide](docs/research/Concepts.md) and [glossary](docs/research/Glossary.md) |
| What are Shells, and how do they relate to compensation? | [Shells and compensation](docs/research/Shells_and_Compensation.md) |
| What was tested, and how do I reproduce it? | [Evidence and reproduction](docs/research/Evidence_and_Reproduction.md) |
| Where is the implementation? | [Code map](docs/research/Code_Map.md) |
| Where are the original specifications and historical records? | [Documentation index](docs/README.md) |

## A first run

Use Python **3.12** (verified with 3.12.14). The example uses only the standard library; no API key, model service, package installation or evidence-archive download is needed. The exact verified Python version is recorded in the [run receipt](docs/research/First_Run_Verification.json).

```sh
git clone https://github.com/GregoritHub/Socionics_Engine.git
cd Socionics_Engine
python3 docs/examples/first_run.py --output ../srl-first-run
```

On Windows, use `py -3` in place of `python3`. The output directory must not already exist. The example prepares a maintenance problem, lets a participant select and execute a workflow, checks an actual downstream use, and compares a generated approval Shell with a paid local correction. A deliberate gate bypass must be rejected by the ordinary auditor. See the [walkthrough](docs/research/First_Run.md) for expected output, saved checkpoints and the limits of this demonstration.

## What is implemented

- **A shared versioned object world:** material objects, interpretations, messages, procedures, relationships and institutions have identities, revisions and provenance. Participant access is separately delivered and paid for.
- **Consequential processing:** all 16 named Crux routes under both polarities, in two bounded content settings. Results must satisfy destination-specific obligations and support actual downstream use.
- **Participant selection and continued work:** outcome requests, bounded candidate comparison, paid execution, acquired capabilities, generated-result chains, fair population turns and finite stopping policies.
- **Shell dynamics and development:** five executable effect kinds, generated approval patterns, prevention and active interruption, scoped correction, practice, recurrence and evidence-based refusal of unsupported clearance.
- **Social and material constraints:** real custody, resources, repair/use, delivery, consent, understanding, collective work and versioned institutional rules remain distinct.
- **Inspection and reproduction:** exact checkpoint restoration, raw transaction audits, controls, source freezes and a [standalone release inspector](docs/HLE_Full_Crux_C7_Inspector_v4.html).

The [capability guide](docs/research/Capabilities.md) maps these claims to implementation and tests. This is a code-and-evidence research lab, not a hosted chat application or a personality-typing service.

## Theory, implementation and results

| Layer | What it warrants | Primary entry |
| --- | --- | --- |
| Theory and source definitions | The project's meanings, formal structures and hypotheses | [Companion Theory](project_sources/HLE_Final_Build_Companion_Theory_v1_0.txt) |
| Implementation | What the finite rules and APIs actually execute | [Code map](docs/research/Code_Map.md), [current specification](docs/HLE_Full_Crux_Build_Specification_v12.md) |
| Tested results | What the declared panels, controls and auditors established on frozen source | [Release report](docs/HLE_Full_Crux_C7_Release_Report_v4.md), [clean assessment](evidence/Corrective6/Clean_Assessment.json) |

The accepted run passed **54 required jobs, 742 distinct test methods, 81 isolated measurement workers, and all 32 route/polarity rows in both settings**. Clean delivery verified **739 historical evidence identities** and **1,312 inspector evidence references**. These are software acceptance results within the declared panels, not empirical validation of Socionics. Counts and denominators are explained in the [evidence guide](docs/research/Evidence_and_Reproduction.md).

## Scope and limits

The canonical setting concerns tools, condition/repair, scalar resources and static interfaces. The workflow setting concerns timed maintenance runbooks, bounded to eight tasks, eight inputs, two participants, unit-duration serial scheduling and slots 0–1,000. Initial worlds and goals are supplied; there is no unrestricted natural-language understanding, spontaneous goal formation, general learning, unbounded population growth or universal Shell diagnosis.

Model G grades do not price work in this release. Axis/DCNH mappings do not assign anyone a subtype or affect behavior. Wallets are finite, with no energy replenishment. The separate sealed 5.2.1 reference-kernel rerun remains owed and is explicitly non-blocking for Release 1.0. No optimization gain or pixel-rendering verification is claimed.

## Repository layout

| Path | Purpose |
| --- | --- |
| [hle_unified/](hle_unified/) | Accepted unified engine and independent auditors |
| [baseline/HLE_Rebuild_R21B/](baseline/HLE_Rebuild_R21B/) | Preserved baseline and Model A kernel; sealed |
| [tools/](tools/) and `tests_*` | Scenario runners, auditors, measurements and test fixtures |
| [contracts/](contracts/) | Prospective protocols, bounds and amendments |
| [docs/research/](docs/research/) | Current researcher-facing guides |
| [project_sources/](project_sources/) | Committed project theory and build instructions |
| [evidence/](evidence/) | Committed results, hashes and indices of larger raw archives |
| [reference/](reference/) | Preserved historical implementations and reference material |

Large historical/raw archives are indexed separately; a clone alone is enough for the first run, but not for the complete historical release audit. See [evidence access](docs/research/Evidence_and_Reproduction.md#access-to-raw-evidence). Do not treat an inaccessible archive as reproduced evidence.

Research changes should state a question and a prospective protocol, preserve original worlds and failed attempts, use new output directories, and keep theoretical interpretations separate from observed software outcomes. See [research workflow](docs/research/Evidence_and_Reproduction.md#running-a-new-experiment). Existing licensing and file notices are unchanged; this documentation makes no new licensing grant.
