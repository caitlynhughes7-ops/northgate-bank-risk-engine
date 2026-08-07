import pandas as pd
from .config import table

def map_products(tape: pd.DataFrame) -> pd.DataFrame:
    h = table("product_hierarchy.csv")
    return tape.merge(h, on="PROD_CD", how="left", suffixes=("", "_H"))
