"""
Reddit Comment Counts - SOFI & IONQ

Reddit の公開 JSON API から投資系サブレディットでの銘柄別言及を収集し、
日次コメント数（≒注目度）を集計して data/ に CSV 保存。
MakeoverMonday (Python/Plotly) と TidyTuesday (R/ggplot2) の両方で利用。

データソース:
  - Reddit Search API (JSON、認証不要、User-Agent 必須)
  - 対象サブレディット: wallstreetbets, stocks, investing, StockMarket, 銘柄固有
  - 指標: 投稿数, コメント数, スコア(upvotes)

Usage:
    python prepare_data.py              # API からデータ取得
    python prepare_data.py --days 30    # 過去30日分取得（デフォルト14日）
"""

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
SYMBOLS = ["SOFI", "IONQ"]

# 検索対象サブレディット
SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "StockMarket",
    "options",
]

# 銘柄固有サブレディット
TICKER_SUBS = {
    "SOFI": ["sofi", "SOFIstock"],
    "IONQ": ["IonQ"],
}

HEADERS = {"User-Agent": "trading-dashboard/1.0 (educational-project, weekly-post)"}
REQUEST_DELAY = 1.5  # Reddit rate limit 対策
OUTPUT_DIR = Path(__file__).resolve().parent / "data"


def fetch_reddit_posts(symbol: str, subreddit: str, days: int = 14, limit: int = 100) -> list[dict]:
    """指定サブレディットでティッカーを検索し、投稿一覧を返す。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    time_filter = "month" if days > 7 else "week"

    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {
        "q": symbol,
        "sort": "new",
        "restrict_sr": "on",
        "limit": limit,
        "t": time_filter,
    }

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
    posts = data.get("data", {}).get("children", [])
    results = []

    for p in posts:
        d = p.get("data", {})
        created_utc = d.get("created_utc", 0)
        dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)

        if dt < cutoff:
            continue

        results.append({
            "symbol": symbol,
            "subreddit": subreddit,
            "date": dt.strftime("%Y-%m-%d"),
            "title": d.get("title", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "upvote_ratio": d.get("upvote_ratio", 0),
            "created_utc": created_utc,
            "permalink": d.get("permalink", ""),
        })

    return results


def fetch_global_search(symbol: str, days: int = 14, limit: int = 100) -> list[dict]:
    """Reddit 全体検索で $TICKER または TICKER を検索。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    time_filter = "month" if days > 7 else "week"

    url = "https://www.reddit.com/search.json"
    params = {
        "q": f"${symbol} OR {symbol} stock",
        "sort": "new",
        "limit": limit,
        "t": time_filter,
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"      Global search: HTTP {resp.status_code}")
            return []
    except requests.RequestException as e:
        print(f"      Global search: {e}")
        return []

    data = resp.json()
    posts = data.get("data", {}).get("children", [])
    results = []

    for p in posts:
        d = p.get("data", {})
        created_utc = d.get("created_utc", 0)
        dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
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
            "created_utc": created_utc,
            "permalink": d.get("permalink", ""),
        })

    return results


def collect_all(symbols: list[str], days: int = 14) -> pd.DataFrame:
    """全シンボル × 全サブレディットからデータ収集。"""
    all_posts = []

    for symbol in symbols:
        print(f"\n  [{symbol}]")

        # 1. 全体検索
        print(f"    Global search...")
        posts = fetch_global_search(symbol, days=days)
        print(f"      -> {len(posts)} posts")
        all_posts.extend(posts)
        time.sleep(REQUEST_DELAY)

        # 2. サブレディット別検索
        subs = SUBREDDITS + TICKER_SUBS.get(symbol, [])
        for sub in subs:
            print(f"    r/{sub}...")
            posts = fetch_reddit_posts(symbol, sub, days=days)
            print(f"      -> {len(posts)} posts")
            all_posts.extend(posts)
            time.sleep(REQUEST_DELAY)

    if not all_posts:
        return pd.DataFrame()

    df = pd.DataFrame(all_posts)
    # 重複排除（permalink ベース）
    before = len(df)
    df = df.drop_duplicates(subset=["permalink"], keep="first")
    print(f"\n  Dedup: {before} -> {len(df)} posts")
    return df


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """日次集計: 投稿数、合計コメント数、合計スコア。"""
    if df.empty:
        return pd.DataFrame(columns=[
            "date", "symbol", "post_count", "total_comments", "total_score",
            "avg_upvote_ratio",
        ])

    daily = df.groupby(["date", "symbol"]).agg(
        post_count=("num_comments", "count"),
        total_comments=("num_comments", "sum"),
        total_score=("score", "sum"),
        avg_upvote_ratio=("upvote_ratio", "mean"),
    ).reset_index()

    daily = daily.sort_values(["date", "symbol"]).reset_index(drop=True)
    daily["avg_upvote_ratio"] = daily["avg_upvote_ratio"].round(3)
    return daily


def aggregate_by_subreddit(df: pd.DataFrame) -> pd.DataFrame:
    """サブレディット × 銘柄の集計。"""
    if df.empty:
        return pd.DataFrame()

    sub_agg = df.groupby(["symbol", "subreddit"]).agg(
        post_count=("num_comments", "count"),
        total_comments=("num_comments", "sum"),
        total_score=("score", "sum"),
    ).reset_index()

    sub_agg = sub_agg.sort_values(["symbol", "total_comments"], ascending=[True, False])
    return sub_agg


def main():
    parser = argparse.ArgumentParser(description="Reddit comment counts for SOFI & IONQ")
    parser.add_argument("--days", type=int, default=14, help="Days to look back (default: 14)")
    parser.add_argument("--force", action="store_true", help="Force re-fetch even if data exists")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    daily_csv = OUTPUT_DIR / "reddit_daily_counts.csv"
    posts_csv = OUTPUT_DIR / "reddit_posts.csv"
    subreddit_csv = OUTPUT_DIR / "reddit_by_subreddit.csv"

    # 既存データチェック
    if daily_csv.exists() and not args.force:
        existing = pd.read_csv(daily_csv)
        print(f"Existing data found: {len(existing)} rows ({existing['date'].min()} ~ {existing['date'].max()})")
        print("To re-fetch, use --force flag or delete data/reddit_daily_counts.csv")
        return

    print(f"Collecting Reddit data for {SYMBOLS} (past {args.days} days)...")

    # データ収集
    raw_df = collect_all(SYMBOLS, days=args.days)
    if raw_df.empty:
        print("ERROR: No posts collected. Check internet connection or API availability.")
        return

    # 保存: 生データ
    raw_df.to_csv(posts_csv, index=False)
    print(f"\nRaw posts saved: {posts_csv} ({len(raw_df)} rows)")

    # 日次集計
    daily_df = aggregate_daily(raw_df)
    daily_df.to_csv(daily_csv, index=False)
    print(f"Daily counts saved: {daily_csv} ({len(daily_df)} rows)")

    # サブレディット別集計
    sub_df = aggregate_by_subreddit(raw_df)
    sub_df.to_csv(subreddit_csv, index=False)
    print(f"Subreddit breakdown saved: {subreddit_csv} ({len(sub_df)} rows)")

    # サマリー
    print("\n--- Daily Summary ---")
    print(daily_df.to_string(index=False))

    print("\n--- Subreddit Summary ---")
    print(sub_df.to_string(index=False))


if __name__ == "__main__":
    main()
