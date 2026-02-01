# -*- coding: utf-8 -*-
"""
TidyTuesday Data Preparation: S&P 500 Sector Performance

Fetches S&P 500 sector ETF data from Yahoo Finance and calculates:
- Daily returns (%)
- Year-to-date returns (%)

Output: data/sector_performance.parquet
"""

import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime


# S&P 500 Sector ETFs mapping
SECTOR_ETFS = {
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLF": "Financials",
    "XLP": "Cons. Staples",
    "XLI": "Industrials",
    "SPY": "S&P 500",
    "XLC": "Comm. Serv.",
    "XLK": "Info. Tech.",
    "XLY": "Cons. Discr.",
}

# Display order (matching reference chart)
SECTOR_ORDER = [
    "Energy", "Health Care", "Utilities", "Materials", "Real Estate",
    "Financials", "Cons. Staples", "Industrials", "S&P 500",
    "Comm. Serv.", "Info. Tech.", "Cons. Discr."
]


def main():
    print("=" * 60)
    print("S&P 500 Sector Performance - Data Preparation")
    print("=" * 60)
    
    # Output path
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "sector_performance.parquet"
    
    # Fetch data
    tickers = list(SECTOR_ETFS.keys())
    current_year = datetime.now().year
    ytd_start = f"{current_year}-01-01"
    
    print(f"\nFetching data from {ytd_start} to today...")
    print(f"Tickers: {', '.join(tickers)}")
    
    try:
        data = yf.download(
            tickers,
            start=ytd_start,
            auto_adjust=True,
            progress=False
        )
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    # Extract close prices
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data
    
    if prices.empty:
        print("Error: No data fetched")
        return
    
    print(f"Fetched {len(prices)} trading days of data")
    
    # Calculate returns
    daily_returns = prices.pct_change().iloc[-1] * 100
    ytd_returns = ((prices.iloc[-1] / prices.iloc[0]) - 1) * 100
    
    # Create DataFrame
    performance_data = pd.DataFrame({
        "ticker": tickers,
        "sector": [SECTOR_ETFS[t] for t in tickers],
        "daily_return": [daily_returns[t] for t in tickers],
        "ytd_return": [ytd_returns[t] for t in tickers]
    })
    
    # Add sort order and sort
    performance_data["sort_order"] = performance_data["sector"].map(
        {s: i for i, s in enumerate(SECTOR_ORDER)}
    )
    performance_data = performance_data.sort_values("sort_order").reset_index(drop=True)
    
    # Add metadata
    latest_date = prices.index[-1].strftime("%Y-%m-%d")
    performance_data["data_date"] = latest_date
    
    # Save to parquet
    performance_data.to_parquet(output_file, index=False)
    print(f"\nData saved to: {output_file}")
    
    # Display summary
    print(f"\nLatest date: {latest_date}")
    print("\nSector Performance Summary:")
    print("-" * 50)
    for _, row in performance_data.iterrows():
        print(f"{row['sector']:15s}  Daily: {row['daily_return']:+6.2f}%  YTD: {row['ytd_return']:+6.2f}%")
    
    print("\n" + "=" * 60)
    print("Data preparation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
