<!-- Generated from README.md.jinja; do not edit directly. -->

# ibkr-canada-rates

This repository contains the daily IBKR Canada interest and margin rates, with the latest snapshots available in [`data/2025/12/24/ibkr-canada-interest-rates.csv`](data/2025/12/24/ibkr-canada-interest-rates.csv) and [`data/2025/12/24/ibkr-canada-margin-rates.csv`](data/2025/12/24/ibkr-canada-margin-rates.csv).

The data is updated daily at 6AM EST.

## Usage

Run the Python updater to download the latest HTML pages, parse them, and
write CSV snapshots into `data/<YYYY>/<MM>/<DD>`. The project uses a `src`
layout, so set `PYTHONPATH` accordingly before invoking the module:

```
PYTHONPATH=src python -m ibkr_rates.update --output-dir data
```

For development or testing you can point the updater at local HTML copies
instead of fetching from the network:

```
PYTHONPATH=src python -m ibkr_rates.update \
    --output-dir data \
    --interest-html tests/interest-rates.html \
    --margin-html tests/margin-rates.html
```

## Automation

The scheduled GitHub Actions workflow runs the updater daily and pushes the
resulting CSV snapshots directly to the default branch. When the workflow runs
for a pull request it creates a temporary branch named `auto-update/<run-id>`
and pushes the generated data there so reviewers can inspect the diff without
affecting the base branch.

## Testing

```
pytest
```

## Historical rate snapshots

The charts below track the latest 31-day history for several popular margin
and interest rate tiers across USD, CAD, and JPY.

The table below shows the latest 31-day margin and interest rate histories for each currency in a single chart.

| Currency | Margin + interest rates |
| --- | --- |
| USD | <a href="./assets/2025-12-24/usd-rates-100000-10000.svg?raw=1"><img src="./assets/2025-12-24/usd-rates-100000-10000.svg" alt="Historical USD margin and interest rates for $100,000 borrowed and balances ≥ $10,000" width="480" /></a> |
| CAD | <a href="./assets/2025-12-24/cad-rates-130000-13000.svg?raw=1"><img src="./assets/2025-12-24/cad-rates-130000-13000.svg" alt="Historical CAD margin and interest rates for C$130,000 borrowed and balances ≥ C$13,000" width="480" /></a> |
| JPY | <a href="./assets/2025-12-24/jpy-rates-11000000-5000000.svg?raw=1"><img src="./assets/2025-12-24/jpy-rates-11000000-5000000.svg" alt="Historical JPY margin and interest rates for ¥11,000,000 borrowed and balances ≥ ¥5,000,000" width="480" /></a> |

# Disclaimer

This repository is for educational and informational purposes only. The data is scraped from publicly available IBKR Canada web pages and may contain errors or be outdated. I am not affiliated with Interactive Brokers or IBKR Canada in any way. Users should verify all rates directly with IBKR Canada before making any financial decisions. I disclaim all responsibility for the accuracy, completeness, or reliability of this data.

