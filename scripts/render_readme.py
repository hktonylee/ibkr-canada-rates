#!/usr/bin/env python3
"""Render README.md from README.md.jinja using the latest dataset."""

from __future__ import annotations

import argparse
import textwrap
from datetime import date
from pathlib import Path

from build_usd_margin_chart import load_usd_margin_history

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
    """Return the README snippet that documents the USD margin chart."""

    records = load_usd_margin_history(data_dir)
    if not records:
        raise SystemExit(
            "No USD margin rate records found; ensure the data directory contains snapshots."
        )

    earliest = records[0][0]
    latest = records[-1][0]
    chart_path = Path("assets") / latest.isoformat() / "usd-margin-100000.svg"
    chart_rel = chart_path.as_posix()

    return textwrap.dedent(
        f"""
        The chart below visualizes the historical USD margin rate that applies to a
        borrowed balance of USD 100,000 (the second tier in IBKR Canada's pricing
        table). The data points come directly from the daily CSV snapshots stored in
        `data/<YYYY>/<MM>/<DD>/ibkr-canada-margin-rates.csv`, spanning from the earliest
        available entry on {earliest.isoformat()} through the latest snapshot on {latest.isoformat()}.

        <p align=\"center\">
          <img src=\"./{chart_rel}\" alt=\"Historical USD margin rate for $100,000 borrowed\" width=\"720\" />
        </p>

        The SVG is generated automatically by the repository workflow and written to
        `{chart_rel}`. To refresh it locally after adding new data files, run the helper
        script below:

        ```
        python scripts/build_usd_margin_chart.py
        ```
        """
    ).strip()


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
            "README_INJECT_CHART": chart_section,
            "README_INJECT_LATEST_SNAPSHOTS": latest_snapshot_links,
        },
    )
    args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()
