import pandas as pd


def board_pack(aggregate: pd.DataFrame) -> pd.DataFrame:
    """Aggregate segment×stage ECL output into the legacy board pack."""
    result = (
        aggregate.groupby("SEGMENT", dropna=False)
        .agg(
            EAD=("TOTAL_EAD", lambda values: values.sum(min_count=1)),
            ECL=("TOTAL_ECL", lambda values: values.sum(min_count=1)),
        )
        .sort_index(na_position="first")
        .reset_index()
    )
    return result
