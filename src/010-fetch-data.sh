#!/usr/bin/env bash

if [ "$1" == "interest-rates" ]; then
    curl -sL https://www.interactivebrokers.ca/en/accounts/fees/pricing-interest-rates.php
elif [ "$1" == "margin-rates" ]; then
    curl -sL https://www.interactivebrokers.ca/en/trading/margin-rates.php
else
    echo "Invalid argument"
    exit 1
fi
