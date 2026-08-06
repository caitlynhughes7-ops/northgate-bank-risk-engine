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

## Operational logging lineage

| Log NOTE component | Source | Python / SAS implementation | Spec basis |
|---|---|---|---|
| Severity prefix | `config/rules/logging.csv` (`log_note_prefix`) | `util_logging.py` / `m_util_logging.sas` | no specification basis |
| `[ECL]` tag | `config/rules/logging.csv` (`log_tag`) | `util_logging.py` / `m_util_logging.sas` | no specification basis |
| Step token | Python caller | `util_logging.py` / `m_util_logging.sas` | no specification basis |
| Message token | Python caller | `util_logging.py` / `m_util_logging.sas` | no specification basis |
| Timestamp | System clock (`datetime.now()` by default) | `util_logging.py` / `m_util_logging.sas` | no specification basis |

## Recon controls log lineage

The control artifact is log-only: `%recon_controls` in
`sas/macros/m_recon_controls.sas` writes no dataset or file. The following
components are emitted by the Python behaviour-equivalence port and map to
the legacy macro and spec §8.

| Log component | Source and transformation | Python / SAS implementation | Spec basis |
|---|---|---|---|
| NOTE severity prefix | `logging.csv:log_note_prefix` | `recon.py` / `%put NOTE:` | no specification basis |
| ERROR severity prefix | `logging.csv:log_error_prefix` | `recon.py` / `%put ERROR:` | no specification basis |
| `[ECL]` tag | `logging.csv:log_tag` | `recon.py` / `%put` text | no specification basis |
| Step token | `recon_controls` macro step name | `recon.py` / `%log_step(recon_controls)` | no specification basis |
| Drawn total | SAS `SUM(DRAWN_BAL)` over arrears tape | `recon.py` / `select sum(DRAWN_BAL)` | §8 control intent |
| EAD total | SAS `SUM(EAD)` over account ECL frame | `recon.py` / `select sum(EAD)` | §8 control intent |
| ECL total | SAS `SUM(ECL)` over account ECL frame | `recon.py` / `select sum(ECL)` | no explicit §8 control basis |
| Null-stage count | Numeric-missing `STAGE` row count | `recon.py` / `where STAGE is null` | §8 staging control intent |
| Null-stage threshold | `recon_controls.csv:null_stage_error_threshold` | `recon.py` / `%if &n_nullstage > 0` | §8 control intent |
| Timestamp | Runtime clock via `log_step` | `util_logging.py` / `%log_step` | no specification basis |
| BEST12 rendering | Configured format and retained width | `recon.py` / SQL `INTO` macro variables | no explicit basis; documented assumption |
| RECON_TOL | Not read by the migrated control unit; standalone observability tooling reads candidate environment values | `recon_observability.py` / environment `%let RECON_TOL` | required by §8 but absent from legacy code |

The corrected comparison, tolerance, and blocking order required by §8 have
no implementation basis in the legacy macro and remain an open governance
decision. `tools/recon_whatif.py` quantifies candidate outcomes without
changing the behaviour-equivalence control.

## Recon observability artifact lineage

The standalone `tools/recon_observability.py` tool is not invoked by
`engine.run()` and writes only
`data/output/observability/recon_observability_<period>.json`. It provides
non-blocking §8 evidence; no verdict can abort or alter the batch.

| Artifact field | Source and transformation | Implementation | Spec basis |
|---|---|---|---|
| `control_1.sum_drawn_bal` | `SUM(DRAWN_BAL)` over the arrears tape | `recon_observability.py` / `m_recon_controls.sas` | §8 control intent |
| `control_1.sum_ead` | `SUM(EAD)` over account-level ECL | `recon_observability.py` / `m_recon_controls.sas` | §8 control intent |
| `control_1.absolute_difference` | Absolute difference of the two totals | `recon_observability.py` | §8 control intent |
| `control_1.relative_difference` | Absolute difference divided by drawn total; null for missing/zero denominator | `recon_observability.py` | §8 control intent |
| `control_1.env_tolerance_breach` | Relative difference against `RECON_TOL` from selected environment | `recon_observability.py` | §8 candidate |
| `control_1.spec_section_8_tolerance_breach` | Relative difference against configured `spec_section_8_tolerance` | `recon_observability.py` | §8 candidate |
| `control_2.null_stage_count` | Numeric-missing `STAGE` row count | `recon_observability.py` / `m_recon_controls.sas` | §8 control intent |
| `control_3` | Prior-month coverage comparison unavailable | `recon_observability.py` | §8 control intent |
| `basis.legacy_pairing_open_question` | EAD includes `CCF × UNDRAWN` under §5 | `recon_observability.py` | unresolved basis |
| Log prefix | `logging.csv:log_observability_prefix` (`OBS:`) | `recon_observability.py` | no specification basis |
