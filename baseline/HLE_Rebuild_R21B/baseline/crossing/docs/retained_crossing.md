# Retained capacity across the missing horizontal connection

The current experiment makes three things separately testable: content identity,
acquired capacity, and its consequential use after support ends. It is a finite
prototype over R11, not a completed implementation of individuation.

## The agreed distinction

Under the adopted club/quadrant bridge, the function edges are:

| Family | Edge |
| --- | --- |
| F | I–We |
| T | It–Its |
| N | I–Its |
| S | It–We |

There is no primitive I–It or We–Its function edge. A sequence along existing
edges establishes reachability; it cannot establish acquired capacity. No edge
is added by this experiment, and TIM stays fixed. For SLI, the native pair is
Si–Te at It and the complementary valued pair is Ne–Fi at I.

The user's crossing narrative supplies the acceptance direction: keep the
complementary capacity, use it on a consequential return, and test it again
under renewed demand. The prototype implements a small part of that contract.
The older statement that a single function cannot change *rows* should not be
used: every listed function edge crosses the individual/collective rows. The
missing edges connect the two quadrants *within* each row.

## What the content operators actually do

| Experimental operation | Checkable output | Elected processing target |
| --- | --- | --- |
| Search | Enumerate available offered alternatives with a learned selection rule | Ne |
| Relate | Filter alternatives against this partner's explicitly delivered acceptance set | Fi |
| Infer | Eliminate candidate programs inconsistent with observed demonstrations | Ti |
| Prepare | Select an admissible item and its recipient for action | Te |
| Hold | Copy an already completed content object without changing it | Fe |

These mappings are **implementation choices**. Enumeration is a narrow stand-in
for possibility generation; explicit acceptance sets are a narrow stand-in for
relational constraints. They are not comprehensive definitions of Ne and Fi.
The supplied search hypotheses are first, last, and all; the boundary hypotheses
are ignore, respect, and reverse. Learning requires exactly one surviving
hypothesis in each family. Contradictory or ambiguous demonstrations cannot
publish a rule.

R11's `Produce → Fe` and `Perform → Te` remain fixed hypotheses in the pinned
engine. They do not establish the semantic element of every message. This
experiment separates the **content aspect** from the **current processing
activity**: a validated finite content kind determines the former; a paid
operation determines the latter. No rule assigns content from the sender's type
or automatically calls its creative function the content.

`Hold → Fe` deliberately retains a production-like activity as a control. A held
Ne or Fi demonstration still arrives as Ne or Fi. Issuing the same completed
demonstration after Ti inference also preserves its content identity. The
adapter does not infer elements from arbitrary prose or solve the general
content-to-element mapping problem.

## The run

The learner initially selects the first offered item and ignores acceptance
constraints. Those are supplied defaults shared by **all** types, not an SLI
behavioral law. Two demanded baseline trials expose repeated failures.

A helper computes and sends demonstrations. The learner pays for reception,
infers programs from the delivered examples, and pays to retain either, both,
or neither program. An assisted practice trial checks that help was usable.
Then a new controller uses only the learner's own current endorsed rule memories.
The same world, wallets, objects, and TIM continue. No transient helper output
is passed to this controller.

Twelve held-out tasks use new object identifiers, two requesting partners,
three to five offered alternatives, and every possible location of the single
acceptable item at each width. A partner's acceptance set is part of its
addressed request, not a hidden answer supplied by the evaluator. The policy and
content operators receive no world Truth, condition name, or desired verdict.

After selection, an actual R11 inspection establishes local ownership. A paid
R11 transfer must then change ownership to the intended recipient. The evaluator
checks both that consequence and agreement with the partner's request. An
ownership-permitted but unwanted transfer fails the task.

| Condition | Successful held-out returns | Interpretation |
| --- | ---: | --- |
| No instruction | 3/12 | First-item default sometimes happens to work |
| Help without retained rules | 3/12 | Assisted practice succeeds; unsupported performance does not improve |
| Search rule retained | 3/12 | Finds alternatives but still violates constraints |
| Boundary rule retained | 3/12 | Avoids unwanted transfers but cannot select beyond the first item |
| Both rules retained | 12/12 | Finite retained-complement candidate for SLI |
| Both retained, execution withheld | 0/12 | Correct selections do not establish consequential return |
| Quiet after help | Not assessed | No renewed demand from which to judge clearance |

The helper performs no work during the held-out phase. All 32 comparisons of
identical content across different sender activities preserve the content hash,
aspect, receiving position, and reception cost: two content families across 16
receiver types, each compared after Fe and Ti activity.

The same learning procedure also succeeds 12/12 for all 16 types. Their total
learner costs range from 569 to 969 model units; SLI uses 823. Type influences
R11 routing prices, not which program is learned or which item is chosen. The
Ne–Fi pair is complementary only for the ST types SLI and LSE; success by other
types is recorded as task learning, without the complementary-capacity verdict.
These are comparisons within this supplied task, not human type rankings.

## What this establishes, and what remains open

The positive case satisfies an explicit finite conjunction: same TIM, matching
complementary pair, owned retained rules used again, no helper work, new objects,
complete search, respected partner constraints, actual return, and repeated
success under equal or greater offered-set demand. Removing a required component
prevents this verdict. The programs depend on demonstrations; a different
consistent demonstration can teach a different program.

This is procedural learning in a supplied hypothesis space. It does **not** yet
establish the narrative's full individuation claim, spontaneous development,
altitude change, a dual/kindred schedule, or human validation. In particular:

- Role, collapse, cancellation, compensation, and their recurrence are not
  generated or measured here. The observed baseline failure is not labeled a
  psychological Shell. Resolving that finite failure is not full Shell clearance.
- Native Si capacity is an assumed starting competence; the code does not learn
  all four beats of Si → Ne → Fi → Te. It realizes the final return through
  inspection and transfer.
- The adapter leaves R11's processing perspective unchanged. It tests useful
  complementary task operations and retained use, not an implemented horizontal
  Crux movement. Graph reachability never supplies the acceptance verdict.
- Memory retrieval uses explicit owned addresses. In the help-only control,
  inference receipts still exist in the journal, but the fresh controller's
  durable-capacity interface excludes unretained receipts. This is a declared
  memory-use policy, not a derived forgetting mechanism.
- Requests are truthful, channels reliable, ownership stationary within each
  task, and ample resources supplied for the main panel. Partial work is tested
  separately and cannot publish content. Numerical work prices are model choices.
- The experimental command codec is not implemented: checkpoint/restore raises
  explicitly. This is an executable study adapter, not an R12 engine release.

The next substantive mechanism is to generate compensation/cancellation and
test whether it recurs when the acquired capacity meets a new kind of demand.
Merely increasing offered-set width cannot settle that mechanism.

## Run and validation

```bash
python run_crossing.py
python -m unittest discover -s tests -p test_crossing.py -v
```

The runner uses the bundled R11 runtime and the standard library. It writes one
current result file, `results/crossing.json`. The committed
[compressed result](../results/crossing.json.gz) contains all trial evidence and
controls. The [protocol](../crossing_protocol.json) declares source status,
assumptions and source-document hashes. Full source manuscripts are not copied
into this repository.

Validation: 16 new behavior/boundary tests and all 10 existing study checks pass.
Every work charge reconciles independently with its energy and time debits.
All 82 pinned runtime modules still match their source manifests. The new tests
exercise the model directly rather than using the stored result as an oracle.
