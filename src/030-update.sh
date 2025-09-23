#!/usr/bin/env bash

SCRIPT_ROOT="$( cd "$( dirname -- "${BASH_SOURCE:-$0}" )" && pwd )"

TODAY="$(TZ=US/Eastern date '+%Y/%m/%d/')"
DATA_DIR="$SCRIPT_ROOT/../data/$TODAY"

update_interest_rates() {
    "$SCRIPT_ROOT/010-fetch-data.sh" interest-rates \
        | "$SCRIPT_ROOT/020-parse-interest-rates.sh" \
        >> "$DATA_DIR/ibkr-canada-interest-rates.csv"
}

update_margin_rates() {
    "$SCRIPT_ROOT/010-fetch-data.sh" margin-rates \
        | "$SCRIPT_ROOT/021-parse-margin-rates.sh" \
        >> "$DATA_DIR/ibkr-canada-margin-rates.csv"
}

mkdir -p "$DATA_DIR"
update_interest_rates
update_margin_rates
