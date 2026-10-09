# First run: a chosen workflow and a corrected Shell

[Documentation index](../README.md) · [Example source](../examples/first_run.py) · [Verified run receipt](First_Run_Verification.json)

This small demonstration uses existing, explicitly prepared test fixtures. It runs the actual engine and ordinary auditors. It shows participant choice, downstream use, exact restoration and a generated approval-pattern comparison. It does **not** rerun the complete release suite or establish that the supplied scenario arose spontaneously.

## Requirements and command

Use Python **3.12** (verified with 3.12.14), Git and this checkout. The source uses modern Python type syntax; other interpreter versions were not checked for this documentation run. The runtime and demo use the standard library only. Node is needed for the full inspector verification, not this example. No network service or credentials are used by the demonstration.

```sh
git clone https://github.com/GregoritHub/Socionics_Engine.git
cd Socionics_Engine
python3 docs/examples/first_run.py --output ../srl-first-run
```

Windows: replace `python3` with `py -3`. These Windows instructions describe the interpreter command convention; the recorded execution was on Linux. If the directory already exists, select a new name such as `../srl-first-run-02`. The example deliberately refuses to overwrite prior output.

The script adds the repository and `baseline/HLE_Rebuild_R21B` to its own import path. Direct Python experiments need those same import roots. Do not install an unrelated package called `hle` to resolve an import error.

## What happens

1. The [workflow-selection fixture](../../tests_workflow_selection/fixtures.py) supplies actors, a maintenance opportunity and paid outcome-demand content. Its scenario label prepares the test conditions; the resulting `WorkflowSelectionRequest` has no route or recipe instruction field.
2. The participant pays for candidate comparison and selects `workflow-contemplate-accumulation-v1`. The movement creates a personal workflow result, and a later operation actually uses it to answer the next-task question.
3. The [ordinary selection auditor](../../hle_unified/workflow_selection_audit.py) reconstructs the recorded choice. The producing engine restores its checkpoint exactly.
4. The [Shell fixture](../../tests_workflow_shell/fixtures.py) first generates an approval pattern from paid history, then runs a deformed arm, a locally corrected arm, and an intentionally invalid admission-bypass arm. The helper checks the first two worlds and requires the ordinary auditor to reject the bypass.

The first example demonstrates one self-route. It does not on its own demonstrate all 32 cells, the sustained population panel, general learning or all correction mechanisms.

## Expected result

The verified run printed these fields:

| Field | Value | Meaning |
| --- | --- | --- |
| `passed` | `true` | The example assertions and ordinary audits completed |
| `automatic_recipe` | `workflow-contemplate-accumulation-v1` | Chosen recipe in the supplied opportunity |
| `downstream_next_task` | `handover` | A later operation used the generated result |
| `automatic_selections_audited` | `1` | This small example's selection count |
| `checkpoint_restore_exact` | `true` | Restored serialization equals the original |
| `shell.origin_mode` | `generated` | The approval pattern came from the implemented formation rule |
| `shell.blocked` | `unavailable` | Deformed arm could not produce the downstream result |
| `shell.corrected_next_task` | `handover` | Paid local correction enabled later use |
| `shell.correction_spent` | `29` | Modeled work in this particular correction fixture |
| `shell.rejection` | `workflow Shell admission disagrees with paid encounter` | The deliberate bypass was rejected |

All three admission arms spent 38 modeled units in this fixture. The bypass can reach the same next task as the corrected world and still be invalid. That is deliberate: an endpoint does not prove that the process honored its contract. The correction's additional paid work is separately visible. These numbers are fixture results, not calibrated human costs.

## Files to inspect

The new output directory contains:

- `summary.json`: the actual returned result, including the rejected-control reason.
- `automatic_checkpoint.json`: the selected workflow and subsequent consumer.
- `shell_deformed_checkpoint.json`, `shell_corrected_checkpoint.json`, `shell_bypass_checkpoint.json`: separate saved arms, with the last explicitly an invalid control.
- `SHA256.json`: hashes of those outputs, allowing you to identify the exact bytes produced locally.

Restore the automatic checkpoint with `WorkflowSelectionEngine.restore`; the saved Shell arms originate from `WorkflowShellEngine` or the deliberately bypassing test subclass. A checkpoint schema is not interchangeable with every engine class. The [code map](Code_Map.md) explains these families.

The receipt's output hashes identify the documentation verification run. To compare your result, inspect the semantic fields and audit outcome first; preserve your own files and hashes. This demo is a fresh small execution, not a substitute for downloading and validating historical release evidence.

## A small test suite next

From the repository root, choose a new output directory:

```sh
python3 tools/test_c6.py ../srl-workflow-choice-tests tests_workflow_selection
```

The helper configures the same import roots and writes `source.json`, `tests.log` and `summary.json`. The documentation check passed 20/20 methods with no source change; [saved results](verification/workflow_choice_summary.json) and [test log](verification/workflow_choice_tests.log) are included. This is a targeted workflow-choice suite, not all 742 accepted methods. For the full release protocol and its required raw inputs, use [Evidence and reproduction](Evidence_and_Reproduction.md).
