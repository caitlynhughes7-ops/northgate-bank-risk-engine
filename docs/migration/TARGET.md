# ECL engine migration - target state and acceptance criteria

Raised by Technology as part of the SAS cost reduction programme (KI-052) and
endorsed by the Model Risk Committee in light of KI-047 (key person dependency
and undocumented model code).

## Target state

- Python 3.11, no SAS dependency, runnable on the group container platform.
- Deterministic, seed free, no reliance on SAS dataset ordering.
- Model logic separated from I/O so that the calculation can be unit tested.
- Configuration read from `config/rules/` - no thresholds, weights, haircuts or
  coefficients hardcoded in model code.
- Output contract unchanged: `data/output/ecl_by_segment_<period>.csv` with the
  same columns as the legacy `PROC EXPORT`, plus the Finance GL feed.
- Every calculation step traceable to a section of the model specification, or
  explicitly flagged where no specification exists.

## Acceptance criteria

1. **Numeric parity.** For period 202409 the migrated engine must reproduce
   `data/expected/ecl_by_segment_202409.csv` at segment and stage level to the
   penny (tolerance 0.01 absolute on TOTAL_ECL and TOTAL_EAD).
2. **Parity is evidenced, not asserted.** A regression harness must produce a
   machine readable comparison that can be attached to the model change record.
3. **Any divergence must be explained.** Where the migrated engine cannot match
   the legacy figure, the cause must be identified and documented, and the
   correct treatment agreed with Model Governance before the difference is
   accepted. Silent divergence is not acceptable to the auditors.
4. **Documented lineage.** Field level lineage from source extract to disclosure
   line, sufficient to answer a regulator's question without reading the code.
5. **No behavioural change without approval.** Where the legacy engine departs
   from the approved specification, the migration must preserve the legacy
   behaviour and raise the departure for decision. It must not quietly "fix" it.

## Running outside the bank network

The SAS paths in `config/env/*.cfg` point at production mount points that are not
available on the container platform. Use the checked in sample period instead:

| Legacy | Repository |
|---|---|
| `&INBOUND./loan_tape_<period>.csv` | `data/input/loan_tape_202409.csv` |
| `&INBOUND./collateral_<period>.csv` | `data/input/collateral_202409.csv` |
| `&INBOUND./macro_scenarios.csv` | `data/input/macro_scenarios.csv` |
| `&OUTBOUND./ecl_by_segment_<period>.csv` | `data/output/ecl_by_segment_202409.csv` |

`data/expected/ecl_by_segment_202409.csv` is the legacy engine's output for that
period, captured from the last production run, and is the parity baseline.

## Out of scope for the first phase

- Corporate and Treasury exposures (separate engine).
- Replacing the Finance GL feed file format.
- Re-calibrating any model parameter.
