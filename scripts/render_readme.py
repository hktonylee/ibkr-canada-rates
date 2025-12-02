#!/usr/bin/env python3
"""Render README.md from README.md.jinja using the latest datasets."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from build_rate_charts import (
    COMBINED_CHART_DEFINITIONS,
    load_series_records,
)

try:  # pragma: no cover - dependency injection path
    from jinja2 import Environment, FileSystemLoader, StrictUndefined  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when jinja2 is unavailable
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore
    StrictUndefined = None  # type: ignore


def _snapshot_prefix(filename: str) -> str:
    if filename.endswith("-interest-rates.csv"):
        return filename[: -len("-interest-rates.csv")]
    if filename.endswith("-margin-rates.csv"):
        return filename[: -len("-margin-rates.csv")]
    return filename


def _format_region_label(region_slug: str) -> str:
    if len(region_slug) <= 3:
        return region_slug.upper()
    return region_slug.title()


def find_latest_snapshot_pairs(data_dir: Path) -> dict[str, tuple[date, Path, Path]]:
    """Return the latest snapshots keyed by their filename prefix."""

    latest: dict[str, tuple[date, Path, Path]] = {}

    for interest_path in data_dir.rglob("ibkr-*-interest-rates.csv"):
        prefix = _snapshot_prefix(interest_path.name)
        margin_path = interest_path.with_name(f"{prefix}-margin-rates.csv")
        if not margin_path.exists():
            continue

        try:
            day = int(interest_path.parent.name)
            month = int(interest_path.parents[1].name)
            year = int(interest_path.parents[2].name)
        except (IndexError, ValueError):
            continue

        snapshot_date = date(year, month, day)
        existing = latest.get(prefix)
        if existing is None or snapshot_date > existing[0]:
            latest[prefix] = (snapshot_date, interest_path, margin_path)

    if not latest:
        raise SystemExit(
            "No valid interest and margin rate CSV pairs found in the data directory."
        )

    return latest


def build_latest_snapshot_sentence(data_dir: Path) -> str:
    """Describe the newest interest and margin CSV snapshots for the README."""

    snapshots = find_latest_snapshot_pairs(data_dir)
    parts = []
    for prefix, (_date, interest_path, margin_path) in sorted(snapshots.items()):
        slug = _snapshot_prefix(prefix).removeprefix("ibkr-")
        region = _format_region_label(slug)
        interest_rel = interest_path.as_posix()
        margin_rel = margin_path.as_posix()
        parts.append(
            f"{region}: [`{interest_rel}`]({interest_rel}) and [`{margin_rel}`]({margin_rel})"
        )

    return "; ".join(parts)


def build_chart_section(data_dir: Path) -> str:
    """Return the README snippet that documents the rendered rate charts."""

    lines = [
        "The table below shows the latest 31-day margin and interest rate histories "
        "for each currency in a single chart.",
    ]

    sections: list[tuple[str, list[str]]] = [
        ("IBKR US", []),
        ("IBKR Canada", []),
    ]

    for definition in COMBINED_CHART_DEFINITIONS:
        series_records = load_series_records(definition, data_dir)
        latest = max(records[-1][0] for _series, records in series_records)
        chart_path = Path("assets") / latest.isoformat() / definition.filename
        chart_rel = chart_path.as_posix()

        snippet = (
            f"<img src=\"./{chart_rel}\" alt=\"{definition.alt_text}\" width=\"480\" />"
        )

        if definition.currency == "USD":
            sections[0][1].append(f"| {definition.currency} | {snippet} |")
        else:
            sections[1][1].append(f"| {definition.currency} | {snippet} |")

    for heading, rows in sections:
        if not rows:
            continue
        lines.extend(["", f"### {heading}", "", "| Currency | Margin + interest rates |", "| --- | --- |"])
        lines.extend(rows)

    return "\n".join(lines).strip()


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
