# Shells and their connection to compensation

[Documentation index](../README.md) · [Glossary](Glossary.md) · [Runnable comparison](First_Run.md)

**A Shell is a persistent deformation of how a participant encounters something. Compensation is one way of managing the resulting difficulty while leaving the organizing pattern in place.** In this project, successful action and correction of the underlying relation are separate questions.

That connection is a **project-specific interpretive bridge**, grounded below in the target theory and two concrete code paths. It does not identify Shells with every use of “compensation” in psychology or Socionics, nor does it establish a clinical mechanism.

## Theory: what the concept is trying to capture

The [Target Conception](../../contracts/Target_Conception_v1.md), under “A Shell is a persistent deformation of encounter,” defines a defensive pattern that can bind to a person, tool, group, rule, memory, possibility, action or relation. The object need not have a mind. The projecting participant, target, carrier and bearer of consequences can differ.

The proposed pattern “receiving help means surrendering control” illustrates the idea. A particular offer may contain no continuing obligation, yet the participant processes it as if it did. The pattern can then shape attention, attributed authority, anticipated consequences or available actions. The conception explicitly includes routing a discrepancy into a compensating procedure that leaves the original relationship unexamined.

This is why the theory insists on retaining the original material and its history. An arrangement may make the immediate situation manageable without changing the relation that generates the problem. The [Companion Theory §10](../../project_sources/HLE_Final_Build_Companion_Theory_v1_0.txt) makes the operational boundary precise: a Shell must alter a realization or a later decision. It creates no extra Crux route and cannot make an unfinished result count as complete.

## A concrete example: confirmation that is not actually required

Imagine a participant returning a clean borrowed tool. The current agreed terms permit direct return. The participant has nevertheless acquired an expectation that an external person must confirm it.

| Response | Immediate result | What remains to examine |
| --- | --- | --- |
| Wait for attributed approval | The available return is delayed or not initiated | Whether approval was an actual requirement or an added one |
| Obtain another confirmation | The tool may be returned successfully | The unnecessary dependency can survive and be reinforced |
| Revise the unnecessary prerequisite through paid work | Direct action may become available in the supported scope | Whether that change survives renewed demand, changed targets and unsupported conditions |
| Respect an actual approval rule or refusal | Completion may legitimately be prevented | Noncompletion alone is not evidence of a Shell |

The second row illustrates compensation: the surrounding arrangement accommodates the difficulty. It may work materially while the organizing dependency remains. The third is a correction claim, which requires different evidence. Neither row is a diagnosis of a person.

## Implementation lineage 1: the preserved compensation model

The sealed [compensation.py](../../baseline/HLE_Rebuild_R21B/hle/compensation.py) implements a finite tool-return model in `CompensationWorld`. The [records](../../baseline/HLE_Rebuild_R21B/hle/compensation_records.py) keep current terms, a learned confirmation dependency, supporting history, accessible reviewers and material treatment.

In [select_release](../../baseline/HLE_Rebuild_R21B/hle/compensation_policy.py), a clean, due, owned return can proceed directly if neither the real terms nor the participant's dependency requires confirmation. Otherwise the policy compares accessible confirmation against paid reconsideration of retained supports. It minimizes **immediate content work**, not truth error or long-term cost. When confirmation is genuinely required, reconciliation cannot simply waive it; an unavailable reviewer can cause a legitimate wait.

The learning and cost assumptions deliberately permit a locally inexpensive, self-confirming accommodation. Its raw particulars can be accurate and the physical endpoint successful while the generalized prerequisite is unnecessary. These are explicit experimental assumptions in the preserved code, not an inferred universal law. This legacy runtime and the unified runtime below retain distinct schemas and evidence; one is not a drop-in replacement for the other.

## Implementation lineage 2: reusable Shells in the unified engine

The accepted unified engine represents the process through ordinary objects, owned information and paid operations:

| Stage | Concrete mechanism | Source |
| --- | --- | --- |
| Formation | Fresh paid encounters with processed blame under an available demand can generate accountability material and an approval pattern. The configurable threshold defaults to two distinct experiences; duplicate rereading does not substitute. | [ShellEngine._commit](../../hle_unified/shell.py), [PatternPolicy and Pattern](../../hle_unified/shell_records.py) |
| Scope and recurrence | Pattern matching uses owner, context, cue and trigger; each encounter records exact target, carrier, bearer, evidence and applied pattern. A new matching target can reactivate the history. | [shell.py](../../hle_unified/shell.py), [U7 architecture](../U7_Architecture_and_Scope_v1.md) |
| Deformation | Encounter and forecast policies alter attributed prerequisites, salience, risk or action eligibility using actor-owned information. | [shell_policy.py](../../hle_unified/shell_policy.py) |
| Consequence | The Crux/workflow gate can prevent initiation or interrupt work after a paid intermediate. It cannot award the intended destination. | [workflow_shell_execution.py](../../hle_unified/workflow_shell_execution.py), [workflow_interruption_execution.py](../../hle_unified/workflow_interruption_execution.py) |
| Local correction | Paid processing of current, complete counterevidence can release a supported approval/obligation attribution for an exact target revision. | [DevelopmentEngine._derive](../../hle_unified/development.py), [development_policy.py](../../hle_unified/development_policy.py) |
| Retained development | Actual response → delivered/read result → practice retention → guarded reorganization → qualifying later returns for reownership. Each stage has separate evidence requirements. | [development.py](../../hle_unified/development.py), [U8 architecture](../U8_Architecture_and_Scope_v1.md) |

The generated material is not deleted when treatment changes. Local correction is not blanket clearance. Reorganization requires independently successful retained episodes over distinct targets; reownership requires later use, including novel targets and a changed partner within the declared scope. This tracks whether an apparent improvement remains dependent on a particular support arrangement.

**Only approval formation is generated by an implemented evidence rule.** Obligation, salience, adverse forecast and action exclusion are executable effects introduced as explicit fixtures. They must not be described as four additional learned formation mechanisms. Nor does the correction path establish general treatment for all five effects.

## Five effects are not four diagnostic signs

| List | Members | What the list describes |
| --- | --- | --- |
| Executable effect kinds | Approval, obligation, salience, adverse forecast, action exclusion | How a pattern can change processing or choice |
| Operationalized diagnostic signs | Premature translation, forced placement, new defensive structure, residual fragmentation | What a trace and its controls must demonstrate |

For example, a changed route label alone is not proof of premature translation. The evidence must preserve the intended obligation, actual intermediate/result, remaining failure and an available supported continuation. “Residual fragmentation” requires following the same source material through correction and renewed demand. See [Specification §7](../HLE_Full_Crux_Build_Specification_v12.md) and the [Companion Theory §10](../../project_sources/HLE_Final_Build_Companion_Theory_v1_0.txt).

## Why compensation can become a social fact

The target theory allows a private expectation to influence communication and a shared arrangement. The implemented [institution layer](../../hle_unified/institutions.py) provides a bounded version: participants generate structured proposals, exchange and process them, assent to an exact rule, perform actual work and maintain or revise the institution through further paid acts.

Once such a rule is enacted, its constraints are real within that voluntary collective service. Correcting one participant's approval attribution does not erase other participants' commitments or amend the public rule. In the [U12 example](../U12_Architecture_and_Scope_v1.md), personal correction precedes a failed public revision; a later consented revision changes the service constraint while preserving old costs and consequences. Obeying that actual rule is not automatically classified as a personal Shell because of the rule's origin.

The connection to compensation is thus inspectable at two levels: an arrangement can support an individual's immediate action, and a maintained arrangement can become part of the environment other participants must navigate. The finite implementation does not claim unrestricted institutional emergence or coercive social enforcement.

## Tested results and research use

The accepted panels include deformation/control comparisons across all 32 cells in both settings, prevention and active interruption, scoped correction and renewed-demand recurrence. Corrective verification reconstructed 192 native continuation comparisons, eight parent scenarios and separate status-forgery/paid-bypass rejections. These results are recorded in the [release report](../HLE_Full_Crux_C7_Release_Report_v4.md) and [clean assessment](../../evidence/Corrective6/Clean_Assessment.json).

The [first-run example](First_Run.md) demonstrates one generated approval case: the deformed arm blocks the movement; paid local correction permits a downstream task; a bypass reaches that same task but fails the ordinary auditor. It shows why reaching an endpoint is insufficient evidence that the process was legitimate.

For a new experiment, ask separately: Were the actual terms restrictive? What had the actor received and paid to process? Which attribution changed behavior? Who carried the work or consequences? Did correction follow the original material? Does it survive an appropriate return test? Resource exhaustion, missing information, danger, refusal and disagreement remain alternative explanations. A quiet interval or an assessor's label does not clear a Shell.
