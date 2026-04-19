#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週間経済指標カレンダー自動投稿スクリプト

毎週日曜日に翌週（月〜日）の重要経済指標と米国市場休場情報をXに投稿する。

使用方法:
    python post_weekly_calendar.py
    python post_weekly_calendar.py --dry-run  # テスト実行
    python post_weekly_calendar.py --date 2026-02-08  # 特定日付を基準に実行
"""

import os
import sys
import argparse
import re
import io
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

# Windows環境でのUnicode出力対応
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import requests
except ImportError:
    print("ERROR: requests is not installed. Run: pip install requests")
    sys.exit(1)

try:
    from icalendar import Calendar
except ImportError:
    print("ERROR: icalendar is not installed. Run: pip install icalendar")
    sys.exit(1)

try:
    import tweepy
except ImportError:
    print("ERROR: tweepy is not installed. Run: pip install tweepy")
    sys.exit(1)


# Monex経済指標カレンダーのiCal URL（複数のURLを試行）
MONEX_ICAL_URLS = [
    "https://mst.monex.co.jp/mst/servlet/ITS/info/ICSCalendarGw",
    "https://info.monex.co.jp/news/calendar/calendar.ics",
]

# 日本標準時
JST = ZoneInfo("Asia/Tokyo")

# 米国市場休場日（2026-2027年）
US_MARKET_HOLIDAYS = {
    # 2026年
    "2026-01-01": "元日",
    "2026-01-19": "キング牧師記念日",
    "2026-02-16": "大統領の日",
    "2026-04-03": "聖金曜日",
    "2026-05-25": "戦没者追悼記念日",
    "2026-06-19": "ジューンティーンス",
    "2026-07-03": "独立記念日（振替）",
    "2026-09-07": "労働者の日",
    "2026-11-26": "感謝祭",
    "2026-12-25": "クリスマス",
    # 2027年
    "2027-01-01": "元日",
    "2027-01-18": "キング牧師記念日",
    "2027-02-15": "大統領の日",
    "2027-03-26": "聖金曜日",
    "2027-05-31": "戦没者追悼記念日",
    "2027-06-18": "ジューンティーンス（振替）",
    "2027-07-05": "独立記念日（振替）",
    "2027-09-06": "労働者の日",
    "2027-11-25": "感謝祭",
    "2027-12-24": "クリスマス（振替）",
}

# 曜日の日本語表記
WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def get_week_range(base_date: datetime) -> tuple[datetime, datetime]:
    """
    基準日の翌週（月〜日）の日付範囲を取得する
    
    Args:
        base_date: 基準日（通常は日曜日）
        
    Returns:
        (週の開始日（月曜）, 週の終了日（日曜）)
    """
    # 翌日（月曜日）から始まる週を取得
    next_monday = base_date + timedelta(days=1)
    # 週の開始を月曜にする
    days_since_monday = next_monday.weekday()
    week_start = next_monday - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end


def fetch_monex_calendar() -> list[dict]:
    """
    Monex経済指標カレンダーからイベントを取得する
    
    Returns:
        イベントのリスト（date, time, summary, importance を含む辞書）
    """
    events = []
    
    # 複数のURLを試行
    for url in MONEX_ICAL_URLS:
        print(f"Trying to fetch calendar from: {url}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, timeout=15, headers=headers)
            response.raise_for_status()
            
            cal = Calendar.from_ical(response.content)
            
            for component in cal.walk():
                if component.name == "VEVENT":
                    # 日時を取得
                    dtstart = component.get("dtstart")
                    if not dtstart:
                        continue
                    
                    dt = dtstart.dt
                    # dateオブジェクトの場合はdatetimeに変換
                    if not isinstance(dt, datetime):
                        dt = datetime.combine(dt, datetime.min.time())
                    
                    # タイムゾーン処理
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=JST)
                    else:
                        dt = dt.astimezone(JST)
                    
                    summary = str(component.get("summary", ""))
                    description = str(component.get("description", ""))
                    
                    # 重要度を判定
                    importance = determine_importance(summary, description)
                    
                    # 時刻を取得
                    if component.get("dtstart").params.get("VALUE") == "DATE":
                        time_str = "終日"
                    else:
                        time_str = dt.strftime("%H:%M")
                    
                    events.append({
                        "date": dt.date(),
                        "datetime": dt,
                        "time": time_str,
                        "summary": clean_summary(summary),
                        "importance": importance,
                    })
            
            if events:
                print(f"Fetched {len(events)} events from {url}")
                return events
                
        except requests.RequestException as e:
            print(f"WARNING: Failed to fetch from {url}: {e}")
            continue
        except Exception as e:
            print(f"WARNING: Failed to parse calendar from {url}: {e}")
            continue
    
    # フォールバック: 主要な定例経済指標（毎月の固定イベント）
    print("Using fallback: generating standard monthly economic events")
    events = generate_fallback_events()
    
    return events


def generate_fallback_events() -> list[dict]:
    """
    フォールバック用の定例経済指標イベントを生成する
    
    毎月の主要な経済指標発表日の目安:
    - 第1金曜: 米国雇用統計
    - 第2週: CPI
    - 第3週: 小売売上高
    """
    events = []
    now = datetime.now(JST)
    current_year = now.year
    current_month = now.month
    
    # 今月と来月の主要イベントを生成
    for month_offset in range(3):
        month = current_month + month_offset
        year = current_year
        if month > 12:
            month -= 12
            year += 1
        
        # 第1金曜日（雇用統計）を計算
        first_day = datetime(year, month, 1)
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)
        
        events.append({
            "date": first_friday.date(),
            "datetime": first_friday.replace(hour=22, minute=30, tzinfo=JST),
            "time": "22:30",
            "summary": "米国雇用統計・失業率",
            "importance": "high",
        })
        
        # 第2週水曜（CPI - 概算）
        cpi_day = first_day + timedelta(days=10)
        events.append({
            "date": cpi_day.date(),
            "datetime": cpi_day.replace(hour=22, minute=30, tzinfo=JST),
            "time": "22:30",
            "summary": "米国消費者物価指数(CPI)",
            "importance": "high",
        })
    
    return events


def load_json_calendar(project_root: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """
    JSONファイルから経済指標カレンダーと休場日を読み込む
    
    GitHub Actionsで使用される主要なデータソース。
    .github/data/upcoming_calendar.json から読み込む。
    
    Args:
        project_root: プロジェクトルートパス
        
    Returns:
        (イベントのリスト, 休場日のリスト)
    """
    import json
    
    json_path = os.path.join(
        project_root, ".github", "data", "upcoming_calendar.json"
    )
    
    if not os.path.exists(json_path):
        print(f"JSON calendar file not found: {json_path}")
        return [], []
    
    print(f"Loading calendar from JSON: {json_path}")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        events = []
        for item in data.get("events", []):
            date_str = item.get("date", "")
            time_str = item.get("time", "終日")
            
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            
            # datetimeを構築（時刻がある場合）
            if time_str and time_str != "終日":
                try:
                    hour, minute = map(int, time_str.split(":"))
                    dt = datetime(event_date.year, event_date.month, event_date.day,
                                 hour, minute, tzinfo=JST)
                except (ValueError, AttributeError):
                    dt = datetime.combine(event_date, datetime.min.time()).replace(tzinfo=JST)
            else:
                dt = datetime.combine(event_date, datetime.min.time()).replace(tzinfo=JST)
            
            events.append({
                "date": event_date,
                "datetime": dt,
                "time": time_str,
                "summary": item.get("summary", ""),
                "importance": item.get("importance", "medium"),
            })
        
        # 休場日を読み込み
        holidays = []
        for item in data.get("holidays", []):
            date_str = item.get("date", "")
            name = item.get("name", "")
            if date_str and name:
                holidays.append((date_str, name))
        
        print(f"Loaded {len(events)} events and {len(holidays)} holidays from JSON")
        return events, holidays
        
    except Exception as e:
        print(f"WARNING: Failed to read JSON calendar: {e}")
        return [], []


def load_local_calendar(project_root: str) -> list[dict]:
    """
    ローカルのparquetファイルから経済指標データを読み込む
    
    Args:
        project_root: プロジェクトルートパス
        
    Returns:
        イベントのリスト
    """
    try:
        import pandas as pd
    except ImportError:
        print("WARNING: pandas not installed, cannot read local parquet")
        return []
    
    parquet_path = os.path.join(
        project_root, "data", "economicCalendar", "economic_calendar_latest.parquet"
    )
    
    if not os.path.exists(parquet_path):
        print(f"Local calendar file not found: {parquet_path}")
        return []
    
    print(f"Loading local calendar from: {parquet_path}")
    
    try:
        df = pd.read_parquet(parquet_path)
        events = []
        
        for _, row in df.iterrows():
            dt_date = row.get("date")
            if dt_date is None:
                continue
            
            # datetime変換
            if isinstance(dt_date, datetime):
                dt = dt_date
            else:
                dt = datetime.combine(dt_date, datetime.min.time())
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=JST)
            
            # 時刻処理
            time_val = row.get("time", "")
            if pd.isna(time_val) or time_val in ["終日", ""]:
                time_str = "終日"
            else:
                time_str = str(time_val)
            
            summary = str(row.get("summary", ""))
            importance = str(row.get("importance", "medium"))
            
            events.append({
                "date": dt.date(),
                "datetime": dt,
                "time": time_str,
                "summary": clean_summary(summary),
                "importance": importance if importance in ["high", "medium", "low"] else "medium",
            })
        
        print(f"Loaded {len(events)} events from local file")
        return events
        
    except Exception as e:
        print(f"WARNING: Failed to read local calendar: {e}")
        return []


def determine_importance(summary: str, description: str) -> str:
    """
    イベントの重要度を判定する
    
    Returns:
        "high", "medium", "low"
    """
    text = (summary + " " + description).upper()
    
    # 高重要度のキーワード
    high_keywords = [
        "FRB", "FOMC", "政策金利", "雇用統計", "NFP", "非農業部門",
        "CPI", "消費者物価", "GDP", "ECB", "BOJ", "日銀",
        "失業率", "英中銀"
    ]
    
    # 中重要度のキーワード
    medium_keywords = [
        "ISM", "PMI", "小売売上", "鳴生産", "住宅", "貿易収支",
        "景気指数", "製造業", "PPI", "生産者物価"
    ]
    
    for keyword in high_keywords:
        if keyword in text:
            return "high"
    
    for keyword in medium_keywords:
        if keyword in text:
            return "medium"
    
    return "low"


def clean_summary(summary: str) -> str:
    """サマリーをクリーンアップする"""
    # 国旗絵文字などを保持しつつ、余分な空白を除去
    summary = re.sub(r'\s+', ' ', summary).strip()
    
    # 【】や()内の期間情報を簡略化
    summary = re.sub(r'（[^）]*速報[^）]*）', '(速報)', summary)
    summary = re.sub(r'（[^）]*改定[^）]*）', '(改定)', summary)
    
    return summary


def get_holidays_in_range(start_date: datetime, end_date: datetime) -> list[tuple[str, str]]:
    """
    指定期間内の米国市場休場日を取得する
    
    Returns:
        [(日付文字列, 休場名)] のリスト
    """
    holidays = []
    current = start_date
    
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        if date_str in US_MARKET_HOLIDAYS:
            holidays.append((date_str, US_MARKET_HOLIDAYS[date_str]))
        current += timedelta(days=1)
    
    return holidays


def format_event_line(event: dict) -> str:
    """イベントを1行形式にフォーマットする"""
    dt = event["datetime"]
    weekday = WEEKDAY_JA[dt.weekday()]
    date_str = f"{dt.month}/{dt.day}({weekday})"
    
    time_str = event["time"]
    if time_str != "終日":
        return f"・{date_str} {time_str} {event['summary']}"
    else:
        return f"・{date_str} {event['summary']}"


def generate_tweet(
    week_start: datetime,
    week_end: datetime,
    events: list[dict],
    holidays: list[tuple[str, str]]
) -> str:
    """
    ツイート本文を生成する（280文字制限を考慮）
    """
    # ヘッダー
    header = f"📅 来週の重要経済指標（{week_start.month}/{week_start.day}〜{week_end.month}/{week_end.day}）\n"
    
    # フッター（ハッシュタグ）
    footer = "\n#経済指標 #マーケット"
    
    # 期間内のイベントをフィルタ
    week_events = [
        e for e in events
        if week_start.date() <= e["date"] <= week_end.date()
    ]
    
    # 重要度でソート（high → medium → low）
    importance_order = {"high": 0, "medium": 1, "low": 2}
    week_events.sort(key=lambda e: (importance_order[e["importance"]], e["datetime"]))
    
    # 重要度別に分類
    high_events = [e for e in week_events if e["importance"] == "high"]
    medium_events = [e for e in week_events if e["importance"] == "medium"]
    
    # ツイート本文を構築
    body_parts = []
    
    # 高重要度イベント
    if high_events:
        body_parts.append("\n🔴 重要")
        for event in high_events[:5]:  # 最大5件
            body_parts.append(format_event_line(event))
    
    # 中重要度イベント（残り文字数次第）
    if medium_events:
        body_parts.append("\n🟡 中程度")
        for event in medium_events[:3]:  # 最大3件
            body_parts.append(format_event_line(event))
    
    # 休場情報
    if holidays:
        holiday_str = "、".join([f"{h[1]}" for h in holidays])
        body_parts.append(f"\n🏦 休場: {holiday_str}")
    else:
        body_parts.append("\n🏦 休場: なし")
    
    # 本文を結合
    body = "\n".join(body_parts)
    tweet = header + body + footer
    
    # 280文字を超える場合は中重要度を削減
    while len(tweet) > 280 and medium_events:
        medium_events = medium_events[:-1]
        body_parts = []
        
        if high_events:
            body_parts.append("\n🔴 重要")
            for event in high_events[:5]:
                body_parts.append(format_event_line(event))
        
        if medium_events:
            body_parts.append("\n🟡 中程度")
            for event in medium_events:
                body_parts.append(format_event_line(event))
        
        if holidays:
            holiday_str = "、".join([f"{h[1]}" for h in holidays])
            body_parts.append(f"\n🏦 休場: {holiday_str}")
        else:
            body_parts.append("\n🏦 休場: なし")
        
        body = "\n".join(body_parts)
        tweet = header + body + footer
    
    # それでも超える場合は高重要度も削減
    while len(tweet) > 280 and high_events and len(high_events) > 1:
        high_events = high_events[:-1]
        body_parts = []
        
        body_parts.append("\n🔴 重要")
        for event in high_events:
            body_parts.append(format_event_line(event))
        
        if holidays:
            holiday_str = "、".join([f"{h[1]}" for h in holidays])
            body_parts.append(f"\n🏦 休場: {holiday_str}")
        else:
            body_parts.append("\n🏦 休場: なし")
        
        body = "\n".join(body_parts)
        tweet = header + body + footer
    
    # イベントがない場合
    if not high_events and not medium_events:
        body = "\n今週は重要な経済指標の発表予定はありません。"
        if holidays:
            holiday_str = "、".join([f"{h[1]}" for h in holidays])
            body += f"\n\n🏦 休場: {holiday_str}"
        tweet = header + body + footer
    
    return tweet


def post_to_x(tweet: str, dry_run: bool = False) -> tuple[bool, int]:
    """Xに投稿する。(success, http_status) を返す。"""
    if dry_run:
        print("=== DRY RUN MODE ===")
        print(f"Would post:\n{tweet}")
        print(f"\nCharacter count: {len(tweet)}")
        return True, 200
    
    # 環境変数から認証情報を取得
    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("ERROR: Missing X API credentials in environment variables")
        print("Required: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET")
        return False, 0
    
    try:
        # Twitter API v2 クライアントを作成
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # ツイートを投稿
        response = client.create_tweet(text=tweet)
        print(f"Successfully posted tweet: {response.data['id']}")
        return True, 200
    
    except tweepy.Forbidden:
        print("WARNING: 403 Forbidden — likely a duplicate tweet. Treating as already posted.")
        return False, 403
    
    except tweepy.TweepyException as e:
        print(f"ERROR: Failed to post tweet: {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(
        description="Post weekly economic calendar to X (Twitter)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without actually posting"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Base date (YYYY-MM-DD format, defaults to today)"
    )
    parser.add_argument(
        "--use-local",
        action="store_true",
        help="Try to load from local parquet file (for local testing)"
    )
    
    args = parser.parse_args()
    
    # プロジェクトルートを推定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # 基準日を決定
    if args.date:
        base_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        base_date = datetime.now(JST).replace(tzinfo=None)
    
    print(f"Base date: {base_date.strftime('%Y-%m-%d')} ({WEEKDAY_JA[base_date.weekday()]})")
    
    # 翌週の日付範囲を取得
    week_start, week_end = get_week_range(base_date)
    print(f"Target week: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
    
    # 経済指標カレンダーを取得
    # 優先順位: JSON（GitHub Actions用） → ローカルparquet → Monex → フォールバック
    events = []
    json_holidays = []
    
    # 1. まずJSONファイルを試行（GitHub Actions環境のメインソース）
    events, json_holidays = load_json_calendar(project_root)
    
    # 2. JSONがない/空の場合、ローカルparquetを試行（--use-local指定時のみ）
    if not events and args.use_local:
        events = load_local_calendar(project_root)
    
    # 3. それでもない場合、Monex/フォールバックを試行
    if not events:
        events = fetch_monex_calendar()
    
    # 期間内のイベント数をカウント
    week_events = [
        e for e in events
        if week_start.date() <= e["date"] <= week_end.date()
    ]
    print(f"Events in target week: {len(week_events)}")
    
    # 休場日を取得（JSONから取得した休場日を優先、なければハードコード版を使用）
    if json_holidays:
        # JSONから取得した休場日を期間でフィルタ
        holidays = [
            (date_str, name) for date_str, name in json_holidays
            if week_start.strftime("%Y-%m-%d") <= date_str <= week_end.strftime("%Y-%m-%d")
        ]
    else:
        holidays = get_holidays_in_range(week_start, week_end)
    
    if holidays:
        print(f"Holidays in target week: {[h[1] for h in holidays]}")
    else:
        print("No holidays in target week")
    
    # ツイート本文を生成
    tweet = generate_tweet(week_start, week_end, events, holidays)
    print(f"\n--- Generated Tweet ({len(tweet)} chars) ---")
    print(tweet)
    print("--- End of Tweet ---\n")
    
    # 投稿
    success, status = post_to_x(tweet, dry_run=args.dry_run)
    
    if success or status == 403:
        if status == 403:
            print("Tweet was already posted (duplicate). Treating as success.")
        else:
            print("Tweet posted successfully!")
        
        # GitHub Actions用の出力
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"posted=true\n")
                f.write(f"week_start={week_start.strftime('%Y-%m-%d')}\n")
                f.write(f"week_end={week_end.strftime('%Y-%m-%d')}\n")
                f.write(f"event_count={len(week_events)}\n")
                f.write(f"was_duplicate={'true' if status == 403 else 'false'}\n")
    else:
        print("Failed to post tweet")
        sys.exit(1)


if __name__ == "__main__":
    main()
