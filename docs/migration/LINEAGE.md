# IFRS 9 ECL migration lineage

The Python engine preserves the execution order in
`sas/driver/run_ifrs9_ecl.sas`; each disclosure row is an aggregation of
account-level fields produced by the steps below.

| Disclosure field | Source extract and transformations | Python / SAS implementation | Spec basis |
|---|---|---|---|
| SEGMENT | `PROD_CD` in loan tape, product hierarchy join | `product.py` / `m_map_product_hierarchy.sas` | s.1 |
| STAGE | DPD, default, forbearance, watchlist, origination/lifetime PD | `staging.py` / `m_staging_sicr.sas` | s.6 |
| N_EXPOSURES | account count after EAD and LGD legs | `aggregate.py` / `m_aggregate_reporting.sas` | s.8 |
| TOTAL_EAD | `DRAWN_BAL`, `UNDRAWN`, segment CCF | `ead.py` / `m_ead_ccf.sas` | s.5 |
| TOTAL_ECL | PIT PD, constant-hazard curve, LGD, EIR discounting, overlay | `pd_model.py`, `lgd.py`, `discount.py`, `ecl.py` / corresponding SAS macros | s.2–s.7 |
| COVERAGE | `TOTAL_ECL / TOTAL_EAD` | `aggregate.py` / `m_aggregate_reporting.sas` | s.8 |

Detailed source-to-field chain: loan tape and collateral are loaded by
`io.py` (`m_load_loan_tape.sas`), cleaned in `clean.py`, mapped and bucketed in
`product.py` and `arrears.py`, then passed through EAD, PIT PD, term structure,
secured/unsecured LGD, staging, overlay, discounting, ECL and aggregation.

The following legacy details have no basis in the 2016 specification and are
explicitly retained for parity: the v4.3 frozen scenario weights, the BTL
haircut code mismatch, the KI-041 personal-loan discount formula, and the
specific uplift, overlay, CCF and PD masterscale values embedded in later SAS
macros. Their governance status is recorded in `PARITY_FINDINGS.md`.

## Product display-format lineage

| Display output | Source and transformation | Python implementation | Spec basis / calculation status |
|---|---|---|---|
| SEGMENT display label | Segment code rendered by the `$seg.` format in `sas/formats/fmt_product.sas` | `formats.segment_label` / `formats.segment_labels`, backed by `config/rules/fmt_seg.csv` | No basis in `docs/ECL_Model_Spec_v3_2016.md`; display-only and outside the calculation path |
| STAGE display label | Numeric stage rendered by the `stage.` format in `sas/formats/fmt_product.sas` | `formats.stage_label` / `formats.stage_labels`, backed by `config/rules/fmt_stage.csv` | No basis in `docs/ECL_Model_Spec_v3_2016.md`; display-only and outside the calculation path |
| Rating masterscale display label | Numeric rating rendered by the `grade.` format in `sas/formats/fmt_ratings.sas` | `formats.grade_label` / `formats.grade_labels`, backed by `config/rules/fmt_grade.csv` | No basis in `docs/ECL_Model_Spec_v3_2016.md`; display-only and outside the calculation path |

These formats are defined in the legacy autoexec but are not applied by any
reachable batch program. The Python unit preserves their display behaviour
without importing it into any calculation module.

## Environment bootstrap lineage

| Field / assignment | Source file and SAS statement | Python symbol | Spec basis |
|---|---|---|---|
| ENV | `config/env/{uat,prod}.cfg`, `%let ENV = ...` | `EnvironmentSettings.env` | No specification basis |
| INBOUND | `config/env/{uat,prod}.cfg`, `%let INBOUND = ...` | `EnvironmentSettings.inbound` | No specification basis |
| OUTBOUND | `config/env/{uat,prod}.cfg`, `%let OUTBOUND = ...` | `EnvironmentSettings.outbound` | No specification basis |
| HISTLIB | `config/env/{uat,prod}.cfg`, `%let HISTLIB = ...` | `EnvironmentSettings.histlib` | No specification basis |
| RECON_TOL | `config/env/{uat,prod}.cfg`, `%let RECON_TOL = ...` | `EnvironmentSettings.recon_tol`, `recon_tolerance` | No specification basis |
| MAX_TERM_M | `config/env/{uat,prod}.cfg`, `%let MAX_TERM_M = ...` | `EnvironmentSettings.max_term_m`, `max_term_months` | No specification basis |
| raw | `sas/autoexec.sas`, `libname raw "&INBOUND" access=readonly` | `Environment.raw` | No specification basis |
| stg | `sas/autoexec.sas`, `libname stg "&ROOT"` | `Environment.stg` | No specification basis |
| out | `sas/autoexec.sas`, `libname out "&OUTBOUND"` | `Environment.out` | No specification basis |
| hist | `sas/autoexec.sas`, `libname hist "&HISTLIB"` | `Environment.hist` | No specification basis |
| Autocall path | `sas/autoexec.sas`, `options sasautos=("&BASE./sas/macros" sasautos)` | `Environment.autocall_path` | No specification basis |

## Job orchestration lineage

| Observable / artifact | Legacy source | Migrated implementation | Spec basis |
|---|---|---|---|
| Working directory (`sas/`) | `jobs/monthly_ecl.sh:14`, `cd "$(dirname "$0")/../sas"` | `ecl.job.run`, temporarily changes to `ROOT/sas` | No specification basis |
| Board-pack artifact (`out.board_pack`) | `sas/driver/run_month_end.sas:7–11`, post-ECL `proc sql` extract | Produced by the separate board-pack migration unit; intentionally out of scope for this orchestration unit | No specification basis |
| Log file path | `jobs/monthly_ecl.sh:21`, `../logs/ecl_${PERIOD}_${ENVN}.log` | `ecl.job._paths`, configured by `config/rules/job_orchestration.csv`; replaces the prior log at invocation start, then carries captured engine stdout/stderr and appended failure tracebacks | No specification basis |
| Listing path convention | `jobs/monthly_ecl.sh:21`, `../logs/ecl_${PERIOD}_${ENVN}.lst` | `ecl.job._paths`; convention retained, no file fabricated because the Python engine has no print stream | No specification basis |
| SYSparm ordering | `jobs/monthly_ecl.sh:18–19`, `-sysparm "$PERIOD $ENVN"` | `ecl.job.run`, passed to `ecl.environment.bootstrap` and consumed by `scan_sysparm_env`; the environment token currently affects only the log/listing filename | No specification basis |
| Stdout count line | `jobs/monthly_ecl.sh:23`, `grep -c '^ERROR'` | `ecl.job.run`, prints the configured line-start error count, including bare `0` | No specification basis |
| Stdout success message | `jobs/monthly_ecl.sh:28`, `ECL run complete for $PERIOD ($ENVN)` | `ecl.job.run`, configured by `job_orchestration.csv` | No specification basis |
| Stderr usage message | `jobs/monthly_ecl.sh:9–11`, `usage: $0 <YYYYMM> [prod|uat]` | `ecl.job.main`, configured by `job_orchestration.csv` | No specification basis |
| Stderr error message | `jobs/monthly_ecl.sh:24`, `ECL run reported errors, see log` | `ecl.job.run`, configured by `job_orchestration.csv` | No specification basis |
| Missing-argument exit code 2 | `jobs/monthly_ecl.sh:9–11` | `ecl.job.main`, configured by `job_orchestration.csv` | No specification basis |
| Log-error exit code 1 | `jobs/monthly_ecl.sh:23–26` | `ecl.job.run`, configured by `job_orchestration.csv` | No specification basis |
| Clean exit code 0 | `jobs/monthly_ecl.sh:23–28` | `ecl.job.run`, configured by `job_orchestration.csv` | No specification basis |
| Engine-failure exit status | `jobs/monthly_ecl.sh:18` under `set -e` | `ecl.job.run`, generic nonzero code 1 because SAS-specific statuses do not exist in Python | No specification basis |
