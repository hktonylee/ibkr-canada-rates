"""Utilities for downloading and parsing IBKR Canada rate tables."""

from .parser import RateRow, parse_interest_rates, parse_margin_rates, rows_to_csv
from .update import run_update

__all__ = [
    "RateRow",
    "parse_interest_rates",
    "parse_margin_rates",
    "rows_to_csv",
    "run_update",
]
