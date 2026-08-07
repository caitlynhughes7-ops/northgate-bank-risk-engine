# Provision dashboard

Static read-only view of the monthly ECL output, used by Group Credit Risk to
review the provision before it is circulated to Finance.

    python3 -m http.server 8080 --directory .

Then open http://localhost:8080/dashboard/ from the repository root.

A published snapshot of this view is served as a static site from the repository
root, so `/` serves the dashboard. The snapshot's migrated-engine figures are the
committed `data/output/ecl_by_segment_202409.csv`, produced by
`tools/regression_harness.py`; re-run the engine and commit that file to refresh
it.

The `Engine` selector reads:

- **Legacy SAS engine** - `data/expected/ecl_by_segment_<period>.csv`
- **Migrated engine** - `data/output/ecl_by_segment_<period>.csv`
- **Compare** - both, with per cell variance and a parity summary
