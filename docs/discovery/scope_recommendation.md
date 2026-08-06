# Scope recommendation — the 113 unreachable macro definitions

**Audience.** Stakeholders deciding the budget and the regulatory exposure of the IFRS 9
ECL engine migration. It assumes no knowledge of SAS.

**What this document is.** The discovery pack established that most of the code in this
repository is never executed by the month-end batch. This document does not repeat that
analysis. It answers the next question: *for each block of unreached code, what would have
to be true for it to be in migration scope, what evidence would settle it, who owns that
evidence, and what it costs if the answer is yes.*

**What this document is not.** It is not a decision. Every recommendation below is
conditional on evidence that does not exist inside this repository and must be obtained
from the bank. Where a fact could not be determined from the repository, it is marked as
an open question rather than assumed.

Every claim below carries a file and line citation. They are meant to be opened.

---

## 0. Summary of the position

The repository holds 71 `.sas` files with 133 macro definitions
(`docs/discovery/01_program_inventory.md:3`). The month-end batch reaches 20 executed
macros across 23 files. The remaining **113 macro definitions are reached by no driver at
all**: 112 definitions in 48 unreachable files, plus `%months_between`, which sits in a
file the batch does reach but is never called
(`docs/discovery/04_never_invoked.md:15-25`). The inventory records this per row:
`docs/discovery/program_inventory.csv` has 138 rows over 72 paths, of which 25 carry
`invoked_in_batch=yes` and 113 carry `no` (column `invoked_in_batch`,
`docs/discovery/program_inventory.csv:1`).

Those 113 divide into four blocks:

| Block | Files | Macro definitions |
|---|---|---|
| ETL source extracts (`sas/etl/m_ext_*.sas`) | 15 | 15 |
| Portfolio override books (`sas/macros/portfolio/m_ovr_*.sas`) | 12 | 36 |
| Regulatory report programs (`sas/reports/m_rpt_*.sas`) | 20 | 60 |
| Orphans (`%pd_ttc`, `%months_between`) | 1 + part of 1 | 2 |

Each block is examined in sections 2 to 5. Section 1 is the question that has to be
answered before any of them can be.

---

## 1. The top open question: **the running engine may not be this repository**

This is the headline finding and it is deliberately placed first, because **every other
scoping question in this document is downstream of it**. Until it is resolved, no answer
to "is this code in scope" can be relied on.

### 1.1 The evidence

**(a) As checked in, the batch could not resolve a single one of its macros.**

`sas/autoexec.sas:25` sets the macro search path:

```
options sasautos=("&BASE./sas/macros" sasautos);
```

SAS's autocall mechanism requires the *file name* to match the *macro name*. Every macro
file in this repository is prefixed `m_`: `sas/macros/m_ecl_calc.sas:6` defines
`%macro ecl_calc(...)`. No file `%include`s any macro source — the only `%include`
statements in the repository are for the environment configuration and the two format
programs (`sas/autoexec.sas:14`, `sas/autoexec.sas:27-28`) and for the driver
(`sas/driver/run_month_end.sas:5`). And `sas/etl`, `sas/reports` and
`sas/macros/portfolio` are not on the autocall path at all; autocall does not recurse into
subdirectories (`docs/discovery/04_never_invoked.md:76-78`).

Taken literally, the batch would fail at its very first macro call —
`sas/driver/run_ifrs9_ecl.sas:7`, `%period_dates(&PERIOD);`. The repository documents a
monthly scheduled run (`README.md:7`, "scheduled via Control-M"; `docs/ops/RUNBOOK.md:8`)
but contains no run logs or run records proving production executes it. If it does run,
**the production job depends on something that is not in this repository**: a pre-compiled
macro catalogue (`SASMSTORE`), a site-level autocall path, or a wrapper that includes the
sources. This is recorded in the discovery pack as EO-10
(`docs/discovery/02_execution_order.md:141-150`).

Note that the operational runbook records a related but *different* constraint — "The job
must be run from the `sas/` directory or `autoexec.sas` will not find the macro library"
(`docs/ops/RUNBOOK.md:14-15`). That is about `&BASE.` resolving relatively
(`sas/autoexec.sas:10`, `docs/discovery/02_execution_order.md` EO-09) and does not explain
the file-name mismatch. Running from the right directory does not make
`sas/macros/m_ecl_calc.sas` resolvable as `%ecl_calc`.

**(b) The filed Pillar 3 CR1 line has no reproducible derivation in this codebase.**

`docs/discovery/README.md:31-38` states this directly, and the four independent breaks
between the engine's last calculation step and the CR1 file are itemised as LIN-01 to
LIN-04 at `docs/discovery/03_lineage_secured_lgd.md:139-146`. The consequence recorded at
`docs/discovery/03_lineage_secured_lgd.md:149-152` is that the migration's acceptance
criterion 4, documented lineage to disclosure line
(`docs/migration/TARGET.md:30-31`), cannot currently be met for CR1, and numeric parity
can only be evidenced as far as `ecl_by_segment_<period>.csv`.

### 1.2 Why this decides the budget

The bank files these disclosures. They are produced by *something*. Two readings of the
evidence are consistent with everything in this repository, and **they have opposite
scoping answers**:

| Reading | What the 113 definitions are | Scoping consequence |
|---|---|---|
| **A — the live code is elsewhere** | This repository is a stale or partial copy. The live deployment has `BOOK_CD`, persists account-level ECL, and runs the extracts and reports. | The migration is currently scoped against the wrong source. The 113 definitions are in scope *and* the real versions of them, which may differ, have not been inventoried. Scope grows materially. |
| **B — this is the live code and the dead parts are genuinely dead** | The engine really does produce only the segment CSV, the GL feed and the board pack, and the disclosure layer is assembled somewhere else entirely (manually, or by another system). | The 113 definitions are abandoned code. Porting them buys nothing. Scope shrinks — but the bank has a separate, unmigrated disclosure process that nobody has inventoried. |

Both readings are reportable. Under A the migration is under-scoped; under B the group has
an undocumented disclosure layer outside change control. **No amount of further reading of
this repository can distinguish them** — the discriminating evidence is not in the code.

### 1.3 What would settle it

Two named artefacts, both external to this repository:

1. **The production Control-M job definition for the monthly ECL run, and the SAS
   deployment it actually invokes** — specifically the `SASMSTORE` catalogue or site
   autocall path in force in production, and a directory listing of the deployed macro
   library. Comparing that listing against this repository answers reading A versus B
   outright. `README.md:7` confirms the platform is "SAS 9.4 M5 on RHEL 7, scheduled via
   Control-M".
2. **The provenance of the last filed Pillar 3 CR1 submission** — the submitted return,
   plus whatever produced it: job, spreadsheet, or manual process. If it is
   `%rpt_pillar3_cr1` running somewhere, reading A holds. If it is anything else, reading
   B holds and the real disclosure process needs its own inventory.

### 1.4 Owner

**Infra Batch Services** is the nearest named owner: `docs/ops/RUNBOOK.md:23` ("Batch
failures: Infra Batch Services.") and `README.md:30` ("Platform / scheduling | Infra Batch
Services"). The discovery pack already directs this question to them
(`docs/discovery/02_execution_order.md:149-150`). Note that no document in the repository
states that Infra Batch Services owns the *job definitions* themselves, only the platform
and scheduling and batch-failure escalation.

For the CR1 submission provenance, **owner not named in the repository**. The report source
comments attribute the CR1 variance control to "Finance Control"
(`sas/reports/m_rpt_pillar3_cr1.sas:30`, `:42`); other reports name Regulatory Reporting,
the CFO's office, Group Risk or Internal Audit (see 4.3 for the full mapping). Those are
the names the code uses; none appears in `README.md`, `docs/ops/RUNBOOK.md`,
`docs/migration/TARGET.md` or `docs/ops/known_issues.md` as an accountable owner, and no
individual or distribution list is given for any of them. **This is an open question: who
owns the filed Pillar 3 return?**

### 1.5 Cost

Answering section 1 is not an engineering task and costs no migration effort. It costs one
request to Infra Batch Services and one to whoever owns the filing. **It should be raised
before any further migration unit is started**, because if reading A holds, work already
completed has been parity-tested against a baseline produced by code that is not the code
under migration.

---

## 2. ETL layer — 15 files, 15 macros

`sas/etl/m_ext_*.sas`, one macro per file:
`%ext_book_mapping`, `%ext_collections_status`, `%ext_cust_master`,
`%ext_default_register`, `%ext_forbearance_cases`, `%ext_gl_balances`,
`%ext_interest_rates`, `%ext_limit_management`, `%ext_macro_forecast`, `%ext_prior_ecl`,
`%ext_product_reference`, `%ext_rating_grades`, `%ext_securitisation`,
`%ext_valuation_feed`, `%ext_write_offs` (`docs/discovery/04_never_invoked.md:41-45`).

All fifteen follow one template — `filename` → `proc import` from
`&INBOUND./<extract>_<period>.csv` → an `ACCOUNT_ID` normalisation step → `%assert_rows`
minimum row count → a guard that raises `ERROR:` if the extract spans more than one
`EXTRACT_PERIOD`. `sas/etl/m_ext_cust_master.sas:10-32` is representative; the pattern is
described at `docs/discovery/04_never_invoked.md:47-50`. **None is invoked, so none of
those data-quality guards has ever run.**

**None of the extracts they read is checked in.** `data/input/` holds three files only:
`loan_tape_202409.csv`, `collateral_202409.csv`, `macro_scenarios.csv`. Those are the only
three inbound files the batch reads, both inside `%load_loan_tape` and `%pd_pit`
(`docs/discovery/04_never_invoked.md:52-54`).

The header of each file names its source system — for example
`sas/etl/m_ext_valuation_feed.sas:4`, "Source system: Hometrack feed   Frequency:
monthly". `docs/discovery/01_program_inventory.md:64-78` tabulates all fifteen: Reference
data, Tallyman, CIS (Hogan), Credit Risk, CaseWorks, SAP, mortgage servicing, Vision Plus,
Economics (manual), the ECL engine itself, RiskCalc, Trust reporting and Hometrack.

Two matter more than the rest (`docs/discovery/04_never_invoked.md:60-68`):

- `%ext_valuation_feed` is the documented source of property valuations and indexation —
  the secured LGD inputs. The collateral data actually used is imported inline by
  `%load_loan_tape` *without* the `ACCOUNT_ID` normalisation and *without* the row-count
  assertion this program would have applied.
- `%ext_book_mapping` is **the only program in the repository that would create
  `BOOK_CD`**, which all twelve override books in section 3 require. Both halves of that
  mechanism are dead.

### 2.1 What would have to be true for this to be in scope

1. The named source systems still exist and still produce these extracts on the stated
   frequency.
2. The extracts are landing somewhere the production job can read — that is, `&INBOUND.`
   in production contains more than the three files reflected here.
3. The migrated Python engine actually needs one or more of those feeds. On the evidence
   here it needs none of them: everything the batch consumes arrives pre-joined on the loan
   tape, or does not reach the engine at all
   (`docs/discovery/04_never_invoked.md:54-58`).

Point 3 is the discriminator. If the production `&INBOUND.` holds only the three files,
these 15 programs are dead regardless of whether the source systems still run.

### 2.2 What evidence would settle it

- **A production directory listing of `&INBOUND.` for a recent period.** The path is
  configured per environment in `config/env/*.cfg` (`docs/migration/TARGET.md:38-39`); the
  runbook gives the production convention as `/data/gcra/inbound/loan_tape_<YYYYMM>.csv`
  (`docs/ops/RUNBOOK.md:5`). One listing answers "do these extracts exist" definitively.
- **One sample production extract with its header row**, for any of the fifteen —
  ideally `book_mapping_<period>.csv`, because it is the one that would carry `BOOK_CD`
  and therefore also settles half of section 3.
- **A schema or landing-area contract for the inbound area**, if one exists, naming the
  producing system per file.

### 2.3 Who owns that evidence

- The landing area and the batch that reads it: **Infra Batch Services**
  (`docs/ops/RUNBOOK.md:23`, `README.md:30`).
- Macro scenarios specifically: **Economics** — the runbook requires their sign-off before
  each run (`docs/ops/RUNBOOK.md:7`), and the inventory records `%ext_macro_forecast` as
  "source Economics (manual), quarterly refresh"
  (`docs/discovery/01_program_inventory.md:74`).
  Note this is a sign-off function for the scenarios, not a stated ownership of the
  inbound extract.
- Every other source system (Tallyman, CIS/Hogan, CaseWorks, SAP, Vision Plus, RiskCalc,
  Trust reporting, Hometrack): **owner not named in the repository.** The system names come
  from the file headers and the inventory only; no document names a team or contact for any
  of them.

### 2.4 Cost if the answer is yes

Engineering effort is small. Fifteen near-identical CSV loaders with a row-count assertion
and a duplicate-period guard are mechanical to port, and the pattern is uniform.

| | Estimate (Devin sessions, one migration unit per session) |
|---|---|
| Port all 15 extracts, with tests, if the file contracts are known | **2–3 sessions** |
| Add per-extract reconciliation to a real production sample | +1 session per extract that turns out to differ from the template |

Drivers that would make it larger: each extract whose real header differs from what
`proc import` infers here (`guessingrows=max` means the legacy code never declared a
schema, so the true column list is unknown until a sample is seen); any extract that turns
out to be fixed-width, delimited differently, or delivered by a mechanism other than a
file drop; and `%ext_valuation_feed`, which is entangled with the secured-LGD lineage
already documented in `docs/discovery/03_lineage_secured_lgd.md`.

**External dependencies are the longer pole.** Obtaining a production directory listing and
one sample extract per source system requires a request to each source-system owner, and
no owner is named for most of them (2.3). Sourcing production data samples will also need a
data-handling approval that is not described in this repository. Engineering cannot begin
on any extract until its sample exists, so the calendar cost is set by the slowest source
system, not by the 2–3 sessions of work.

---

## 3. Portfolio override books — 12 files, 36 macros

`sas/macros/portfolio/m_ovr_*.sas`, twelve acquired books — `ashdown`, `calder`, `fenwick`,
`kelvin`, `lowry`, `meridian`, `ngcore`, `orwell`, `pennine`, `severn`, `stanmore`,
`trent` — each defining three macros, `%ovr_<book>`, `%ovr_<book>_controls` and
`%ovr_<book>_recon` (`docs/discovery/04_never_invoked.md:70-74`).

These are not cosmetic. Each book applies material model adjustments: a PD multiplier
between 0.96 and 1.43, an LGD multiplier between 0.93 and 1.29 with a book-specific LGD
floor, a book-specific CCF between 0.45 and 0.90, and in several books a further quirk
(`docs/discovery/04_never_invoked.md:85-93`; per-book factors tabulated at
`docs/discovery/01_program_inventory.md:82-94`). Worked example, Stanmore
(`sas/macros/portfolio/m_ovr_stanmore.sas:12-27`): filter `BOOK_CD = "STANMORE"`, PD ×0.97,
LGD ×1.13 floored at 0.10, CCF 0.45, and a rescale of `DRAWN_BAL` and `UNDRAWN` by 100 when
`BAL_UNIT = 'P'` because "this book reports balances in pence on the legacy feed"
(`:23-26`). Kelvin carries the same pence rescale
(`docs/discovery/01_program_inventory.md:91`,
`sas/macros/portfolio/m_ovr_kelvin.sas:23-26`). NGCORE suppresses the relative SICR test for
accounts converted in 2003 by setting `PD_LIFETIME_ORIG = PD_LIFETIME` when
`CONV_FLAG = 'Y'` (`sas/macros/portfolio/m_ovr_ngcore.sas:23-26`).

The `_controls` macros silently default missing `RATING_GRADE`, `REMAIN_TERM_M` and `EIR`
to book-specific values, with the comment "agreed with Finance at onboarding, see the
acquisition file" (`sas/macros/portfolio/m_ovr_ashdown.sas:44`, and the identical line in
all twelve).

**They are unreachable twice over and unrunnable as written.** Nothing calls them;
`sas/macros/portfolio` is not on the autocall path
(`docs/discovery/04_never_invoked.md:76-78`); and every one of them begins
`where BOOK_CD = "<BOOK>"`, but `BOOK_CD` does not exist in
`data/input/loan_tape_202409.csv`, in any staged dataset, or anywhere else in the
repository outside these 12 files and 9 report programs
(`docs/discovery/04_never_invoked.md:80-83`). The loan tape's columns are `ACCOUNT_ID,
PROD_CD, REGION, RATING_GRADE, DRAWN_BAL, UNDRAWN, DPD, FORBEARANCE, WATCHLIST,
DEFAULT_IND, IO_FLAG, MONTHLY_PAYMENT, EIR, REMAIN_TERM_M, LTV, PD_LIFETIME_ORIG`. The only
program that would create `BOOK_CD` is `%ext_book_mapping`, itself dead (section 2).

The discovery pack states the consequence plainly
(`docs/discovery/04_never_invoked.md:95-98`): either the group's live engine applies these
adjustments and this repository is not the code that runs, or twelve books of
acquisition-agreed adjustments and their agreed data-quality treatments are not being
applied to the provision. That is section 1 restated in its sharpest form, and it is why
this block is described in the pack as the largest single unknown.

### 3.1 What would have to be true for this to be in scope

1. **`BOOK_CD` exists in some upstream source**, and a book-to-account mapping is
   obtainable for the periods being migrated — historically as well as currently, if the
   parity baseline is to be reproduced.
2. **The book adjustments are actually being applied to the filed provision today.** If
   they are not, porting them is not a migration but a change in the provision, which is
   an entirely different governance path.
3. **The per-book factors here are current.** Stanmore's own header says the book was
   "Reviewed by Model Governance not since onboarding"
   (`sas/macros/portfolio/m_ovr_stanmore.sas:5`). Factors last reviewed at acquisition may
   not be the factors in force.
4. The books still have balances. The `_controls` macros describe themselves as "retained
   pending book run off" (`sas/macros/portfolio/m_ovr_stanmore.sas:31`); a book that has
   run off to zero needs no port.

### 3.2 What evidence would settle it

- **A sample of the production book mapping extract** (`book_mapping_<period>.csv`) or the
  equivalent source, showing `BOOK_CD` and its account coverage. This is the single most
  valuable artefact in this document: it settles 3.1(1) and materially informs section 1.
- **The current provision broken down by book**, from whatever produces the filed number.
  If the totals are consistent with the multipliers here being applied, reading A of
  section 1 is supported; if they are not, the adjustments are not live.
- **The acquisition files referenced in the code** (`m_ovr_ashdown.sas:44`, "see the
  acquisition file") — twelve of them, one per book. These are the authority for the
  factors and for the agreed data-quality treatments, and are the only place the *intent*
  of these adjustments is recorded.
- **The Model Governance record for each book**, establishing whether the factors have been
  reviewed since onboarding.

### 3.3 Who owns that evidence

- **Methodology and the model itself: GCRA.** `README.md:6` ("Owner: Group Credit Risk
  Analytics (GCRA)"), `docs/ops/RUNBOOK.md:24` ("Methodology questions: GCRA."). The
  discovery pack directs this block specifically to GCRA and Infra Batch Services
  (`docs/discovery/04_never_invoked.md:98`).
- **Whether the adjustments run in production:** **Infra Batch Services** is the nearest
  operational contact (`docs/ops/RUNBOOK.md:23`, `README.md:30`), and
  `docs/discovery/02_execution_order.md:149-150` directs the question there. No document
  assigns them ownership of production model behaviour. This is the section 1 question.
- **The data-quality treatments:** **Finance** is named in the code as having agreed them
  at onboarding (`sas/macros/portfolio/m_ovr_ashdown.sas:43-44`); current ownership of the
  treatment is not established anywhere in the repository. Finance is separately named as
  the recipient of the recon pack (`docs/ops/RUNBOOK.md:10`) and in the GL feed output
  contract (`docs/migration/TARGET.md:14-15`).
- **Changes to the factors: Model Governance.** `docs/ops/RUNBOOK.md:25` requires Model
  Governance sign-off and external review for methodology changes;
  `docs/migration/TARGET.md:26-29` requires any divergence to be agreed with Model
  Governance rather than quietly fixed. The book headers reference Model Governance review
  directly (`sas/macros/portfolio/m_ovr_stanmore.sas:5`).
- **The acquisition files, and a book taxonomy owner: owner not named in the repository.**
  No document says where the acquisition files are held or who is accountable for the book
  code list. **Open question.**
- **A named individual for staging and disclosure: none.** `README.md:29` says only "see
  GCRA distribution list"; the two named individuals in the contacts table left the bank in
  2019 and 2022 (`README.md:27-28`), and the GCRA Confluence space that held further detail
  was decommissioned in 2021 (`README.md:20-21`). `docs/ops/RUNBOOK.md:24` adds that no
  current member of GCRA has worked on the PD term structure code.

### 3.4 Cost if the answer is yes

| | Estimate (Devin sessions, one migration unit per session) |
|---|---|
| Port the 12 `%ovr_<book>` adjustment macros | **3–4 sessions** (the arithmetic is simple and uniform; the twelve differ only in constants and one quirk each) |
| Port the 12 `_controls` and 12 `_recon` macros | **2–3 sessions** |
| Reconstruct the `BOOK_CD` join and thread it through the existing engine | **2–3 sessions** — this is the real work, because it changes the shape of the account-level dataset that every already-migrated unit consumes |
| Re-establish parity for units already migrated, now that accounts carry a book | **1–2 sessions** |
| **Subtotal** | **8–12 sessions** |

The factors themselves should come from configuration, not code —
`docs/migration/TARGET.md:12-13` requires that no thresholds, weights, haircuts or
coefficients be hardcoded in model code — so a per-book rules file is part of the port, not
an extra.

Drivers that would make it larger: books whose adjustment order matters relative to the
existing calculation chain (the override macros assume they run against a dataset with
`PD_12M`, `LGD`, `DRAWN_BAL`, `UNDRAWN`, `BAL_UNIT`, `CONV_FLAG`, `IO_FLAG` and
`WATCHLIST_FL` present, and several of those fields — `BAL_UNIT`, `CONV_FLAG` — do not
exist in the loan tape either, so each is a further sourcing question); the NGCORE SICR
suppression, which interacts with a staging rule the discovery pack already flags as
contradicting the specification (`docs/discovery/06_spec_contradictions.md`); and any book
whose factors turn out to have been revised since onboarding, in which case there are two
candidate truths and the code is not authoritative for either.

**External dependencies dominate.** The book mapping source must be found (section 2), the
acquisition files retrieved from twelve separate onboarding records with no named
custodian, and — critically — **if these adjustments are not currently applied, turning
them on changes the provision**, which is a Model Governance and Model Risk Committee
matter, not an engineering one (`docs/ops/RUNBOOK.md:25`,
`docs/migration/TARGET.md:26-29`, `docs/migration/TARGET.md:3-5`). That approval path is
the longest pole in this document and its duration cannot be estimated from the
repository.

---

## 4. Regulatory report programs — 20 files, 60 macros

`sas/reports/m_rpt_*.sas`, twenty programs each defining a main extract, a `_validate`
control macro and an `_archive` macro (`docs/discovery/01_program_inventory.md:101-103`,
`docs/discovery/04_never_invoked.md:103-109`). They cover the Pillar 3 CR1, CR2, CQ1 and
CQ3 lines, EBA FINREP 18 and 19, three IFRS 7 disclosures (coverage, ECL movement, stage
reconciliation), the GL journal extract, the GL feed reconciliation, the board provision
pack and board sensitivity, the ICAAP stress feed, IRB backtests for PD and LGD, model
monitoring, the data quality dashboard, the audit sample extract and the prior-period
comparison.

Three separate things are wrong with them, and they compound.

**(a) They read a dataset that does not contain the columns they select.** Every report
declares `inds=stg.ecl_acct`. That dataset is created at `sas/macros/m_ecl_calc.sas:30-38`
with exactly seven columns: `ACCOUNT_ID, SEGMENT, STAGE, EAD, LGD, OVERLAY_FACTOR, ECL`.
The reports collectively select `REGION`, `BOOK_CD`, `SICR_REASON`, `DEFAULT_FL`,
`FORBEARANCE_FL`, `ARREARS_BUCKET` and `PD_LIFETIME` — none of which is present. Which
report needs which missing column, and where each was dropped, is tabulated at
`docs/discovery/04_never_invoked.md:120-128`. In SAS this is a hard error, not a warning
(`docs/discovery/03_lineage_secured_lgd.md:143`).

**(b) There is nothing for them to read even if the columns existed.** `stg` is the SAS
WORK library — `sas/autoexec.sas:9` sets `%let ROOT = %sysfunc(pathname(work))` and
`sas/autoexec.sas:21` sets `libname stg "&ROOT"`. Every intermediate dataset, including
`stg.ecl_acct`, is destroyed when the session ends. **Nothing in the batch persists
account-level ECL anywhere** (`docs/discovery/02_execution_order.md:109-112`, EO-06).

**(c) Their prior-period controls have never executed.** Every `_validate` macro reads
`hist.<report>_&PRIOR_YYYYMM`. The `hist` library is assigned at `sas/autoexec.sas:23`, and
the `_archive` macros do contain code that writes to it (for example
`sas/reports/m_rpt_pillar3_cr1.sas:60-64`) — but no driver invokes any `_archive` macro, so
**no batch step has ever written to `hist`**
(`docs/discovery/02_execution_order.md:114-117`, EO-07). On a first run every `_validate`
fails on a non-existent table. The variance controls described in the code as "referenced
in the … control attestation" (`sas/reports/m_rpt_pillar3_cr1.sas:30`) have therefore never
run.

Several `where` filters also look like copy-paste survivals rather than intent —
`%rpt_gl_journal_extract`, a provision posting extract, filters `DEFAULT_FL = 1` and would
post only defaulted exposures (`docs/discovery/04_never_invoked.md:137-140`).

The discovery pack's conclusion is unambiguous and this document endorses it
(`docs/discovery/04_never_invoked.md:142-146`): **these 20 programs should not be
reimplemented from the code as written.** The code does not tell you what the reports are
meant to contain. The specifications have to be re-established from the filed submissions
and the attestations.

### 4.1 What would have to be true for this to be in scope

1. **Account-level ECL is persisted somewhere.** Today it is not (EO-06). Either production
   differs from this repository — section 1 again — or the reports have never had an input.
2. **The missing columns have a real derivation.** `REGION` and `ARREARS_BUCKET` exist
   earlier in the chain and are dropped at driver step 11; `SICR_REASON`, `DEFAULT_FL`,
   `FORBEARANCE_FL` and `PD_LIFETIME` are dropped at step 16
   (`docs/discovery/04_never_invoked.md:120-128`), so those seven are recoverable in
   principle by not dropping them. `BOOK_CD` is not: it is never created anywhere, so the
   three reports that group by it and the six whose validators join on it are blocked
   behind section 3.
3. **The filed submissions are actually produced by these programs.** If they are not
   (reading B of section 1), then porting this code produces reports that match nothing the
   bank has ever filed.
4. Retaining the seven dropped columns through to a persisted account-level output is a
   **behavioural change** to the migrated engine, and
   `docs/migration/TARGET.md:32-34` requires that behavioural changes be raised for
   decision rather than made quietly. `docs/discovery/03_lineage_secured_lgd.md:153-155`
   makes the same point for CR1 and CR2 specifically.

### 4.2 What evidence would settle it

- **The last filed Pillar 3 return (CR1, CR2, CQ1, CQ3) and the last FINREP 18/19
  submission, with their production lineage** — what job or process produced each figure.
  This is the artefact that decides whether this block exists at all, and it is the same
  artefact named in section 1.3.
- **The control attestations the code references**
  (`sas/reports/m_rpt_pillar3_cr1.sas:30` and equivalents in every report). The
  attestations state what the control is and what totals it compares; the code does not.
- **A production example of any archived report table in `hist`** — its existence or
  absence settles (c) directly and, with it, whether the production deployment runs the
  `_archive` macros.
- **A sample of the GL journal extract as actually posted**, to establish whether the
  `DEFAULT_FL = 1` filter reflects intent or is a defect. (Note: identifying it is in
  scope; *fixing* it is not a migration task —
  `docs/migration/TARGET.md:32-34`.)

### 4.3 Who owns that evidence

- **Four parties are named in the report sources themselves** as the owners of the control
  attestation each report is referenced in, and as the party that queries its prior-period
  variance. Each report names exactly one. This is the complete mapping:

  | Named party | Reports (`sas/reports/`, comment lines as noted) |
  |---|---|
  | **CFO's office** | `m_rpt_audit_sample_extract.sas:29,41`; `m_rpt_data_quality_dashboard.sas:29,41`; `m_rpt_eba_fintrep_19.sas:29,41`; `m_rpt_gl_journal_extract.sas:30,42`; `m_rpt_irb_backtest_pd.sas:29,41`; `m_rpt_model_monitoring.sas:30,42`; `m_rpt_pillar3_cq1.sas:29,41` |
  | **Regulatory Reporting** | `m_rpt_pillar3_cr2.sas:30,42`; `m_rpt_pillar3_cq3.sas:28,40`; `m_rpt_eba_fintrep_18.sas:29,41`; `m_rpt_ifrs7_stage_recon.sas:29,41`; `m_rpt_irb_backtest_lgd.sas:30,42`; `m_rpt_gl_feed_recon.sas:30,42`; `m_rpt_board_provision_pack.sas:29,41`; `m_rpt_stress_icaap_feed.sas:28,40` |
  | **Finance Control** | `m_rpt_pillar3_cr1.sas:30,42`; `m_rpt_board_sensitivity.sas:29,41`; `m_rpt_ifrs7_ecl_movement.sas:29,41` |
  | **Group Risk** | `m_rpt_ifrs7_coverage.sas:29,41` |
  | **Internal Audit** | `m_rpt_prior_period_compare.sas:30,42` |

  **None of these five names appears as an accountable owner in `README.md`,
  `docs/ops/RUNBOOK.md`, `docs/migration/TARGET.md` or `docs/ops/known_issues.md`, and no
  contact is given for any of them.** They are the right place to start, but the
  accountable owner of each filed return is **not named in the repository**. Open question.
  Note also that these attributions describe a control that has never executed — see (c)
  above.
- **Finance** is named as the recipient of the recon pack (`docs/ops/RUNBOOK.md:10`) and in
  the GL feed output contract (`docs/migration/TARGET.md:14-15`), which makes Finance the
  natural first port of call on the GL journal extract question.
- **GCRA** for what the disclosures are methodologically meant to contain
  (`README.md:6`, `docs/ops/RUNBOOK.md:24`) — subject to the caveat at
  `docs/ops/RUNBOOK.md:24-25` and `README.md:20-21,27-29` that the people and the
  documentation are largely gone.
- **Model Governance** for approving the retention of dropped columns as a behavioural
  change (`docs/ops/RUNBOOK.md:25`, `docs/migration/TARGET.md:26-29`).
- **Internal Audit** is recorded as the consumer of `%rpt_audit_sample_extract`
  (`docs/discovery/01_program_inventory.md:107`, "for Internal Audit sampling") and as the
  party querying `%rpt_prior_period_compare`
  (`sas/reports/m_rpt_prior_period_compare.sas:30,42`). Note that the audit sample
  extract's own control is attributed not to Internal Audit but to the CFO's office
  (`sas/reports/m_rpt_audit_sample_extract.sas:29,41`). Internal Audit is **not named as an
  owner anywhere**.

### 4.4 Cost if the answer is yes

This is by far the largest block and the estimate has the widest range, because the driver
is not code volume but specification recovery.

| | Estimate (Devin sessions, one migration unit per session) |
|---|---|
| Persist account-level ECL and retain the seven dropped columns, with parity re-established on the existing baseline | **2–3 sessions** |
| Port 20 reports *from the code as written* (not recommended — see below) | **7–10 sessions** |
| Port 20 reports *from re-established specifications*, which is what 4.1(3) requires | **20–30 sessions**, roughly one to one and a half per report, and this assumes the specification arrives first |
| Rebuild the 20 `_validate` prior-period controls and the `hist` archive, once there is a specification for what each control compares | **6–8 sessions** |
| **Subtotal, specification-led** | **28–41 sessions** |

Drivers that would make it larger: the nine reports blocked behind `BOOK_CD`, which cannot
start until section 3 resolves; any report whose filed figure turns out not to be derivable
from account-level ECL at all (CR1 today is exactly this case —
`docs/discovery/03_lineage_secured_lgd.md:147-152`); and the fact that thirty of the sixty
macros here (`_validate` and `_archive`) have never run, so there is no legacy behaviour to
be faithful to.

That last point is the important one for budget, and it recurs in the recommendation:
**for code with no captured output, there is nothing to be parity-tested against.**
`docs/migration/TARGET.md:24-25` requires that "parity is evidenced, not asserted", by a
machine-readable comparison attachable to the model change record. The only captured
legacy output in the repository is `data/expected/ecl_by_segment_202409.csv`
(`docs/migration/TARGET.md:48-49`), which covers the segment CSV and nothing else. There
is **no repository policy for a unit with no captured legacy output** — none could be
found, and this is an open question the migration governance needs to answer explicitly.

**External dependencies dominate even more than in section 3.** Retrieving filed
submissions and control attestations, agreeing the retention of dropped columns with Model
Governance, and obtaining sign-off for reports whose translation cannot be evidenced are
all outside engineering control and all sequential ahead of the work.

---

## 5. The two orphans

**`%pd_ttc`** (`sas/macros/m_pd_ttc.sas:7`) — the through-the-cycle logistic scorecard.
It is the only orphan in the repository whose orphaning is documented:
`docs/CHANGELOG.txt:11-12` records "2019-09-05  v4.2  m_pd_ttc no longer called from driver
(superseded by PIT). Left in place pending Model Governance retirement." Its own header
repeats this and adds "Do not delete" (`sas/macros/m_pd_ttc.sas:4-5`).

The complication is that it is also **the only implementation of specification section
3.1**, which the specification still presents as the origin of PD
(`docs/discovery/04_never_invoked.md:34-37`, and SC-01 in
`docs/discovery/06_spec_contradictions.md`). So it is dead code that the approved
specification still points at.

*Recommendation:* do not port it. Retire it formally — the changelog says it has been
awaiting Model Governance retirement since 2019 — and record the specification section
3.1 discrepancy as part of that retirement. **Owner: Model Governance**
(`docs/ops/RUNBOOK.md:25`, and the Model Governance Committee approval recorded at
`docs/ECL_Model_Spec_v3_2016.md:3`). Cost: **0 sessions** of engineering; one governance
item.

**`%months_between`** (`sas/macros/m_util_dates.sas:10-12`) — a one-line wrapper around
`intck`. It sits in a file the batch does reach, but is never called
(`docs/discovery/01_program_inventory.md:57`). *Recommendation:* drop it. Cost: nil. No
governance implication.

---

## 6. Recommendation

**6.1 Resolve section 1 before scoping anything else, and before starting another
migration unit.** Request the production Control-M job definition and the deployed SAS
macro library listing from Infra Batch Services, and the provenance of the last filed
Pillar 3 CR1 submission from whoever owns that return. Everything in sections 2 to 4 is
conditional on the answer, and the two possible answers point in opposite directions.
This costs no engineering effort and blocks the largest budget decision in the programme.

**6.2 Continue the in-flight migration of the 25 reachable rows unchanged.** They have a
captured baseline (`data/expected/ecl_by_segment_202409.csv`,
`docs/migration/TARGET.md:48-49`) and can be evidenced to the standard the acceptance
criteria require. Nothing in this document should slow that work — with one caveat: if
section 1 resolves to reading A, the baseline itself was produced by code that is not the
code being migrated, and completed parity evidence would need revisiting.

**6.3 ETL — provisionally descope, revisit on evidence.** Ask for one production listing of
the inbound area. If it contains only the three files this repository reads, descope all
fifteen extracts formally. If it contains more, the port is small (2–3 sessions) but is
gated on obtaining a sample per source system from owners who are not currently named.

**6.4 Portfolio overrides — do not descope; escalate.** This is the block where being wrong
is most expensive in both directions. Either twelve books of acquisition-agreed adjustments
are missing from the provision, or the live engine is not this repository. Both are
reportable findings, not migration tasks. The engineering cost if they are in scope is
8–12 sessions, but the decision belongs to GCRA and Model Governance, and turning the
adjustments on where they are not currently applied changes the provision.

**6.5 Regulatory reports — recommend formal descope as written, and a separate,
specification-led piece of work if the disclosures prove to be in scope.** Porting 28–41
sessions of code that has never executed, against no captured output, to produce
regulatory disclosures, is the worst value in this document. Two options are defensible:

- *Descope and record as deliberately abandoned.* If section 1 resolves to reading B and
  the filed disclosures are produced elsewhere, this code is dead and should be recorded as
  abandoned rather than migrated. **For genuinely dead code, formally abandoning it is a
  legitimate and much cheaper outcome than porting it** — it is a documented decision with
  a named approver, not an omission.
- *Rebuild from the filed submissions.* If the disclosures are in scope, they should be
  specified from the filed returns and the control attestations, then built — not
  translated from code that cannot run. That is a separate initiative with its own budget,
  not a line item in an engine migration.

What should not happen is a literal port of `sas/reports/`. It would carry across filters
that look like defects (`docs/discovery/04_never_invoked.md:137-140`), controls that have
never executed, and joins on columns that do not exist — and it could not be evidenced.

**6.6 The orphans:** retire `%pd_ttc` through Model Governance; drop `%months_between`.

### 6.7 The evidence point that should be recorded explicitly

`docs/migration/TARGET.md:24-25` requires that parity be **evidenced, not asserted**. The
only captured legacy output the programme holds is the segment-level CSV for 202409
(`docs/migration/TARGET.md:48-49`). **No captured legacy output for any of the 113
definitions in this document is present in this repository** — on the evidence here the
ETL guards have never run, the override books have never been applied, and thirty of the
sixty report macros have never executed at all. (What may have executed in a production
deployment outside this repository is section 1's question, and is exactly why that
question comes first.)

**Under the stated acceptance criterion, a unit with no captured legacy output cannot
satisfy the repository's defined numeric-parity evidence standard, and the repository does
not specify an alternative.** Therefore any decision to port these groups, as things
stand, is also a decision to accept **unevidenced translations of code that governs
regulatory disclosures**. That trade-off should be made knowingly, by a named approver, and
recorded — not absorbed silently into a migration plan whose stated acceptance criteria it
does not meet.

---

## 7. Open questions this document could not close

Each of these is a fact that is not determinable from this repository. None has been
guessed at.

1. **Does the production deployment run this code?** Section 1. Nothing in the repository
   can answer it.
2. **What produces the filed Pillar 3 CR1 line?** `docs/discovery/03_lineage_secured_lgd.md:147-152`.
3. **Who owns the filed regulatory returns?** The report sources name five parties — the
   CFO's office, Regulatory Reporting, Finance Control, Group Risk and Internal Audit (full
   mapping in 4.3) — but no ownership document names any of them. Owner not named in the
   repository.
4. **Who owns each inbound source system?** Thirteen distinct systems are named in file
   headers and `docs/discovery/01_program_inventory.md:64-78`. Economics is the only
   source-related function named in the documentation, and it is named for macro-scenario
   sign-off (`docs/ops/RUNBOOK.md:7`) rather than explicitly as the owner of an inbound
   source system. Owners not named in the repository.
5. **Who owns the book taxonomy and the twelve acquisition files?** Referenced at
   `sas/macros/portfolio/m_ovr_ashdown.sas:44`; no custodian named. Owner not named in the
   repository.
6. **Who owns the SAS macro catalogue / `SASMSTORE` in production?** Owner not named in the
   repository; `docs/discovery/02_execution_order.md:149-150` suggests confirming with
   Infra Batch Services.
7. **Does `BOOK_CD` exist upstream, and where?** Section 3.
8. **Are the override adjustments applied to the filed provision today?** Section 3.
9. **What is the migration's policy for a unit with no captured legacy output?** No such
   policy exists in the repository; `docs/migration/TARGET.md:21-25` assumes a baseline
   exists. Section 6.7.
10. **Have the per-book factors been revised since onboarding?**
    `sas/macros/portfolio/m_ovr_stanmore.sas:5` says the book has not been reviewed by
    Model Governance since onboarding; the position for the other eleven is unstated.

### Note on the estimates

The session estimates in sections 2 to 4 are engineering judgements made for this document,
sized against the code as it stands. They are **not** sourced from the repository: neither
`docs/migration/TARGET.md` nor the discovery pack expresses migration effort in sessions,
PRs or any other unit. They are stated in Devin sessions because that is the unit in which
this migration is being run, one migration unit per session. They exclude all external
dependencies — obtaining extracts, retrieving filed submissions, and governance sign-off —
which in every group above is the longer pole, and whose duration cannot be estimated from
anything in this repository.
