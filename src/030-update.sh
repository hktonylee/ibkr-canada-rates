#!/usr/bin/env bash

SCRIPT_ROOT="$( cd "$( dirname -- "${BASH_SOURCE:-$0}" )" && pwd )"


update_interest_rates() {
    "$SCRIPT_ROOT/010-fetch-data.sh" interest-rates \
        | "$SCRIPT_ROOT/020-parse-interest-rates.sh" \
        | sed '1d' >> "$SCRIPT_ROOT/../ibkr-canada-interest-rates.csv"
}

update_margin_rates() {
    "$SCRIPT_ROOT/010-fetch-data.sh" margin-rates \
        | "$SCRIPT_ROOT/021-parse-margin-rates.sh" \
        | sed '1d' >> "$SCRIPT_ROOT/../ibkr-canada-margin-rates.csv"
}

update_interest_rates
update_margin_rates
