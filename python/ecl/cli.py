import argparse
from .engine import run
from .util_logging import EclAbort

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    args = parser.parse_args()
    try:
        run(args.period)
    except EclAbort:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
