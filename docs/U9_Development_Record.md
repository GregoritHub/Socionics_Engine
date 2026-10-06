# U9 development record

The supplied U8 evidence ZIP has a ZIP local-header signature but cannot be opened by Python ZipFile (BadZipFile: File is not a zip file). The source ZIP extracted successfully. Relevant predecessor tests and witnesses will be freshly rerun from source.

The first U9 circuit failed before notice: Particular.value excludes complete Material facets. Changed disclosure to exact scalar material fields through the inherited Selector interface, rather than broadening access types. The subsequent recorded first_circuit.log passes.

The first full test run recorded 23 errors from adding a Concept role without its mandatory Concept facet. The native schema correctly rejected those writes. Added the explicit concept facet; no base validation was relaxed.

The second full run had 32 passes and one failing test expectation: the persistent-consequence test assumed primitive-minimal repair, although the declared policy tries an existing retained capacity first. Corrected the test to measure preserved completed use and actual recovery, without imposing an undeclared optimality rule. The third run passed 37 tests.

Post-test review found that eager branch expansion could use a procedure's initial state at a later conditional. Replaced eager expansion with an immutable residual interpreter stack. Added intermediate-state conditional and midprocedure replay checks. Added explicit interrupted/resource/unresolved-failure categories so cancellation cannot generate a false generalization counterexample.

The fourth development run passed 40 tests, including the dynamic conditional and midprocedure continuation checks. All 24 raw witness checks then passed. Final review identified the need to carry the number of already-considered options into an interpreter-budget stop. Corrected that counter update; the new targeted check passed. The final frozen panel includes 41 U9 tests.
