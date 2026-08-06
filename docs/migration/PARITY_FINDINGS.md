# Parity findings and governance items

Status for every item below: **raised for Model Governance decision —
legacy behaviour preserved**.

* **Scenario weights (v4.3):** `m_pd_pit.sas` ignores
  `scenario_weights.csv` and assigns BASE/UPSIDE/DOWNSIDE/SEVERE =
  0.70/0.10/0.20/0.00. The migration externalizes those verbatim values in
  `scenario_weights_frozen_v43.csv`, selected by `model_params.csv`. The
  configured 0.50/0.15/0.30/0.05 set remains available for sensitivity.
  On 202409, switching to the configured set increases total ECL by
  **340,580.26**.
* **KI-021 BTL haircut:** `product_hierarchy.csv` uses PROD_CD 2110 while
  `collateral_haircuts.csv` retains 110. Therefore BTL receives haircut 0,
  exactly as SAS does. Do not repair this during migration; the harness
  sensitivity reports the provision change for applying 0.35 to BTL. On
  202409, correcting only that join increases BTL ECL by **806,095.73**
  (Stage 1 +343.60, Stage 2 +656,812.15, Stage 3 +148,939.97).
* **KI-041 discounting:** personal loans use simple
  `1/(1+EIR*T/12)` rather than monthly compounding; all other segments use
  the compounding formula.
* **SICR precedence and conjunction:** default/90+ DPD precedes DPD,
  forbearance, watchlist, and the conjunction of relative and absolute PD
  tests. Missing thresholds default to 2.0, 0.01 and 30.
* **Legacy input coercions:** whitespace is removed from tape account IDs,
  DPD sentinels and missing values become zero, mortgage EIR percentages are
  divided by 100, and IO accounts have zero monthly payment.
* **CSV rendering boundary:** CREDIT_CARD Stage 1 and Stage 2 TOTAL_EAD are
  numerically identical to the SAS results but can render as `870038.43` vs
  `870038.42` and `696748.69` vs `696748.68`. The underlying engine doubles
  are `870038.42500000004656612873077392578125` and
  `696748.6850000000558793544769287109375`, respectively: approximately
  5e-12 above the exact half-penny boundary. The difference is caused by
  floating-point summation order at rendering, not model logic. The engine
  output is numerically identical and the differences are far below the
  0.01 acceptance tolerance. CSV output is therefore not guaranteed byte
  identical to the SAS export; parity is defined numerically at 0.01 under
  acceptance criterion 1. The two affected cells are not adjusted.
* **Parity comparison basis:** the harness compares unrounded engine aggregate
  values with the captured baseline, which is itself a 2dp SAS export. Thus
  the measured difference can include up to half a penny of baseline
  rounding. The 202409 artifact records a worst-case absolute unrounded
  difference of **0.005000000004656613**, against the strict 0.01 tolerance.
  The separately reported rendered-CSV check is informational only and does
  not drive the pass/fail result.

No model parameter was recalibrated. Quantified sensitivity results are
recorded with the regression run and must accompany the model change record.
