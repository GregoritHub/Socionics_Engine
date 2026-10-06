# R18 development findings

No frozen R12 gate, model dimension, complex pairing or perspective circuit was changed.

1. Initial local smoke work exposed a missing local offer binding while registering a failed production signal. The commit adapter was repaired before the behavioral suite and 48-case panel. No result from that smoke was counted as acceptance.
2. The initial independent observer used incorrect inherited work-record field names (`debit`/`credit` rather than `charged`/`credited`). It was corrected to fold the actual inherited accounting contract before acceptance evaluation.
3. The first 35 new behavioral/integrity tests passed. Review then identified two additional material risks: withdrawal between proposal and action, and counting a learner-authored reply as partner acknowledgment. Current-procedure validation before action and two explicit regressions were added. The final suite contains 37 tests.
4. The 48-case panel explicitly uses partner load capacity 5 with learner load budget 3. The first continuation runner imported R17 with the new work-order domain's default partner capacity 3. That confounded the Se budget trap with Fe partner availability. The inherited Fe procedure could filter the trap, so Se never received its own failed-then-successful practice. Both endpoint circuits succeeded but the observer correctly refused R18.1/R18.2: only seven procedures were retained. The continuation runner was repaired to use the same declared partner configuration as the panel. The failed run and earlier runner remain in the evidence. No failed gate was relaxed, and the matched work-order opportunities were rerun from the original R17 checkpoint.

The work-order production ledger was also given an actual shared load index. Concurrent commitments now compete for the same available capacity. Positive sequential cases retain distinct epochs; a contention control establishes the consequence of overlapping commitments. This prevents a system-effect claim from resting solely on separate successful local outputs.

The initial continuation report also compared the entire historical report object, including its running `events_consumed` counter. The repaired observer compares every assessment/coverage/error field unchanged and reports the before/after event count separately. A continuing journal necessarily increments that telemetry counter; no historical finding is removed or reclassified.

Final observer review added explicit tracking of original R17 capacity withdrawal and material-access restriction. Historical work-order success cannot keep a current R18 gate open after its root procedure becomes unavailable. The material-access regression checks both the live view and the independent observer.
