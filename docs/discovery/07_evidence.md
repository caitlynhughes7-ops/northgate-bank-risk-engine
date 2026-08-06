# Evidence — quantified impact on the 202409 sample period

## Method and its significance

To test whether the findings in this pack are real rather than a misreading of the SAS, the
20 macros that the batch executes were reimplemented independently in Python from the code
as written — including every fallback, the hardcoded weights, the `AND` in the SICR test,
the simple-interest branch for personal loans and the undiscounted Stage 3 treatment — and
run against the checked-in sample period.

**The reimplementation reproduces `data/expected/ecl_by_segment_202409.csv` exactly:**

| | Reproduced | Expected (legacy) | Difference |
|---|---:|---:|---:|
| `TOTAL_EAD` | £364,013,988.04 | £364,013,988.03 | +£0.01 |
| `TOTAL_ECL` | £8,975,618.4724 | £8,975,618.47 | +£0.0024 |

Per segment and stage, every one of the 18 rows matches on `N_EXPOSURES` and on `TOTAL_EAD`
and `TOTAL_ECL` to under a penny — inside the 0.01 absolute tolerance that
`docs/migration/TARGET.md` acceptance criterion 1 sets. This has two consequences for the
migration:

1. **The findings below are not hypotheses.** The code as read in this repository is the
   code that produced the parity baseline, for the calculation chain at least. Every number
   in this document is a measured impact on the actual reported provision.
2. **Numeric parity is achievable outside SAS, and it is achievable quickly.** The
   calculation is not the hard part of this migration. The unresolved parts are the ones this
   pack flags as open questions: the never-invoked layers
   ([04](04_never_invoked.md)), the missing disclosure derivation
   ([03](03_lineage_secured_lgd.md) §5), and whether the production job runs code that is
   not in this repository ([02](02_execution_order.md) EO-10).

Caveat on scope: this exercises the calculation chain against one period of synthetic data
(`tools/make_sample_data.py`). It says nothing about production data volumes, the ETL layer
or the report layer, and it cannot confirm behaviour on inputs the sample does not contain —
all nine `PROD_CD` values on the tape are in `product_hierarchy.csv`, so SF-04 (unmapped
products) is unexercised here and its consequences are read from the code rather than
measured. SF-03, SF-05 and SF-08 to SF-10 are likewise latent on this data. SF-11, by
contrast, is live in the baseline — see below.

## The secured LGD model is non-binding for 99.3% of the secured book

| | Accounts | EAD |
|---|---:|---:|
| Secured exposures | 1,054 | £350,961,029.75 |
| …whose LGD equals the segment regulatory floor exactly | **1,047** | **£348,375,989.99** |
| …whose LGD is set by the collateral calculation | 7 | £2,585,039.76 |

By segment: BTL 254 of 254, retail mortgage 666 of 669, SME secured 127 of 131.

The entire secured collateral chain documented in [03](03_lineage_secured_lgd.md) — the
valuation, the HPI indexation, the haircut, the forced-sale calculation — changes the
reported provision for **seven exposures**. For everything else, secured LGD is the floor
from `config/rules/lgd_floors.csv`. This is directly visible in the parity baseline, where
every Stage 3 retail mortgage row has coverage of exactly 0.100000 and every Stage 3 BTL row
exactly 0.150000.

That is worth stating plainly to Model Governance: the bank's secured LGD figure is, in
practice, a table of six floors, and the collateral model that the specification devotes
section 4.1 to is inert. It also explains why KI-021 could not be diagnosed at segment level
(SF-02 below) — a haircut error cannot move an LGD that is already at its floor.

## SF-02 / KI-021 — the buy-to-let haircut that has never matched

`collateral_haircuts.csv` carries the pre-2019 product code `110` for buy-to-let; the tape
and the product hierarchy carry `2110`.

| | Value |
|---|---:|
| Exposures with no haircut match (all `PROD_CD` 2110) | 254 |
| Their EAD | £86,427,344.18 |
| Their average LGD as the engine computes it | 0.150000 (i.e. the BTL floor, for all 254) |
| Their average LGD with the intended 0.35 haircut | 0.192250 |
| **Understatement of BTL ECL** | **£806,095.73** |
| As a share of reported BTL segment ECL | **+31.9%** |
| As a share of total reported ECL | +9.0% |

So the "looks low versus benchmark" note against KI-021 in 2019 was correct, the effect is
just under a third of the buy-to-let provision, and the cause is one stale key in one
configuration file. Correcting it is a provision increase and therefore a Model Governance
and Finance decision, not a bug fix — `docs/migration/TARGET.md` criterion 5 applies.

## SC-06 — the AND/OR defect in the SICR test

| | Accounts | EAD |
|---|---:|---:|
| Stage 2 on the quantitative test as coded (`_rel AND _abs`) | 1,084 | £279,602,919.30 |
| Would move Stage 1 → Stage 2 under the spec's `OR` test | **296** | **£33,947,189.58** |
| Would move in the other direction | 0 | — |

The correction is one-directional: implementing spec section 6 as written moves £33.9m of
EAD from a 12-month to a lifetime measurement, and moves nothing back. Provision effect:

| | ECL |
|---|---:|
| Reported (AND, as coded) | £8,975,618.47 |
| Spec §6 (OR) | £9,101,063.26 |
| **Understatement** | **£125,444.79 (+1.4%)** |

By segment: personal loan +£55,269, SME term +£49,465, retail mortgage +£9,871, BTL +£6,050,
credit card +£3,899, overdraft +£891. The unsecured and SME segments dominate despite
holding far less EAD than the mortgage books, because a re-staged mortgage exposure moves
to a lifetime measurement whose LGD is the regulatory floor. Note that the
quantitative test is already the dominant Stage 2 trigger (1,084 of 1,248 Stage 2
exposures), which is itself worth a look — 605 of 669 retail mortgages sit in Stage 2, driven
by a lifetime PD built from a constant hazard over up to 120 months being compared with a
`PD_LIFETIME_ORIG` supplied on the tape on an unknown basis (see
[05](05_silent_failure_modes.md) SF-07).

## SF-11 — the DPD sentinels are live in the baseline

The sample tape carries 18 rows with `DPD = 999` and 14 with `DPD = 'N/A'`; `%clean_loan_tape`
maps both to `DPD_N = 0`. So the reported provision already contains accounts that are
staged as though they were up to date:

| Tape `DPD` | Accounts | EAD | Currently Stage 1 | Stage 2 | Stage 3 |
|---|---:|---:|---:|---:|---:|
| `999` | 18 | £4,025,759.63 | 6 | 11 | 1 |
| `N/A` | 14 | £2,048,674.78 | 6 | 7 | 1 |

If `999` means what the field says rather than what the comment says — 999 days past due
rather than "closed" — then 17 of the 18 (the eighteenth is already Stage 3) are
credit-impaired under the 90-day trigger and spec §6:

| | Value |
|---|---:|
| Accounts moving to Stage 3 | 17 |
| Their EAD | £3,986,618.44 |
| **ECL understatement** | **£566,275.83 (+6.3% of total ECL)** |

By segment: retail mortgage +£238,522, SME term +£205,749, BTL +£76,060, personal loan
+£30,239, credit card +£15,706. The `N/A` rows change nothing, since a genuinely unknown
DPD has no trigger either way.

Which reading is right is a data question, not a code question: it depends on what the
collections platform actually emits `999` for, and the only statement of intent is a
code comment. It needs confirming with Collections before the migration reproduces the
behaviour, because on this period it is worth £0.57m of provision.

## SC-02 — the "temporary" 2020 scenario weight freeze

| Weights | BASE | UPSIDE | DOWNSIDE | SEVERE | Macro scalar |
|---|---:|---:|---:|---:|---:|
| Hardcoded in `%pd_pit` (in force) | 0.70 | 0.10 | 0.20 | 0.00 | 1.067095 |
| `config/rules/scenario_weights.csv` (governed) | 0.50 | 0.15 | 0.30 | 0.05 | 1.133110 |

Effect of using the governed weights instead:

| Segment | ECL impact |
|---|---:|
| RETAIL_MORTGAGE | +£132,983.21 |
| SME_TERM | +£92,513.23 |
| BTL_MORTGAGE | +£88,966.25 |
| PERSONAL_LOAN | +£21,107.58 |
| CREDIT_CARD | +£4,413.49 |
| OVERDRAFT | +£596.50 |
| **Total** | **+£340,580.26 (+3.8%)** |

The freeze that `docs/CHANGELOG.txt` v4.3 marked "TEMPORARY — revert after sign-off" in
February 2020 is understating the provision by £0.34m on this period, and is the reason the
scalar is insensitive to the downside scenario (KI-023).

## SC-08 — personal loan discounting (KI-041)

| Treatment | PERSONAL_LOAN ECL |
|---|---:|
| Simple interest, as coded | £544,423.14 |
| Monthly compounding, per spec §7 | £533,939.37 |
| **Effect of the legacy branch** | **+£10,483.77 (+2.0% of the segment)** |

Small in absolute terms, and it overstates rather than understates, which is presumably why
"consistent with prior periods" was accepted in 2022. It still needs a documented decision,
because it is a knowing departure from the approved methodology on an audited number.

## SF-01 — the ID normalisation the collateral join silently depends on

213 of the 2,000 tape account IDs are padded to 12 characters; 119 of those are secured
exposures. The collateral file is uniformly 11 characters and is **not** normalised on its
side of the join. The single `ACCOUNT_ID = left(compress(ACCOUNT_ID))` in `%load_loan_tape`
is what makes the join work.

If a migration drops that normalisation — the most natural mistake to make when porting a
data step whose only comment is "the source system pads account ids to 12 chars in some
months and not others" — the effect is:

| Segment | Exposures losing collateral | EAD | LGD applied | ECL impact |
|---|---:|---:|---:|---:|
| RETAIL_MORTGAGE | 73 | £25,721,866.30 | 1.00 | +£4,548,315.71 |
| SME_TERM | 18 | £6,521,999.57 | 1.00 | +£1,047,030.47 |
| BTL_MORTGAGE | 28 | £9,846,709.84 | 1.00 | +£881,342.89 |
| **Total** | **119** | **£42,090,575.71** | **1.00** | **+£6,476,689.07 (+72%)** |

A 72% increase in the group provision, from one missing `.strip()`, with no error, no
warning and no control that would catch it — the `%recon_controls` totals are on EAD, which
is unaffected. This is the strongest argument in this pack for instrumenting every join
with a match-rate check in the target implementation, and for making the parity harness of
`docs/migration/TARGET.md` criterion 2 mandatory rather than advisory.

## Summary of quantified impacts

| ID | Finding | Direction | Impact on 202409 reported ECL |
|---|---|---|---|
| SF-02 | BTL haircut key never matches (KI-021) | understates | £806,096 (+9.0% of total ECL) |
| SC-02 | Hardcoded 2020 scenario weights | understates | £340,580 (+3.8%) |
| SC-06 | SICR quantitative test is AND, spec says OR | understates | £125,445 (+1.4%), 296 exposures and £33.9m of EAD re-staged |
| SC-08 | Personal loan simple-interest discounting (KI-041) | overstates | £10,484 (−0.1%) |
| SF-11 | `DPD = 999` treated as up to date | understates, if `999` means past due | £566,276 (+6.3%), 17 exposures not staged as credit-impaired |
| SF-01 | Collateral join depends on ID normalisation | migration risk | £6,476,689 (+72%) if lost |
| — | Secured collateral model non-binding | n/a | 1,047 of 1,054 secured exposures priced at the floor |

Reproduced figures were generated deterministically and confirmed identical on re-run. The
reimplementation used for this section is throwaway analysis code and is deliberately not
committed here; the parity harness required by `docs/migration/TARGET.md` criterion 2 should
be built as part of the migration itself, not as part of discovery.
