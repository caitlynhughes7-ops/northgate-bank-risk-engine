# Migration discovery pack — IFRS 9 ECL engine (SAS 9.4)

Purpose: give the migration team, Model Governance and audit a description of what
the engine **actually does**, derived by reading the code and the checked-in sample
period, not from `docs/`.

Everything in this pack was derived from the repository at the commit this folder was
added on. Where the code and the documentation disagree, this pack describes the code
and flags the disagreement.

| File | Contents |
|---|---|
| [01_program_inventory.md](01_program_inventory.md) | Every migration unit: purpose, reads, writes, dependencies |
| [program_inventory.csv](program_inventory.csv) | The same inventory, machine readable |
| [02_execution_order.md](02_execution_order.md) | True execution order derived from the drivers, with the dataset flow |
| [03_lineage_secured_lgd.md](03_lineage_secured_lgd.md) | Field-level lineage of secured LGD, source extract → Pillar 3 CR1 |
| [04_never_invoked.md](04_never_invoked.md) | Every program that no driver reaches |
| [05_silent_failure_modes.md](05_silent_failure_modes.md) | Every lookup/join that can fail without an error, and the consequence |
| [06_spec_contradictions.md](06_spec_contradictions.md) | Where the code contradicts `docs/ECL_Model_Spec_v3_2016.md` |
| [07_evidence.md](07_evidence.md) | Quantified impact of the findings on the 202409 sample period |

## Headline conclusions

1. **The engine is much smaller than the repository.** 71 `.sas` files containing 133
   macro definitions are checked in. The month-end batch reaches **20 macros in 19
   files**. The remaining **113 macro definitions in 48 files** — the whole `sas/etl/`
   layer, all 12 portfolio override books, and all 20 regulatory report programs —
   are never invoked by any driver. See [04](04_never_invoked.md).
2. **The regulatory reporting layer in this repository cannot run at all**, even if it
   were invoked: the reports select columns (`REGION`, `BOOK_CD`, `SICR_REASON`,
   `DEFAULT_FL`, `FORBEARANCE_FL`, `ARREARS_BUCKET`, `PD_LIFETIME`) that the dataset
   they read (`stg.ecl_acct`) does not contain. The Pillar 3 CR1 line therefore has
   **no reproducible derivation in this codebase** — see [03](03_lineage_secured_lgd.md)
   §5. Either the filed disclosures are produced somewhere outside this repository, or
   the code here is not the code that runs. **This needs resolving before migration
   scope can be agreed**, because it decides whether the disclosure layer is in scope.
3. **The documented model and the coded model differ in at least 11 material places**,
   including the SICR test (spec: relative OR absolute; code: relative AND absolute),
   scenario weights (spec: from configuration, and explicitly "MUST NOT be hardcoded";
   code: hardcoded since v4.3 as a "TEMPORARY" year-end freeze), and the section 8
   reconciliation controls, which compute their totals but never compare them to
   anything. See [06](06_spec_contradictions.md).
4. **KI-021 has a specific, findable root cause.** `config/rules/collateral_haircuts.csv`
   still carries the pre-2019 product code `110` for buy-to-let, while the loan tape
   carries the renumbered `2110`. The join silently misses, the haircut defaults to
   zero, and secured LGD for the entire BTL book is understated. See
   [05](05_silent_failure_modes.md) SF-02 and [07](07_evidence.md). It is understating the
   buy-to-let provision by 31.9% on the checked-in sample period.
5. **Twelve lookups, joins and fallbacks can miss without raising anything**, and in every case the
   code substitutes a default rather than failing. Two are live on the checked-in period
   (SF-02, and SF-11 where a `999` past-due sentinel is measured as up to date) and one
   (SF-01) is a £6.5m porting trap that SAS's blank-padded string comparison currently
   hides. See [05](05_silent_failure_modes.md).

## How to use this pack for the migration

`docs/migration/TARGET.md` acceptance criterion 5 requires legacy behaviour to be
preserved and departures raised for decision rather than quietly fixed. This pack is
the input to that decision: every item in [05](05_silent_failure_modes.md) and
[06](06_spec_contradictions.md) has an ID, so the migration can carry a per-item
decision (preserve / fix with approval) and the parity harness can carry a per-item
test.

One finding is load-bearing for the rest. An independent reimplementation of the 20 macros
the batch executes reproduces the parity baseline
(`data/expected/ecl_by_segment_202409.csv`) to £0.0024 on £8.98m of ECL, matching all 18
segment/stage rows. The calculation chain described in this pack is therefore verified
rather than inferred, every quantified impact in [07](07_evidence.md) is a measured effect
on the reported provision, and criterion 1 of `docs/migration/TARGET.md` is demonstrably
achievable outside SAS. The unresolved risk in this migration is not the arithmetic — it is
the unreachable layers and the missing disclosure derivation.

Nothing in this pack changes any code or configuration.
