import pandas as pd
from ecl.arrears import derive_arrears
from ecl.clean import clean
from ecl.discount import discount
from ecl.lgd import secured
from ecl.staging import stage

def test_clean_legacy_values():
    d = pd.DataFrame({"ACCOUNT_ID": ["  a  b "], "DPD": ["999"], "FORBEARANCE": ["N"], "WATCHLIST": ["N"], "DEFAULT_IND": ["N"], "IO_FLAG": ["Y"], "MONTHLY_PAYMENT": [4], "EIR": [3.0], "DRAWN_BAL": [1], "UNDRAWN": [0]})
    x = clean(d)
    assert x.ACCOUNT_ID.iloc[0] == "ab" and x.DPD_N.iloc[0] == 0 and x.MONTHLY_PAYMENT.iloc[0] == 0 and x.EIR.iloc[0] == 0.03

def test_arrears_part_month():
    d = pd.DataFrame({"DPD_N": [1], "MONTHLY_PAYMENT": [1], "DRAWN_BAL": [2000]})
    assert derive_arrears(d).ARREARS_BUCKET.iloc[0] == "0"

def test_discount_personal_loan_legacy_formula():
    d = pd.DataFrame({"SEGMENT": ["PERSONAL_LOAN"], "EIR": [0.12], "T": [12]})
    assert discount(d).DF.iloc[0] == 1 / (1 + 0.12)

def test_secured_missing_fallbacks_and_unmatched_floor():
    d = pd.DataFrame({"ACCOUNT_ID": ["a"], "SECURED_FLAG": ["Y"], "EAD": [100.0], "PROD_CD": [9999], "SEGMENT": ["UNMAPPED"]})
    c = pd.DataFrame(columns=["ACCOUNT_ID", "VALUATION", "HPI_INDEX_ORIG", "HPI_INDEX_CURR"])
    x = secured(d, c)
    assert x.LGD_RAW.iloc[0] == 1 and x.LGD.iloc[0] == 1

def test_staging_precedence():
    d = pd.DataFrame({"SEGMENT": ["PERSONAL_LOAN"], "DEFAULT_FL": [True], "DPD_N": [0], "FORBEARANCE_FL": [False], "WATCHLIST_FL": [True], "PD_LIFETIME": [0.5], "PD_LIFETIME_ORIG": [0.01]})
    assert stage(d).STAGE.iloc[0] == 3
