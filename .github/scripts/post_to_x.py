#!/usr/bin/env python3
"""
X (Twitter) 自動投稿スクリプト

投稿キューから最古の未投稿記事を取得し、Xに投稿する。
画像がある場合は添付する（1枚のみ）。
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


def find_chart_image(item: dict, project_root: Path) -> Path | None:
    """チャート画像を検索する（1枚のみ）
    
    検索順序:
    1. キューに指定された画像パス（image フィールド）
    2. docs/quarto/latest/posts/{post-dir}/index_files/figure-html/*.png
    3. docs/quarto/latest/posts/{post-dir}/chart-1.png
    """
    # 1. キューに画像パスが指定されている場合
    if item.get("image"):
        image_path = project_root / item["image"]
        if image_path.exists():
            return image_path
        # docs配下も確認
        image_path = project_root / "docs" / "quarto" / "latest" / item["image"]
        if image_path.exists():
            return image_path
    
    # URLからpost-dirを取得
    url = item.get("url", "")
    # https://.../posts/2026-01-28-tidytuesday/ -> 2026-01-28-tidytuesday
    if "/posts/" in url:
        post_dir = url.split("/posts/")[-1].rstrip("/")
    else:
        # 日付からpost-dirを推測
        date = item.get("date", "")
        post_type = "tidytuesday" if "TidyTuesday" in item.get("title", "") else "makeover-monday"
        post_dir = f"{date}-{post_type}"
    
    docs_post_dir = project_root / "docs" / "quarto" / "latest" / "posts" / post_dir
    
    # 2. figure-html ディレクトリから最初のPNG
    figure_html_dir = docs_post_dir / "index_files" / "figure-html"
    if figure_html_dir.exists():
        png_files = sorted(figure_html_dir.glob("*.png"))
        if png_files:
            return png_files[0]
    
    # 3. chart-1.png（MakeoverMonday用）
    chart_file = docs_post_dir / "chart-1.png"
    if chart_file.exists():
        return chart_file
    
    return None


def format_tweet(item: dict, post_type: str) -> str:
    """ツイート本文を生成する"""
    title = item.get("title", "")
    description = item.get("description", "")
    url = item.get("url", "")
    
    # ハッシュタグの決定（#My~ で公式版ではないことを示す）
    if post_type == "makeover-monday":
        hashtags = "#MakeoverMonday #MyMakeoverMonday #DataViz #Python"
    else:
        hashtags = "#TidyTuesday #MyTidyTuesday #DataViz #RStats"
    
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


def upload_media(image_path: Path, api_key: str, api_secret: str, 
                 access_token: str, access_token_secret: str) -> str | None:
    """画像をアップロードしてmedia_idを取得する"""
    try:
        # Twitter API v1.1 で画像アップロード
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret,
            access_token, access_token_secret
        )
        api = tweepy.API(auth)
        
        # 画像をアップロード
        media = api.media_upload(filename=str(image_path))
        print(f"Uploaded image: {image_path.name} (media_id: {media.media_id})")
        return str(media.media_id)
        
    except tweepy.TweepyException as e:
        print(f"WARNING: Failed to upload image: {e}")
        return None


def post_to_x(tweet: str, image_path: Path | None = None, dry_run: bool = False) -> bool:
    """Xに投稿する（画像添付対応）"""
    if dry_run:
        print("=== DRY RUN MODE ===")
        print(f"Would post:\n{tweet}")
        print(f"Character count: {len(tweet)}")
        if image_path:
            print(f"Would attach image: {image_path}")
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
        # 画像がある場合はアップロード
        media_ids = None
        if image_path and image_path.exists():
            media_id = upload_media(image_path, api_key, api_secret, 
                                   access_token, access_token_secret)
            if media_id:
                media_ids = [media_id]
        
        # Twitter API v2 クライアントを作成
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # ツイートを投稿（画像がある場合はmedia_ids付き）
        if media_ids:
            response = client.create_tweet(text=tweet, media_ids=media_ids)
        else:
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
    
    # チャート画像を検索
    image_path = find_chart_image(item, project_root)
    if image_path:
        print(f"Found chart image: {image_path}")
    else:
        print("No chart image found (will post text only)")
    
    # ツイート本文を生成
    tweet = format_tweet(item, args.type)
    print(f"\nTweet content:\n{tweet}\n")
    
    # 投稿
    if post_to_x(tweet, image_path=image_path, dry_run=args.dry_run):
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
                f.write(f"has_image={'true' if image_path else 'false'}\n")
    else:
        print("Failed to post to X")
        sys.exit(1)


if __name__ == "__main__":
    main()
