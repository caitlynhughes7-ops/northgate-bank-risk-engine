# Northgate Bank Group — IFRS 9 ECL Engine

SAS 9.4 batch engine that produces the monthly IFRS 9 Expected Credit Loss (ECL)
provision for the Retail and SME lending portfolios of Northgate Bank Group plc.

Owner: Group Credit Risk Analytics (GCRA)
Platform: SAS 9.4 M5 on RHEL 7, scheduled via Control-M
Downstream: Finance GL feed (ECL_GL_FEED), Board Risk Pack, ICAAP/Pillar 3 disclosure

## Running

    ./jobs/monthly_ecl.sh 202409 prod

See `docs/ops/RUNBOOK.md`.

## Documentation

Model methodology is documented in `docs/ECL_Model_Spec_v3_2016.md`.

> NOTE: further detail was held on the GCRA Confluence space (RISK-ANALYTICS), which was
> decommissioned during the 2021 intranet migration. Some links below no longer resolve.

## Contacts

| Area | Owner |
|---|---|
| PD models | P. Whitcombe (left 2019) |
| LGD / collateral | A. Ferris (left 2022) |
| Staging & disclosure | see GCRA distribution list |
| Platform / scheduling | Infra Batch Services |
