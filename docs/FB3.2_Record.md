# FB3.2 — Workflow active interruption: prospective protocol

[source_defined] Batch 3.2 follows the unchanged Phase 3 protocol and CT §10. The separate prospective clarification `C7_Workflow_Shell_FB3.2_Amendment_v1.json` specifies the matched paid prefix, the zero-cost cancellation intervention, 32 exact checkpoint pairs, effect assignment and one-attempt preservation. SHA-256: `9bcd49e3e71ed8709c1b92cb0f16be793d539775f6b968fc7903be9ceaa332ba`.

[open] Implementation and all gates remain pending. Accepted batch 3.1 and its admission-only schema remain unchanged; Phase 7 requires explicit R5.

[derived] Added three new interruption modules with a separate schema and namespace. They start the ordinary workflow, stop exactly after its first semantic step, preserve cancellation spending and the retained intermediate, and keep the substituted personal intention separate from the requested destination. The accepted admission-only layer and all previously frozen files remain byte-identical.

[open] Attempt1 freeze `2d3bce8dd37a219cb97d6f970ddbad94db5ff6a0397f53e4a539907efb00f2ad` covers 1260 files. New tests, exhaustive 32-cell panel, exact restoration pairs, independent reconstruction and existing regression are next.
