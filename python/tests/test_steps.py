import pandas as pd
from ecl.config import params, table
from ecl.arrears import derive_arrears
from ecl.clean import clean
from ecl.discount import discount
from ecl.io import write_outputs
from ecl.lgd import secured
from ecl.staging import stage

def test_clean_legacy_values():
    d = pd.DataFrame({"ACCOUNT_ID": ["  a  b "] * 100, "DPD": ["999"] * 100, "FORBEARANCE": ["N"] * 100, "WATCHLIST": ["N"] * 100, "DEFAULT_IND": ["N"] * 100, "IO_FLAG": ["Y"] * 100, "MONTHLY_PAYMENT": [4] * 100, "EIR": [3.0] * 100, "DRAWN_BAL": [1] * 100, "UNDRAWN": [0] * 100})
    x = clean(d)
    assert x.ACCOUNT_ID.iloc[0] == "ab" and x.DPD_N.iloc[0] == 0 and x.MONTHLY_PAYMENT.iloc[0] == 0 and x.EIR.iloc[0] == 0.03


def test_io_flag_is_case_sensitive_after_trimming():
    d = pd.DataFrame(
        {
            "ACCOUNT_ID": ["a", "b", "c"] + ["extra"] * 97,
            "DPD": ["0", "0", "0"] + ["0"] * 97,
            "FORBEARANCE": ["N"] * 100,
            "WATCHLIST": ["N"] * 100,
            "DEFAULT_IND": ["N"] * 100,
            "IO_FLAG": ["Y", "Y ", "y"] + ["N"] * 97,
            "MONTHLY_PAYMENT": [4, 4, 4] + [1] * 97,
            "EIR": [0.1] * 100,
            "DRAWN_BAL": [1] * 100,
            "UNDRAWN": [0] * 100,
        }
    )
    assert clean(d).MONTHLY_PAYMENT.tolist()[:3] == [0, 0, 4]

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


def test_btl_ki021_config_mismatch_keeps_haircut_zero():
    # KI-021: hierarchy code 2110 has no match for legacy haircut code 110.
    d = pd.DataFrame(
        {
            "ACCOUNT_ID": ["a"],
            "SECURED_FLAG": ["Y"],
            "EAD": [100.0],
            "PROD_CD": [2110],
            "SEGMENT": ["BTL_MORTGAGE"],
        }
    )
    c = pd.DataFrame(
        {
            "ACCOUNT_ID": ["a"],
            "VALUATION": [100.0],
            "HPI_INDEX_ORIG": [100.0],
            "HPI_INDEX_CURR": [100.0],
        }
    )
    assert secured(d, c).HAIRCUT.iloc[0] == 0


def test_active_scenario_weights_are_frozen_v43():
    assert params()["active_scenario_weights"] == "frozen_v43"
    weights = table("scenario_weights_frozen_v43.csv")
    assert dict(zip(weights.SCENARIO, weights.WEIGHT)) == {
        "BASE": 0.70,
        "UPSIDE": 0.10,
        "DOWNSIDE": 0.20,
        "SEVERE": 0.00,
    }


def test_gl_feed_record_layout(tmp_path):
    out = pd.DataFrame(
        {
            "SEGMENT": ["SEGMENT_NAME"],
            "STAGE": [2],
            "N_EXPOSURES": [1],
            "TOTAL_EAD": [100.0],
            "TOTAL_ECL": [12.3],
            "COVERAGE": [0.123],
        }
    )
    write_outputs(out, tmp_path, "202409")
    line = (tmp_path / "data/output/ECL_GL_FEED_202409.txt").read_text().rstrip("\n")
    assert len(line) == 39
    assert line[:20] == "SEGMENT_NAME".ljust(20)
    assert line[20] == "2"
    assert line[21:] == f"{12.3:18.2f}"


def test_gl_feed_unmapped_segment_is_blank(tmp_path):
    out = pd.DataFrame(
        {
            "SEGMENT": [None],
            "STAGE": [1],
            "N_EXPOSURES": [1],
            "TOTAL_EAD": [100.0],
            "TOTAL_ECL": [12.3],
            "COVERAGE": [0.123],
        }
    )
    write_outputs(out, tmp_path, "202409")
    line = (tmp_path / "data/output/ECL_GL_FEED_202409.txt").read_text().rstrip("\n")
    assert line[:20] == " " * 20

def test_staging_precedence():
    d = pd.DataFrame({"SEGMENT": ["PERSONAL_LOAN"], "DEFAULT_FL": [True], "DPD_N": [0], "FORBEARANCE_FL": [False], "WATCHLIST_FL": [True], "PD_LIFETIME": [0.5], "PD_LIFETIME_ORIG": [0.01]})
    assert stage(d).STAGE.iloc[0] == 3
