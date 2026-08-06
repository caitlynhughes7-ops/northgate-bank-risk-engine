from pathlib import Path
import pandas as pd
from .io import load_period, write_outputs
from .clean import clean
from .product import map_products
from .arrears import derive_arrears
from .ead import ead_ccf
from .pd_model import pd_pit, term_structure
from .lgd import secured, unsecured
from .staging import stage
from .overlay import apply_overlay
from .discount import discount
from .ecl import calculate
from .aggregate import aggregate

def run(period: str, root: Path | None = None, weight_file: str | None = None, haircut_overrides: dict[int, float] | None = None):
    root = root or Path(__file__).resolve().parents[2]
    tape, collateral, scenarios = load_period(root, period)
    x = ead_ccf(derive_arrears(map_products(clean(tape))))
    x = pd_pit(x, scenarios, weight_file)
    curve, life = term_structure(x)
    legs = [secured(x, collateral, haircut_overrides), unsecured(x)]
    exposure = pd.concat(legs, ignore_index=True).merge(life, on="ACCOUNT_ID", how="left")
    exposure = apply_overlay(stage(exposure))
    result = calculate(exposure, discount(curve))
    out = aggregate(result)
    write_outputs(out, root, period)
    return out, result
