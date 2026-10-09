# Implemented capabilities, code and evidence

[Documentation index](../README.md) · [First run](First_Run.md) · [Evidence guide](Evidence_and_Reproduction.md)

This catalogue describes the accepted **Release 1.0**. “Implemented” means a concrete finite mechanism; it does not mean the full architectural aspiration has been realized. Historical architecture reports explain individual layers, while the [final decision](../../evidence/Corrective6/Delivery_Decision.json) and [joint ledger](../../C7_Final_Ledger_v3.json) govern current acceptance. The current suite retains all declared inherited method IDs.

## Objects, access and executable work

| Capability | What researchers can inspect or vary | Implementation and test entry |
| --- | --- | --- |
| Versioned shared objects | Stable identities, exact revisions, typed roles, links, lineage and transactions; distinguish events, interpretations and hypotheticals | [records.py](../../hle_unified/records.py), [store.py](../../hle_unified/store.py), [U2 tests](../../tests_u2/) |
| Situated information and memory | Disclosure, delivered particulars, paid reading, contextual bindings and bounded recall; shared storage does not grant shared knowledge | [particulars.py](../../hle_unified/particulars.py), [U3 tests](../../tests_u3/) |
| Material action and resource constraints | Inspect, care, use, repair, transfer and return where supported; exact custody, stock, condition, revision and skill checks | [material.py](../../hle_unified/material.py), [operations.py](../../hle_unified/operations.py), [U4 tests](../../tests_u4/) |
| Model A processing and cognition | Type-specific lawful paths, support seats, paid partial progress, conceptual binding, anticipation and distinction between a forecast and an actual effect | [cognitive_routes.py](../../hle_unified/cognitive_routes.py), [cognition.py](../../hle_unified/cognition.py), [U5](../../tests_u5/) and [U6 tests](../../tests_u6/) |
| Cancellation, failure and restoration | Preserve spent work, partial results, reservations and real effects; restore with the producing engine's checkpoint schema | [operations.py](../../hle_unified/operations.py), [codec.py](../../hle_unified/codec.py), [continuation tests](../../tests_workflow_continuation/) |
| Exact storage and derived views | Shared immutable structure, dependency-sensitive summaries and indexed access without giving an actor privileged knowledge | [compact.py](../../hle_unified/compact.py), [efficiency.py](../../hle_unified/efficiency.py), [U13 tests](../../tests_u13/) |

## Meaning, choice and continued consequences

| Capability | Implemented behavior and scope | Implementation and evidence entry |
| --- | --- | --- |
| All Crux cells | 16 routes × two polarities in canonical and timed-workflow content; destination semantics, before/after changes and downstream consumers | [Crux execution](../../hle_unified/crux_execution.py), [workflow execution](../../hle_unified/workflow_execution.py), [joint ledger](../../C7_Final_Ledger_v3.json) |
| Automatic participant choice | Outcome-based requests; bounded candidate comparison from owned/received information, resource estimates and acquired capacities; comparison, admission and completion remain separate | [canonical selection](../../hle_unified/selection_execution.py), [final workflow selector](../../hle_unified/workflow_selection_execution.py), [FB2.4 record](../FB2.4_Record.md) |
| Composed operations and contextual transfer | Executable intermediate handoffs, applicability checks, scalar/context qualification, retained output and separately evidenced downstream use | [composition.py](../../hle_unified/composition.py), [Crux composition](../../hle_unified/crux_composition_execution.py), [C4 tests](../../tests_c4/) |
| Continued generated-result families | Theorize → Apply → Embody; Share → Commune → Identify; Coordinate → Mobilize; Institutionalize → Educate; Organize → Integrate → Apply | [workflow_agenda.py](../../hle_unified/workflow_agenda.py), [FB5.3](../FB5.3_Record.md), [FB5.4](../FB5.4_Record.md), [family tests](../../tests_workflow_families/) |
| Bounded parents and polarity behavior | Parent claims depend on real compatible child results; interruption/failure remains visible; charges are once-only; accumulation and expenditure retain distinct contracts | [workflow nesting](../../hle_unified/workflow_nesting_execution.py), [FB4.2](../FB4.2_Record.md), [corrective parent assessment](../../evidence/Corrective6/corrective-parents_clean_verification.json) |
| Sustained fair populations | Deterministic turns for independently owned agendas, accessible prior results, retained semantic changes, finite budgets/episodes, cancellation and exact restore | [workflow population](../../hle_unified/workflow_agenda_population.py), [FB5.5](../FB5.5_Record.md), [sustained tests](../../tests_workflow_sustained_panel/) |

The scheduler chooses whose turn runs. It does not force a route or treat duplicated outputs as development. The sustained 32-cell panel and generated families are specifically declared experiments, not a claim that every arbitrary population spontaneously explores all 32 cells.

## Shells, correction and social consequences

| Capability | Implemented behavior and scope | Implementation and evidence entry |
| --- | --- | --- |
| Executable Shell effects | Approval, obligation, salience, adverse forecast and route exclusion change actual processing/choice; only approval has a generated formation rule | [shell.py](../../hle_unified/shell.py), [shell_policy.py](../../hle_unified/shell_policy.py), [U7 tests](../../tests_u7/) |
| Route-wide deformation controls | Prevention before initiation and interruption after a paid intermediate; unfinished destinations remain unfinished | [workflow Shell gate](../../hle_unified/workflow_shell_execution.py), [interruption](../../hle_unified/workflow_interruption_execution.py), [FB3.1](../FB3.1_Record.md) and [FB3.2](../FB3.2_Record.md) |
| Scoped development | Paid local release, actual response, observed practice, reusable guarded organization and reownership under declared return conditions | [development.py](../../hle_unified/development.py), [U8 architecture](../U8_Architecture_and_Scope_v1.md), [development tests](../../tests_workflow_development/) |
| Longitudinal recurrence and clearance refusal | Follow original material through correction, later native use and renewed demand on the same or another target; reject fabricated or unsupported clearance | [longitudinal auditor](../../hle_unified/workflow_longitudinal_shell_audit.py), [FB5.6](../FB5.6_Record.md), [corrective check](../../evidence/Corrective6/corrective-longitudinal_clean_verification.json) |
| Grounded language and teaching | Structured utterances, addressed delivery, recipient interpretation and separately checked acquisition; reading does not create skill | [grounded_language.py](../../hle_unified/grounded_language.py), [language_semantics.py](../../hle_unified/language_semantics.py), [U10 tests](../../tests_u10/) |
| Collective work and retained group capacity | Acyclic membership, scoped summaries, individual consent and real constituent performance; group capacity is not personal competence | [collective.py](../../hle_unified/collective.py), [U11 architecture](../U11_Architecture_and_Scope_v1.md), [U11 tests](../../tests_u11/) |
| Public rules and institutional correction | Finite generated proposals, exact electorate/assent, trial and maintained rules, service permissions, revision, teaching, succession and dissolution | [institutions.py](../../hle_unified/institutions.py), [U12 architecture](../U12_Architecture_and_Scope_v1.md), [U12 tests](../../tests_u12/) |

The [Shells guide](Shells_and_Compensation.md) explains why task success can coexist with an unresolved pattern, and why personal correction does not dissolve a real public rule. The original generated material and previous consequences remain in history.

## Structural queries and audit tooling

| Capability | What is available | Boundary |
| --- | --- | --- |
| Model A and intertype relations | Eight-position stacks, exact fields, frames and relation/landing maps in the [kernel](../../baseline/HLE_Rebuild_R21B/hle/model_a.py) | Finite formal tables; no person typing or interpersonal-outcome prediction |
| Model G | [Read-only queries](../../hle_unified/model_g.py) for A↔G positions, names, blocks, partners, grades, signs and the declared spine | No changed energy prices, conditioning, regeneration or behavioral feedback |
| Axes and DCNH formulas | [Read-only queries](../../hle_unified/axes.py) for position pairs, formula positions/planes and integer load/tilt recovery | No subtype assignment; source-transcription limits retained |
| Independent assessment | Raw auditors reconstruct inputs, access, paid work, outputs and authority without calling the selector/executor being checked | Shared record definitions and formal geometry remain common; this is not an external human replication |
| Release inspection | [Inspector v4](../HLE_Full_Crux_C7_Inspector_v4.html), per-cell ledger, full-run acceptance, hashes and clean-delivery verification | Data/filter/reference checks passed; no pixel-rendering claim |

## Limits that matter

- The content languages are finite. Workflow bounds are eight tasks, eight inputs, two participants and unit-duration serial slots 0–1,000. Legacy collective layers have their own declared bounds; the two-participant workflow limit is not a universal object-store limit.
- Initial worlds, demands, opportunities and experimental conditions are supplied. No unlimited goal formation, open-ended institution invention, general learning or population growth is claimed.
- Only approval formation is generated. Other Shell effects are explicit fixtures; correction does not grant blanket treatment of every effect kind or every context.
- Acquired capacity, consent, understanding, authority, hypothetical possibility and actual completion are separate facts. A label never substitutes for one of them.
- The current Model G/DCNH layer is structural. Phase 7's proposed two-currency pricing and conditioning experiment has not started.
- Performance checks satisfy fixed host-specific tolerances. No speedup, constant-time behavior, bounded total history storage or calibrated human energy model is claimed.
- The sealed pyref reruns, source questions and empirical human claims remain separate from release acceptance.

For exact denominators and the distinction between release evidence and a tutorial run, see [Evidence and reproduction](Evidence_and_Reproduction.md).
