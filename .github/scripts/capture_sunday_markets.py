#!/usr/bin/env python3
"""
サンデー指数キャプチャ & X投稿スクリプト

毎週日曜日に nikkei225jp.com 上の IG証券サンデー指数
（ダウ / NAS100 / ドル円）のチャートをキャプチャし、X に自動投稿する。

使用方法:
    python capture_sunday_markets.py
    python capture_sunday_markets.py --dry-run
    python capture_sunday_markets.py --capture-only
"""

import os
import sys
import io
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright is not installed. Run: pip install playwright")
    sys.exit(1)

try:
    import tweepy
except ImportError:
    print("ERROR: tweepy is not installed. Run: pip install tweepy")
    sys.exit(1)

JST = ZoneInfo("Asia/Tokyo")

TARGETS = [
    {
        "name": "サンデーダウ",
        "url": "https://nikkei225jp.com/_ssi/if/?c=731",
        "filename": "sunday_dow.png",
        "emoji": "🇺🇸",
    },
    {
        "name": "サンデーNAS100",
        "url": "https://nikkei225jp.com/_ssi/if/?c=737",
        "filename": "sunday_nas100.png",
        "emoji": "📈",
    },
    {
        "name": "サンデードル円",
        "url": "https://nikkei225jp.com/_ssi/if/?c=734",
        "filename": "sunday_usdjpy.png",
        "emoji": "💵",
    },
]

CLEANUP_CSS = """
#gnav, .gnav, .gnav-area,
#header, .header, .header-area,
.side-menu, .sidebar, #sidebar,
#footer, .footer, .footer-area,
.ad, .ad-area, .advertisement,
.breadcrumb, .breadcrumbs,
.sns-share, .sns-buttons,
.popular-content, .ranking,
.link-area, .external-links,
.navi, .navigation, .nav-area,
.cookie-banner, .cookie-notice,
.related-content, .sub-content,
.menu-area, .submenu {
    display: none !important;
}
body {
    margin: 0 !important;
    padding-top: 0 !important;
    overflow-x: hidden !important;
}
"""

FIND_CHART_BOUNDS_JS = """
() => {
    const els = document.querySelectorAll('*');
    for (const el of els) {
        const text = (el.textContent || '').trim();
        if (/^(X\\s+)?サンデー/.test(text) && text.length < 40
            && el.offsetHeight > 30 && el.offsetHeight < 60) {
            const rect = el.getBoundingClientRect();
            if (rect.y > 100) {
                return { x: 0, y: Math.floor(rect.y), found: true };
            }
        }
    }
    return { x: 0, y: 305, found: false };
}
"""


def _try_close_popups(page) -> None:
    """Cookie バナーやポップアップを閉じる"""
    selectors = [
        "button:has-text('同意')",
        "button:has-text('OK')",
        "button:has-text('Accept')",
        "button:has-text('閉じる')",
        ".cookie-close",
        "[class*='cookie'] button",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1000):
                el.click()
                page.wait_for_timeout(300)
        except Exception:
            pass


def _try_select_ig_chart(page) -> bool:
    """IG チャートタブがあればクリックして選択する"""
    try:
        candidates = page.locator("a, button, span, div").filter(has_text="IG")
        for i in range(candidates.count()):
            el = candidates.nth(i)
            text = (el.text_content() or "").strip()
            if text == "IG" and el.is_visible(timeout=1000):
                el.click()
                page.wait_for_timeout(3000)
                print("    Selected IG chart view")
                return True
    except Exception:
        pass
    return False


def _try_select_1day(page) -> bool:
    """1日チャートタブがあればクリックして選択する"""
    try:
        candidates = page.locator("a, button, span, div").filter(has_text="１日")
        for i in range(candidates.count()):
            el = candidates.nth(i)
            text = (el.text_content() or "").strip()
            if text == "１日" and el.is_visible(timeout=1000):
                el.click()
                page.wait_for_timeout(2000)
                print("    Selected 1-day view")
                return True
    except Exception:
        pass
    return False


def capture_charts(output_dir: Path, chart_timeout_ms: int = 8000) -> list[Path]:
    """各サンデー指数のチャートをキャプチャする"""
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )

        for target in TARGETS:
            print(f"\n  Capturing: {target['name']}")
            print(f"    URL: {target['url']}")
            page = context.new_page()

            try:
                page.goto(target["url"], wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(chart_timeout_ms)

                _try_close_popups(page)
                _try_select_ig_chart(page)
                _try_select_1day(page)

                page.add_style_tag(content=CLEANUP_CSS)
                page.wait_for_timeout(500)

                bounds = page.evaluate(FIND_CHART_BOUNDS_JS)
                chart_y = bounds.get("y", 305)
                print(f"    Chart top: y={chart_y} (auto-detected={bounds.get('found', False)})")

                filepath = output_dir / target["filename"]
                clip_x = 85
                clip_w = min(1280 - clip_x, 610)
                clip_h = min(900 - chart_y, 430)
                page.screenshot(
                    path=str(filepath),
                    clip={
                        "x": clip_x,
                        "y": max(chart_y - 5, 0),
                        "width": clip_w,
                        "height": clip_h,
                    },
                )

                size_kb = filepath.stat().st_size / 1024
                print(f"    Saved: {filepath.name} ({size_kb:.0f} KB)")
                screenshots.append(filepath)

            except Exception as e:
                print(f"    ERROR: {e}")
            finally:
                page.close()

        browser.close()

    return screenshots


def generate_tweet_text() -> str:
    """ツイート本文を生成する（280文字以内）"""
    now = datetime.now(JST)
    date_str = f"{now.month}/{now.day}"

    tweet = (
        f"📊 サンデー指数 速報（{date_str}）\n"
        f"\n"
        f"今週の市場の方向性を占う\n"
        f"週末トレードの動向です。\n"
        f"\n"
        f"🇺🇸 サンデーダウ\n"
        f"📈 サンデーNAS100\n"
        f"💵 サンデードル円\n"
        f"\n"
        f"#サンデーダウ #投資 #株式投資 #マーケット"
    )

    if len(tweet) > 280:
        tweet = (
            f"📊 サンデー指数（{date_str}）\n\n"
            f"🇺🇸 サンデーダウ\n"
            f"📈 サンデーNAS100\n"
            f"💵 サンデードル円\n\n"
            f"#サンデーダウ #投資 #マーケット"
        )

    return tweet


def upload_media(
    image_path: Path,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
) -> str | None:
    """画像をアップロードして media_id を返す"""
    try:
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_token_secret
        )
        api = tweepy.API(auth)
        media = api.media_upload(filename=str(image_path))
        print(f"    Uploaded: {image_path.name} (media_id: {media.media_id})")
        return str(media.media_id)
    except tweepy.TweepyException as e:
        print(f"    WARNING: Failed to upload {image_path.name}: {e}")
        return None


def post_to_x(
    tweet: str, screenshots: list[Path], dry_run: bool = False
) -> bool:
    """X に画像付きで投稿する"""
    if dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Tweet ({len(tweet)} chars):\n{tweet}")
        print(f"\nImages ({len(screenshots)}):")
        for s in screenshots:
            print(f"  - {s}")
        return True

    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("ERROR: Missing X API credentials")
        print("Required: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET")
        return False

    try:
        media_ids = []
        for img in screenshots:
            if img.exists():
                mid = upload_media(
                    img, api_key, api_secret, access_token, access_token_secret
                )
                if mid:
                    media_ids.append(mid)

        if not media_ids:
            print("WARNING: No images uploaded successfully, posting text only")

        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        kwargs = {"text": tweet}
        if media_ids:
            kwargs["media_ids"] = media_ids

        response = client.create_tweet(**kwargs)
        print(f"\nSuccessfully posted tweet: {response.data['id']}")
        return True

    except tweepy.Forbidden:
        print("WARNING: 403 Forbidden — likely a duplicate tweet")
        return False

    except tweepy.TweepyException as e:
        print(f"ERROR: Failed to post tweet: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Capture Sunday market indices and post to X"
    )
    parser.add_argument("--dry-run", action="store_true", help="Test without posting")
    parser.add_argument(
        "--capture-only", action="store_true", help="Capture screenshots only (no posting)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None, help="Output directory for screenshots"
    )
    parser.add_argument(
        "--chart-timeout",
        type=int,
        default=8000,
        help="Wait time in ms for chart rendering (default: 8000)",
    )
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent.parent.parent / "tmp" / "sunday_markets"

    print("=" * 50)
    print("Sunday Markets Capture & Post")
    print("=" * 50)
    print(f"Time (JST): {datetime.now(JST).strftime('%Y-%m-%d %H:%M')}")
    print(f"Output dir:  {output_dir}")
    print(f"Chart wait:  {args.chart_timeout}ms")
    print(f"Mode:        {'dry-run' if args.dry_run else 'capture-only' if args.capture_only else 'live'}")

    screenshots = capture_charts(output_dir, chart_timeout_ms=args.chart_timeout)
    print(f"\nCaptured {len(screenshots)}/{len(TARGETS)} charts")

    if not screenshots:
        print("ERROR: No charts were captured")
        sys.exit(1)

    if args.capture_only:
        print("\nCapture-only mode — skipping post")
        sys.exit(0)

    tweet = generate_tweet_text()
    print(f"\nTweet ({len(tweet)} chars):\n{tweet}\n")

    success = post_to_x(tweet, screenshots, dry_run=args.dry_run)

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"posted={'true' if success else 'false'}\n")
            f.write(f"image_count={len(screenshots)}\n")

    if success:
        print("\nDone!")
    else:
        print("\nFailed to post")
        sys.exit(1)


if __name__ == "__main__":
    main()
