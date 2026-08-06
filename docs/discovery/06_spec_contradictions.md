# Where the code contradicts docs/ECL_Model_Spec_v3_2016.md

The specification is v3.0, approved 14 November 2016, never reissued. `docs/CHANGELOG.txt`
records changes up to v4.7 (2024) that were "captured in change tickets only". The
contradictions below are therefore a mixture of undocumented model changes and defects; the
distinction matters for governance, so each item says which it appears to be.

Quantified impacts on the 202409 sample period are in [07_evidence.md](07_evidence.md).

| ID | Spec | Code | Type |
|---|---|---|---|
| SC-01 | §3.1 TTC PD from a logistic scorecard | Hardcoded PD masterscale by grade; the scorecard is never called | undocumented change |
| SC-02 | §3.2 scenario weights from configuration, "MUST NOT be hardcoded" | Hardcoded in `%pd_pit`; `scenario_weights.csv` is not read; `SEVERE` weighted 0.00 | known temporary change, never reverted |
| SC-03 | §3.2 PIT PD is probability-weighted across scenarios | A single scalar is summed across scenario rows and applied to every exposure | undocumented change |
| SC-04 | §3.3 marginal PDs capped at 120 months | Capped at `&MAX_TERM_M` from environment config (currently 120 in both) | consistent today, fragile |
| SC-05 | §4.1 LGD = max((EAD − realisable)/EAD, floor) | Additionally floored at zero before the regulatory floor; floor skipped if the join misses | defect |
| SC-06 | §6 Stage 2 if relative **OR** absolute PD increase | Requires relative **AND** absolute (`if _rel and _abs`) | defect or undocumented change |
| SC-07 | §6 30+ days past due triggers Stage 2 | `DPD_TRIGGER` from config (30 for every segment today), and `999` DPD is reset to 0 | consistent today, plus a defect |
| SC-08 | §7 discount at the original EIR, compounded monthly | Personal loans use simple interest | known departure (KI-041), never resolved |
| SC-09 | §2 ECL is the PV of expected cash shortfalls | Stage 3 ECL is `LGD × EAD × overlay`, undiscounted | undocumented change |
| SC-10 | §8 three post-run controls with tolerances | The control macro computes totals and compares nothing; `&RECON_TOL` is never referenced | defect |
| SC-11 | (not in the spec at all) | A segment-level management overlay of up to 1.15 multiplies every ECL | unspecified model component |

## Detail

### SC-01 — the specified PD model is not the PD model

Spec §3.1: "A logistic scorecard produces a TTC PD by rating grade (see `m_pd_ttc.sas`)."
§3.2: "TTC PD is converted to PIT using a macroeconomic scalar."

`%pd_ttc` exists, is a logistic scorecard, and is never invoked
([04](04_never_invoked.md) §1). `%pd_pit` does not consume a TTC PD at all — it reads a
hardcoded 15-point masterscale (`when (1) PD_GRADE = 0.0003; … when (15) PD_GRADE = 1.0000;`)
and scales that. So the documented two-stage TTC → PIT construction does not exist in the
running engine, and the masterscale — a model parameter — lives in macro source rather than
in `config/rules/`. `docs/CHANGELOG.txt` v4.2 records only that `m_pd_ttc` is no longer
called; it does not record what replaced it, and the spec was never updated.

`%pd_pit` also applies arrears and forbearance PD uplifts (`×1.35` / `×2.60` / `×4.10` by
arrears bucket, `×1.50` for forbearance, and `PD_12M = 1` where the default flag is set)
that appear nowhere in the specification.

### SC-02 — scenario weights are hardcoded, against an explicit prohibition

Spec §3.2: "Scenario weights are held in configuration (`config/rules/scenario_weights.csv`)
and MUST NOT be hardcoded in the model code."

`%pd_pit`:

```sas
/* v4.3: hardcoded for the year end reporting freeze. TEMPORARY.
   (config/rules/scenario_weights.csv is no longer read here) */
select (upcase(SCENARIO));
  when ('BASE')     WEIGHT = 0.70;
  when ('UPSIDE')   WEIGHT = 0.10;
  when ('DOWNSIDE') WEIGHT = 0.20;
  when ('SEVERE')   WEIGHT = 0.00;
```

`config/rules/scenario_weights.csv` still holds the governed weights — BASE 0.50,
UPSIDE 0.15, DOWNSIDE 0.30, SEVERE 0.05 — and no program in the repository reads that file.
`docs/CHANGELOG.txt` v4.3 is dated 2020-02-14 and says "TEMPORARY — revert after sign-off";
five years later the code still carries it. The hardcoded set weights the base case 20
points higher, halves the downside weight and removes the severe scenario entirely, so the
provision is lower than the governed weights would produce, and Economics' sign-off of the
scenario set has no effect on the weighting applied.

This is not the cause of the original KI-023 observation ("PIT scalar appears insensitive
to the downside scenario. Economics queried; no change made"): KI-023 was raised in
2019-11, before the v4.3 freeze dated 2020-02-14. Before the freeze, the governed 0.30
downside weight was in force. The unresolved query is nevertheless consistent with the
scalar being downside-insensitive ever since the freeze: the downside weight was reduced
to 0.20 and the severe scenario zeroed, and the "TEMPORARY" freeze remains in place.

`docs/migration/TARGET.md` requires configuration-driven parameters in the target state, so
this item cannot simply be carried across: the migration has to decide whether to reproduce
the frozen weights (parity) or the governed weights (compliance), and that is a Model
Governance decision with a provision impact.

### SC-03 — the macro scalar is one number for the whole book, summed across scenario rows

Spec §3.2 describes a probability-weighted PIT PD. The code computes:

```sas
create table stg.scalar as
select sum( WEIGHT * ( 1 + (-0.85 * GDP_SHOCK) + (0.22 * (UNEMP_RATE - 4.2)) ) )
         as MACRO_SCALAR from stg.scen_w;
```

then `call symputx` it into a macro variable and multiplies every exposure's grade PD by it.
Three consequences:

- The sensitivity coefficients (`-0.85`, `0.22`) and the unemployment baseline (`4.2`) are
  hardcoded model parameters, not configuration, and appear in no document.
- The weighting is a single `sum` over the rows of `macro_scenarios.csv`. It is correct only
  if that file has exactly one row per scenario. If Economics ever supplies a multi-horizon
  scenario file (one row per scenario per year, which is the normal shape of a scenario
  feed), the weights effectively multiply up and the scalar is silently wrong. Nothing
  checks the row count or that the weights sum to 1.
- Probability weighting is applied to the *scalar*, not to the ECL. Weighting a
  non-linear function's input is not the same as probability-weighting its output, which is
  what IFRS 9 and spec §2 describe.

### SC-04 — the lifetime cap is environment configuration, not a model constant

Spec §3.3 caps the cumulative PD curve at 120 months. `%pd_term_structure` uses
`min(REMAIN_TERM_M, &MAX_TERM_M)`, where `&MAX_TERM_M` is set in `config/env/prod.cfg` and
`config/env/uat.cfg` — both currently 120, so there is no difference in behaviour today.
It is listed because a model parameter sitting in an *environment* file means UAT and
production can legitimately compute different lifetimes, and a change in one file would not
look like a model change to anyone reviewing it.

### SC-05 — LGD is floored twice, and the regulatory floor is conditional

Spec §4.1: `Loss given default = max( (EAD - realisable value) / EAD , regulatory floor )`,
and "the regulatory LGD floor is applied AFTER the collateral calculation".

The code computes `LGD_RAW = max((EAD - REALISABLE_VAL)/EAD, 0)` and then
`LGD = max(LGD_RAW, LGD_FLOOR)`. The extra floor at zero is not in the spec. On its own it
is harmless (the regulatory floor is above zero for every segment in `lgd_floors.csv`), but
it means an over-collateralised exposure and an exposure with exactly break-even collateral
are indistinguishable downstream, and it hides how far below the floor the collateral
calculation actually lands. More seriously, the regulatory floor is applied only if the
`SEGMENT` join to `lgd_floors.csv` matches — see [05](05_silent_failure_modes.md) SF-03 —
so "applied AFTER the collateral calculation" is not unconditionally true.

Related, though not strictly a contradiction: spec §2 writes `LGD(t)` as time-varying;
the engine has a single scalar LGD per exposure applied to every month of the curve. And
spec §4.1 describes "regional HPI index ratio" — the code uses `HPI_INDEX_CURR /
HPI_INDEX_ORIG` supplied per account on the collateral extract, so the regional dimension
is the extract's responsibility and `REGION` on the loan tape is never used for it.

### SC-06 — the SICR test is AND where the spec says OR

Spec §6: "An exposure is allocated to Stage 2 where **ANY** of the following is met: lifetime
PD has increased by more than the relative threshold vs origination, **OR** absolute
lifetime PD increase exceeds the absolute threshold, OR the account is 30+ days past due,
OR the account is flagged forbearance or watchlist."

`%staging_sicr`:

```sas
_rel = (PD_LIFETIME > REL_PD_MULT * PD_LIFETIME_ORIG);
_abs = ((PD_LIFETIME - PD_LIFETIME_ORIG) > ABS_PD_INCR);
...
else if _rel and _abs then do; STAGE = 2; SICR_REASON = 'QUANT_PD'; end;
```

The two quantitative triggers are combined with `and`, so an exposure whose lifetime PD has
tripled but in absolute terms only by 0.8pp is **not** staged, and neither is one that has
increased by 5pp but less than the relative multiple. This understates Stage 2 and therefore
the provision. The DPD, forbearance and watchlist triggers are implemented as separate
branches and are correct.

The branch order also means `SICR_REASON` records only the first trigger that fires
(impaired → DPD → forbearance → watchlist → quantitative), so the reason codes cannot be
used to count how many exposures each trigger caught — relevant because four of the
never-invoked report programs group by `SICR_REASON`.

### SC-07 — DPD trigger

Spec §6 fixes the past-due trigger at 30 days and Stage 3 at 90+ days or the default flag.
The code takes `DPD_TRIGGER` from `config/rules/sicr_thresholds.csv` (30 for every segment
today, so no behavioural difference) but hardcodes the 90-day Stage 3 test. Combined with
[05](05_silent_failure_modes.md) SF-11, an account whose DPD arrives as the `999` sentinel
is reset to `DPD_N = 0` and so passes both tests as up to date, which contradicts §6
directly for those records.

### SC-08 — personal loans are discounted on simple interest

Spec §7: "Expected cash shortfalls are discounted at the original effective interest rate
(EIR) of the instrument, compounded monthly."

```sas
if SEGMENT = 'PERSONAL_LOAN' then
  /* legacy treatment retained for comparability, see KI-041 */
  DF = 1 / (1 + EIR * (T/12));
else
  DF = 1 / ( (1 + EIR/12) ** T );
```

Simple interest gives a **higher** discount factor than monthly compounding at every
horizon, so personal loan ECL is higher than the spec would produce. KI-041 records that
external audit queried this in 2022 and the response was "consistent with prior periods".
The code comment and the issue log agree with each other and both contradict the spec; no
change was made. The migration must reproduce this to hit parity, and it should be raised
explicitly rather than carried silently, because "consistent with prior periods" is not a
methodology.

Also note `%clean_loan_tape` normalises EIR with `if EIR > 1 then EIR = EIR / 100`
("stored as a percentage on the mortgage feed and a decimal on the unsecured feed"). Any
genuine EIR above 100% on the unsecured feed — not impossible for a revolving product with
fees — would be silently divided by 100.

### SC-09 — Stage 3 ECL is not discounted

Spec §2 defines ECL as the probability-weighted present value of expected cash shortfalls,
with a lifetime horizon for Stage 2 and Stage 3. `%ecl_calc`:

```sas
case when e.STAGE = 3 then e.LGD * e.EAD * e.OVERLAY_FACTOR
     else coalesce(r.ECL_UNADJ,0) * e.OVERLAY_FACTOR end as ECL
```

Stage 3 exposures are measured as an undiscounted `LGD × EAD`, with no PD term (defensible
— PD is 1 at default) and, more importantly, no discount factor and no time to realisation.
For a secured Stage 3 exposure with a multi-year recovery period this materially overstates
the provision relative to the spec; the header comment of the macro documents the treatment
("Stage 3 measured at LGD*EAD") but the spec does not. This is the likely mechanism behind
KI-014 (Stage 3 coverage in the Board pack differing from the GL feed), which was closed as
"rounding".

The Stage 1 truncation, by contrast, is implemented as specified: `if STAGE = 1 and T > 12
then delete`.

### SC-10 — the section 8 controls do not test anything

Spec §8 requires three controls after aggregation: total EAD reconciling to the loan tape
within 0.01%, no exposure with a null stage, and segment coverage within tolerance of the
prior month. `%recon_controls` in full:

```sas
select sum(DRAWN_BAL) into :tape_drawn from &tapeds;
select sum(EAD), sum(ECL) into :ecl_ead, :ecl_tot from &eclds;
select count(*) into :n_nullstage from &eclds where STAGE is null;
%put NOTE: [ECL] control drawn=&tape_drawn ead=&ecl_ead ecl=&ecl_tot;
%if &n_nullstage > 0 %then %put ERROR: ...
```

- **Control 1 is not implemented.** The two totals are printed, never compared, and no
  tolerance is applied. `&RECON_TOL` — 0.0005 in production, 0.005 in UAT — is defined in
  both environment configs and referenced nowhere in the repository. In any case the
  comparison as set up could not pass: it compares `sum(DRAWN_BAL)` with `sum(EAD)`, and
  EAD includes `CCF × UNDRAWN` by construction (spec §5), so the two are not meant to be
  equal.
- **Control 2 cannot fire.** Every branch of `%staging_sicr` assigns a stage, so
  `STAGE is null` is always zero. The check that would matter — exposures dropped by the
  `%ecl_calc` inner join, [05](05_silent_failure_modes.md) SF-09 — is not performed.
- **Control 3 does not exist.** There is no prior-month comparison anywhere in the batch;
  the only prior-period logic in the repository is in the never-invoked report `_validate`
  macros, which read a `hist` library nothing ever writes to
  ([02](02_execution_order.md) EO-07).
- Even if a control did fail, `%put ERROR:` does not stop the run, and the controls execute
  after `%export_disclosure` has already written the CSV and the Finance GL feed
  ([02](02_execution_order.md) EO-05).

`docs/CHANGELOG.txt` v4.7 (2024-05-14) reads "Tolerance widened on recon control (was
failing spuriously)". There is no tolerance in the code to widen. Whatever that change
actually did, the control it refers to is not present, so the engine has been running
without the spec §8 reconciliation for at least the period since.

### SC-11 — a management overlay of up to 15% is applied and is not in the spec

`%fli_overlay` (in `m_forward_looking_overlay.sas`) multiplies every exposure's ECL by a
segment factor: credit card and overdraft 1.15, personal loan 1.10, SME term 1.05, all
others 1.00. The specification contains no overlay of any kind; the only in-repository
authority for it is the macro's own comments ("as agreed with the CFO", "Provisions
Committee Dec-2023: cost of living overlay retained on unsecured, released on secured") and
`docs/CHANGELOG.txt` v3.4, which describes something different — "Overlay macro added for
FLI scenario weighting". The macro name (`fli_overlay`, forward-looking information) and
the file name still say scenario weighting; the content is a post-model management overlay.

For the migration this is the clearest example of `docs/migration/TARGET.md`'s "explicitly
flagged where no specification exists": the factors are model inputs subject to quarterly
Provisions Committee review, they are hardcoded in a macro, and there is no record in the
repository of the current approved values or of when they were last approved. They should
move to `config/rules/` with an effective date, and the current values need confirming with
the Provisions Committee before the migrated engine is used.

## Contradictions with the operational documentation (for completeness)

Not spec items, but the same governance problem — recorded here so they are not lost:

| Where | Documentation says | Code does |
|---|---|---|
| `docs/ops/RUNBOOK.md` | If the collateral extract is late, "secured LGD will fall back to defaults" | LGD becomes 1.00 for those exposures ([05](05_silent_failure_modes.md) SF-01) |
| `docs/ops/RUNBOOK.md` | "Re-running the same period twice appends to `ECL_HIST`. Delete the period first" | `ECL_HIST` does not exist in the repository; every batch output is written with `replace` |
| `docs/ops/RUNBOOK.md` | Check the log for `ERROR:` and for the MERGE warning | The engine contains no `MERGE` statement; the warning it tells operators to look for cannot be produced |
| `docs/ops/RUNBOOK.md` | "Run the recon pack and circulate to Finance" | There is no recon pack; `%rpt_gl_feed_recon` is never invoked and could not run |
| `README.md` | Downstream includes the Board Risk Pack and ICAAP/Pillar 3 disclosure | The batch produces only the segment CSV, the GL feed and `out.board_pack`; every ICAAP and Pillar 3 program is orphaned ([04](04_never_invoked.md)) |
| `docs/CHANGELOG.txt` v3.2 | "Add BTL as separate product group. Haircuts copied from RM." | The BTL haircut row is keyed on the pre-2019 code `110` and never matches ([05](05_silent_failure_modes.md) SF-02) |
