"""Generate the anonymised sample loan tape used for UAT and regression runs.

The production tape is extracted from the lending warehouse and cannot leave the
bank's network. This script produces a statistically similar synthetic tape with
the same column contract, so the engine can be exercised outside production.

    python tools/make_sample_data.py --period 202409 --accounts 2000
"""

import argparse
import csv
import random
from pathlib import Path

PRODUCTS = [
    # prod_cd, weight, secured, term range, rate range (pct for secured feed)
    (2100, 0.26, True, (60, 300), (2.1, 5.9)),
    (2101, 0.07, True, (48, 240), (2.4, 6.2)),
    (2110, 0.13, True, (60, 300), (3.1, 6.8)),
    (2120, 0.04, True, (36, 180), (4.0, 8.5)),
    (2130, 0.03, True, (24, 120), (4.5, 9.0)),
    (2400, 0.17, False, (12, 84), (0.069, 0.229)),
    (2500, 0.16, False, (12, 120), (0.189, 0.349)),
    (2600, 0.08, False, (12, 60), (0.159, 0.399)),
    (2700, 0.06, False, (24, 96), (0.059, 0.149)),
]

# Loan to value and house price index profile by secured product. The owner
# occupied book is long held and has benefited from index growth; the buy to let
# and SME books were largely written in the 2021-22 vintages at higher leverage
# and have seen flat to negative index movement since.
SECURED_PROFILE = {
    2100: {"ltv": (35, 88), "hpi_growth": (1.02, 1.34)},
    2101: {"ltv": (40, 82), "hpi_growth": (1.00, 1.28)},
    2110: {"ltv": (68, 92), "hpi_growth": (0.96, 1.08)},
    2120: {"ltv": (60, 88), "hpi_growth": (0.94, 1.06)},
    2130: {"ltv": (55, 85), "hpi_growth": (0.95, 1.10)},
}

REGIONS = ["LON", "SE", "SW", "MID", "NW", "NE", "SCO", "WAL", "NI"]


def pick_product(rng):
    r = rng.random()
    acc = 0.0
    for row in PRODUCTS:
        acc += row[1]
        if r <= acc:
            return row
    return PRODUCTS[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="202409")
    ap.add_argument("--accounts", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20240930)
    ap.add_argument("--outdir", default="data/input")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    tape_rows = []
    coll_rows = []

    for i in range(args.accounts):
        acct = "NB%09d" % (10_000_000 + i * 7)
        prod_cd, _w, secured, term_rng, rate_rng = pick_product(rng)

        grade = min(15, max(1, int(rng.gauss(7.2, 2.6))))
        if rng.random() < 0.015:
            grade = 15

        if secured:
            drawn = round(rng.uniform(45_000, 620_000), 2)
            undrawn = 0.0
        elif prod_cd == 2500:
            limit = round(rng.choice([1500, 3000, 5000, 8000, 12_000]), 2)
            drawn = round(limit * rng.uniform(0.05, 0.98), 2)
            undrawn = round(limit - drawn, 2)
        elif prod_cd == 2600:
            limit = round(rng.choice([500, 1000, 2500, 5000]), 2)
            drawn = round(limit * rng.uniform(0.0, 1.0), 2)
            undrawn = round(limit - drawn, 2)
        else:
            drawn = round(rng.uniform(1_000, 45_000), 2)
            undrawn = round(rng.choice([0, 0, 0, 2500]), 2)

        # arrears profile is grade dependent
        p_arr = min(0.6, 0.005 + 0.010 * grade)
        if rng.random() < p_arr:
            dpd = rng.choice([5, 12, 22, 35, 47, 62, 75, 95, 130, 190])
        else:
            dpd = 0

        default_ind = "Y" if (grade == 15 or dpd >= 90) and rng.random() < 0.85 else "N"

        # the collections platform emits sentinels for a small number of accounts
        if dpd == 0 and rng.random() < 0.03:
            dpd_out = rng.choice(["N/A", "999", ""])
        else:
            dpd_out = str(dpd)

        term = rng.randint(*term_rng)
        rate = round(rng.uniform(*rate_rng), 4)
        io = "Y" if secured and prod_cd == 2101 and rng.random() < 0.8 else "N"
        monthly_pay = 0.0 if io == "Y" else round(drawn / max(term, 1) * 1.18, 2)

        if secured:
            prof = SECURED_PROFILE[prod_cd]
            ltv = round(rng.uniform(*prof["ltv"]), 1)
        else:
            prof = None
            ltv = 0.0

        # lifetime PD at origination, held on the tape by the staging feed
        base = {1: 0.0009, 2: 0.0018, 3: 0.0036, 4: 0.0062, 5: 0.0098}.get(
            grade, 0.0098 + 0.0125 * (grade - 5)
        )
        pd_orig = round(min(0.95, base * rng.uniform(0.55, 1.15)), 6)

        tape_rows.append(
            {
                "ACCOUNT_ID": acct if rng.random() > 0.1 else acct.ljust(12),
                "PROD_CD": prod_cd,
                "REGION": rng.choice(REGIONS),
                "RATING_GRADE": grade,
                "DRAWN_BAL": drawn,
                "UNDRAWN": undrawn,
                "DPD": dpd_out,
                "FORBEARANCE": "Y" if rng.random() < 0.02 else "N",
                "WATCHLIST": "Y" if rng.random() < 0.03 else "N",
                "DEFAULT_IND": default_ind,
                "IO_FLAG": io,
                "MONTHLY_PAYMENT": monthly_pay,
                "EIR": rate,
                "REMAIN_TERM_M": term,
                "LTV": ltv,
                "PD_LIFETIME_ORIG": pd_orig,
            }
        )

        if secured:
            val = round(drawn / max(ltv, 20) * 100, 2)
            hpi_orig = round(rng.uniform(88, 118), 1)
            coll_rows.append(
                {
                    "ACCOUNT_ID": acct,
                    "VALUATION": val,
                    "VAL_DT": "%d-%02d-01" % (rng.randint(2012, 2023), rng.randint(1, 12)),
                    "HPI_INDEX_ORIG": hpi_orig,
                    "HPI_INDEX_CURR": round(hpi_orig * rng.uniform(*prof["hpi_growth"]), 1),
                }
            )

    def dump(path, rows):
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print("wrote %s (%d rows)" % (path, len(rows)))

    dump(outdir / ("loan_tape_%s.csv" % args.period), tape_rows)
    dump(outdir / ("collateral_%s.csv" % args.period), coll_rows)

    with open(outdir / "macro_scenarios.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["SCENARIO", "GDP_SHOCK", "UNEMP_RATE"])
        w.writerow(["BASE", 0.004, 4.3])
        w.writerow(["UPSIDE", 0.021, 3.8])
        w.writerow(["DOWNSIDE", -0.018, 5.6])
        w.writerow(["SEVERE", -0.047, 7.9])
    print("wrote %s" % (outdir / "macro_scenarios.csv"))


if __name__ == "__main__":
    main()
