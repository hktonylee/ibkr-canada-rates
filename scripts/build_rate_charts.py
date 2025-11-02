#!/usr/bin/env python3
"""Generate SVG charts for all supported margin and interest currencies."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from rate_chart_utils import (
    build_svg,
    currency_amount,
    infer_second_tier_lower_bound,
    load_rate_history,
    write_svg,
)


MARGIN_CSV = "ibkr-canada-margin-rates.csv"
INTEREST_CSV = "ibkr-canada-interest-rates.csv"


def _discover_currencies(data_dir: Path, csv_name: str) -> list[str]:
    currencies: set[str] = set()
    for csv_path in sorted(data_dir.rglob(csv_name)):
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                if len(row) < 2:
                    continue
                currency = row[1].strip()
                if currency:
                    currencies.add(currency)
    return sorted(currencies)


def _currency_slug(currency: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", currency).strip("-")
    return slug.lower() or "unknown"


def _series_output_path(output_dir: Path, prefix: str, currency: str, tier: str) -> Path:
    safe_tier = tier.replace(".", "-")
    slug = _currency_slug(currency)
    return output_dir / f"{prefix}-{slug}-{safe_tier}.svg"


def build_margin_series(data_dir: Path, output_dir: Path) -> list[Path]:
    created: list[Path] = []
    for currency in _discover_currencies(data_dir, MARGIN_CSV):
        tier = infer_second_tier_lower_bound(
            data_dir, csv_name=MARGIN_CSV, currency=currency
        )
        records = load_rate_history(
            data_dir,
            csv_name=MARGIN_CSV,
            currency=currency,
            tier_lower_bound=tier,
        )
        if not records:
            continue
        label = currency_amount(currency, tier)
        svg = build_svg(
            records,
            title=f"Historical {currency} Margin Rate (Tier ≥ {label})",
            y_axis_label="Annual Margin Rate (%)",
        )
        output_path = _series_output_path(output_dir, "margin", currency, tier)
        write_svg(svg, output_path)
        created.append(output_path)
    return created


def build_interest_series(data_dir: Path, output_dir: Path) -> list[Path]:
    created: list[Path] = []
    for currency in _discover_currencies(data_dir, INTEREST_CSV):
        tier = infer_second_tier_lower_bound(
            data_dir, csv_name=INTEREST_CSV, currency=currency
        )
        records = load_rate_history(
            data_dir,
            csv_name=INTEREST_CSV,
            currency=currency,
            tier_lower_bound=tier,
        )
        if not records:
            continue
        label = currency_amount(currency, tier)
        svg = build_svg(
            records,
            title=f"Historical {currency} Interest Rate (Tier ≥ {label})",
            y_axis_label="Annual Interest Rate (%)",
            line_colour="#d62728",
        )
        output_path = _series_output_path(output_dir, "interest", currency, tier)
        write_svg(svg, output_path)
        created.append(output_path)
    return created


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
        help="Directory that will receive the generated SVG files (default: assets)",
    )
    parser.add_argument(
        "--skip-margin",
        action="store_true",
        help="Skip generating margin rate charts.",
    )
    parser.add_argument(
        "--skip-interest",
        action="store_true",
        help="Skip generating interest rate charts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generated_paths: list[Path] = []
    if not args.skip_margin:
        generated_paths.extend(build_margin_series(args.data_dir, args.output_dir))
    if not args.skip_interest:
        generated_paths.extend(build_interest_series(args.data_dir, args.output_dir))

    for path in generated_paths:
        print(path.as_posix())


if __name__ == "__main__":  # pragma: no cover
    main()

