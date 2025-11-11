#!/usr/bin/env python3
"""Render README.md from README.md.jinja using the latest dataset."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import date
from pathlib import Path

from build_rate_charts import CHART_DEFINITIONS, ChartDefinition, load_rate_history

try:  # pragma: no cover - dependency injection path
    from jinja2 import Environment, FileSystemLoader, StrictUndefined  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when jinja2 is unavailable
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore
    StrictUndefined = None  # type: ignore


def find_latest_snapshot_files(data_dir: Path) -> tuple[date, Path, Path]:
    """Return the latest (date, interest_path, margin_path) tuple."""

    latest_date: date | None = None
    latest_interest: Path | None = None
    latest_margin: Path | None = None

    for year_dir in sorted(data_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)

        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            month = int(month_dir.name)

            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue
                day = int(day_dir.name)

                interest_path = day_dir / "ibkr-canada-interest-rates.csv"
                margin_path = day_dir / "ibkr-canada-margin-rates.csv"
                if not interest_path.exists() or not margin_path.exists():
                    continue

                snapshot_date = date(year, month, day)
                if latest_date is None or snapshot_date > latest_date:
                    latest_date = snapshot_date
                    latest_interest = interest_path
                    latest_margin = margin_path

    if latest_date is None or latest_interest is None or latest_margin is None:
        raise SystemExit(
            "No valid interest and margin rate CSV pairs found in the data directory."
        )

    return latest_date, latest_interest, latest_margin


def build_latest_snapshot_sentence(data_dir: Path) -> str:
    """Describe the newest interest and margin CSV snapshots for the README."""

    _, interest_path, margin_path = find_latest_snapshot_files(data_dir)
    interest_rel = interest_path.as_posix()
    margin_rel = margin_path.as_posix()

    return (
        f"[`{interest_rel}`]({interest_rel}) and [`{margin_rel}`]({margin_rel})"
    )


def build_chart_section(data_dir: Path) -> str:
    """Return the README snippet that documents the latest rate snapshot table."""

    grouped: "OrderedDict[str, dict[str, tuple[ChartDefinition, date, float]]]" = (
        OrderedDict()
    )

    for definition in CHART_DEFINITIONS:
        records = load_rate_history(
            data_dir,
            definition.dataset,
            currency=definition.currency,
            tier_lower_bound=definition.tier_lower_bound,
            tier_upper_bound=definition.tier_upper_bound,
            lookback_days=definition.lookback_days,
        )
        if not records:
            raise SystemExit(
                "No rate records found; ensure the data directory contains snapshots."
            )

        latest_date, latest_rate = records[-1]
        currency_entries = grouped.setdefault(definition.currency, {})
        currency_entries[definition.dataset] = (definition, latest_date, latest_rate)

    def format_cell(entry: tuple[ChartDefinition, date, float] | None) -> str:
        if entry is None:
            return "—"

        definition, latest_date, latest_rate = entry
        rate_text = f"{latest_rate:.3f}%"
        return f"{rate_text} ({definition.tier_display}, {latest_date.isoformat()})"

    rows: list[str] = ["| Currency | Margin rate | Interest rate |", "| --- | --- | --- |"]
    for currency, datasets in grouped.items():
        margin_entry = datasets.get("margin")
        interest_entry = datasets.get("interest")
        rows.append(
            f"| {currency} | {format_cell(margin_entry)} | {format_cell(interest_entry)} |"
        )

    return "\n".join(["### Selected rates", "", *rows])


def render_template(template_path: Path, context: dict[str, str]) -> str:
    """Render the README template using Jinja2 when available."""

    if Environment is not None:
        env = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=False,
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        template = env.get_template(template_path.name)
        return template.render(context)

    # Lightweight fallback replacement for environments without jinja2 installed.
    content = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        content = content.replace(f"{{{{ {key} }}}}", value)
    return content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("README.md.jinja"),
        help="Path to the README template (default: README.md.jinja)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("README.md"),
        help="Path to the rendered README file (default: README.md)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing the scraped CSV snapshots (default: data)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chart_section = build_chart_section(args.data_dir)
    latest_snapshot_links = build_latest_snapshot_sentence(args.data_dir)
    rendered = render_template(
        args.template,
        {
            "README_INJECT_CHARTS": chart_section,
            "README_INJECT_LATEST_SNAPSHOTS": latest_snapshot_links,
        },
    )
    args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()
