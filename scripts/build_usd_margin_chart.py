#!/usr/bin/env python3
"""Generate an SVG line chart for the USD 100k margin rate history."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from pathlib import Path
from typing import List, Sequence, Tuple


RateRecord = Tuple[dt.date, float]


def load_usd_margin_history(data_dir: Path, tier_lower_bound: str = "100000") -> List[RateRecord]:
    """Return the USD margin rate history for the requested tier."""

    records_by_date: dict[dt.date, RateRecord] = {}
    for csv_path in sorted(data_dir.rglob("ibkr-canada-margin-rates.csv")):
        day = int(csv_path.parent.name)
        month = int(csv_path.parents[1].name)
        year = int(csv_path.parents[2].name)
        snapshot_date = dt.date(year, month, day)

        with csv_path.open(newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # header row
            for row_date, currency, lower, upper, rate, _discount in reader:
                if currency == "USD" and lower == tier_lower_bound:
                    records_by_date[snapshot_date] = (snapshot_date, float(rate))
                    break

    records = list(records_by_date.values())
    records.sort()

    if records:
        latest_date = records[-1][0]
        cutoff_date = latest_date - dt.timedelta(days=31)
        records = [record for record in records if record[0] >= cutoff_date]

    return records


def _scale(value: float, *, domain: Tuple[float, float], range_: Tuple[float, float]) -> float:
    start, end = domain
    out_start, out_end = range_
    span = end - start or 1.0
    return out_start + ((value - start) / span) * (out_end - out_start)


def build_svg(records: Sequence[RateRecord], *, width: int = 900, height: int = 460) -> str:
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

    unique_dates = sorted({date for date, _rate in records})
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
        y_ticks.append(
            "".join(
                [
                    f"<line x1='{margin_left-6}' y1='{y:.2f}' x2='{margin_left}' y2='{y:.2f}' stroke='#333' stroke-width='1' />",
                    f"<text x='{margin_left-10}' y='{y+4:.2f}' font-size='12' text-anchor='end' fill='#333'>{value:.2f}%</text>",
                    f"<line x1='{margin_left}' y1='{y:.2f}' x2='{width-margin_right}' y2='{y:.2f}' stroke='#d0d0d0' stroke-width='0.5' stroke-dasharray='4 4' />",
                ]
            )
        )

    x_ticks: List[str] = []
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

    circles = [f"<circle cx='{scale_x(date):.2f}' cy='{scale_y(rate):.2f}' r='3' fill='#1f77b4' />" for date, rate in records]

    generated_on = dt.date.today().isoformat()

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}'>
    <style>
        text {{ font-family: 'DejaVu Sans', Arial, sans-serif; }}
    </style>
    <rect x='0' y='0' width='{width}' height='{height}' fill='white'/>
    <text x='{width/2}' y='{margin_top-20}' text-anchor='middle' font-size='20' fill='#111'>Historical USD Margin Rate for $100,000 Borrowed</text>
    {''.join(axis_lines)}
    <polyline fill='none' stroke='#1f77b4' stroke-width='2' points='{" ".join(points)}' />
    {''.join(circles)}
    {''.join(y_ticks)}
    {''.join(x_ticks)}
    <text x='{width/2}' y='{height-margin_bottom+50}' text-anchor='middle' font-size='14' fill='#333'>Date</text>
    <text x='{margin_left-60}' y='{height/2}' text-anchor='middle' font-size='14' fill='#333' transform='rotate(-90 {margin_left-60} {height/2})'>Annual Margin Rate (%)</text>
    <text x='{width/2}' y='{height-20}' text-anchor='middle' font-size='12' fill='#555'>Data source: IBKR Canada margin rate snapshots • Generated on {generated_on}</text>
</svg>"""
    return svg


def write_svg(svg: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing the scraped CSV snapshots (default: data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Path to the SVG that will be written (default: assets/<date>/"
            "usd-margin-100000.svg)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_usd_margin_history(args.data_dir)
    svg = build_svg(records)

    if args.output is not None:
        output_path = args.output
    else:
        latest_date = records[-1][0]
        output_path = Path("assets") / latest_date.isoformat() / "usd-margin-100000.svg"

    write_svg(svg, output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
