# Holonic Living Engine rebuild R11

Release **1.1.0** · 17 September 2026

R11 integrates paid Model A routing into all four language and eight organization operations. Each job retains its starting processing state, typed route, content price and partial payment. Completing a semantic operation changes the actor's active information element, which affects the next route and subsequent message emission. The original Ne initialization and actual-active-element emission convention remain.

An actor's unfinished semantic work excludes conflicting R4 movements, reception and other semantic jobs. Explicit cancellation preserves costs and activation; changed local evidence fails an unfinished job without publishing a usable output. Local decisions require and preserve the I perspective. No automatic conversion from ITS/IT to I is supplied.

## Run

Python 3.12 or later; standard library only. Run from this directory.

```bash
python -m hle
python -I tools/verify.py --output /tmp/hle-r11-tests
python -I tools/r11_evidence.py --output /tmp/hle-r11-evidence
python -I tools/validate_release.py
python -I tools/verify_r11_release.py --tests /tmp/hle-r11-tests/results.json --evidence /tmp/hle-r11-evidence --output /tmp/hle-r11-release.json
```

The first command demonstrates language and organizational lifecycle behavior. The full acceptance panel takes several minutes and writes 24 compressed command journals plus controls, source hashes and measurements. Use a new output directory when evaluating a changed implementation. `--section main|controls|profiles|hash|causal` can run a declared subset; only `all` writes the complete panel acceptance summary.

- `docs/Step_R11_Report.md`: executed acceptance results and their limits.
- `docs/Progress_After_R11.md`: exact milestone status and remaining work.
- `docs/r11/acceptance.md`: declaration, complete operation mappings and fresh gates.
- `docs/r11/inherited_changes.md`: the three explicitly adjusted historical checks.
- `docs/Release_Scope.md`: current scope; historical R10 scope is retained separately.
- `tools/r11_workloads.py`: seeded, supplied lifecycle opportunities.
- `tools/r11_oracle.py`: independent route, cost, state and ownership reconstruction.
- `tools/r10_oracle.py`: independent accounting, consent and practice reconstruction.
- `hle/semantic_records.py`: checkpointed controls, route specifications and cancellation command.
- `reference/`: unchanged governing documents and original archives, including R10.

Earlier milestone tools/reports remain historical. Run their numerical acceptance commands with their corresponding archived release. R11 uses new language/organization checkpoint schemas and provides no live R10 migration. R2-R7 checkpoint contracts remain unchanged.

The route targets and numerical prices are declared modeling hypotheses. This release implements a finite symbolic ownership domain with externally scheduled lifecycle opportunities. It does not establish empirical psychological calibration, autonomous institutions, unrestricted language, spontaneous Shell generation/clearance, recursive Cross closure, bounded history or an open-world game.
