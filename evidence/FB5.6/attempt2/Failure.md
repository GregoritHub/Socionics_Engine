# FB5.6 attempt2 — uncredited evaluator path failure

[probe] The dry evaluation generated all 29 declared raw worlds, then failed before writing the integrated ledger because the evaluator required its output directory to be below the repository root. The attempted output was `/tmp/fb56-eval`; `Path.relative_to(ROOT)` raised `ValueError`.

[derived] This is a tool-path assumption, not an engine or Shell result. No acceptance gate is credited. The generated worlds, rows, summary and pre-run source freeze are preserved in `matrix/`. The correction accepts either a repository-relative evidence path or an absolute dry-run path; the counted evaluation will still use the repository evidence directory fixed by the protocol.
