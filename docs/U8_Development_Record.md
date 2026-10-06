# U8 development record

The protocol was written and hashed before implementing the U8 operations. Development results were retained without replacing failed runs.

| Run | Tests | Result | Cause and resolution |
| --- | ---: | --- | --- |
| run_01 | 12 | 12 errors | The common substrate accepts scalar attributes. New compound fields needed lossless indexed tuple encoding. |
| run_02 | 12 | 12 errors | New effect references were placed in interpretation content before they were available through participant access. The retained content now states the derived result; separate paid records preserve its causal references. |
| run_03 | 12 | 7 errors | Revised treatment records were constructed before their immediate predecessor was pinned. Version construction now supplies that predecessor atomically. Five tests already passed. |
| run_04 | 34 | 1 failure | The scarcity fixture still had 82 units for a 27-unit operation. The fixture budget was lowered from 200 to 130, leaving 12 units while preserving the same required work. All other tests passed. |
| run_05 | 34 | Pass | The corrected U8 suite passes with no errors, failures or skips. |

A full development smoke circuit independently passed the raw audit and exact replay. The raw U8 witness then passed all 26 checks, including an actual material comparison. The final gate separately reruns every native suite, the expanded legacy panel and all native witnesses on frozen execution source.

The physical comparison starts both arms from the same generated-pattern and practice history. Only the treatment arm performs the paid reorganization. It therefore begins forecasting with 19,513 energy units versus 19,561 for the control; both are far above all immediate operation costs. The tested tool has no local correction. Control chooses inspection and leaves wear at zero; retained organization chooses use and produces wear one. This is not a matched-total-work or efficiency experiment.

Original material is retained. The implementation and documents claim only the declared guarded-response organization and finite returns. No reserved release cases or R21C acceptance are used.
