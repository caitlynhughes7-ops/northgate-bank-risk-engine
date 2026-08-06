# Programs that are never invoked

Method: start from `jobs/monthly_ecl.sh`, follow `run_month_end.sas` →
`%include run_ifrs9_ecl.sas`, and take the transitive closure of macro calls. Then search
the whole repository for every call site of every other macro. The searches used were, in
effect, "find every `%name(` that is not inside a `%macro` definition line" plus a direct
search for `%ext_`, `%ovr_` and `%rpt_`.

Result: **no `ext_*`, `ovr_*` or `rpt_*` macro is called anywhere in the repository**, and
`%pd_ttc` is not called either. There is no dispatcher, no `%if`-guarded call, no
`call execute`, no data-driven macro invocation and no other driver.

## Totals

| | Files | Macro definitions |
|---|---|---|
| Reached by the batch | 23 (2 drivers, `autoexec.sas`, 2 format programs, 16 core, 2 utility) | 20 |
| Never invoked | 48 | 113 |
| Total in repository | 71 | 133 |

The 48 unreachable files are the 15 `sas/etl/` extracts, the 12 `sas/macros/portfolio/`
books, the 20 `sas/reports/` programs and `sas/macros/m_pd_ttc.sas`, holding 112 macro
definitions between them. The 113th orphan is `%months_between` in `m_util_dates.sas` — a
file the batch does reach, but that macro is never called from anywhere.

## 1. `sas/macros/m_pd_ttc.sas` — 1 macro

`%pd_ttc` — the through-the-cycle logistic scorecard. Superseded per `docs/CHANGELOG.txt`
v4.2 (2019-09-05, "no longer called from driver … left in place pending Model Governance
retirement"), and its own header says so. It is the only orphan in the repository whose
orphaning is documented.

Significance for the migration: it is dead code, but it is also **the only implementation
of spec section 3.1**, which the spec still presents as the origin of PD. See
[06](06_spec_contradictions.md) SC-01. It should be retired formally rather than carried
across.

## 2. `sas/etl/` — 15 programs, 15 macros

`%ext_book_mapping`, `%ext_collections_status`, `%ext_cust_master`,
`%ext_default_register`, `%ext_forbearance_cases`, `%ext_gl_balances`,
`%ext_interest_rates`, `%ext_limit_management`, `%ext_macro_forecast`, `%ext_prior_ecl`,
`%ext_product_reference`, `%ext_rating_grades`, `%ext_securitisation`,
`%ext_valuation_feed`, `%ext_write_offs`.

All 15 follow one template: `filename` → `proc import` → an `ACCOUNT_ID` normalisation
data step → `%assert_rows` → a duplicate-period guard that `%put`s an `ERROR:` if the
extract contains more than one `EXTRACT_PERIOD`. None is invoked, so none of those guards
ever runs.

What the engine does instead: the batch reads only three inbound files, all inside
`%load_loan_tape` and `%pd_pit` — `loan_tape_<period>.csv`, `collateral_<period>.csv` and
`macro_scenarios.csv`. So the data that these 15 extracts would supply either arrives
pre-joined on the loan tape (`RATING_GRADE`, `EIR`, `DEFAULT_IND`, `FORBEARANCE`,
`WATCHLIST`, `PD_LIFETIME_ORIG`) or does not reach the engine at all
(`stg.book_mapping`, `stg.securitisation`, `stg.write_offs`, `stg.gl_balances`,
`stg.prior_ecl`, `stg.collections_status`, `stg.limit_management`, `stg.cust_master`).

Two of these are worth flagging specifically:

- `%ext_valuation_feed` (Hometrack) is the documented source of property valuations and
  indexation, i.e. of the secured LGD inputs — but the collateral data actually used is
  imported inline by `%load_loan_tape` without the `ACCOUNT_ID` normalisation and without
  the row-count assertion that this program would have applied
  (see [03](03_lineage_secured_lgd.md) §1).
- `%ext_book_mapping` is the only program that would create `BOOK_CD`, which all 12
  portfolio override books require (section 3). Both halves of that mechanism are dead.

## 3. `sas/macros/portfolio/` — 12 programs, 36 macros

Twelve acquired-book override programs, each defining `%ovr_<book>`,
`%ovr_<book>_controls` and `%ovr_<book>_recon`: `ashdown`, `calder`, `fenwick`, `kelvin`,
`lowry`, `meridian`, `ngcore`, `orwell`, `pennine`, `severn`, `stanmore`, `trent`.

They are unreachable twice over: nothing calls them, and `sas/macros/portfolio` is not on
the autocall path (`autoexec.sas` adds `&BASE./sas/macros` only, and autocall does not
recurse into subdirectories).

They are also unrunnable as written: every one of them starts with `where BOOK_CD = "<BOOK>"`,
and `BOOK_CD` does not exist in the loan tape (`data/input/loan_tape_202409.csv` has no
such column), in any staged dataset, or anywhere else in the repository outside these 12
files and 4 report programs.

This is the largest single unknown in the pack, because these are not cosmetic. Each
`%ovr_<book>` applies material model adjustments — a PD multiplier from 0.96 to 1.43, an
LGD multiplier from 0.93 to 1.29 with a book-specific LGD floor, a book-specific CCF
between 0.45 and 0.90, and in some books an interest-only PD uplift or a regional LGD
discount — and each `%ovr_<book>_controls` silently defaults missing `RATING_GRADE`,
`REMAIN_TERM_M` and `EIR` to book-specific values, with the comment "data quality
exceptions are suppressed rather than rejected for this book — agreed with Finance at
onboarding". `%ovr_ngcore` additionally suppresses the relative SICR test for accounts
converted in 2003 by setting `PD_LIFETIME_ORIG = PD_LIFETIME`.

Either the group's live engine applies these adjustments and this repository is not the
code that runs, or twelve books of acquisition-agreed adjustments and their agreed data
quality treatments are not being applied to the provision. Both possibilities are
reportable. **This is the first thing to establish with GCRA and Infra Batch Services.**
Per-book factors are tabulated in [01](01_program_inventory.md).

## 4. `sas/reports/` — 20 programs, 60 macros

`%rpt_audit_sample_extract`, `%rpt_board_provision_pack`, `%rpt_board_sensitivity`,
`%rpt_data_quality_dashboard`, `%rpt_eba_fintrep_18`, `%rpt_eba_fintrep_19`,
`%rpt_gl_feed_recon`, `%rpt_gl_journal_extract`, `%rpt_ifrs7_coverage`,
`%rpt_ifrs7_ecl_movement`, `%rpt_ifrs7_stage_recon`, `%rpt_irb_backtest_lgd`,
`%rpt_irb_backtest_pd`, `%rpt_model_monitoring`, `%rpt_pillar3_cq1`, `%rpt_pillar3_cq3`,
`%rpt_pillar3_cr1`, `%rpt_pillar3_cr2`, `%rpt_prior_period_compare`,
`%rpt_stress_icaap_feed` — each with a `_validate` and an `_archive` sibling.

The only reporting the batch performs is `%aggregate_reporting` → `%export_disclosure`
(the segment CSV and the fixed-width Finance GL feed) plus the inline `out.board_pack`
`proc sql` in `run_month_end.sas`. The board pack "added 2023 for Pillar 3 template
change" is that four-line `proc sql`, not `%rpt_board_provision_pack`.

Beyond not being invoked, most of these programs would not run against the dataset they
declare (`inds=stg.ecl_acct`, which has only `ACCOUNT_ID, SEGMENT, STAGE, EAD, LGD,
OVERLAY_FACTOR, ECL`):

| Program | Column it needs that `stg.ecl_acct` does not have |
|---|---|
| `rpt_pillar3_cr1`, `rpt_pillar3_cr2` | `REGION` (dropped at driver step 11) |
| `rpt_ifrs7_coverage`, `rpt_ifrs7_stage_recon` | `BOOK_CD` (never created anywhere) |
| `rpt_audit_sample_extract`, `rpt_pillar3_cq3`, `rpt_gl_feed_recon` | `SICR_REASON` (created at step 13, dropped at step 16) |
| `rpt_board_sensitivity`, `rpt_eba_fintrep_18`, `rpt_model_monitoring`, `rpt_gl_journal_extract`, `rpt_gl_feed_recon` | `DEFAULT_FL` (dropped at step 16) |
| `rpt_board_sensitivity`, `rpt_eba_fintrep_18` | `ARREARS_BUCKET` (dropped at step 11) |
| `rpt_pillar3_cr2`, `rpt_ifrs7_coverage`, `rpt_irb_backtest_lgd`, `rpt_prior_period_compare` | `FORBEARANCE_FL` (dropped at step 16) |
| `rpt_gl_feed_recon` | `PD_LIFETIME` (dropped at step 16) |

The `_validate` macros add a second layer of the same problem: seven of them join the
prior period on `c.BOOK_CD = p.BOOK_CD`, and several join on `c.STAGE = p.STAGE` against
a table they themselves created without a `STAGE` column. Every `_validate` macro reads
`hist.<report>_&PRIOR_YYYYMM`, and nothing in the batch ever writes to `hist`, so on a
first run every one of them fails on a non-existent table. Several of the `where` filters
also look like copy-paste survivals rather than intent — `%rpt_prior_period_compare`
filters `FORBEARANCE_FL = 1`, `%rpt_gl_journal_extract` (a provision posting extract)
filters `DEFAULT_FL = 1`, so it would post only defaulted exposures.

Migration implication: these 20 programs should **not** be reimplemented from the code as
written. The code does not tell you what the reports are meant to contain, and the
`_validate` control totals described as "referenced in the … control attestation" have
never executed. The report specifications need to be re-established from the filed
submissions and the attestations themselves.
