# Migration decision register

Decisions below remain open until explicitly resolved by the named owner.

| ID | Decision | Status | Owner | Evidence and reproducing tools |
|---|---|---|---|---|
| DR-001 | The bank currently has no effective reconciliation control on this engine. The §8 totals are computed and discarded by the legacy-compatible `%recon_controls` unit (`RECON_TOL` is referenced nowhere); the null-stage check cannot fire on 202409 because every `%staging_sicr` branch assigns a stage; and controls run after the disclosure CSV and Finance GL feed have already been written (EO-05), so no control can stop a wrong number reaching Finance. The correct comparison basis, tolerance, and operational response remain unresolved. | Open — not resolved by this migration | Model Governance | On 202409, `sum(DRAWN_BAL)=363,101,872.42`, `sum(EAD)=364,013,988.04`, difference `912,115.62` and relative difference `0.251201%`; `tools/recon_whatif.py` and `tools/recon_observability.py` reproduce the evidence without blocking the run. |
