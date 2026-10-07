# FB4.2 development attempt 1 — retained failure

- Command: `PYTHONPATH=.:baseline/HLE_Rebuild_R21B python -m unittest tests_workflow_nesting_faces.test_nesting_faces -v`
- Result: failed; six discovered methods, with the new parent lifecycle methods unable to commit and the Act face pair rejected.
- Cause 1: the inherited paid movement dispatcher recognizes its frozen `c1`, `c2`, `c3`, `c4` and `c7w` flags. The new additive `c7n` flag therefore reached ready status without creating its two semantic steps.
- Correction: the new subclass implements only its own `c7n` paid-step dispatch, leaving the inherited dispatcher byte-identical.
- Cause 2: the first pair check required one material target identity for both Act faces. The preregistered second-setting contract instead distinguishes restoration of a borrowed tool from transfer of an owned tool.
- Correction: both faces retain an identical fresh starting world, actor and context; Act alone retains its contractually distinct material target role.
- Additional assertion-only corrections: negative tests now accept the earlier inherited-access rejection when it is stricter than the new parent-specific rejection.
- Exit-gate credit: none. This attempt remains failed.
