import argparse
from .engine import run

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    args = parser.parse_args()
    run(args.period)

if __name__ == "__main__":
    main()
