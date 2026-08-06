# Field-level lineage — secured LGD, source extract to Pillar 3 CR1

Scope: the secured loss-given-default figure, every transformation it passes through,
and every field it depends on. Read with [02](02_execution_order.md) for the step order.

Summary of the conclusion, up front: the lineage is complete and traceable from the
collateral extract as far as `out.ecl_by_segment` and the Finance GL feed. It **does not
reach the Pillar 3 CR1 disclosure line in this repository** — the CR1 program exists but
is not invoked by any driver, and could not run if it were, because it reads columns that
its declared input does not contain. Section 5 sets out exactly where the chain stops.

## 1. Sources

| Field | Source file | Loaded by | Landed as |
|---|---|---|---|
| `ACCOUNT_ID` | `&INBOUND./collateral_<period>.csv` | `%load_loan_tape` (step 2) | `stg.collateral.ACCOUNT_ID` |
| `VALUATION` | same | same | `stg.collateral.VALUATION` |
| `HPI_INDEX_ORIG` | same | same | `stg.collateral.HPI_INDEX_ORIG` |
| `HPI_INDEX_CURR` | same | same | `stg.collateral.HPI_INDEX_CURR` |
| `VAL_DT` | same | same | `stg.collateral.VAL_DT` — **read but never used** |
| `ACCOUNT_ID`, `PROD_CD`, `DRAWN_BAL`, `UNDRAWN` | `&INBOUND./loan_tape_<period>.csv` | `%load_loan_tape` | `stg.loan_tape` |
| `SEGMENT`, `SECURED_FLAG` | `config/rules/product_hierarchy.csv` | `%map_product_hierarchy` (step 4) | `stg.tape_mapped` |
| `HAIRCUT` | `config/rules/collateral_haircuts.csv` | `%lgd_secured` (step 9) | `stg.haircuts` |
| `LGD_FLOOR` | `config/rules/lgd_floors.csv` | `%lgd_secured` (step 9) | `stg.floors` |

Notes on the sources:

- The collateral extract is loaded by `%load_loan_tape`, i.e. as a side effect of the
  loan tape step, using a second `filename`/`proc import` pair at the end of that macro.
  It is **not** loaded by `sas/etl/m_ext_valuation_feed.sas`, which is the program whose
  header describes exactly this feed ("Property valuations and indexation", Hometrack)
  and which is never invoked (see [04](04_never_invoked.md)).
- `%assert_rows` is applied to `stg.loan_tape` (minimum 100 rows) but **not** to
  `stg.collateral`. An empty, truncated or stale collateral extract does not stop the run.
- Column types come from `proc import` type guessing. The loan tape import uses
  `guessingrows=max`; the collateral import does not specify `guessingrows` and so uses
  the default (20 rows), meaning `VALUATION` could be typed from the first 20 rows only.
  Both `ACCOUNT_ID` columns are joined without any length or type normalisation on the
  collateral side (the tape side is `left(compress(ACCOUNT_ID))`).

## 2. Derivation in `%lgd_secured` (`sas/macros/m_lgd_secured.sas`)

Input dataset: `stg.pd_pit` (so the record already carries `EAD` from step 6, `SEGMENT`
and `SECURED_FLAG` from step 4, `PROD_CD` from the tape, and the PD fields from step 7).

`stg.sec_base` is built as:

```
stg.pd_pit  LEFT JOIN stg.collateral ON ACCOUNT_ID = ACCOUNT_ID
            LEFT JOIN stg.haircuts   ON PROD_CD    = PROD_CD
WHERE SECURED_FLAG = 'Y'
```

carrying `COLL_VALUATION = c.VALUATION`, `COLL_VAL_DT = c.VAL_DT`, `HPI_ORIG =
c.HPI_INDEX_ORIG`, `HPI_CURR = c.HPI_INDEX_CURR`, `HAIRCUT = h.HAIRCUT`.

Then, per row:

| Output field | Formula | Depends on |
|---|---|---|
| `COLL_VALUATION` | `if missing then 0` | collateral join |
| `HPI_ORIG` | `if missing or 0 then 100` | collateral join |
| `HPI_CURR` | `if missing or 0 then 100` | collateral join |
| `HAIRCUT` | `if missing then 0` | haircut join on `PROD_CD` |
| `INDEXED_VAL` | `COLL_VALUATION * (HPI_CURR / HPI_ORIG)` | the four above |
| `REALISABLE_VAL` | `INDEXED_VAL * (1 - HAIRCUT)` | `INDEXED_VAL`, `HAIRCUT` |
| `LGD_RAW` | `if EAD > 0 then max((EAD - REALISABLE_VAL)/EAD, 0) else 0` | `EAD`, `REALISABLE_VAL` |
| `LGD` | `max(LGD_RAW, LGD_FLOOR)`, `LGD_FLOOR` from `stg.floors` joined on `SEGMENT` | `LGD_RAW`, floor join |

Three properties of this step matter for lineage:

- **`LGD_RAW` is floored at zero before the regulatory floor is applied.** Over-collateralised
  exposures therefore land on the segment floor exactly (0.10 retail mortgage, 0.15 BTL),
  which is visible in the parity baseline: every Stage 3 retail mortgage row in
  `data/expected/ecl_by_segment_202409.csv` has coverage of exactly `0.10`, and every
  Stage 3 BTL row exactly `0.15`. For those exposures the collateral calculation is
  entirely non-binding — the collateral extract has no effect on the reported number.
- **The final step recreates `&outds` from `&outds`.** `proc sql; create table &outds as
  select b.*, max(b.LGD_RAW, f.LGD_FLOOR) as LGD from &outds as b left join stg.floors ...`
  reads and replaces `stg.lgd_sec` in one statement. It works in SAS but is order- and
  warning-sensitive, and it means `stg.lgd_sec` has two different column sets during the run.
- **`max()` here is the row-wise SAS function, and it ignores missing values.** If the
  floor join misses (segment not in `lgd_floors.csv`), `max(LGD_RAW, .)` returns `LGD_RAW`
  and no floor is applied, with no message.

## 3. What survives into the exposure record

`run_ifrs9_ecl.sas` step 11 stacks the secured and unsecured legs with an explicit
`keep=`:

```
keep = ACCOUNT_ID SEGMENT EAD LGD PD_LIFETIME_ORIG DPD_N
       FORBEARANCE_FL WATCHLIST_FL DEFAULT_FL EIR
```

**This is where the secured LGD audit trail is destroyed.** `COLL_VALUATION`,
`COLL_VAL_DT`, `HPI_ORIG`, `HPI_CURR`, `HAIRCUT`, `INDEXED_VAL`, `REALISABLE_VAL`,
`LGD_RAW` and `SECURED_FLAG` are all dropped at step 11. From that point on, the only
evidence that an exposure is secured is the value of `SEGMENT`, and the only surviving
number is `LGD`. No output of the batch — not the CSV, not the GL feed, not
`out.board_pack` — contains the collateral inputs, the haircut applied, or the indexed
valuation. A regulator's question of the form "show me how you got to this LGD" cannot
be answered from the engine's outputs; it can only be answered by re-running it.

Also note that `PROD_CD`, `REGION` and `ARREARS_BUCKET` are dropped here, and
`SICR_REASON` is created later (step 13) but dropped at step 16. This is the direct cause
of the CR1 break in section 5.

## 4. Onward flow to the segment output

| Step | Dataset | What happens to `LGD` |
|---|---|---|
| 11 | `stg.lgd_all` | carried unchanged (secured and unsecured rows stacked) |
| 12 | `stg.lgd_life` | carried unchanged; `PD_LIFETIME` joined on from `stg.pd_lifetime` |
| 13 | `stg.staged` | carried unchanged; `STAGE`, `SICR_REASON` added |
| 14 | `stg.exposure` | carried unchanged; `OVERLAY_FACTOR` added |
| 16 | `stg.ecl_acct` | used, and retained as a column. `ECL = LGD * EAD * OVERLAY_FACTOR` for Stage 3; otherwise `ECL = (Σ over t of PD_MARG(t) * LGD * EAD * DF(t)) * OVERLAY_FACTOR`, i.e. the same `LGD` for every month `t` — LGD is not time-varying anywhere in the engine, despite the `LGD(t)` in spec section 2 |
| 17 | `out.ecl_by_segment` | **`LGD` is not carried.** Output columns are `SEGMENT, STAGE, N_EXPOSURES, TOTAL_EAD, TOTAL_ECL, COVERAGE`. LGD influences the disclosure only through `TOTAL_ECL` and `COVERAGE` |
| 18 | `ecl_by_segment_<p>.csv`, `ECL_GL_FEED_<p>.txt` | as step 17; the GL feed carries only `SEGMENT`, `STAGE`, `TOTAL_ECL` |
| 20 | `out.board_pack` | `SEGMENT`, `sum(TOTAL_EAD)`, `sum(TOTAL_ECL)` — sums across stages |

So the last place secured LGD exists as a field is `stg.ecl_acct`, which lives in WORK
and is deleted when the SAS session ends (see [02](02_execution_order.md) EO-06).

## 5. Where the chain to Pillar 3 CR1 stops

`sas/reports/m_rpt_pillar3_cr1.sas` defines `%rpt_pillar3_cr1(inds=stg.ecl_acct, period=)`,
which would produce `&OUTBOUND./pillar3_cr1_<period>.csv` as:

```
select REGION, SEGMENT, count(*) as N_EXPOSURES, sum(EAD) as EAD,
       sum(ECL) as ECL, sum(ECL)/sum(EAD) as COVERAGE
from stg.ecl_acct where STAGE in (2,3) group by REGION, SEGMENT
```

Four independent breaks sit between step 16 and that file:

| Break | Detail |
|---|---|
| **LIN-01** | `%rpt_pillar3_cr1` is not invoked by `run_month_end.sas`, `run_ifrs9_ecl.sas`, `jobs/monthly_ecl.sh` or any other program in the repository. No driver reaches any `rpt_*` macro. |
| **LIN-02** | Its input `stg.ecl_acct` has columns `ACCOUNT_ID, SEGMENT, STAGE, EAD, LGD, OVERLAY_FACTOR, ECL`. It selects and groups by `REGION`, which was dropped at step 11 and does not exist in `stg.ecl_acct`. In SAS this is a hard `ERROR: Column REGION could not be found`, not a warning. |
| **LIN-03** | Even if `stg.ecl_acct` were persisted, the file is not on the autocall path (`sas/reports/` is not in `sasautos`) and its file name does not match its macro name, so the macro cannot resolve — see [02](02_execution_order.md) EO-10. |
| **LIN-04** | `%rpt_pillar3_cr1_validate` joins `stg.rpt_pillar3_cr1` to `hist.rpt_pillar3_cr1_&PRIOR_YYYYMM` on `c.SEGMENT = p.SEGMENT and c.STAGE = p.STAGE`, but `stg.rpt_pillar3_cr1` is grouped by `REGION, SEGMENT` and has no `STAGE` column, and nothing in the batch ever writes to `hist`. The 5%-variance control described as "queried by Finance Control" therefore cannot execute either. |

Consequences to resolve before migration scope is fixed:

- The CR1 line that is actually filed is produced by something not in this repository.
  Until that is identified, `docs/migration/TARGET.md` acceptance criterion 4
  ("documented lineage … to disclosure line") cannot be met for CR1, and criterion 1
  (numeric parity) can only be evidenced as far as `ecl_by_segment_<period>.csv`.
- If the intent is that CR1 is derived from the engine, then the specification of CR1
  requires `REGION` (and CR2 requires `REGION` and `FORBEARANCE_FL`) to survive step 11.
  That is a behavioural change and needs Model Governance agreement, not a quiet fix.

## 6. The lineage in one line, as it actually is

```
collateral_<p>.csv[VALUATION, HPI_INDEX_ORIG, HPI_INDEX_CURR]
  + loan_tape_<p>.csv[DRAWN_BAL, UNDRAWN → EAD; PROD_CD]
  + product_hierarchy.csv[SEGMENT, SECURED_FLAG]
  + collateral_haircuts.csv[HAIRCUT]      (join key PROD_CD — see SF-02, this misses for BTL)
  + lgd_floors.csv[LGD_FLOOR]             (join key SEGMENT)
  → INDEXED_VAL → REALISABLE_VAL → LGD_RAW → LGD
  → stg.lgd_all (all collateral detail dropped here)
  → stg.lgd_life → stg.staged → stg.exposure
  → ECL in stg.ecl_acct (LGD × EAD × OVERLAY_FACTOR, or PD-weighted and discounted)
  → out.ecl_by_segment[TOTAL_ECL, COVERAGE]
  → ecl_by_segment_<p>.csv and ECL_GL_FEED_<p>.txt
  ⇥ Pillar 3 CR1: NOT PRODUCED BY THIS CODEBASE (LIN-01 … LIN-04)
```
