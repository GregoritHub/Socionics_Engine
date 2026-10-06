# R15 verification evolution

The protocol was recorded before implementation in Protocol_R15_v1.json. The frozen R12 declaration and all inherited behavioral assertions remain unchanged.

The initial 32-test R15 run had one failure in the new independent accounting evaluator's resource-resumption check. The runtime correctly records Credit as credited resources in a WorkRecord. The evaluator initially treated every completed unit as a debit and applied Credit a second time. It was corrected to reconstruct before + credited - charged = after, verify actual debit units separately, and recognize the recorded credit once. The failing tests_initial.log is preserved. Runtime accounting and acceptance thresholds were not weakened.

Review identified two lifecycle risks before delivery: reusing an enacted decision under a new command ID, and overwriting an outstanding request with another consideration. Both now reject before mutation and have explicit tests. A full-witness inspection verifies that new owned evidence invalidates partly paid work without material publication, followed by successful fresh processing.

The evaluator includes partial consideration debits even before a final decision exists. Every paid continuation contributes to the work by item.

A final comparison matches current wallets exactly at the first optional return, establishing that unequal historical spending is not what selects the contrasting paths. R15 adds 35 tests. Initial failures, targeted repair logs and complete final logs are retained.

One concurrent log capture ended without the unittest completion trailer. It was retained as tests_interrupted.log and was not counted as a pass. A serialized, captured rerun reports all 35 tests and a complete OK trailer in tests_final.log and tests_summary.json.
