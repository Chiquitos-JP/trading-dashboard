"""
Attention Metrics + Price Overlay - SOFI & IONQ

Reddit 話題量（Raw Count / Share of Attention / z-score）と
yfinance 価格データを組み合わせ、底打ち候補フラグを付与する。

出力:
  data/reddit_daily_counts.csv   -- 日次 raw count
  data/reddit_posts.csv          -- 生投稿データ
  data/price_data.csv            -- yfinance 終値・出来高
  data/attention_metrics.csv     -- 統合指標 + bottom_candidate

Usage:
    python prepare_data.py               # デフォルト 60 日
    python prepare_data.py --days 90     # 90 日分取得
    python prepare_data.py --force       # キャッシュ無視で再取得
"""

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:
    yf = None
    print("WARNING: yfinance not installed. Price data will be skipped.")

SYMBOLS = ["SOFI", "IONQ"]

SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "StockMarket",
    "options",
]

TICKER_SUBS = {
    "SOFI": ["sofi", "SOFIstock"],
    "IONQ": ["IonQ"],
}

HEADERS = {"User-Agent": "trading-dashboard/1.0 (educational-project, weekly-post)"}
REQUEST_DELAY = 1.5
OUTPUT_DIR = Path(__file__).resolve().parent / "data"

Z_WINDOW = 20
Z_THRESHOLD = -1.5
RETURN_WINDOW = 20


# ---------------------------------------------------------------------------
# Reddit data collection (reused from last week)
# ---------------------------------------------------------------------------

def fetch_reddit_posts(symbol: str, subreddit: str, days: int = 60, limit: int = 100) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    time_filter = "year" if days > 30 else ("month" if days > 7 else "week")

    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {"q": symbol, "sort": "new", "restrict_sr": "on", "limit": limit, "t": time_filter}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 429:
            print(f"      Rate limited on r/{subreddit}. Waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"      r/{subreddit}: HTTP {resp.status_code}")
            return []
    except requests.RequestException as e:
        print(f"      r/{subreddit}: {e}")
        return []

    data = resp.json()
    results = []
    for p in data.get("data", {}).get("children", []):
        d = p.get("data", {})
        dt = datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc)
        if dt < cutoff:
            continue
        results.append({
            "symbol": symbol,
            "subreddit": d.get("subreddit", subreddit),
            "date": dt.strftime("%Y-%m-%d"),
            "title": d.get("title", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "upvote_ratio": d.get("upvote_ratio", 0),
            "created_utc": d.get("created_utc", 0),
            "permalink": d.get("permalink", ""),
        })
    return results


def fetch_global_search(symbol: str, days: int = 60, limit: int = 100) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    time_filter = "year" if days > 30 else ("month" if days > 7 else "week")

    url = "https://www.reddit.com/search.json"
    params = {"q": f"${symbol} OR {symbol} stock", "sort": "new", "limit": limit, "t": time_filter}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
    except requests.RequestException:
        return []

    results = []
    for p in resp.json().get("data", {}).get("children", []):
        d = p.get("data", {})
        dt = datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc)
        if dt < cutoff:
            continue
        results.append({
            "symbol": symbol,
            "subreddit": d.get("subreddit", "other"),
            "date": dt.strftime("%Y-%m-%d"),
            "title": d.get("title", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "upvote_ratio": d.get("upvote_ratio", 0),
            "created_utc": d.get("created_utc", 0),
            "permalink": d.get("permalink", ""),
        })
    return results


def collect_reddit(symbols: list[str], days: int) -> pd.DataFrame:
    all_posts = []
    for symbol in symbols:
        print(f"\n  [{symbol}]")
        print("    Global search...")
        posts = fetch_global_search(symbol, days=days)
        print(f"      -> {len(posts)} posts")
        all_posts.extend(posts)
        time.sleep(REQUEST_DELAY)

        for sub in SUBREDDITS + TICKER_SUBS.get(symbol, []):
            print(f"    r/{sub}...")
            posts = fetch_reddit_posts(symbol, sub, days=days)
            print(f"      -> {len(posts)} posts")
            all_posts.extend(posts)
            time.sleep(REQUEST_DELAY)

    if not all_posts:
        return pd.DataFrame()
    df = pd.DataFrame(all_posts)
    before = len(df)
    df = df.drop_duplicates(subset=["permalink"], keep="first")
    print(f"\n  Dedup: {before} -> {len(df)} posts")
    return df


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", "symbol", "post_count", "total_comments", "total_score"])
    daily = df.groupby(["date", "symbol"]).agg(
        post_count=("num_comments", "count"),
        total_comments=("num_comments", "sum"),
        total_score=("score", "sum"),
    ).reset_index()
    return daily.sort_values(["date", "symbol"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Price data (yfinance)
# ---------------------------------------------------------------------------

def fetch_price_data(symbols: list[str], days: int) -> pd.DataFrame:
    if yf is None:
        return pd.DataFrame()

    start = (datetime.now() - timedelta(days=days + 10)).strftime("%Y-%m-%d")
    print(f"\n  Fetching price data from {start}...")

    frames = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(start=start, auto_adjust=True)
            if hist.empty:
                continue
            df = hist[["Close", "Volume"]].copy()
            df.columns = ["close", "volume"]
            df["symbol"] = sym
            df.index.name = "date"
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            frames.append(df)
            print(f"    {sym}: {len(df)} trading days")
        except Exception as e:
            print(f"    {sym}: ERROR {e}")

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Attention metrics (Section 3 of methodology)
# ---------------------------------------------------------------------------

def compute_attention_metrics(daily: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()

    daily["date"] = pd.to_datetime(daily["date"])
    all_dates = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")

    frames = []
    for sym in SYMBOLS:
        sym_daily = daily[daily["symbol"] == sym].set_index("date")["total_comments"]
        sym_daily = sym_daily.reindex(all_dates, fill_value=0).rename("raw_count")
        sym_daily.index.name = "date"
        df = sym_daily.reset_index()
        df["symbol"] = sym

        # Share of Attention: this symbol / total across all symbols
        total_daily = daily.groupby("date")["total_comments"].sum().reindex(all_dates, fill_value=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            df["share"] = np.where(
                total_daily.values > 0,
                df["raw_count"].values / total_daily.values,
                0,
            )

        # z-score (rolling window)
        rolling_mean = df["raw_count"].rolling(Z_WINDOW, min_periods=5).mean()
        rolling_std = df["raw_count"].rolling(Z_WINDOW, min_periods=5).std()
        df["z_score"] = np.where(rolling_std > 0, (df["raw_count"] - rolling_mean) / rolling_std, 0)

        frames.append(df)

    metrics = pd.concat(frames, ignore_index=True)

    # Merge price data for bottom candidate detection
    if not price.empty:
        price_dt = price.copy()
        price_dt["date"] = pd.to_datetime(price_dt["date"])
        metrics = metrics.merge(price_dt[["date", "symbol", "close", "volume"]], on=["date", "symbol"], how="left")
        metrics["close"] = metrics.groupby("symbol")["close"].ffill()
        metrics["volume"] = metrics.groupby("symbol")["volume"].ffill()

        # 20-day return
        for sym in SYMBOLS:
            mask = metrics["symbol"] == sym
            close_series = metrics.loc[mask, "close"]
            metrics.loc[mask, "return_20d"] = close_series.pct_change(RETURN_WINDOW)

        # Bottom candidate flag
        metrics["bottom_candidate"] = (
            (metrics["z_score"] < Z_THRESHOLD) &
            (metrics["return_20d"] < 0) &
            metrics["close"].notna()
        )
    else:
        metrics["close"] = np.nan
        metrics["volume"] = np.nan
        metrics["return_20d"] = np.nan
        metrics["bottom_candidate"] = False

    metrics["date"] = metrics["date"].dt.strftime("%Y-%m-%d")
    metrics["share"] = metrics["share"].round(4)
    metrics["z_score"] = metrics["z_score"].round(3)
    metrics["return_20d"] = metrics["return_20d"].round(4)

    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Attention metrics + price data for SOFI & IONQ")
    parser.add_argument("--days", type=int, default=60, help="Days to look back (default: 60)")
    parser.add_argument("--force", action="store_true", help="Force re-fetch")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    metrics_csv = OUTPUT_DIR / "attention_metrics.csv"
    if metrics_csv.exists() and not args.force:
        existing = pd.read_csv(metrics_csv)
        print(f"Existing data found: {len(existing)} rows ({existing['date'].min()} ~ {existing['date'].max()})")
        print("Use --force to re-fetch.")
        return

    print(f"Collecting data for {SYMBOLS} (past {args.days} days)...\n")

    # 1. Reddit data
    print("=== Reddit Data ===")
    raw_df = collect_reddit(SYMBOLS, days=args.days)
    if raw_df.empty:
        print("ERROR: No Reddit posts collected.")
        return

    raw_df.to_csv(OUTPUT_DIR / "reddit_posts.csv", index=False)
    daily_df = aggregate_daily(raw_df)
    daily_df.to_csv(OUTPUT_DIR / "reddit_daily_counts.csv", index=False)
    print(f"\nReddit: {len(raw_df)} posts, {len(daily_df)} daily rows")

    # 2. Price data
    print("\n=== Price Data ===")
    price_df = fetch_price_data(SYMBOLS, days=args.days)
    if not price_df.empty:
        price_df.to_csv(OUTPUT_DIR / "price_data.csv", index=False)
        print(f"Price: {len(price_df)} rows saved")

    # 3. Attention metrics
    print("\n=== Attention Metrics ===")
    metrics = compute_attention_metrics(daily_df, price_df)
    metrics.to_csv(metrics_csv, index=False)
    print(f"Metrics: {len(metrics)} rows saved")

    # Summary
    for sym in SYMBOLS:
        sym_data = metrics[metrics["symbol"] == sym]
        n_bottom = sym_data["bottom_candidate"].sum()
        print(f"\n  {sym}: {len(sym_data)} days, {n_bottom} bottom candidates")
        if n_bottom > 0:
            bc = sym_data[sym_data["bottom_candidate"]]
            print(f"    Dates: {', '.join(bc['date'].values[:5])}")


if __name__ == "__main__":
    main()
