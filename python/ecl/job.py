"""Control-M-compatible orchestration for the monthly ECL engine."""

from __future__ import annotations

import csv
import os
import re
import sys
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, Sequence

from . import engine
from .environment import bootstrap, resolve_env

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "config" / "rules" / "job_orchestration.csv"


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    try:
        path = path.resolve()
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


def _rules() -> dict[str, str]:
    with RULES_PATH.open(newline="") as stream:
        return {
            row["KEY"]: row["VALUE"]
            for row in csv.DictReader(
                line for line in stream if not line.startswith("#")
            )
        }


def _paths(period: str, env: str, rules: dict[str, str]) -> tuple[Path, Path]:
    basename = rules["log_filename_template"].format(period=period, env=env)
    listing_basename = rules["listing_filename_template"].format(
        period=period, env=env
    )
    work_dir = ROOT / rules["working_dir"]
    log = work_dir / rules["log_dir"] / f"{basename}{rules['log_suffix']}"
    listing = (
        work_dir
        / rules["log_dir"]
        / f"{listing_basename}{rules['listing_suffix']}"
    )
    return log, listing


def count_log_errors(log_path: Path, pattern: str) -> int | None:
    """Count line-start errors, returning None when grep would fail to read."""
    try:
        with log_path.open() as stream:
            return sum(bool(re.match(pattern, line)) for line in stream)
    except FileNotFoundError:
        return None


def run(
    period: str,
    env: str,
    *,
    run_engine: Callable[..., object] | None = None,
    stdout: object = sys.stdout,
    stderr: object = sys.stderr,
) -> int:
    """Run the configured engine and preserve the legacy shell signalling."""
    rules = _rules()
    log_path, _listing_path = _paths(period, env, rules)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.open("w").close()
    sysparm = rules["sysparm_template"].format(period=period, env=env)
    try:
        work_dir = ROOT / rules["working_dir"]
        with _working_directory(work_dir):
            with log_path.open("a") as log_stream:
                with redirect_stdout(log_stream), redirect_stderr(log_stream):
                    with bootstrap(sysparm, ROOT):
                        (run_engine or engine.run)(period, root=ROOT)
    except Exception:
        with log_path.open("a") as log_stream:
            traceback.print_exc(file=log_stream)
        return int(rules["exit_error"])

    count = count_log_errors(log_path, rules["error_pattern"])
    if count is None:
        missing_path = Path(os.path.relpath(log_path, ROOT / rules["working_dir"]))
        print(f"grep: {missing_path}: No such file or directory", file=stderr)
    else:
        print(count, file=stdout)
    if count is not None and count > 0:
        print(rules["error_template"], file=stderr)
        return int(rules["exit_error"])
    print(rules["success_template"].format(period=period, env=env), file=stdout)
    return int(rules["exit_success"])


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    rules = _rules()
    if len(args) < 2 or not args[1]:
        print(
            rules["usage_template"].format(
                prog=os.environ.get("ECL_JOB_PROG", args[0] if args else "")
            ),
            file=sys.stderr,
        )
        return int(rules["exit_missing_args"])
    period = args[1]
    env = args[2] if len(args) > 2 else ""
    return run(period, resolve_env(env))


if __name__ == "__main__":
    raise SystemExit(main())
