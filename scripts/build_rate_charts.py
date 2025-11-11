#!/usr/bin/env python3
"""Generate SVG line charts for IBKR Canada margin and interest rate histories."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Literal, Sequence, Tuple


RateRecord = Tuple[dt.date, float]
Dataset = Literal["margin", "interest"]


@dataclass(frozen=True)
class ChartDefinition:
    """Configuration describing an individual chart to render."""

    slug: str
    dataset: Dataset
    currency: str
    tier_lower_bound: str | None
    tier_upper_bound: str | None
    title_suffix: str
    tier_display: str
    alt_text: str
    y_axis_label: str
    source_label: str
    group_heading: str
    lookback_days: int = 31
    color: str = "#1f77b4"

    @property
    def filename(self) -> str:
        return f"{self.slug}.svg"


CHART_DEFINITIONS: tuple[ChartDefinition, ...] = (
    ChartDefinition(
        slug="usd-margin-100000",
        dataset="margin",
        currency="USD",
        tier_lower_bound="100000",
        tier_upper_bound="1000000",
        title_suffix="Margin Rate",
        tier_display="$100,000 borrowed",
        alt_text="Historical USD margin rate for $100,000 borrowed",
        y_axis_label="Annual Margin Rate (%)",
        source_label="IBKR Canada margin rate snapshots",
        group_heading="Margin rates",
    ),
    ChartDefinition(
        slug="usd-interest-10000",
        dataset="interest",
        currency="USD",
        tier_lower_bound="10000",
        tier_upper_bound=None,
        title_suffix="Interest Rate",
        tier_display="balances ≥ $10,000",
        alt_text="Historical USD interest rate for balances ≥ $10,000",
        y_axis_label="Annual Interest Rate (%)",
        source_label="IBKR Canada interest rate snapshots",
        group_heading="Interest rates",
        color="#d62728",
    ),
    ChartDefinition(
        slug="cad-margin-130000",
        dataset="margin",
        currency="CAD",
        tier_lower_bound="130000",
        tier_upper_bound="1300000",
        title_suffix="Margin Rate",
        tier_display="C$130,000 borrowed",
        alt_text="Historical CAD margin rate for C$130,000 borrowed",
        y_axis_label="Annual Margin Rate (%)",
        source_label="IBKR Canada margin rate snapshots",
        group_heading="Margin rates",
        color="#ff7f0e",
    ),
    ChartDefinition(
        slug="jpy-margin-11000000",
        dataset="margin",
        currency="JPY",
        tier_lower_bound="11000000",
        tier_upper_bound="114000000",
        title_suffix="Margin Rate",
        tier_display="¥11,000,000 borrowed",
        alt_text="Historical JPY margin rate for ¥11,000,000 borrowed",
        y_axis_label="Annual Margin Rate (%)",
        source_label="IBKR Canada margin rate snapshots",
        group_heading="Margin rates",
        color="#9467bd",
    ),
    ChartDefinition(
        slug="cad-interest-13000",
        dataset="interest",
        currency="CAD",
        tier_lower_bound="13000",
        tier_upper_bound=None,
        title_suffix="Interest Rate",
        tier_display="balances ≥ C$13,000",
        alt_text="Historical CAD interest rate for balances ≥ C$13,000",
        y_axis_label="Annual Interest Rate (%)",
        source_label="IBKR Canada interest rate snapshots",
        group_heading="Interest rates",
        color="#2ca02c",
    ),
    ChartDefinition(
        slug="jpy-interest-5000000",
        dataset="interest",
        currency="JPY",
        tier_lower_bound="5000000",
        tier_upper_bound=None,
        title_suffix="Interest Rate",
        tier_display="balances ≥ ¥5,000,000",
        alt_text="Historical JPY interest rate for balances ≥ ¥5,000,000",
        y_axis_label="Annual Interest Rate (%)",
        source_label="IBKR Canada interest rate snapshots",
        group_heading="Interest rates",
        color="#17becf",
    ),
)


def load_rate_history(
    data_dir: Path,
    dataset: Dataset,
    *,
    currency: str,
    tier_lower_bound: str | None = None,
    tier_upper_bound: str | None = None,
    lookback_days: int = 31,
) -> List[RateRecord]:
    """Return a rate history for the requested dataset, currency, and tier."""

    if dataset == "margin":
        filename = "ibkr-canada-margin-rates.csv"
    elif dataset == "interest":
        filename = "ibkr-canada-interest-rates.csv"
    else:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported dataset: {dataset}")

    records_by_date: dict[dt.date, RateRecord] = {}

    for csv_path in sorted(data_dir.rglob(filename)):
        try:
            day = int(csv_path.parent.name)
            month = int(csv_path.parents[1].name)
            year = int(csv_path.parents[2].name)
        except (ValueError, IndexError):  # pragma: no cover - unexpected layout
            continue

        snapshot_date = dt.date(year, month, day)

        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # header row
            for _row_date, row_currency, lower, upper, rate, _diff in reader:
                if row_currency != currency:
                    continue
                if tier_lower_bound is not None and lower != tier_lower_bound:
                    continue
                if tier_upper_bound is not None and upper != tier_upper_bound:
                    continue

                rate = rate.strip()
                if not rate:
                    continue

                try:
                    rate_value = float(rate)
                except ValueError:  # pragma: no cover - unexpected value
                    continue

                records_by_date[snapshot_date] = (snapshot_date, rate_value)
                break

    records = list(records_by_date.values())
    records.sort()

    if records and lookback_days is not None:
        latest_date = records[-1][0]
        cutoff_date = latest_date - dt.timedelta(days=lookback_days)
        records = [record for record in records if record[0] >= cutoff_date]

    return records


def _scale(value: float, *, domain: Tuple[float, float], range_: Tuple[float, float]) -> float:
    start, end = domain
    out_start, out_end = range_
    span = end - start or 1.0
    return out_start + ((value - start) / span) * (out_end - out_start)


def build_svg(
    records: Sequence[RateRecord],
    *,
    title: str,
    y_axis_label: str,
    line_color: str,
    source_label: str,
    width: int = 900,
    height: int = 460,
) -> str:
    if not records:
        raise ValueError("No records provided")

    rates = [record[1] for record in records]
    min_rate, max_rate = min(rates), max(rates)
    if min_rate == max_rate:
        # Expand the range slightly so the line and points are visible.
        min_rate -= 0.01
        max_rate += 0.01

    margin_left, margin_right, margin_top, margin_bottom = 90, 40, 50, 160
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
    label_y = height - margin_bottom + 48

    for date in unique_dates:
        x = scale_x(date)
        rotate_anchor = f"{x:.2f} {label_y:.2f}"
        x_ticks.append(
            "".join(
                [
                    f"<line x1='{x:.2f}' y1='{height-margin_bottom}' x2='{x:.2f}' y2='{height-margin_bottom+6}' stroke='#333' stroke-width='1' />",
                    (
                        "<text x='{x:.2f}' y='{label_y:.2f}' font-size='12' "
                        "text-anchor='end' dominant-baseline='middle' fill='#333' "
                        "transform='rotate(-90 {rotate_anchor})'>{date}</text>"
                    ).format(
                        x=x,
                        label_y=label_y,
                        rotate_anchor=rotate_anchor,
                        date=date.isoformat(),
                    ),
                    f"<line x1='{x:.2f}' y1='{margin_top}' x2='{x:.2f}' y2='{height-margin_bottom}' stroke='#eeeeee' stroke-width='0.5' />",
                ]
            )
        )

    circles = [
        f"<circle cx='{scale_x(date):.2f}' cy='{scale_y(rate):.2f}' r='3' fill='{line_color}' />"
        for date, rate in records
    ]

    generated_on = dt.date.today().isoformat()

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}'>
    <style>
        text {{ font-family: 'DejaVu Sans', Arial, sans-serif; }}
    </style>
    <rect x='0' y='0' width='{width}' height='{height}' fill='white'/>
    <text x='{width/2}' y='{margin_top-20}' text-anchor='middle' font-size='20' fill='#111'>{title}</text>
    <text x='{width/2}' y='{height-margin_bottom+120}' text-anchor='middle' font-size='14' fill='#333'>Date</text>
    <text x='{margin_left-60}' y='{height/2}' text-anchor='middle' font-size='14' fill='#333' transform='rotate(-90 {margin_left-60} {height/2})'>{y_axis_label}</text>
    <text x='{width/2}' y='{height-20}' text-anchor='middle' font-size='12' fill='#555'>Data source: {source_label} • Generated on {generated_on}</text>
    {''.join(axis_lines)}
    <polyline fill='none' stroke='{line_color}' stroke-width='2' points='{" ".join(points)}' />
    {''.join(circles)}
    {''.join(y_ticks)}
    {''.join(x_ticks)}
</svg>"""
    return svg


def build_chart_svg(definition: ChartDefinition, records: Sequence[RateRecord]) -> str:
    """Build a chart SVG for the provided definition and rate series."""

    if not records:
        raise ValueError("No records provided")

    start_date = records[0][0].isoformat()
    end_date = records[-1][0].isoformat()
    title = (
        f"Historical {definition.currency} {definition.title_suffix} "
        f"({definition.tier_display}, {start_date} - {end_date})"
    )

    svg = build_svg(
        records,
        title=title,
        y_axis_label=definition.y_axis_label,
        line_color=definition.color,
        source_label=definition.source_label,
    )

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
        "--output-dir",
        type=Path,
        default=Path("assets"),
        help=(
            "Directory where the charts will be stored "
            "(default: assets/<date>/<chart>.svg)"
        ),
    )
    parser.add_argument(
        "--only",
        metavar="SLUG",
        nargs="*",
        choices=[definition.slug for definition in CHART_DEFINITIONS],
        help="Optionally limit generation to the listed chart slugs",
    )
    return parser.parse_args()


def iter_selected_definitions(only: Iterable[str] | None) -> Iterable[ChartDefinition]:
    if not only:
        yield from CHART_DEFINITIONS
        return

    selected = set(only)
    for definition in CHART_DEFINITIONS:
        if definition.slug in selected:
            yield definition


def main() -> None:
    args = parse_args()

    for definition in iter_selected_definitions(args.only):
        records = load_rate_history(
            args.data_dir,
            definition.dataset,
            currency=definition.currency,
            tier_lower_bound=definition.tier_lower_bound,
            tier_upper_bound=definition.tier_upper_bound,
            lookback_days=definition.lookback_days,
        )

        if not records:
            raise SystemExit(
                f"No records found for {definition.currency} {definition.dataset} tier"
            )

        svg = build_chart_svg(definition, records)

        latest_date = records[-1][0]
        output_path = (
            args.output_dir
            / latest_date.isoformat()
            / definition.filename
        )
        write_svg(svg, output_path)


if __name__ == "__main__":  # pragma: no cover
    main()
