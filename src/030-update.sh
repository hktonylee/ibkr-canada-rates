#!/usr/bin/env bash

set -e

SCRIPT_ROOT="$( cd "$( dirname -- "${BASH_SOURCE:-$0}" )" && pwd )"

TODAY="$(TZ=US/Eastern date '+%Y/%m/%d')"
DATA_DIR="$SCRIPT_ROOT/../data/$TODAY"

basic_check() {
    local DATA_FILE="$1"
    if [ ! -f "$DATA_FILE" ]; then
        echo "Error: Data file not found: $DATA_FILE"
        exit 1
    fi
    if [ ! -s "$DATA_FILE" ]; then
        echo "Error: Data file is empty: $DATA_FILE"
        exit 1
    fi

    if (( $(cat "$DATA_FILE" | wc -l) < 20 )); then
        echo "Error: Data file has less than 20 rows: $DATA_FILE"
        exit 1
    fi

    if (( $(head -1 "$DATA_FILE") != "Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff" )); then
        echo "Error: Data file has incorrect header: $DATA_FILE"
        exit 1
    fi

    if ! grep ",USD," "$DATA_FILE" 2>&1 >/dev/null; then
        echo "Error: Data file does not contain USD: $DATA_FILE"
        exit 1
    fi
}

update_interest_rates() {
    local DATA_FILE="$DATA_DIR/ibkr-canada-interest-rates.csv"

    "$SCRIPT_ROOT/010-fetch-data.sh" interest-rates \
        | "$SCRIPT_ROOT/020-parse-interest-rates.sh" \
        > "$DATA_FILE"

    basic_check "$DATA_FILE"
}

update_margin_rates() {
    local DATA_FILE="$DATA_DIR/ibkr-canada-margin-rates.csv"

    "$SCRIPT_ROOT/010-fetch-data.sh" margin-rates \
        | "$SCRIPT_ROOT/021-parse-margin-rates.sh" \
        > "$DATA_FILE"

    basic_check "$DATA_FILE"
}

mkdir -p "$DATA_DIR"
update_interest_rates
update_margin_rates
