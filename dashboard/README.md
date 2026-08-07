# Provision dashboard

Static read-only view of the monthly ECL output, used by Group Credit Risk to
review the provision before it is circulated to Finance.

    python3 -m http.server 8080 --directory .

Then open http://localhost:8080/dashboard/ from the repository root.

A published snapshot of this view is served as a static site; `/` redirects to
`/dashboard/`. The snapshot's migrated-engine figures are the committed
`data/output/ecl_by_segment_202409.csv`, produced by
`tools/regression_harness.py`; re-run the engine and commit that file to refresh
it.

## Wording

The view is read by Finance, Model Governance and the Board Risk Committee, so it
labels everything in plain English and uses no acronyms: EAD reads as "lending",
ECL as "provision", coverage as "provision rate", and the three IFRS 9 stages as
`Performing`, `On the watchlist` and `In default`. The underlying CSV column names
are unchanged.

## Comparison basis

Side-by-side mode evaluates both `TOTAL_ECL` and `TOTAL_EAD` against the baseline
at the `docs/migration/TARGET.md` tolerance of 0.01 absolute, and shows the
variance on each per cell.

Note that both files are rendered to 2dp, so a cell whose unrounded value sits on
a half-penny boundary can show a 1p variance that is not an engine divergence.
For 202409 this affects `CREDIT_CARD` stages 1 and 2, where EAD is 0.005 above
the baseline unrounded and so renders 1p higher; `data/output/parity_202409.json`
records the unrounded comparison.

The `Figures from` selector reads:

- **The old engine** - `data/expected/ecl_by_segment_<period>.csv`
- **The new engine** - `data/output/ecl_by_segment_<period>.csv`
- **Both, side by side** - both, with per cell variance and a parity summary
