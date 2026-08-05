# IFRS 9 ECL Model Specification — v3.0

Status: APPROVED (Model Governance Committee, 14 Nov 2016)
Author: P. Whitcombe, Group Credit Risk Analytics

> This document describes v3.0 of the ECL engine as approved for IFRS 9 transition.
> Subsequent changes were captured in change tickets only. This document has NOT been
> reissued since 2016.

## 1. Scope

Retail mortgages (secured), buy-to-let, personal loans, credit cards, overdrafts,
and SME term lending. Corporate and Treasury exposures are out of scope (separate engine).

## 2. ECL measurement

ECL is measured as the probability-weighted present value of expected cash shortfalls:

    ECL = SUM over t of ( PD_marginal(t) * LGD(t) * EAD(t) * DF(t) )

where the summation horizon is 12 months for Stage 1 and lifetime for Stage 2 and Stage 3.

## 3. PD

### 3.1 Through-the-cycle PD
A logistic scorecard produces a TTC PD by rating grade (see `m_pd_ttc.sas`).

### 3.2 Point-in-time PD
TTC PD is converted to PIT using a macroeconomic scalar derived from the
scenario set. Scenario weights are held in configuration (`config/rules/scenario_weights.csv`)
and MUST NOT be hardcoded in the model code.

### 3.3 Lifetime PD term structure
Marginal PDs are derived from a cumulative PD curve using a constant hazard assumption
per rating grade, capped at 120 months.

## 4. LGD

### 4.1 Secured
LGD is derived from the forced-sale value of collateral:

    Indexed valuation  = original valuation * regional HPI index ratio
    Realisable value   = indexed valuation * (1 - haircut)
    Loss given default = max( (EAD - realisable value) / EAD , regulatory floor )

Haircuts are held by product group in `config/rules/collateral_haircuts.csv` and reflect
forced-sale discount, disposal costs and time to realisation.

The regulatory LGD floor is applied AFTER the collateral calculation and is held in
`config/rules/lgd_floors.csv`.

### 4.2 Unsecured
Segment-level LGD from internal recovery data, floored at 45%.

## 5. EAD

Drawn balance plus credit conversion factor applied to the undrawn commitment.

## 6. Staging (SICR)

An exposure is allocated to Stage 2 where ANY of the following is met:

- lifetime PD has increased by more than the relative threshold vs origination, OR
- absolute lifetime PD increase exceeds the absolute threshold, OR
- the account is 30+ days past due, OR
- the account is flagged forbearance or watchlist.

Stage 3 is credit-impaired: 90+ days past due or default flag.
Thresholds are held in `config/rules/sicr_thresholds.csv`.

## 7. Discounting

Expected cash shortfalls are discounted at the original effective interest rate (EIR)
of the instrument, compounded monthly.

## 8. Controls

Reconciliation controls are executed after aggregation:
- total EAD must reconcile to the loan tape within 0.01%
- no exposure may have a null stage
- ECL coverage ratio by segment must be within tolerance of prior month
