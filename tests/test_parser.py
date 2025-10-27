from __future__ import annotations

from datetime import date
from pathlib import Path

from ibkr_rates.parser import CSV_HEADER, RateRow, parse_interest_rates, parse_margin_rates, rows_to_csv


FIXTURE_DIR = Path(__file__).parent


def _load_html(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_interest_rates_extracts_rows():
    html = _load_html("interest-rates.html")
    rows = parse_interest_rates(html, as_of=date(2024, 1, 1))

    assert len(rows) >= 20
    assert rows[0] == RateRow(
        date="2024-01-01",
        currency="USD",
        tier_low="0",
        tier_high="10000",
        rate="0",
        benchmark_diff="0",
    )
    assert rows[1] == RateRow(
        date="2024-01-01",
        currency="USD",
        tier_low="10000",
        tier_high="",
        rate="3.580",
        benchmark_diff="-0.5",
    )
    assert any(row.currency == "CHF" and row.rate == "-0.218" for row in rows)


def test_parse_margin_rates_extracts_rows():
    html = _load_html("margin-rates.html")
    rows = parse_margin_rates(html, as_of=date(2024, 1, 1))

    assert len(rows) >= 20
    assert rows[0] == RateRow(
        date="2024-01-01",
        currency="USD",
        tier_low="0",
        tier_high="100000",
        rate="5.580",
        benchmark_diff="1.5",
    )
    assert rows[1] == RateRow(
        date="2024-01-01",
        currency="USD",
        tier_low="100000",
        tier_high="1000000",
        rate="5.080",
        benchmark_diff="1",
    )


def test_rows_to_csv_outputs_header_and_data():
    rows = [
        RateRow("2024-01-01", "USD", "0", "10000", "0", "0"),
        RateRow("2024-01-01", "USD", "10000", "", "3.580", "-0.5"),
    ]
    csv_text = rows_to_csv(rows)

    lines = csv_text.strip().splitlines()
    assert lines[0] == CSV_HEADER
    assert lines[1] == "2024-01-01,USD,0,10000,0,0"
    assert lines[2] == "2024-01-01,USD,10000,,3.580,-0.5"
    assert csv_text.endswith("\n")
