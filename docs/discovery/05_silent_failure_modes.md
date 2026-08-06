# Silent failure modes — lookups and joins that can miss without an error

A "silent failure" here means: the code continues, no `ERROR:` is written, the run exits
as successful, and the reported provision is wrong or unverifiable. `%put ERROR:` messages
do **not** stop a SAS run; only `%assert_rows` aborts, and it is applied to two datasets
in the whole batch (`stg.loan_tape`, `stg.tape_clean`).

Quantified impacts on the 202409 sample period are in [07_evidence.md](07_evidence.md).

| ID | Where | Trigger | Consequence |
|---|---|---|---|
| SF-01 | `%lgd_secured`, collateral join | `ACCOUNT_ID` mismatch, or a late/short/stale collateral extract | LGD forced to 1.00 for the affected secured exposures |
| SF-02 | `%lgd_secured`, haircut join on `PROD_CD` | Product code not in `collateral_haircuts.csv` | `HAIRCUT = 0`, secured LGD understated — this is live today for the whole BTL book |
| SF-03 | `%lgd_secured`, floor join on `SEGMENT` | Secured segment not in `lgd_floors.csv` | No regulatory floor applied (latent — all six segments match today) |
| SF-04 | `%map_product_hierarchy`, product join | `PROD_CD` not in `product_hierarchy.csv` | Null `SEGMENT`/`SECURED_FLAG`; exposure treated as unsecured with LGD 0.65 and lands in a blank segment in the disclosure |
| SF-05 | driver step 12, `stg.pd_lifetime` join | Any exposure absent from `stg.pd_curve` | `PD_LIFETIME` missing → quantitative SICR test cannot fire → exposure stays Stage 1 |
| SF-06 | `%staging_sicr`, threshold join on `SEGMENT` | Segment not in `sicr_thresholds.csv` | Hardcoded fallback thresholds (2.0 / 0.01 / 30) applied silently |
| SF-07 | `%staging_sicr`, `PD_LIFETIME_ORIG` from the tape | Field missing or blank on the tape | Exposure stays Stage 1 regardless of PD deterioration |
| SF-08 | `%ecl_calc`, `stg.ecl_raw` left join | Exposure has no curve rows | `coalesce(r.ECL_UNADJ, 0)` → ECL of zero for that exposure |
| SF-09 | `%ecl_calc`, inner join of curve to exposure | Exposure has no curve rows, or curve rows exist for an exposure absent from `stg.exposure` | Curve rows dropped silently; the exposure is still reported, measured at `ECL = 0` (see SF-08) |
| SF-10 | `%pd_pit`, `RATING_GRADE` | Grade outside 1–15, or missing | `otherwise PD_GRADE = 0.0410`, i.e. silently graded 10 (`B`) |
| SF-11 | `%clean_loan_tape`, DPD sentinels | DPD is `999` or non-numeric | `DPD_N = 0`; a 999-day-past-due account is treated as up to date |
| SF-12 | `%pd_pit`, scenario names | Scenario label not `BASE`/`UPSIDE`/`DOWNSIDE`/`SEVERE` | `WEIGHT = 0`, scenario silently excluded from the macro scalar |

## Detail and consequence

### SF-01 — collateral join miss forces LGD to 100%, it does not "fall back to defaults"

```sas
left join stg.collateral as c on t.ACCOUNT_ID = c.ACCOUNT_ID
...
if missing(COLL_VALUATION) then COLL_VALUATION = 0;
```

With `COLL_VALUATION = 0`, `REALISABLE_VAL = 0` and `LGD_RAW = (EAD - 0)/EAD = 1`, so the
exposure is measured at a 100% loss given default. `docs/ops/RUNBOOK.md` states that if the
collateral extract is late "the run will still complete. Secured LGD will fall back to
defaults." There is no default: the fallback is the most conservative possible LGD. The
run does complete, silently, and the provision is materially overstated rather than
understated.

Live triggers in SAS are a short, late or stale collateral extract, or a key that differs by
something SAS does not ignore — case, leading whitespace, or a reformatted account number.
Trailing padding is *not* one of them: `%load_loan_tape` normalises the tape side with
`ACCOUNT_ID = left(compress(ACCOUNT_ID))` (because "the source system pads account ids to 12
chars in some months and not others") and the collateral side is not normalised at all, but
SAS blank-pads the shorter operand in a character comparison, so `'NB010000070 '` matches
`'NB010000070'` with or without the `compress`. In the 202409 sample all 213 padded tape IDs
carry exactly one trailing space and no leading whitespace, so that call is a no-op for this
join as the engine runs today.

It is not a no-op for the target implementation, and this is the trap. In Python trailing
blanks are significant, so a port that reads the tape without reproducing the strip loses
the collateral for 119 secured exposures and measures them at LGD 1.00 — £6.5m of spurious
provision on this period, with nothing to catch it ([07](07_evidence.md) SF-01). No count,
no `WARNING` and no `%assert_rows` protects this join in either implementation, and nothing
anywhere checks that the number of secured exposures equals the number of collateral rows.

### SF-02 — the haircut join misses for the whole buy-to-let book (root cause of KI-021)

```sas
left join stg.haircuts as h on t.PROD_CD = h.PROD_CD
...
if missing(HAIRCUT) then HAIRCUT = 0;
```

`config/rules/collateral_haircuts.csv` contains:

```
PROD_CD,PROD_DESC,HAIRCUT
2100,Residential mortgage - repayment,0.25
2101,Residential mortgage - interest only,0.28
110,Buy to let mortgage,0.35        <-- pre-2019 product code
2120,SME commercial property,0.40
2130,SME other secured,0.45
```

`config/rules/product_hierarchy.csv` and the loan tape both use `2110` for buy-to-let.
`docs/CHANGELOG.txt` v4.1 (2019-07-18) records the group-wide `PROD_CD` renumbering and
states plainly: "Mapping tables refreshed EXCEPT collateral haircuts — refresh raised as
separate ticket, see KI-021." That refresh never happened. The join has therefore missed
for every buy-to-let exposure for six years, `HAIRCUT` defaults to zero, the realisable
value of BTL collateral is overstated by the full 35% forced-sale discount, and secured
LGD for the BTL book is understated.

This is exactly the symptom recorded against KI-021 ("secured LGD for part of the mortgage
book looks low versus benchmark. Segment-level review inconclusive"). The review was
inconclusive because at segment level the effect is diluted by the LGD floor: most BTL
exposures are over-collateralised and land on the 0.15 floor either way, so only the
exposures near the floor boundary move. The defect is invisible in aggregate and obvious
in the join.

Note also that `stg.haircuts` is imported with `getnames=yes` and no `guessingrows`, and
that the CSV carries a `PROD_DESC` column that is also present in `stg.prod_hier` — a
duplicate-name collision waiting for anyone who changes the select list.

### SF-03 — the LGD floor can be skipped without a message

```sas
select b.*, max(b.LGD_RAW, f.LGD_FLOOR) as LGD
from &outds as b left join stg.floors as f on b.SEGMENT = f.SEGMENT
```

`max()` with two arguments is the row-wise SAS function and it **ignores missing values**,
so an unmatched segment yields `LGD = LGD_RAW` with no floor and no warning: a secured
segment that is not in `lgd_floors.csv` bypasses the regulatory floor entirely. Spec
section 4.1 requires the floor to be applied after the collateral calculation; the code
applies it only when the join happens to match.

This is latent rather than live — every segment in `config/rules/product_hierarchy.csv` is
present in `lgd_floors.csv` today, so the join matches for all six. It becomes live the
first time a segment is added to the hierarchy without being added to the floors file, and
there is nothing in the batch that would report it. Note that it does **not** apply to
null-segment exposures from SF-04: those are excluded from `%lgd_secured` altogether and
are measured on the unsecured leg, which has its own hardcoded floor.

### SF-04 — unmapped products are reported as a WARNING and then measured anyway

`%map_product_hierarchy` counts unmapped rows and issues `WARNING: [ECL] n exposures with
unmapped PROD_CD` — "unmapped products are reported but not rejected — Finance
requirement". Downstream, an unmapped exposure has `SEGMENT = null` and
`SECURED_FLAG = null`, so:

- `%lgd_secured`'s `where SECURED_FLAG = 'Y'` excludes it;
- `%lgd_unsecured`'s `where SECURED_FLAG ne 'Y'` **includes** it (a missing value satisfies
  `ne 'Y'` in SAS), giving it the `otherwise` LGD of 0.65 — so a secured exposure with a
  new product code is measured as unsecured;
- `%staging_sicr`'s threshold join misses (SF-06), so it gets the fallback thresholds;
- the secured floor join (SF-03) is never reached, because `%lgd_secured` excluded the row.
  The unsecured leg's hardcoded `LGD = max(LGD_RAW, 0.45)` applies instead and is
  non-binding against the 0.65 fallback, so an exposure that should have been floored at
  its secured segment floor is instead measured at 65% — conservative for a mortgage,
  but not the governed number for any segment;
- `%aggregate_reporting` groups by `SEGMENT`, so it appears as a blank segment row in
  `ecl_by_segment_<period>.csv` and as a blank `SEGMENT` in the fixed-width GL feed, where
  Finance's loader has 20 blank characters where a segment code should be.

The `WARNING:` line is the only trace, and `docs/ops/RUNBOOK.md` step 5 tells the operator
to grep the log for `ERROR:` and for one specific MERGE warning, not for this one.

### SF-05 — the PD_LIFETIME join is the load-bearing join in staging

```sas
create table stg.lgd_life as
select a.*, l.PD_LIFETIME from stg.lgd_all as a
left join stg.pd_lifetime as l on a.ACCOUNT_ID = l.ACCOUNT_ID;
```

`stg.pd_lifetime` is a by-product of `%pd_term_structure`. If an exposure is absent from
it, `PD_LIFETIME` is missing, and in `%staging_sicr`:

- `_rel = (PD_LIFETIME > REL_PD_MULT * PD_LIFETIME_ORIG)` — a missing value is lower than
  every number in SAS, so this is false;
- `_abs = ((PD_LIFETIME - PD_LIFETIME_ORIG) > ABS_PD_INCR)` — missing arithmetic gives
  missing, so this is false too.

The exposure therefore falls through to Stage 1 with `SICR_REASON = 'NONE'` unless a DPD,
forbearance, watchlist or default trigger catches it. No `ERROR:`, no `WARNING:`, and
`%recon_controls` only counts `STAGE is null`, which can never happen because every branch
assigns a stage. A silent 12-month measurement for a lifetime-ECL exposure is the single
most material silent failure in the engine.

### SF-06 — missing SICR thresholds fall back to hardcoded values

```sas
if missing(REL_PD_MULT) then REL_PD_MULT = 2.0;
if missing(ABS_PD_INCR) then ABS_PD_INCR = 0.01;
if missing(DPD_TRIGGER) then DPD_TRIGGER = 30;
```

Any segment not present in `config/rules/sicr_thresholds.csv` — including the null segment
from SF-04 — is staged on thresholds that exist only in the code. The values are the retail
mortgage row, so an unmapped credit card exposure would be staged on mortgage thresholds
(2.0 / 0.01 instead of 2.5 / 0.03). Nothing records that a fallback was used.

### SF-07 — `PD_LIFETIME_ORIG` arrives on the tape and is never validated

The origination lifetime PD is taken straight from the loan tape column
`PD_LIFETIME_ORIG`. There is no check that it is populated, in range, or on the same basis
as the `PD_LIFETIME` it is compared against. If it is blank, `_rel` and `_abs` are both
false (same missing-value logic as SF-05) and the exposure stays Stage 1. If it is
populated but on a different basis — which it is; see
[06](06_spec_contradictions.md) SC-06 — the quantitative test is systematically wrong in
one direction rather than randomly wrong, and nothing detects it.

### SF-08 / SF-09 — the two joins in `%ecl_calc` fail in opposite directions

```sas
create table stg.curve_j as select ... from &curveds as c
  inner join &expds as e on c.ACCOUNT_ID = e.ACCOUNT_ID;      /* SF-09 */
...
create table &outds as select ... coalesce(r.ECL_UNADJ,0) ...
  from &expds as e left join stg.ecl_raw as r on e.ACCOUNT_ID = r.ACCOUNT_ID;  /* SF-08 */
```

- SF-09: the `inner join` silently drops curve rows for any account that is not in
  `stg.exposure`, and produces nothing for an exposure that has no curve rows. Nothing
  compares the row count of `stg.exposure` with the number of distinct accounts in
  `stg.curve_j`.
- SF-08: because `&outds` is built from `&expds` with a **left** join to `stg.ecl_raw`, the
  exposure does not disappear — `coalesce(r.ECL_UNADJ, 0)` converts "no curve" into "no
  expected loss". It is reported with its full `EAD` and `ECL = 0` (Stage 1 and 2), so the
  segment coverage ratio is diluted rather than the row vanishing, which is harder to spot
  than an outright drop. Stage 3 exposures are unaffected because their ECL does not use the
  curve.

An exposure can therefore be reported with a multi-million-pound EAD and a zero provision,
and the only evidence would be a coverage ratio that looks slightly low.

### SF-10 — an unknown rating grade becomes grade 10

`%pd_pit` selects `PD_GRADE` from a hardcoded masterscale by `RATING_GRADE` with
`otherwise PD_GRADE = 0.0410`, which is the grade 10 (`B`) PD. A missing grade, a grade
outside 1–15, or a character-typed grade column from `proc import` all land on 4.1%
silently. Compare `%ovr_ngcore_controls`, which does the same substitution but at least
sets `DQ_FLAG = 'GRADE_DEFAULTED'` — and which never runs.

### SF-11 — `999` and `N/A` DPD both become zero

```sas
if DPD in ('N/A','','.','NULL') then _dpd = 0;
else if input(DPD, best12.) = 999 then _dpd = 0;  /* sentinel = closed */
else _dpd = input(DPD, best12.);
```

This is live in the sample period: 18 tape rows carry `999` and 14 carry `N/A`, together
£6.07m of EAD, and on the stricter reading of `999` the provision is £0.57m light
([07](07_evidence.md) SF-11).

The `999` sentinel is documented in the comment as meaning "closed", but the record is not
excluded — it is measured with `DPD_N = 0`, so it is not caught by the 30-day Stage 2
trigger or the 90-day Stage 3 trigger. Any genuinely 999-days-past-due account, and any
account where the collections platform emits `999` for another reason, is staged as up to
date. Unparseable values (anything not in the sentinel list and not numeric) produce a SAS
`NOTE: Invalid argument to function INPUT` and a missing `DPD_N`, which then fails every
`>=` comparison, so those also stage as up to date.

### SF-12 — an unrecognised scenario label is silently weighted zero

`%pd_pit` assigns `WEIGHT` by `select (upcase(SCENARIO))` with `otherwise WEIGHT = 0`. A
renamed or new scenario in `macro_scenarios.csv` (`CENTRAL`, `SEVERE_PLUS`, a trailing
space that survives `upcase`) is dropped from the probability weighting with no message,
and the weights no longer sum to 1. The macro scalar is a single number derived by summing
across whatever rows survive, so this shows up only as a slightly different scalar in the
`NOTE: [ECL] macro scalar` line. Nothing checks that the weights sum to 1, and nothing
checks that all four scenarios are present. Related: `SEVERE` is currently weighted 0.00
in the code, so the severe scenario is already excluded (SC-02).

## Cross-cutting observations

- **No join in the engine is instrumented.** There is no post-join row-count check, no
  match-rate log, and no orphan report anywhere in the 20 macros that run. Six of the
  twelve failure modes above would be caught by a single "count of unmatched rows" check
  after each join.
- **`%put ERROR:` does not fail the batch.** `%recon_controls`, `%map_product_hierarchy`
  and the (never-invoked) ETL and report validators all report problems with `%put`. Only
  `%assert_rows` aborts. The shell wrapper's only failure signal is `^ERROR` in the SAS
  log ([02](02_execution_order.md) EO-08), so a run that produced a wrong number exits 0
  unless SAS itself logged an error.
- **The migration must decide, per item, preserve or fix.** Per
  `docs/migration/TARGET.md` acceptance criterion 5, none of these should be quietly
  corrected during the port. SF-02 in particular changes the reported provision, so
  correcting it is a provision movement that needs Model Governance and Finance agreement,
  not a bug fix.
