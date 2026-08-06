# True execution order

Derived by following the drivers, not `docs/ops/RUNBOOK.md`.

Entry point chain:

```
Control-M job GCRA_ECL_MONTHLY
  -> jobs/monthly_ecl.sh <YYYYMM> <env>        cd's to sas/, invokes SAS with -sysparm "<period> <env>"
     -> sas/autoexec.sas                       runs before the driver; libnames, config, formats
        -> config/env/<env>.cfg                &INBOUND &OUTBOUND &HISTLIB &RECON_TOL &MAX_TERM_M
        -> sas/formats/fmt_product.sas          $seg. and stage. formats
        -> sas/formats/fmt_ratings.sas          grade. format
     -> sas/driver/run_month_end.sas            Control-M entry point
        -> %include "run_ifrs9_ecl.sas"         the whole ECL run happens inside this include
        -> proc sql: out.board_pack             board pack aggregate, after the include returns
```

`run_month_end.sas` is the only true entry point. `run_ifrs9_ecl.sas` is not invoked
directly in the batch; it is `%include`d, so it shares the same SAS session, macro
symbol table and WORK library, and its `%put NOTE: [ECL] run complete` appears
*before* the board pack step rather than at the end of the job.

## Step order inside run_ifrs9_ecl.sas

| # | Step | Kind | Input | Output |
|---|---|---|---|---|
| 1 | `%period_dates(&PERIOD)` | macro (`m_util_dates`) | `&PERIOD` | `&RPT_DT`, `&RPT_DT_SAS`, `&PRIOR_YYYYMM` |
| 2 | `%load_loan_tape(period=)` | macro | `&INBOUND./loan_tape_<p>.csv`, `&INBOUND./collateral_<p>.csv` | `stg.loan_tape`, `stg.collateral` |
| 3 | `%clean_loan_tape()` | macro | `stg.loan_tape` | `stg.tape_clean` |
| 4 | `%map_product_hierarchy()` | macro | `stg.tape_clean`, `config/rules/product_hierarchy.csv` | `stg.prod_hier`, `stg.tape_mapped` |
| 5 | `%derive_arrears()` | macro | `stg.tape_mapped` | `stg.tape_arrears` |
| 6 | `%ead_ccf(...)` | macro | `stg.tape_arrears` | `stg.ead` |
| 7 | `%pd_pit(...)` | macro | `stg.ead`, `&INBOUND./macro_scenarios.csv` | `stg.scen`, `stg.scen_w`, `stg.scalar`, `stg.pd_pit`, `&MACRO_SCALAR` |
| 8 | `%pd_term_structure(...)` | macro | `stg.pd_pit` | `stg.pd_curve` (one row per exposure per month), `stg.pd_lifetime` |
| 9 | `%lgd_secured(...)` | macro | `stg.pd_pit`, `stg.collateral`, 2 config CSVs | `stg.haircuts`, `stg.floors`, `stg.sec_base`, `stg.lgd_sec` |
| 10 | `%lgd_unsecured(...)` | macro | `stg.pd_pit` | `stg.lgd_unsec` |
| 11 | inline `data step` | driver | `stg.lgd_sec`, `stg.lgd_unsec` | `stg.lgd_all` |
| 12 | inline `proc sql` | driver | `stg.lgd_all`, `stg.pd_lifetime` | `stg.lgd_life` |
| 13 | `%staging_sicr(...)` | macro | `stg.lgd_life`, `config/rules/sicr_thresholds.csv` | `stg.sicr`, `stg.stage_base`, `stg.staged` |
| 14 | `%fli_overlay(...)` | macro | `stg.staged` | `stg.exposure` |
| 15 | `%discount_eir(...)` | macro | `stg.pd_curve` | `stg.disc` |
| 16 | `%ecl_calc(...)` | macro | `stg.disc`, `stg.exposure` | `stg.curve_j`, `stg.curve_h`, `stg.ecl_raw`, `stg.ecl_acct` |
| 17 | `%aggregate_reporting(...)` | macro | `stg.ecl_acct` | `out.ecl_by_segment` |
| 18 | `%export_disclosure(...)` | macro | `out.ecl_by_segment` | `&OUTBOUND./ecl_by_segment_<p>.csv`, `&OUTBOUND./ECL_GL_FEED_<p>.txt` |
| 19 | `%recon_controls()` | macro | `stg.tape_arrears`, `stg.ecl_acct` | log only |
| 20 | `proc sql` in `run_month_end` | driver | `out.ecl_by_segment` | `out.board_pack` |

Seventeen of the 20 steps above are macro calls; steps 11, 12 and 20 are logic written
inline in the drivers. Adding `%log_step` and `%assert_rows` (called from inside the
others) and `%_env` (in `autoexec.sas`), **20 of the repository's 133 macro definitions
execute**.

## Dataset flow

```
loan_tape_<p>.csv ──┐
                    ├─> stg.loan_tape ─> stg.tape_clean ─> stg.tape_mapped ─> stg.tape_arrears ─> stg.ead
product_hierarchy ──┘                                                                    │
                                                                                         v
macro_scenarios.csv ───────────────────────────────────────────────────────────────> stg.pd_pit
                                                                          ┌──────────────┴───────────────┐
                                                                          v                              v
                                                        stg.pd_curve ─> stg.disc            stg.lgd_sec + stg.lgd_unsec
collateral_<p>.csv ─> stg.collateral ────────────────────┐  (per-month rows)                             │
collateral_haircuts.csv ─────────────────────────────────┤                                     stg.lgd_all
lgd_floors.csv ──────────────────────────────────────────┘                                               │
                                                        stg.pd_lifetime ────────────────────> stg.lgd_life
sicr_thresholds.csv ───────────────────────────────────────────────────────────────────────> stg.staged
                                                                                                         │
                                                                                              stg.exposure
                                                                                                         │
                                                        stg.disc + stg.exposure ─> stg.ecl_acct ─> out.ecl_by_segment
                                                                                                         │
                                                        ecl_by_segment_<p>.csv, ECL_GL_FEED_<p>.txt, out.board_pack
```

## Order facts that differ from the documentation, or that a migration must not lose

**EO-01 — the ordering constraint that is not obvious.** `stg.pd_lifetime` is created as a
side effect of step 8 (`%pd_term_structure`), not by a step of its own, and is consumed
in step 12 by an inline `proc sql` in the driver. Step 8 is also the 40-minute step. Any
migration that parallelises or defers the term-structure build will silently produce
`PD_LIFETIME = missing` in step 13 and re-stage the whole book (see
[05](05_silent_failure_modes.md) SF-05).

**EO-02 — the discount curve is built from PD data, not from the exposure record.**
Step 15 takes `stg.pd_curve` (per-exposure-per-month), so `DF` is computed on the
per-month rows and `SEGMENT`/`EIR` reach it only because they were carried forward from
the tape through `stg.pd_pit`. Step 15 does not depend on steps 9–14, so the true
dependency graph is a diamond, not the straight line the RUNBOOK implies.

**EO-03 — staging happens after LGD, not before.** The order is EAD → PD → LGD → stage
→ overlay → ECL. The spec presents staging (section 6) before measurement, and the
Stage 3 measurement rule in `%ecl_calc` therefore consumes an `LGD` that was computed
without knowing the stage.

**EO-04 — the overlay is applied to the exposure record before ECL, and again inside it.**
Step 14 writes `OVERLAY_FACTOR`; step 16 multiplies by it once, in both the Stage 3
branch and the non-Stage-3 branch. There is no second application, but note that step 14
overwrites `stg.staged` fields into a new dataset `stg.exposure` whose name does not
appear in the RUNBOOK.

**EO-05 — controls run last and cannot stop anything.** Step 19 runs *after* step 18 has
already written the CSV and the Finance GL feed. Even if the controls did compare
anything (they do not — see [06](06_spec_contradictions.md) SC-10), the outputs are
already published by then.

**EO-06 — `stg` is the WORK directory.** `autoexec.sas` sets `%let ROOT = %sysfunc(pathname(work))`
and `libname stg "&ROOT"`. Every intermediate dataset is therefore destroyed at the end
of the session, including `stg.ecl_acct` — which is the input every report program in
`sas/reports/` declares. Nothing in the batch persists account-level ECL anywhere.

**EO-07 — `hist` is assigned but never used by the batch.** `libname hist "&HISTLIB"`
is set up in `autoexec.sas`; the only code that reads or writes `hist` is the report
`_validate` and `_archive` macros, none of which are invoked. The RUNBOOK instruction
"re-running the same period twice appends to `ECL_HIST`. Delete the period first" does
not correspond to any code in this repository: the string `ECL_HIST` does not appear in
it, and every batch output is written with `replace`.

**EO-08 — the shell wrapper's failure signal depends only on `ERROR:` reaching the log.**
`jobs/monthly_ecl.sh` runs under `set -e` and ends with
`grep -c '^ERROR' <log> && { echo ...; exit 1; }`. The exit-status handling is correct:
`set -e` exempts a command that is not the last in an `&&` list, so a clean run (where
`grep` exits 1 because the count is zero) skips the block, prints the success message and
exits 0, while an errored run exits 1. The only oddity is cosmetic — `grep -c` writes the
count `0` to stdout on a clean run, so the job log contains a bare `0` line.

The real limitation is what the check can see. It matches `^ERROR` at the start of a line,
so it catches the SAS log's own `ERROR:` lines, but `ERROR:` messages that macros raise via
`%put` do not stop the run — only `%assert_rows` aborts (`%abort cancel`) — and the
controls that would raise them execute after the disclosure files have already been
written (EO-05). A job that has published a wrong number can therefore still exit 0 unless
SAS itself logged an error.

**EO-09 — the run depends on the working directory.** `autoexec.sas` sets `%let BASE = ..`,
so every config and format path is relative to `sas/`. `jobs/monthly_ecl.sh` does
`cd "$(dirname "$0")/../sas"`; a manual rerun from anywhere else resolves `&BASE.` wrongly
and the config `%include` fails, leaving `&INBOUND` etc. unresolved.

**EO-10 — as checked in, the autocall path cannot resolve any of these macros.**
`autoexec.sas` sets `options sasautos=("&BASE./sas/macros" sasautos)`. SAS autocall
requires the source member's *file name* to match the macro name; here every file is
prefixed `m_` (`m_ecl_calc.sas` defines `%ecl_calc`), no file `%include`s the macro
sources, and `sas/etl`, `sas/reports` and `sas/macros/portfolio` are not on the autocall
path at all. Taken literally, `run_ifrs9_ecl.sas` would fail at its first macro call.
The production job must therefore rely on something outside this repository — a
pre-compiled macro catalogue (`SASMSTORE`), a site-level autocall path, or a wrapper
that includes the sources. **This is an open question for the migration** and matters,
because it means the repository is not known to be a complete description of the running
engine. It should be confirmed with Infra Batch Services before parity work starts.
