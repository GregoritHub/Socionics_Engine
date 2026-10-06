# R11 implementation contract

`LanguageWorld` and `OrganizationWorld` use one `SemanticRouting` execution path. Existing local content preparation remains in `_prepare` / `_prepare_organization`: it resolves only owned memories, acquired meanings, delivered and fully received packets, local consent and owned practice. The routing module does not read Truth or another actor's private content.

A new job receives an immutable `SemanticRoute`: family, operation, starting processing-state reference, formal I-to-I boundary and polarity, original content extent and optional paid `RoutePlan`. `SemanticPolicy(enabled=False)` is a fixed ablation control; it preserves processing ownership and uses the original content extent without Model A route/cost/activation. Production defaults to enabled.

The route is selected with R4's `_route_geometry`. R4, R6 and R11 share `route_active`, which advances only after the full cost of a hop has been paid. R11 preserves route geometry and partial credit across retries. Processing state is journaled even during zero-funded or partial calls, and its immutable reference becomes a causal input to the next semantic transaction.

The completed semantic result is installed only when all required work has been funded. Until then, the candidate in a job is an inspectable proposed value, not an owned lexeme, utterance, consent or executable plan. Existing record access and action authorization do not accept it as a completed output. Matching complete inputs can yield identical semantics across types while differing in route, required resources and completion under a fixed budget.

## Ownership and transitions

`_semantic_owners` is an incrementally maintained derived map of actor to `(family, task_id)`, reconstructed from the journal on restore. The pair is checked independently of the human-readable `ProcessingState.busy` string, so choosing a colliding R4 task name cannot steal ownership. R4 and R6 retain their prior progress contracts. Semantic work rejects until an unfinished R4 movement or reception finishes; those layers reject while semantic work owns the state. All attempts remain idempotent by exact command ID.

These local operations require the personal I perspective. A completed R4 Theorize leaves ITS, and a valid R4 Understand (or Apply then Embody) must return to I before semantic/reception processing. R11 never resets perspective to make a conflicting command fit. Message sending remains an R2 operation and uses the sender's actual active element at emission, including a partially funded activation if an old completed message is sent during another job.

`CancelSemantic(command_id, task_id, actor, family, reason)` terminates an unfinished language or organization job with failed status and an explicit cancellation reason. It adds no resource charge, refunds none, preserves attained activation and releases ownership. It installs no candidate. Earlier usable outputs remain owned. A new semantic task must use its own globally unique command IDs.

Before new payment on a retry, evidence and candidate extent are checked again. A changed candidate, stale access or newly inadmissible source terminates the job as failed, retains already paid work and releases processing. There is no additional charge on this failed revalidation. Cancellation and stale-input failure are separately identifiable in the event/work reason. R2/R3 changes remain possible while semantic work is partial and are therefore covered by the revalidation tests.

## Continuation and evidence

R11 language/organization checkpoints include `SemanticPolicy`, immutable job routes and transaction processing states. Restore executes the recorded commands and compares every transaction, rejecting altered routes, progress, states and semantic results even if the outer checksum was recomputed. The original R10 release is preserved for earlier live schemas. No cross-version migration is claimed.

`tools/r11_oracle.py` reconstructs current processing states and exclusive ownership from profiles and the journal. Route expectations use the independent fixed-stack/permutation oracle, not `_route_geometry` or `route_active`. It checks exact required cost, payment conservation, route continuity, publication boundaries and state progression. `tools/r10_oracle.py` separately reconstructs wallets, physical ownership, consent and practice. Actor/runtime indexes are compared only after independent reconstruction.

The inherited R6 controller's queued notices and the organization's supplied opportunity scheduler are unchanged. A caller scheduling mixed work must honor processing availability. Journal/state/receipt growth remains linear or greater with retained work; R11 does not introduce bounded archival storage or arbitrary-scale autonomous scheduling.
