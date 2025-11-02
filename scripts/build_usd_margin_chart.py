#!/usr/bin/env python3
"""Generate an SVG line chart for a specific margin rate history."""

from __future__ import annotations

import argparse
from pathlib import Path

from rate_chart_utils import (
    build_svg,
    currency_amount,
    infer_second_tier_lower_bound,
    load_rate_history,
    write_svg,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing the scraped CSV snapshots (default: data)",
    )
    parser.add_argument(
        "--currency",
        default="USD",
        help="Currency code to chart (default: USD)",
    )
    parser.add_argument(
        "--tier-lower-bound",
        default="100000",
        help="Tier lower bound to chart (default: 100000 for USD)",
    )
    parser.add_argument(
        "--infer-second-tier",
        action="store_true",
        help="Infer the second tier automatically for the requested currency.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/usd-margin-100k.svg"),
        help="Path to the SVG that will be written (default: assets/usd-margin-100k.svg)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tier_lower_bound = args.tier_lower_bound
    if args.infer_second_tier:
        tier_lower_bound = infer_second_tier_lower_bound(
            args.data_dir,
            csv_name="ibkr-canada-margin-rates.csv",
            currency=args.currency,
        )

    records = load_rate_history(
        args.data_dir,
        csv_name="ibkr-canada-margin-rates.csv",
        currency=args.currency,
        tier_lower_bound=tier_lower_bound,
    )
    tier_label = currency_amount(args.currency, tier_lower_bound)
    svg = build_svg(
        records,
        title=f"Historical {args.currency} Margin Rate (Tier ≥ {tier_label})",
        y_axis_label="Annual Margin Rate (%)",
    )
    write_svg(svg, args.output)


if __name__ == "__main__":  # pragma: no cover
    main()
