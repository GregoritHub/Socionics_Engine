# R21B implementation notes

The source documents and foundation distinguish efficient exact particulars
from conceptual tension. This implementation stores exact paid computation
receipts beside the workshop's existing owned observations. It neither places
facts into Fool's Memory nor changes a card/rank meaning, Model A topology,
Crux route, source claim grade or individuation acceptance condition.

The work accounting and resource envelopes are explicit engineering choices.
`Protocol_R21_v3.json` first declares the reduced phase extents and paid predicate
reuse. `Protocol_R21_v4.json` retains that policy and revises only the constrained
allocation after a retained v3 resource failure. Neither contract is a theoretical
proof of minimum resources or unrestricted development.

`hle/paid_work.py` is a mixin activated by a validated genesis declaration.
Unenrolled/v1 and v2 episodes retain their historical circuit implementation.
V3/v4 cache keys include actor-local ownership, context, partner identity, all
semantic option values, relative observed epoch, due/budget/output requirements,
and delivered permission/acknowledgment. Instance labels are excluded. Cached
rows contain predicate values, not a selected option or a completed task.
The actual option is rebound and selected in current offer order, using current
retained guards and visible commitments. Actual partner state and physical load
are still checked afresh by enactment.

New cache entries appear only after completed paid choose work. Entries retain
the exact completed event, bulletin and menu references. Withdrawal or correction
of one of those sources makes the entry unavailable. Partial jobs keep their
existing plan and basis. The visible concurrent group at their first paid quantum
is also retained as derived input and reconstructed during journal replay.
Changing that group invalidates continuation; the actor's previous spending is
never refunded. This handles new opportunities arriving during an unfinished
choice as well as changed commitments.

The raw work audit does not use the runtime's cache, key function, selector or
cost quote. It folds committed orders/messages, recreates its own semantic keys,
recomputes predicates and visible loads, checks choice order, cost extents,
unchanged Model A hop/content prices, source receipts and partial-job accounting.
The whole-episode audit separately verifies history, clearance, physical facts,
all 100 intervals and both resource ledgers.

The candidate and witness are separate invocations from identical genesis and
the same declared scenario. They share the finite engine and opportunity policy.
No candidate command trace, candidate cut points or assessment status controls
the reference execution. This establishes constructive feasibility in the finite
tested model; it is not a claim of independently invented learning algorithms.

## Retained corrections and failures

1. The first new audit attempted a nonexistent `requested_units` attribute.
   `WorkRecord.required_units` is the actual field. The audit was corrected and
   rerun without changing engine behavior or the contract. The note is retained
   in `evidence/r21b/initial/harness_correction.txt`.
2. Two initial test fixtures omitted the required explanation on a
   `WithdrawEvidence` command. Their errors remain in `tests_initial.log`; the
   fixture calls were fixed. They were not runtime failures.
3. The v3 SLI/11 constrained episode exhausted its 100,000-unit whole-episode
   wallet after clearance and 50 later opportunities. Its raw partial trace is
   retained. V3's unexecuted cases remain unassessed in its declared denominator.
4. `partial_group_before_fix.log` records the genuine regression in which a new
   concurrent offer was accepted during a partly paid choice. The runtime and
   raw audit now enforce the frozen group. Both pre-fix source files are retained
   here. `tests_after_partial_fix.log` covers the final correction.
5. The initial v4 development execution began before that final edge-case fix.
   `final_source` therefore separately reexecutes every candidate and witness
   against final source, checks all gates again, and compares complete output
   transaction digests. This is construction from scenario inputs, not command
   replay. The standard sequential panel has unchanged output traces; the new
   concurrent-input regression now fails safely.

The initial v3 and v4 pilot/repeated runs are not added to the distinct test count
or the final 60-case development denominator. Fresh release seeds 2001–2010 stay
reserved. Shared/population release and performance gates remain R21C work.
