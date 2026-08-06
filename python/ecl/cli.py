import argparse
from .engine import run_month_end

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    args = parser.parse_args()
    run_month_end(args.period)

if __name__ == "__main__":
    main()
