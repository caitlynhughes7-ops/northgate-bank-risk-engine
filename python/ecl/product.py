import pandas as pd
from .config import table
from .util_logging import log_step

def map_products(tape: pd.DataFrame) -> pd.DataFrame:
    log_step("map_product_hierarchy")
    h = table("product_hierarchy.csv")
    return tape.merge(h, on="PROD_CD", how="left", suffixes=("", "_H"))
