# C5 measurement scope

The prospective protocol is `contracts/C5_Protocol_v1.json`. C5 adds no optimization; it reuses indexed owned-pattern lookup and exact native semantic execution. The protocol compares unchanged direct C4 work under the original C4 executor and the C5 subclass. The new Shell-aware path is measured separately.

Three timing samples per unchanged-contract arm are isolated. The new path varies inactive history at 0, 100 and 1,000 objects, separately for equal and distinct payloads; each case has two timing samples and a separate traced sample. Effective pattern count varies 1, 4 and 16 separately under an actual received approval so a native downstream consumer remains available; again, two timing samples and one traced sample.

Each worker measures active wall/CPU time, modeled spending, retained/peak allocation and object resolutions where traced, exact checkpoint size, fresh-instance restore, and independent audit. Setup and engine construction are excluded from active time. One downstream consumer is exercised per measured workload; its per-result active cost equals the workload's active cost. Total recorded attempts include setup where reported, and must not be confused with timed-work denominators.

Participants, content alternatives, nested depth and dependency semantics are unchanged by C5. Their earlier separate C2–C4 measurements are retained as inherited evidence; this C5 run does not present those dimensions as newly measured. C5 itself wraps one requested movement and introduces no candidate search or recursive nesting. C6 must measure participant selection's new search costs. No claim of exhaustive scaling validation follows from this bounded protocol.
