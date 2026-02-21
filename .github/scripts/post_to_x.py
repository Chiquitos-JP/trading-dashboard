#!/usr/bin/env python3
"""
X (Twitter) 自動投稿スクリプト

各記事の index.qmd の YAML frontmatter (`x-posted: false`) をスキャンし、
最古の未投稿記事を X に投稿する。投稿後は `x-posted: true` に更新。

使用方法:
    python post_to_x.py --type makeover-monday
    python post_to_x.py --type tidytuesday
    python post_to_x.py --type makeover-monday --dry-run
"""

import os
import re
import sys
import argparse
from pathlib import Path

try:
    import tweepy
except ImportError:
    print("ERROR: tweepy is not installed. Run: pip install tweepy")
    sys.exit(1)


QUARTO_POSTS_DIR = "scripts/by_timeSeries/quarto/posts"
DOCS_POSTS_DIR = "docs/quarto/latest/posts"
BASE_URL = "https://chiquitos-jp.github.io/trading-dashboard/quarto/latest/posts"


def extract_frontmatter(qmd_file: Path) -> dict:
    """QMD ファイルから YAML frontmatter を簡易パースする。"""
    content = qmd_file.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    fm = {}
    for key in ("title", "description", "date", "x-posted"):
        m = re.search(rf'^{re.escape(key)}:\s*["\']?(.+?)["\']?\s*$', yaml_text, re.MULTILINE)
        if m:
            val = m.group(1).strip("\"'")
            if key == "x-posted":
                fm[key] = val.lower() == "true"
            else:
                fm[key] = val

    twitter_desc = re.search(
        r'twitter-card:.*?description:\s*["\']?(.+?)["\']?\s*$',
        yaml_text, re.DOTALL | re.MULTILINE,
    )
    if twitter_desc:
        fm["twitter_description"] = twitter_desc.group(1).strip("\"'")

    return fm


def scan_posts(project_root: Path, post_type: str) -> list[dict]:
    """指定タイプの全記事をスキャンし、メタデータのリストを返す。"""
    pattern = f"*-{post_type}"
    posts_dir = project_root / QUARTO_POSTS_DIR
    results = []

    for post_dir in sorted(posts_dir.glob(pattern)):
        qmd = post_dir / "index.qmd"
        if not qmd.exists():
            continue
        fm = extract_frontmatter(qmd)
        if not fm.get("title"):
            continue
        date = fm.get("date", post_dir.name[:10])
        results.append({
            "dir_name": post_dir.name,
            "qmd_path": qmd,
            "date": date,
            "title": fm["title"],
            "description": fm.get("twitter_description") or fm.get("description", ""),
            "url": f"{BASE_URL}/{post_dir.name}/",
            "x_posted": fm.get("x-posted", False),
        })

    results.sort(key=lambda x: x["date"])
    return results


def get_oldest_unposted(posts: list[dict]) -> dict | None:
    """最古の未投稿記事を返す。"""
    for p in posts:
        if not p["x_posted"]:
            return p
    return None


def find_chart_image(item: dict, project_root: Path) -> Path | None:
    """レンダリング済みチャート画像を検索する。"""
    docs_post = project_root / DOCS_POSTS_DIR / item["dir_name"]

    figure_dir = docs_post / "index_files" / "figure-html"
    if figure_dir.exists():
        pngs = sorted(figure_dir.glob("*.png"))
        if pngs:
            return pngs[0]

    chart = docs_post / "chart-1.png"
    if chart.exists():
        return chart

    return None


def format_tweet(item: dict, post_type: str) -> str:
    """ツイート本文を生成する。"""
    title = item["title"]
    description = item["description"]
    url = item["url"]

    if post_type == "makeover-monday":
        hashtags = "#MakeoverMonday #MyMakeoverMonday #DataViz #Python"
    else:
        hashtags = "#TidyTuesday #MyTidyTuesday #DataViz #RStats"

    tweet = f"{title}\n\n{description}\n\n{url}\n\n{hashtags}"

    check_length = len(tweet) - len(url) + 23
    if check_length > 280:
        max_desc = 280 - len(title) - 23 - len(hashtags) - 10
        if max_desc > 0:
            description = description[:max_desc] + "..."
        tweet = f"{title}\n\n{description}\n\n{url}\n\n{hashtags}"

    return tweet


def mark_as_posted(qmd_path: Path) -> None:
    """index.qmd の x-posted: false を x-posted: true に書き換える。"""
    content = qmd_path.read_text(encoding="utf-8")
    updated = re.sub(
        r'^(x-posted:\s*)false\s*$',
        r'\g<1>true',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    qmd_path.write_text(updated, encoding="utf-8")
    print(f"Updated {qmd_path}: x-posted -> true")


def upload_media(image_path: Path, api_key: str, api_secret: str,
                 access_token: str, access_token_secret: str) -> str | None:
    """画像をアップロードして media_id を返す。"""
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api = tweepy.API(auth)
        media = api.media_upload(filename=str(image_path))
        print(f"Uploaded image: {image_path.name} (media_id: {media.media_id})")
        return str(media.media_id)
    except tweepy.TweepyException as e:
        print(f"WARNING: Failed to upload image: {e}")
        return None


def post_to_x(tweet: str, image_path: Path | None = None, dry_run: bool = False) -> tuple[bool, int]:
    """X に投稿する。(success, http_status) を返す。"""
    if dry_run:
        print("=== DRY RUN MODE ===")
        print(f"Would post:\n{tweet}")
        print(f"Character count: {len(tweet)}")
        if image_path:
            print(f"Would attach image: {image_path}")
        return True, 200

    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("ERROR: Missing X API credentials")
        return False, 0

    try:
        media_ids = None
        if image_path and image_path.exists():
            mid = upload_media(image_path, api_key, api_secret, access_token, access_token_secret)
            if mid:
                media_ids = [mid]

        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        response = client.create_tweet(text=tweet, media_ids=media_ids) if media_ids else client.create_tweet(text=tweet)
        print(f"Successfully posted tweet: {response.data['id']}")
        return True, 200

    except tweepy.Forbidden:
        print("WARNING: 403 Forbidden — likely a duplicate tweet. Marking as posted to skip.")
        return False, 403

    except tweepy.TweepyException as e:
        print(f"ERROR: Failed to post tweet: {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(description="Post to X from index.qmd frontmatter")
    parser.add_argument("--type", required=True, choices=["makeover-monday", "tidytuesday"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    quarto_dir = project_root / QUARTO_POSTS_DIR

    print(f"Scanning: {quarto_dir}")
    print(f"Post type: {args.type}")

    posts = scan_posts(project_root, args.type)
    print(f"Found {len(posts)} posts ({sum(1 for p in posts if p['x_posted'])} posted, "
          f"{sum(1 for p in posts if not p['x_posted'])} unposted)")

    item = get_oldest_unposted(posts)
    if not item:
        print(f"No unposted items for type: {args.type}")
        sys.exit(0)

    print(f"\nNext to post: {item['title']} ({item['date']})")

    image_path = find_chart_image(item, project_root)
    if image_path:
        print(f"Found chart image: {image_path}")
    else:
        print("No chart image found (text only)")

    tweet = format_tweet(item, args.type)
    print(f"\nTweet content:\n{tweet}\n")

    success, status = post_to_x(tweet, image_path=image_path, dry_run=args.dry_run)

    if success or status == 403:
        mark_as_posted(item["qmd_path"])

        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a") as f:
                f.write(f"posted=true\n")
                f.write(f"post_date={item['date']}\n")
                f.write(f"post_title={item['title']}\n")
                f.write(f"has_image={'true' if image_path else 'false'}\n")
                f.write(f"was_duplicate={'true' if status == 403 else 'false'}\n")
    else:
        print("Failed to post to X")
        sys.exit(1)


if __name__ == "__main__":
    main()
