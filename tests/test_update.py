from __future__ import annotations

from datetime import date
from pathlib import Path

from ibkr_rates.update import run_update


FIXTURE_DIR = Path(__file__).parent


def _load_html(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_run_update_writes_csv_files(tmp_path):
    overrides = {
        "interest": _load_html("interest-rates.html"),
        "margin": _load_html("margin-rates.html"),
    }

    written = run_update(tmp_path, as_of_date=date(2024, 1, 1), html_overrides=overrides)

    assert set(written) == {"interest", "margin"}
    date_dir = tmp_path / "2024/01/01"
    assert date_dir.is_dir()

    interest_csv = written["interest"].read_text(encoding="utf-8")
    margin_csv = written["margin"].read_text(encoding="utf-8")

    assert interest_csv.startswith("Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff\n")
    assert margin_csv.startswith("Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff\n")
    assert "2024-01-01,USD,0,10000,0,0" in interest_csv
    assert "2024-01-01,USD,0,100000,5.580,1.5" in margin_csv
