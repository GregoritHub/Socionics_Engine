# U1 module migration map

All 98 runtime modules are accounted for. The source remains unchanged during U1.

| Module | Migration treatment | Milestones |
| --- | --- | --- |
| `hle/__init__.py` | adapt | U2, U4 |
| `hle/__main__.py` | adapt | U2, U4 |
| `hle/assessment.py` | adapt assessor | U14 |
| `hle/assessment_demo.py` | compatibility witness | U14 |
| `hle/assessment_records.py` | adapt | U14 |
| `hle/autonomy.py` | generalize | U6 |
| `hle/autonomy_demo.py` | compatibility witness | U6 |
| `hle/autonomy_evaluation.py` | adapt assessor | U6 |
| `hle/autonomy_policy.py` | generalize | U6 |
| `hle/autonomy_records.py` | adapt | U6 |
| `hle/cards.py` | preserve | U2, U5 |
| `hle/clearance.py` | generalize | U7, U8 |
| `hle/clearance_demo.py` | compatibility witness | U7, U8 |
| `hle/clearance_records.py` | adapt | U7, U8 |
| `hle/clearance_reference.py` | adapt assessor | U7, U8 |
| `hle/clearance_runtime.py` | generalize | U7, U8 |
| `hle/clearance_shell.py` | generalize | U7, U8 |
| `hle/closure.py` | generalize | U11, U12 |
| `hle/closure_demo.py` | compatibility witness | U11, U12 |
| `hle/closure_policy.py` | generalize | U11, U12 |
| `hle/closure_records.py` | adapt | U11, U12 |
| `hle/closure_reference.py` | adapt assessor | U11, U12 |
| `hle/codec.py` | adapt | U2, U4 |
| `hle/compensation.py` | generalize | U7, U8 |
| `hle/compensation_demo.py` | compatibility witness | U7, U8 |
| `hle/compensation_evaluation.py` | adapt assessor | U7, U8 |
| `hle/compensation_policy.py` | generalize | U7, U8 |
| `hle/compensation_records.py` | adapt | U7, U8 |
| `hle/composition.py` | generalize | U11, U12 |
| `hle/composition_assessment.py` | adapt assessor | U11, U12 |
| `hle/composition_demo.py` | compatibility witness | U11, U12 |
| `hle/composition_records.py` | adapt | U11, U12 |
| `hle/concept_demo.py` | compatibility witness | U3, U5 |
| `hle/concept_records.py` | adapt | U3, U5 |
| `hle/concept_structure.py` | generalize | U3, U5 |
| `hle/conceptual.py` | generalize | U3, U5 |
| `hle/content_operators.py` | generalize | U9, U10 |
| `hle/content_records.py` | adapt | U9, U10 |
| `hle/contracts.py` | adapt | U2, U4 |
| `hle/conversion.py` | generalize | U7, U8 |
| `hle/conversion_demo.py` | compatibility witness | U7, U8 |
| `hle/conversion_records.py` | adapt | U7, U8 |
| `hle/conversion_reference.py` | adapt assessor | U7, U8 |
| `hle/crux.py` | preserve | U2, U5 |
| `hle/demo.py` | compatibility witness | U2, U4 |
| `hle/development_contracts.py` | generalize | U7, U8 |
| `hle/development_demo.py` | compatibility witness | U7, U8 |
| `hle/development_evaluation.py` | adapt assessor | U7, U8 |
| `hle/development_protocol.py` | generalize | U7, U8 |
| `hle/development_structure.py` | generalize | U7, U8 |
| `hle/developmental.py` | generalize | U7, U8 |
| `hle/gf2.py` | preserve | U2, U5 |
| `hle/idea.py` | adapt assessor | U14 |
| `hle/individuation.py` | generalize | U7, U8 |
| `hle/individuation_demo.py` | compatibility witness | U7, U8 |
| `hle/individuation_logic.py` | generalize | U7, U8 |
| `hle/individuation_records.py` | adapt | U7, U8 |
| `hle/individuation_reference.py` | adapt assessor | U7, U8 |
| `hle/language.py` | generalize | U9, U10 |
| `hle/language_demo.py` | compatibility witness | U9, U10 |
| `hle/language_records.py` | adapt | U9, U10 |
| `hle/meaning_learning.py` | generalize | U9, U10 |
| `hle/memory.py` | generalize | U3, U4 |
| `hle/memory_demo.py` | compatibility witness | U3, U4 |
| `hle/memory_records.py` | adapt | U3, U4 |
| `hle/metabolism.py` | generalize | U3, U5 |
| `hle/metabolism_demo.py` | compatibility witness | U3, U5 |
| `hle/metabolism_records.py` | adapt | U3, U5 |
| `hle/model_a.py` | preserve | U2, U5 |
| `hle/organization.py` | generalize | U11, U12 |
| `hle/organization_demo.py` | compatibility witness | U11, U12 |
| `hle/organization_policy.py` | generalize | U11, U12 |
| `hle/organization_records.py` | adapt | U11, U12 |
| `hle/paid_work.py` | generalize | U4, U13 |
| `hle/ports.py` | adapt | U2, U4 |
| `hle/processing.py` | generalize | U3, U5 |
| `hle/reconciliation.py` | generalize | U7, U8 |
| `hle/reconciliation_demo.py` | compatibility witness | U7, U8 |
| `hle/reconciliation_records.py` | adapt | U7, U8 |
| `hle/reconciliation_reference.py` | adapt assessor | U7, U8 |
| `hle/reconciliation_runtime.py` | generalize | U7, U8 |
| `hle/relations.py` | preserve | U2, U5 |
| `hle/resource_contracts.py` | preserve | U2, U5 |
| `hle/semantic.py` | generalize | U9, U10 |
| `hle/semantic_records.py` | adapt | U9, U10 |
| `hle/shell_assessment.py` | adapt assessor | U7, U8 |
| `hle/shell_demo.py` | compatibility witness | U7, U8 |
| `hle/shell_fixtures.py` | compatibility witness | U7, U8 |
| `hle/shell_records.py` | adapt | U7, U8 |
| `hle/shell_reference.py` | adapt assessor | U7, U8 |
| `hle/shell_runtime.py` | generalize | U7, U8 |
| `hle/socion.py` | generalize | U5, U10, U12 |
| `hle/socion_assessment.py` | adapt assessor | U5, U10, U12 |
| `hle/socion_demo.py` | compatibility witness | U5, U10, U12 |
| `hle/socion_policy.py` | generalize | U5, U10, U12 |
| `hle/socion_records.py` | adapt | U5, U10, U12 |
| `hle/world.py` | generalize | U3, U4 |
| `hle/world_records.py` | adapt | U2, U4 |

The JSON companion retains source descriptions and record fields. Compatibility witnesses remain available for regression. Assessment adapters retain independent reconstruction; storage adapters have one authoritative writer.
