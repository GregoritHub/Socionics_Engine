# R20 implementation findings and test evolution

The R12 gates were preserved throughout. `Protocol_R20_v1.json` was recorded before the first implementation/evaluation; `Operational_Details_R20_v1.json` records the final explicit resource, search and observer interpretation before the accepted population panel.

- The first smoke run exposed a provenance mismatch: generic memory writes require owned memory/observation evidence, rather than arbitrary capacity record types. The bridge now cites actual owned receipts, and R20 participant operations issue their own receipts.
- A second early run exposed exact typed-record validation on the transaction’s output union. The checkpoint codec now allowlists each actual R20 record; it does not accept arbitrary record subclasses.
- Review of the first successful path found that renewal could consult an evaluator grade. Renewal now uses the authenticated shared procedure. Assessments are observer-only and are never delivered as participant evidence.
- The first independent audit omitted material and work records from its raw index. Adding those raw transaction fields repaired the audit; the runtime outcomes were not loosened.
- The first complete 30-test R20 run had one test-harness error: the missing-consent test looked up a future assessment in a deliberately earlier checkpoint. The test now obtains the immutable activation reference from its source fixture and still tests both missing and refused consent.
- Two additional controls enforce primitive execution order and participant independence from evaluator state. Two further controls cover withdrawn child-closure evidence and withdrawn member commitment. The complete 34-test R20 run passes.
- Final review replaced whole-known-record and whole-dependency scans with retained-procedure and origin indexes. Five affected causal checks pass after this change. A constructor check also verifies that inherited closure requires a real lower constituent and that an already retained sufficient constructor yields horizontal adaptation. Repeated checks are not added to the distinct test count.
- The delivered checkpoint is replayed against the final source, and the release archive receives a separate integrity/import/continuation check. A recomputed outer checksum cannot make an invented closure depth replay.

Initial logs, the earlier continuation branch and the final accepted panel are retained under `evidence/r20`. The earlier continuation is clearly separated from the final supported checkpoint in `panel/continued_r19.checkpoint.json.gz`.
