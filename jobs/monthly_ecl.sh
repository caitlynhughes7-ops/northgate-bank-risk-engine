#!/bin/sh
# Monthly IFRS 9 ECL run. Called by Control-M job GCRA_ECL_MONTHLY.
# Usage: ./jobs/monthly_ecl.sh <YYYYMM> <env>
set -e

PERIOD=$1
ENVN=${2:-uat}

if [ -z "$PERIOD" ]; then
  echo "usage: $0 <YYYYMM> [prod|uat]" >&2
  exit 2
fi

cd "$(dirname "$0")/../sas"

SASEXE=${SASEXE:-/opt/sas94/SASFoundation/9.4/sas}

$SASEXE -sysin driver/run_month_end.sas \
        -sysparm "$PERIOD $ENVN" \
        -log "../logs/ecl_${PERIOD}_${ENVN}.log" \
        -print "../logs/ecl_${PERIOD}_${ENVN}.lst"

grep -c '^ERROR' "../logs/ecl_${PERIOD}_${ENVN}.log" && {
  echo "ECL run reported errors, see log" >&2
  exit 1
}

echo "ECL run complete for $PERIOD ($ENVN)"
