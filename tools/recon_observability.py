import argparse
import json
from pathlib import Path

from ecl.arrears import derive_arrears
from ecl.clean import clean
from ecl.engine import run
from ecl.io import load_period
from ecl.product import map_products
from ecl.recon_observability import recon_observability


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="202409")
    parser.add_argument("--env", default=None)
    args = parser.parse_args()
    output = ROOT / "data/output/observability" / f"recon_observability_{args.period}.json"
    try:
        tape, _, _ = load_period(ROOT, args.period)
        arrears = derive_arrears(map_products(clean(tape)))
        _, account = run(args.period, ROOT, write=False)
        artifact = recon_observability(arrears, account, env=args.env)
    except Exception as exc:
        artifact = {
            "status": "not_evaluable",
            "reason": str(exc),
            "control_1": None,
            "control_2": None,
            "control_3": {
                "status": "not_evaluable",
                "reason": "Observability inputs could not be loaded.",
            },
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"period": args.period, **artifact}, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
