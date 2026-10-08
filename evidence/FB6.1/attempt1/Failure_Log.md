# FB6.1 provisional failures retained

[machine-checked] These attempts preceded the accepted three-file source freeze and do not count as the batch evaluation.

1. The first builder run rejected the inherited canonical ablation because the provisional check expected `raw_audit_passed=true`. The saved C2/C3 controls correctly carry `raw_audit_passed=false` with a nonempty ordinary-auditor rejection. The check was corrected to require that rejection.

2. The first verifier run expected one face-row object per polarity. The saved FB4.2 panel correctly stores one route-level row containing both polarity worlds. The verifier was corrected to require one passing paired row.

3. A post-acceptance checkpoint-upload retry exposed that two distinct archive members may lawfully have identical bytes. The compact evidence registry initially keyed only by content digest and refused that case. The registry key was corrected to retain both content digest and archive/member identity; the earlier accepted verbose ledger remained unchanged and was not relabelled.

[machine-checked] After both corrections, the builder and independent verifier ran on the recorded source freeze and exited zero. No failed attempt was relabelled as passing.
