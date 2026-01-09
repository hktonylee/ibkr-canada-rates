"""High level orchestration for downloading and exporting rate tables."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Sequence

from .fetch import fetch_html
from .parser import DEFAULT_TZ, RateRow, parse_interest_rates, parse_margin_rates, rows_to_csv


@dataclass(frozen=True)
class SourceConfig:
    name: str
    url: str
    filename: str
    parser: "ParserFunc"
    minimum_rows: int = 20
    required_currency: str = "USD"


ParserFunc = Callable[[str, Optional[date]], Sequence[RateRow]]


def _parse_interest(html: str, as_of: Optional[date]) -> Sequence[RateRow]:
    return parse_interest_rates(html, as_of=as_of)


def _parse_margin(html: str, as_of: Optional[date]) -> Sequence[RateRow]:
    return parse_margin_rates(html, as_of=as_of)


SOURCES: Dict[str, SourceConfig] = {
    "interest": SourceConfig(
        name="interest",
        url="https://www.interactivebrokers.ca/en/accounts/fees/pricing-interest-rates.php",
        filename="ibkr-canada-interest-rates.csv",
        parser=_parse_interest,
    ),
    "margin": SourceConfig(
        name="margin",
        url="https://www.interactivebrokers.ca/en/trading/margin-rates.php",
        filename="ibkr-canada-margin-rates.csv",
        parser=_parse_margin,
    ),
    "us_interest": SourceConfig(
        name="us_interest",
        url="https://www.interactivebrokers.com/en/accounts/fees/pricing-interest-rates.php",
        filename="ibkr-us-interest-rates.csv",
        parser=_parse_interest,
    ),
    "us_margin": SourceConfig(
        name="us_margin",
        url="https://www.interactivebrokers.com/en/trading/margin-rates.php",
        filename="ibkr-us-margin-rates.csv",
        parser=_parse_margin,
    ),
}


def _resolve_sources(source_names: Optional[Sequence[str]]) -> Sequence[SourceConfig]:
    if source_names is None:
        return list(SOURCES.values())
    resolved = []
    for name in source_names:
        if name not in SOURCES:
            raise KeyError(f"Unknown source '{name}'")
        resolved.append(SOURCES[name])
    return resolved


def _ensure_valid(rows: Sequence[RateRow], config: SourceConfig) -> None:
    if len(rows) < config.minimum_rows:
        raise ValueError(
            f"Parsed {len(rows)} rows for {config.name}, expected at least {config.minimum_rows}"
        )
    if not any(row.currency == config.required_currency for row in rows):
        raise ValueError(
            f"No rows found for {config.required_currency} in {config.name} data set"
        )


def _determine_as_of_date(as_of_date: Optional[date]) -> date:
    if as_of_date is not None:
        return as_of_date
    return datetime.now(tz=DEFAULT_TZ).date()


def run_update(
    output_root: Path,
    *,
    as_of_date: Optional[date] = None,
    source_names: Optional[Sequence[str]] = None,
    html_overrides: Optional[Mapping[str, str]] = None,
    fetcher: Callable[[str], str] = fetch_html,
) -> Dict[str, Path]:
    """Fetch, parse, validate and export the configured data sets.

    Returns a mapping from source name to the path of the written CSV file.
    """

    html_overrides = html_overrides or {}
    sources = _resolve_sources(source_names)
    resolved_date = _determine_as_of_date(as_of_date)
    date_dir = output_root / resolved_date.strftime("%Y/%m/%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    written: Dict[str, Path] = {}
    for config in sources:
        override = html_overrides.get(config.name)
        html_text = override if override is not None else fetcher(config.url)
        rows = config.parser(html_text, resolved_date)
        _ensure_valid(rows, config)
        csv_text = rows_to_csv(rows)
        output_path = date_dir / config.filename
        output_path.write_text(csv_text, encoding="utf-8")
        written[config.name] = output_path

    _update_readme_links(output_root, written)
    return written


def _update_readme_links(output_root: Path, written: Mapping[str, Path]) -> None:
    """Update README.md with links to the freshly written CSV files."""

    try:
        interest_path = written["interest"]
        margin_path = written["margin"]
        us_interest_path = written["us_interest"]
        us_margin_path = written["us_margin"]
    except KeyError:
        # Only update the README when all CSVs are refreshed.
        return

    output_root = output_root.resolve()
    readme_path = output_root.parent / "README.md"
    if not readme_path.exists():
        return

    repo_root = readme_path.parent.resolve()
    try:
        interest_rel = interest_path.resolve().relative_to(repo_root).as_posix()
        margin_rel = margin_path.resolve().relative_to(repo_root).as_posix()
        us_interest_rel = us_interest_path.resolve().relative_to(repo_root).as_posix()
        us_margin_rel = us_margin_path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        # CSVs are outside of the repository – nothing to update.
        return

    updated_line = (
        "This repository contains the daily IBKR Canada and US interest and margin rates, "
        f"with the latest snapshots available in [`{interest_rel}`]({interest_rel}), "
        f"[`{margin_rel}`]({margin_rel}), [`{us_interest_rel}`]({us_interest_rel}), "
        f"and [`{us_margin_rel}`]({us_margin_rel})."
    )

    readme_text = readme_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"This repository contains the daily IBKR Canada and US interest and margin rates,.*"
    )
    new_text, count = pattern.subn(updated_line, readme_text, count=1)
    if count == 0:
        return

    if new_text != readme_text:
        readme_path.write_text(new_text, encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Download and export IBKR Canada and US rate tables."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--as-of", type=lambda s: date.fromisoformat(s), default=None)
    parser.add_argument(
        "--source",
        choices=list(SOURCES.keys()) + ["all"],
        default="all",
        help="Which data set to refresh",
    )
    parser.add_argument(
        "--interest-html", type=Path, default=None, help="Use a local HTML file for Canada interest rates"
    )
    parser.add_argument(
        "--margin-html", type=Path, default=None, help="Use a local HTML file for Canada margin rates"
    )
    parser.add_argument(
        "--us-interest-html", type=Path, default=None, help="Use a local HTML file for US interest rates"
    )
    parser.add_argument(
        "--us-margin-html", type=Path, default=None, help="Use a local HTML file for US margin rates"
    )

    args = parser.parse_args(argv)
    source_names: Optional[Sequence[str]]
    if args.source == "all":
        source_names = None
    else:
        source_names = [args.source]

    overrides: Dict[str, str] = {}
    if args.interest_html is not None:
        overrides["interest"] = args.interest_html.read_text(encoding="utf-8")
    if args.margin_html is not None:
        overrides["margin"] = args.margin_html.read_text(encoding="utf-8")
    if args.us_interest_html is not None:
        overrides["us_interest"] = args.us_interest_html.read_text(encoding="utf-8")
    if args.us_margin_html is not None:
        overrides["us_margin"] = args.us_margin_html.read_text(encoding="utf-8")

    run_update(
        args.output_dir,
        as_of_date=args.as_of,
        source_names=source_names,
        html_overrides=overrides,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
