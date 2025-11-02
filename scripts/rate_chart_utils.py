"""Shared helpers for building historical rate charts."""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Iterable, Sequence


RateRecord = tuple[dt.date, float]


def _normalise_lower(lower: str) -> str:
    return lower or "0"


def _iter_snapshot_files(data_dir: Path, csv_name: str) -> Iterable[Path]:
    """Yield all snapshot CSV paths for the requested dataset."""

    yield from sorted(data_dir.rglob(csv_name))


def _snapshot_date_from_path(csv_path: Path) -> dt.date:
    """Infer the snapshot date from the directory layout."""

    day = int(csv_path.parent.name)
    month = int(csv_path.parents[1].name)
    year = int(csv_path.parents[2].name)
    return dt.date(year, month, day)


def load_rate_history(
    data_dir: Path,
    *,
    csv_name: str,
    currency: str,
    tier_lower_bound: str,
) -> list[RateRecord]:
    """Return historical rate values for the requested currency tier."""

    records_by_date: dict[dt.date, RateRecord] = {}
    for csv_path in _iter_snapshot_files(data_dir, csv_name):
        snapshot_date = _snapshot_date_from_path(csv_path)
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) < 5:
                    continue
                _row_date, row_currency, lower, _upper, rate, *_rest = row
                if row_currency != currency:
                    continue
                normalised_lower = _normalise_lower(lower)
                if normalised_lower == tier_lower_bound:
                    try:
                        value = float(rate)
                    except ValueError:
                        continue
                    records_by_date[snapshot_date] = (snapshot_date, value)
                    break

    records = list(records_by_date.values())
    records.sort()
    return records


def _parse_lower_bound(lower: str) -> float:
    try:
        return float(lower)
    except ValueError:
        return float("inf")


def infer_second_tier_lower_bound(
    data_dir: Path, *, csv_name: str, currency: str
) -> str:
    """Return the second-smallest lower bound for the currency tier."""

    lower_bounds: set[tuple[float, str]] = set()
    for csv_path in _iter_snapshot_files(data_dir, csv_name):
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                if len(row) < 4:
                    continue
                _row_date, row_currency, lower, *_rest = row
                if row_currency != currency:
                    continue
                normalised = _normalise_lower(lower)
                lower_bounds.add((_parse_lower_bound(normalised), normalised))

    if not lower_bounds:
        raise ValueError(
            f"No tiers found for currency {currency!r} in {csv_name!r}."
        )

    ordered = sorted(lower_bounds, key=lambda item: item[0])
    if len(ordered) >= 2:
        return ordered[1][1]
    return ordered[0][1]


def _scale(value: float, *, domain: tuple[float, float], range_: tuple[float, float]) -> float:
    start, end = domain
    out_start, out_end = range_
    span = end - start or 1.0
    return out_start + ((value - start) / span) * (out_end - out_start)


def _format_tick(value: float) -> str:
    return f"{value:.3f}" if abs(value) < 0.1 else f"{value:.2f}"


def build_svg(
    records: Sequence[RateRecord],
    *,
    width: int = 900,
    height: int = 460,
    title: str,
    y_axis_label: str,
    line_colour: str = "#1f77b4",
) -> str:
    """Render the historical series as a standalone SVG chart."""

    if not records:
        raise ValueError("No records provided")

    dates = [record[0] for record in records]
    rates = [record[1] for record in records]
    min_rate, max_rate = min(rates), max(rates)
    if min_rate == max_rate:
        min_rate -= 0.01
        max_rate += 0.01

    margin_left, margin_right, margin_top, margin_bottom = 90, 40, 50, 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    unique_dates = sorted({date for date in dates})
    date_to_index = {date: idx for idx, date in enumerate(unique_dates)}

    def scale_x(date: dt.date) -> float:
        return _scale(
            date_to_index[date],
            domain=(0.0, max(len(unique_dates) - 1, 1)),
            range_=(margin_left, margin_left + plot_width),
        )

    def scale_y(rate: float) -> float:
        return _scale(
            rate,
            domain=(min_rate, max_rate),
            range_=(height - margin_bottom, margin_top),
        )

    points = [f"{scale_x(date):.2f},{scale_y(rate):.2f}" for date, rate in records]
    axis_lines = [
        f"<line x1='{margin_left}' y1='{height-margin_bottom}' x2='{width-margin_right}' y2='{height-margin_bottom}' stroke='#333' stroke-width='1' />",
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{height-margin_bottom}' stroke='#333' stroke-width='1' />",
    ]

    y_ticks = []
    for step in range(6):
        value = min_rate + (max_rate - min_rate) * step / 5
        y = scale_y(value)
        label = _format_tick(value)
        y_ticks.append(
            "".join(
                [
                    f"<line x1='{margin_left-6}' y1='{y:.2f}' x2='{margin_left}' y2='{y:.2f}' stroke='#333' stroke-width='1' />",
                    f"<text x='{margin_left-10}' y='{y+4:.2f}' font-size='12' text-anchor='end' fill='#333'>{label}%</text>",
                    f"<line x1='{margin_left}' y1='{y:.2f}' x2='{width-margin_right}' y2='{y:.2f}' stroke='#d0d0d0' stroke-width='0.5' stroke-dasharray='4 4' />",
                ]
            )
        )

    x_ticks: list[str] = []
    for date in unique_dates:
        x = scale_x(date)
        x_ticks.append(
            "".join(
                [
                    f"<line x1='{x:.2f}' y1='{height-margin_bottom}' x2='{x:.2f}' y2='{height-margin_bottom+6}' stroke='#333' stroke-width='1' />",
                    f"<text x='{x:.2f}' y='{height-margin_bottom+24}' font-size='12' text-anchor='middle' fill='#333'>{date.isoformat()}</text>",
                    f"<line x1='{x:.2f}' y1='{margin_top}' x2='{x:.2f}' y2='{height-margin_bottom}' stroke='#eeeeee' stroke-width='0.5' />",
                ]
            )
        )

    circles = [
        f"<circle cx='{scale_x(date):.2f}' cy='{scale_y(rate):.2f}' r='3' fill='{line_colour}' />"
        for date, rate in records
    ]

    generated_on = dt.date.today().isoformat()

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}'>
    <style>
        text {{ font-family: 'DejaVu Sans', Arial, sans-serif; }}
    </style>
    <rect x='0' y='0' width='{width}' height='{height}' fill='white'/>
    <text x='{width/2}' y='{margin_top-20}' text-anchor='middle' font-size='20' fill='#111'>{title}</text>
    {''.join(axis_lines)}
    <polyline fill='none' stroke='{line_colour}' stroke-width='2' points='{" ".join(points)}' />
    {''.join(circles)}
    {''.join(y_ticks)}
    {''.join(x_ticks)}
    <text x='{width/2}' y='{height-margin_bottom+50}' text-anchor='middle' font-size='14' fill='#333'>Date</text>
    <text x='{margin_left-60}' y='{height/2}' text-anchor='middle' font-size='14' fill='#333' transform='rotate(-90 {margin_left-60} {height/2})'>{y_axis_label}</text>
    <text x='{width/2}' y='{height-20}' text-anchor='middle' font-size='12' fill='#555'>Data source: IBKR Canada snapshots • Generated on {generated_on}</text>
</svg>"""
    return svg


def write_svg(svg: str, output_path: Path) -> None:
    """Persist the rendered SVG to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")


def currency_amount(currency: str, lower_bound: str) -> str:
    """Pretty-print the tier lower bound for labelling charts."""

    try:
        value = int(float(lower_bound))
    except ValueError:
        return f"{currency} {lower_bound}"
    formatted = f"{value:,}"
    return f"{currency} {formatted}"

