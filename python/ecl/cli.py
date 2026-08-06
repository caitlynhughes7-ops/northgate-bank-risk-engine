import argparse
from .engine import run

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    parser.add_argument("--env", default=None)
    args = parser.parse_args()
    run(args.period, env=args.env)

if __name__ == "__main__":
    main()
