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

These formats are defined in the legacy autoexec but are not applied by any
reachable batch program. The Python unit preserves their display behaviour
without importing it into any calculation module.
