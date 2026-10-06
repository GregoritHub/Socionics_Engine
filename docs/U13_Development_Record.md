# U13 development record

21 September 2026

The U1 efficiency contract was read before choosing optimizations and is unchanged. The U13 protocol was frozen after inspecting the code and profiling the reference, before changing the runtime. Additional native workloads and their budgets were declared prospectively. Development observations are not release evidence.

The reference U12 package contains exact copies of all 92 supplied native and fixture Python members. All 3,044 R21B baseline members, including its 98 runtime modules, remain byte-identical. Optimizations live in the separate native namespace or the explicit legacy adapter.

The first compact-store revision removed canonical JSON equality in favor of ordinary equality over encoded structures. Two inherited U3 tests exposed Python's bool/int equivalence: False was treated as zero. This attempt is retained in `development/u3_pass1.log`. The implementation now compares exact recursive types and values. All 32 U3 tests passed on the second run. A dedicated U13 control tests nested bool/int distinctions and another forces structural hash collisions to verify exact comparison before reuse.

The structural pool initially used retained full structural keys. Review replaced these with compact hash buckets that verify complete typed equality, avoiding a second retained copy of every field list. Internal hash randomization never reaches the deterministic wire format.

Profiling, development memory measurements and test passes are retained separately. The first matched IEE checkpoint preserved exact continuation, reduced retained allocations from 37,018,998 to 23,793,268 bytes, and left compressed size and traced restoration peak unchanged. The first shared native fixture preserved exact checkpoint, participant views and wallets, with active and restore time reductions. These observations guide validation; final reporting uses the declared complete panel.

No Model A charge, personal receipt, acquisition prerequisite, public rule, historical effect, unfinished job or resource allocation was relaxed. No U14 evaluation seed or old R21C release panel was used. The report must retain every failed mandatory performance gate if any remains.

The first supplemental interaction worker completed its reference episode but failed while hashing an actor-view string without encoding it. The collection error and invocation are retained under `development/measurement_attempt1`. The collector was fixed; runtime behavior, cases and thresholds were unchanged.

The first complete six-case legacy active-work comparison failed its required geometric-mean budget: 0.913676 against a maximum of 0.85. Every protected output matched. The remaining measurement stages were stopped rather than treating this candidate as accepted. Complete case samples, raw checkpoints, the early gate assessment and its frozen runtime are retained under `development/measurement_attempt2`.

A focused 32-choice profile found 41,120 evidence-liveness checks and six filtered capacity queries per choice. The next implementation caches actor-specific root availability, capacity and signature checks only inside one circuit command. The cache is disabled throughout every commit and removed on completion, nested execution or exception. Material work, policy choices and modeled charges are still performed normally. Four independent state-transition controls cover ownership, mutable-result isolation, commit-time changes, nesting and exception cleanup.

Completed reference measurements may be reused only when reference runtime, fixtures, worker code, protocols, Python and platform match. The next comparison reuses the first completed reference sample set for each eligible case, without selecting by timing. Candidate measurements are always fresh. Missing reference cases and the supplemental interaction cases run afresh. Every reused case retains its original command, source provenance and samples. Default reproduction runs both sides fresh.
