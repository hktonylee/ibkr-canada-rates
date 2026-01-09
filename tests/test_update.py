from __future__ import annotations

from datetime import date
from pathlib import Path

from ibkr_rates.update import run_update


FIXTURE_DIR = Path(__file__).parent


def _load_html(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_run_update_writes_csv_files_and_updates_readme(tmp_path):
    overrides = {
        "interest": _load_html("interest-rates.html"),
        "margin": _load_html("margin-rates.html"),
        "us_interest": _load_html("interest-rates.html"),
        "us_margin": _load_html("margin-rates.html"),
    }

    repo_root = tmp_path
    readme = repo_root / "README.md"
    readme.write_text(
        (
            "This repository contains the daily IBKR Canada and US interest and margin rates, "
            "with the latest snapshots available in [`data/2023/12/31/ibkr-canada-interest-rates.csv`]"
            "(data/2023/12/31/ibkr-canada-interest-rates.csv), "
            "[`data/2023/12/31/ibkr-canada-margin-rates.csv`]"
            "(data/2023/12/31/ibkr-canada-margin-rates.csv), "
            "[`data/2023/12/31/ibkr-us-interest-rates.csv`]"
            "(data/2023/12/31/ibkr-us-interest-rates.csv), and "
            "[`data/2023/12/31/ibkr-us-margin-rates.csv`]"
            "(data/2023/12/31/ibkr-us-margin-rates.csv)."
        ),
        encoding="utf-8",
    )

    data_dir = repo_root / "data"

    written = run_update(
        data_dir, as_of_date=date(2024, 1, 1), html_overrides=overrides
    )

    assert set(written) == {"interest", "margin", "us_interest", "us_margin"}
    date_dir = data_dir / "2024/01/01"
    assert date_dir.is_dir()

    interest_csv = written["interest"].read_text(encoding="utf-8")
    margin_csv = written["margin"].read_text(encoding="utf-8")

    assert interest_csv.startswith("Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff\n")
    assert margin_csv.startswith("Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff\n")
    assert "2024-01-01,USD,0,10000,0,0" in interest_csv
    assert "2024-01-01,USD,0,100000,5.580,1.5" in margin_csv

    readme_text = readme.read_text(encoding="utf-8")
    assert (
        "This repository contains the daily IBKR Canada and US interest and margin rates, "
        "with the latest snapshots available in [`data/2024/01/01/ibkr-canada-interest-rates.csv`]"
        "(data/2024/01/01/ibkr-canada-interest-rates.csv), "
        "[`data/2024/01/01/ibkr-canada-margin-rates.csv`]"
        "(data/2024/01/01/ibkr-canada-margin-rates.csv), "
        "[`data/2024/01/01/ibkr-us-interest-rates.csv`]"
        "(data/2024/01/01/ibkr-us-interest-rates.csv), and "
        "[`data/2024/01/01/ibkr-us-margin-rates.csv`]"
        "(data/2024/01/01/ibkr-us-margin-rates.csv)."
    ) in readme_text
