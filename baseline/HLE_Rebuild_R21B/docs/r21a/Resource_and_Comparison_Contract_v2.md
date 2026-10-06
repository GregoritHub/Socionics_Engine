# R21A — resource and comparison contract

The episode has one fixed allocation per actor. Requirements and remaining
resources are recorded separately. Requirement ordering does not establish
affordability, useful development, or clearance.

This is an explicit experimental contract amendment. It is not a new
psychological law and does not change the source papers. The frozen normative
declaration is `Protocol_R21_v2.json`, identified by its adjacent SHA-256 file
and the matching runtime constant in `hle/resource_contracts.py`.

## Allocation and accounting

| Regime key | Energy per actor | Time per actor | Scope |
| --- | ---: | ---: | --- |
| adequate | 100,000 | 100,000 | Entire episode |
| constrained_feasible | 20,000 | 20,000 | Entire episode |
| inadequate | 0 | 0 | Entire episode |

Regime keys preserve the R12 interface. Their names do not establish that a
successful policy exists. Both positive regimes still require full-horizon
feasibility evidence.

The allocation covers historical exposure, three maintaining engagements,
conversion, acquisition and practice of all eight content aspects, withdrawal
of substitute support, the original plus twelve held-out clearance challenges,
and one hundred later opportunities with two changes. Each participant pays
from its own wallet. There is no pooling, replenishment, stage reset, or refund
of already performed work. Failed, partial, canceled and superseded work remains
charged. Conservation is checked independently for energy and time for every
actor, including lenders and reviewers.

Enrollment is an `EpisodeResourceContract` transaction immediately after
genesis. It identifies the protocol hash, episode, seed and regime, and checks
the actual genesis wallets. The runtime rejects later `Credit` commands before
mutation. The raw auditor also rejects hidden credits or refunds in work
records. A partial job at exhaustion stays in the checkpoint. Resource
exhaustion supplies neither a clearance nor a recurrence verdict.

## Comparison

For a pair of demands in the same enrolled episode, let `q` be the declared
requirement vector and `b` the actual wallet. The evaluator keeps both
`q_prior, b_prior` and `q_current, b_current`.

The requirement relation is equal when every component is equal; greater when
every component weakly increases and at least one strictly increases; lesser
under the reverse condition; and incomparable for mixed component changes.
This is a partial order over the elected requirements, not over psychological
difficulty or total cost.

Comparison also requires the same episode contract, assessed actor, genesis
allocation, family, protocol, required outcome, movement, context, participants,
material lineage, constraints, duration length and set of requirement
dimensions. A changed partner remains incomparable. Different episodes and
different resource regimes are not interchangeable comparison frames.

Within this scope, a declining actual wallet does not erase an otherwise valid
requirement comparison. Both balances must fit the same original allocation,
must have no replenishment rule, and may not increase between the compared
opportunities. The result reports the wallet relation separately. Zero
headroom can coexist with equal requirements; it cannot make unaffordable work
eligible or publish unpaid results.

The online observer reports actual starting and ending wallets, expenditure
before and during each challenge, the genesis allocation, and both comparison
snapshots. The independent observer reconstructs those fields from raw work
records, using its own comparison calculation. The original
`compare_demands` function and unenrolled episodes keep v1 semantics exactly.

## Independent feasibility policy

`tools/r21a_policy.py:run_reference_policy` implements the declared
`r21a.independent-construction.v1` schedule. It creates a fresh world from the
same TIM, seed, complete genesis configuration, policies and per-actor budget.
It accepts no candidate command stream. It independently performs the same
seeded history, maintaining engagements, conversion, eight-aspect acquisition,
support withdrawal, thirteen challenges and full planned continuation.

The environment uses the original maintenance item's seeded identity. It does
not obtain the item or a stopping decision from clearance status. Participant
controllers use their existing permitted observations, terms, capacities and
resources. The schedule attempts all one hundred later opportunities unless
resources are exhausted or a runtime error is retained. It does not branch on
the clearance evaluator's success/failure result. Shared engine primitives do
not make this an independent learning algorithm; independence here means a
separate constructive execution without candidate replay or assessor guidance.

`tools/r21a_audit.py:evaluate_feasibility` always launches that separate
construction. Success requires matching actual scenario scopes, independently
verified historical exposure and maintenance, all thirteen clearance cases,
current conversion plus eight distinct retained aspects, one hundred paid
own opportunities with conditional physical returns and two changes, current
clearance validity, zero credits/refunds, and reconciled work with no unfinished
jobs. Overlapping/repeated intervals, quiet ticks, a copied success flag or a
shortened history cannot supply the missing horizon.

The current construction policy is intentionally an unchanged-cost baseline.
A declared policy or exact replay is not itself a successful feasibility
witness. Its measured budget failures leave R21B open and do not prove that
every alternative policy is impossible. Any later policy/contract change must
be explicitly versioned with this failure evidence retained.

## Evaluation and preservation

The v1 R21 declaration, failed 480-case evaluation, R12 acceptance declaration,
source documents and historical checkpoints remain unchanged. New v2 episodes
carry a separate journaled protocol selection. Existing v1 checkpoints are not
retrofitted or reclassified as v2 successes.

R21C's new held-out seeds are frozen as 2001–2010 before use. The old
1001–1010 seeds remain regression evidence. R21A uses declared development
seeds only, including 12 and 13 to cover history lengths three and four
alongside the original length-five development seeds. The 480-case grid, full
positive success fractions, thirteen challenges, 100-opportunity horizon,
two changes and performance thresholds remain unchanged.

The gate for R21A is an implemented, versioned and verified contract. The gate
for R21B is useful paid policy feasibility under the whole-episode budget. The
gate for R21C is the full release rerun. R21A alone cannot close parent R21.
