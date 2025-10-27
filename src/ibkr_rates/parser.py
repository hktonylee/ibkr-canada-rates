"""Parsing utilities for IBKR Canada interest and margin rate tables."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Iterable, List, Optional, Sequence, Tuple
import html
import re

try:  # Python 3.9+
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo  # type: ignore
    from backports.zoneinfo import ZoneInfoNotFoundError  # type: ignore


def _load_default_timezone() -> timezone:
    try:
        return ZoneInfo("US/Eastern")  # type: ignore[return-value]
    except ZoneInfoNotFoundError:  # pragma: no cover - fallback when tzdata unavailable
        return timezone(timedelta(hours=-5))


DEFAULT_TZ = _load_default_timezone()
CSV_HEADER = "Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff"


@dataclass(frozen=True)
class RateRow:
    """A single row in the exported CSV file."""

    date: str
    currency: str
    tier_low: str
    tier_high: str
    rate: str
    benchmark_diff: str

    def to_csv_row(self) -> str:
        return ",".join(
            [
                self.date,
                self.currency,
                self.tier_low,
                self.tier_high,
                self.rate,
                self.benchmark_diff,
            ]
        )


def _current_date_string(as_of: Optional[date]) -> str:
    if as_of is not None:
        return as_of.strftime("%Y-%m-%d")
    eastern_now = datetime.now(tz=DEFAULT_TZ)
    return eastern_now.strftime("%Y-%m-%d")


def _extract_table_after_heading(html_text: str, heading: str) -> str:
    pattern = re.compile(re.escape(heading), re.IGNORECASE)
    match = pattern.search(html_text)
    if not match:
        raise ValueError(f"Heading '{heading}' not found in supplied HTML")
    table_pattern = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)
    table_match = table_pattern.search(html_text, pos=match.end())
    if not table_match:
        raise ValueError(f"No table found after heading '{heading}'")
    return table_match.group(0)


def _iter_rows(table_html: str) -> Iterable[List[str]]:
    tbody_match = re.search(r"<tbody[^>]*>(.*?)</tbody>", table_html, re.IGNORECASE | re.DOTALL)
    if not tbody_match:
        raise ValueError("Table does not contain a <tbody> section")
    tbody = tbody_match.group(1)
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
    cell_pattern = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
    for row_match in row_pattern.finditer(tbody):
        row_html = row_match.group(1)
        cells = [
            _clean_cell(cell_html)
            for cell_html in cell_pattern.findall(row_html)
        ]
        if cells:
            yield cells


def _clean_cell(cell_html: str) -> str:
    text = re.sub(r"<[^>]+>", "", cell_html)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_rate(rate_text: str) -> str:
    match = re.search(r"-?[0-9]+(?:\.[0-9]+)?%?", rate_text)
    if not match:
        return ""
    return match.group(0).replace("%", "")


def _parse_benchmark_diff(rate_text: str, *, invert: bool) -> str:
    match = re.search(r"BM\s*([+-])\s*([0-9]+(?:\.[0-9]+)?)%", rate_text, re.IGNORECASE)
    if not match:
        return "0"
    sign, value = match.groups()
    if invert:
        if sign == "-":
            return f"-{value}"
        elif sign == "+":
            return value
    return value


def _parse_tier_bounds(tier_text: str) -> Tuple[str, str]:
    normalized = tier_text.strip()
    if not normalized:
        return "", ""
    if normalized.lower() == "all":
        return "", ""
    numbers = [re.sub(r",", "", n) for n in re.findall(r"[0-9][0-9,\.]*", normalized)]
    if ">" in normalized:
        return (numbers[0] if numbers else "", "")
    if any(symbol in normalized for symbol in ["≤", "<=", "-"]):
        if len(numbers) >= 2:
            return numbers[0], numbers[1]
        if len(numbers) == 1:
            return "0", numbers[0]
    if numbers:
        return numbers[0], ""
    return "", ""


def _rows_from_cells(
    cells_iter: Iterable[List[str]],
    *,
    date_string: str,
    benchmark_invert: bool,
) -> List[RateRow]:
    rows: List[RateRow] = []
    last_currency = ""
    for cells in cells_iter:
        if len(cells) < 3:
            continue
        currency, tier_text, rate_text = cells[0], cells[1], cells[2]
        if not currency:
            currency = last_currency
        else:
            last_currency = currency
        rate = _parse_rate(rate_text)
        tier_low, tier_high = _parse_tier_bounds(tier_text)
        if not (currency and tier_text and rate):
            continue
        bm_diff = _parse_benchmark_diff(rate_text, invert=benchmark_invert)
        rows.append(
            RateRow(
                date=date_string,
                currency=currency,
                tier_low=tier_low,
                tier_high=tier_high,
                rate=rate,
                benchmark_diff=bm_diff,
            )
        )
    return rows


def parse_interest_rates(html_text: str, *, as_of: Optional[date] = None) -> List[RateRow]:
    table_html = _extract_table_after_heading(html_text, "Global Interest Rates")
    date_string = _current_date_string(as_of)
    cells_iter = _iter_rows(table_html)
    return _rows_from_cells(cells_iter, date_string=date_string, benchmark_invert=True)


def parse_margin_rates(html_text: str, *, as_of: Optional[date] = None) -> List[RateRow]:
    table_html = _extract_table_after_heading(html_text, "Interest Charged on Margin Loans")
    date_string = _current_date_string(as_of)
    cells_iter = _iter_rows(table_html)
    return _rows_from_cells(cells_iter, date_string=date_string, benchmark_invert=False)


def rows_to_csv(rows: Sequence[RateRow]) -> str:
    csv_lines = [CSV_HEADER]
    csv_lines.extend(row.to_csv_row() for row in rows)
    return "\n".join(csv_lines) + "\n"
