#!/bin/sh
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
exec env ECL_JOB_PROG="$0" PYTHONPATH="$ROOT/python${PYTHONPATH:+:$PYTHONPATH}" python3 -m ecl.job "$@"
