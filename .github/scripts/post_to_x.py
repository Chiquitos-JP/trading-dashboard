#!/usr/bin/env python3
"""
X (Twitter) 自動投稿スクリプト

投稿キューから最古の未投稿記事を取得し、Xに投稿する。
投稿後、キューを更新してコミット可能な状態にする。

使用方法:
    python post_to_x.py --type makeover-monday
    python post_to_x.py --type tidytuesday
    python post_to_x.py --type makeover-monday --dry-run  # テスト実行
"""

import os
import sys
import json
import argparse
from pathlib import Path

try:
    import tweepy
except ImportError:
    print("ERROR: tweepy is not installed. Run: pip install tweepy")
    sys.exit(1)


def load_queue(queue_file: Path) -> dict:
    """投稿キューを読み込む"""
    if not queue_file.exists():
        return {"makeover-monday": [], "tidytuesday": []}
    
    with open(queue_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue_file: Path, queue: dict) -> None:
    """投稿キューを保存する"""
    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def get_oldest_unposted(queue: list) -> dict | None:
    """最古の未投稿記事を取得する"""
    unposted = [item for item in queue if not item.get("posted", False)]
    if not unposted:
        return None
    # 日付でソートして最古を返す
    unposted.sort(key=lambda x: x.get("date", ""))
    return unposted[0]


def format_tweet(item: dict, post_type: str) -> str:
    """ツイート本文を生成する"""
    title = item.get("title", "")
    description = item.get("description", "")
    url = item.get("url", "")
    
    # ハッシュタグの決定
    if post_type == "makeover-monday":
        hashtags = "#MakeoverMonday #DataViz #Python"
    else:
        hashtags = "#TidyTuesday #DataViz #RStats"
    
    # ツイート構成（280文字制限を考慮）
    tweet = f"{title}\n\n{description}\n\n{url}\n\n{hashtags}"
    
    # 文字数チェック（URLは23文字としてカウント）
    # Twitterでは全てのURLが23文字に短縮される
    check_length = len(tweet) - len(url) + 23
    if check_length > 280:
        # descriptionを短縮
        max_desc_len = 280 - len(title) - 23 - len(hashtags) - 10  # 改行分
        if max_desc_len > 0:
            description = description[:max_desc_len] + "..."
        tweet = f"{title}\n\n{description}\n\n{url}\n\n{hashtags}"
    
    return tweet


def post_to_x(tweet: str, dry_run: bool = False) -> bool:
    """Xに投稿する"""
    if dry_run:
        print("=== DRY RUN MODE ===")
        print(f"Would post:\n{tweet}")
        print(f"Character count: {len(tweet)}")
        return True
    
    # 環境変数から認証情報を取得
    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("ERROR: Missing X API credentials in environment variables")
        print("Required: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET")
        return False
    
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
        return True
        
    except tweepy.TweepyException as e:
        print(f"ERROR: Failed to post tweet: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post to X (Twitter) from queue")
    parser.add_argument(
        "--type",
        required=True,
        choices=["makeover-monday", "tidytuesday"],
        help="Type of post to publish"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without actually posting"
    )
    parser.add_argument(
        "--queue-file",
        default=".github/x-post-queue.json",
        help="Path to queue file"
    )
    
    args = parser.parse_args()
    
    # プロジェクトルートを基準にパスを解決
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    queue_file = project_root / args.queue_file
    
    print(f"Queue file: {queue_file}")
    print(f"Post type: {args.type}")
    
    # キューを読み込む
    queue = load_queue(queue_file)
    
    # 指定タイプのキューを取得
    type_queue = queue.get(args.type, [])
    
    if not type_queue:
        print(f"No posts found for type: {args.type}")
        sys.exit(0)
    
    # 最古の未投稿記事を取得
    item = get_oldest_unposted(type_queue)
    
    if not item:
        print(f"No unposted items in queue for type: {args.type}")
        sys.exit(0)
    
    print(f"Found unposted item: {item.get('title')} ({item.get('date')})")
    
    # ツイート本文を生成
    tweet = format_tweet(item, args.type)
    print(f"\nTweet content:\n{tweet}\n")
    
    # 投稿
    if post_to_x(tweet, dry_run=args.dry_run):
        # 投稿成功: キューを更新
        item["posted"] = True
        save_queue(queue_file, queue)
        print(f"Queue updated: {item.get('date')} marked as posted")
        
        # GitHub Actions用の出力
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"posted=true\n")
                f.write(f"post_date={item.get('date')}\n")
                f.write(f"post_title={item.get('title')}\n")
    else:
        print("Failed to post to X")
        sys.exit(1)


if __name__ == "__main__":
    main()
