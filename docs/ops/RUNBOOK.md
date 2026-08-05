# ECL Engine — Operations Runbook

## Monthly run

1. Confirm the loan tape has landed:  `/data/gcra/inbound/loan_tape_<YYYYMM>.csv`
2. Confirm collateral extract has landed: `collateral_<YYYYMM>.csv`
3. Confirm macro scenarios have been signed off by Economics (email from Economics DL).
4. Run:  `./jobs/monthly_ecl.sh <YYYYMM> prod`
5. Check the log for `ERROR:` and for `WARNING: MERGE statement has more than one data set`.
6. Run the recon pack and circulate to Finance by T+3.

## Known operational quirks

- The job must be run from the `sas/` directory or `autoexec.sas` will not find the macro
  library. Control-M does this; manual reruns often do not.
- `m_pd_term_structure.sas` is slow (~40 min). Do not kill it, it is not hung.
- If the collateral extract is late, the run will still complete. Secured LGD will fall
  back to defaults. **This must be flagged to Finance** — see `known_issues.md`.
- Re-running the same period twice appends to `ECL_HIST`. Delete the period first.

## Escalation

Batch failures: Infra Batch Services.
Methodology questions: GCRA. Note that no current member of GCRA has worked on the
PD term structure code; changes there require Model Governance sign-off and external review.
