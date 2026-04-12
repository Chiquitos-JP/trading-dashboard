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
        "short_name": "ダウ",
        "url": "https://nikkei225jp.com/_ssi/if/?c=731",
        "filename": "sunday_dow.png",
        "emoji": "🇺🇸",
        "is_fx": False,
    },
    {
        "name": "サンデーNAS100",
        "short_name": "NAS100",
        "url": "https://nikkei225jp.com/_ssi/if/?c=737",
        "filename": "sunday_nas100.png",
        "emoji": "📈",
        "is_fx": False,
    },
    {
        "name": "サンデードル円",
        "short_name": "ドル円",
        "url": "https://nikkei225jp.com/_ssi/if/?c=734",
        "filename": "sunday_usdjpy.png",
        "emoji": "💵",
        "is_fx": True,
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

SCRAPE_MARKET_DATA_JS = """
() => {
    const result = { value: null, change: null, change_pct: null, debug_texts: [] };
    const segments = [];
    const seen = new Set();

    function walk(node) {
        const tag = node.nodeName.toUpperCase();
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'SVG') return;
        if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent.trim();
            if (text.length >= 1 && text.length <= 50) {
                const parent = node.parentElement;
                if (!parent) return;
                const rect = parent.getBoundingClientRect();
                if (rect.height === 0) return;
                const style = getComputedStyle(parent);
                if (style.display === 'none' || style.visibility === 'hidden') return;
                const key = text + '|' + Math.round(rect.x) + '|' + Math.round(rect.y);
                if (!seen.has(key)) {
                    seen.add(key);
                    segments.push({
                        text: text, x: rect.x, y: rect.y,
                        fontSize: parseFloat(style.fontSize),
                        color: style.color,
                    });
                }
            }
        }
        for (const child of node.childNodes) walk(child);
    }
    walk(document.body);
    segments.sort((a, b) => a.y - b.y || a.x - b.x);

    const chartSegs = segments.filter(s => s.y > 400);
    result.debug_texts = chartSegs.slice(0, 30).map(
        s => '[y=' + Math.round(s.y) + ' x=' + Math.round(s.x)
             + ' fs=' + s.fontSize + ' c=' + s.color.slice(0,20)
             + '] "' + s.text + '"'
    );

    // Price: largest-font pure number in chart area
    let maxFs = 0;
    let priceX = 0, priceY = 0;
    for (const s of chartSegs) {
        const c = s.text.replace(/[,\\s]/g, '');
        if (/^\\d+\\.?\\d*$/.test(c) && s.fontSize > maxFs) {
            const v = parseFloat(c);
            if (v > 1) { result.value = v; maxFs = s.fontSize; priceX = s.x; priceY = s.y; }
        }
    }

    // Combine decimal part for price (e.g. "47,405" + ".20" → 47405.20)
    if (result.value !== null && result.value === Math.floor(result.value)) {
        for (const s of chartSegs) {
            if (/^\\.\\d+$/.test(s.text.trim())
                && Math.abs(s.y - priceY) < 40
                && s.x > priceX && s.x < priceX + 300
                && s.fontSize > maxFs * 0.4) {
                result.value = parseFloat(result.value.toString() + s.text.trim());
                break;
            }
        }
    }

    // Change: red/green colored number or signed number in chart area (fs >= 20)
    function parseColor(c) {
        const m = c.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
        if (!m) return null;
        return { r: parseInt(m[1]), g: parseInt(m[2]), b: parseInt(m[3]) };
    }
    let changeSeg = null;
    for (const s of chartSegs) {
        if (s.fontSize < 20) continue;
        const c = s.text.replace(/[,\\s]/g, '');
        const m = c.match(/^([+-]?\\d+\\.?\\d*)$/);
        if (!m) continue;
        const v = parseFloat(m[1]);
        if (v === result.value || v === 0) continue;
        const rgb = parseColor(s.color);
        if (!rgb) continue;
        const isRed = rgb.r > 150 && rgb.g < 100;
        const isGreen = rgb.g > 100 && rgb.r < 80;
        if (c.startsWith('+') || c.startsWith('-')) {
            result.change = v; changeSeg = s; break;
        }
        if (isRed) {
            result.change = -Math.abs(v); changeSeg = s; break;
        }
        if (isGreen) {
            result.change = Math.abs(v); changeSeg = s; break;
        }
    }

    // Combine decimal part for change
    if (changeSeg && result.change === Math.floor(result.change)) {
        for (const s of chartSegs) {
            if (/^\\.\\d+$/.test(s.text.trim())
                && Math.abs(s.y - changeSeg.y) < 30
                && s.x > changeSeg.x && s.x < changeSeg.x + 200
                && s.fontSize < changeSeg.fontSize) {
                const sign = result.change < 0 ? -1 : 1;
                result.change = sign * parseFloat(Math.abs(result.change).toString() + s.text.trim());
                break;
            }
        }
    }

    // Percentage: medium-font number < 100, not the price or change
    for (const s of chartSegs) {
        if (s.fontSize < 20 || s.fontSize >= maxFs) continue;
        const c = s.text.replace(/[,\\s%]/g, '');
        if (/^\\d+\\.\\d+$/.test(c)) {
            const v = parseFloat(c);
            if (v < 100 && v > 0
                && v !== Math.abs(result.value || 0)
                && v !== Math.abs(result.change || 0)) {
                result.change_pct = (result.change !== null && result.change < 0) ? -v : v;
                break;
            }
        }
    }

    return result;
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


def scrape_market_data(page, target_name: str) -> dict | None:
    """ページから現在値・変動額・変動率をスクレイピングする"""
    try:
        raw = page.evaluate(SCRAPE_MARKET_DATA_JS)
        debug = raw.get("debug_texts", [])
        value = raw.get("value")
        change = raw.get("change")
        change_pct = raw.get("change_pct")

        if debug and value is None:
            print(f"    Scrape debug ({len(debug)} chart segments):")
            for line in debug[:20]:
                print(f"      {line}")

        if value is not None:
            data = {"value": value}
            if change is not None:
                data["change"] = change
            if change_pct is not None:
                data["change_pct"] = change_pct
            print(f"    Scraped: value={value}, change={change}, pct={change_pct}")
            return data

        print(f"    Scrape: no price found for {target_name}")
        return None
    except Exception as e:
        print(f"    Scrape error: {e}")
        return None


def capture_charts(
    output_dir: Path, chart_timeout_ms: int = 8000
) -> tuple[list[Path], dict]:
    """各サンデー指数のチャートをキャプチャし、数値データもスクレイピングする"""
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[Path] = []
    market_data: dict = {}

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

                data = scrape_market_data(page, target["name"])
                if data:
                    market_data[target["name"]] = data

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

    return screenshots, market_data


def _generate_summary(market_data: dict) -> str:
    """変動方向の組み合わせからサマリー1行を生成する"""
    dow = market_data.get("サンデーダウ", {})
    nas = market_data.get("サンデーNAS100", {})
    fx = market_data.get("サンデードル円", {})

    dow_pct = dow.get("change_pct")
    nas_pct = nas.get("change_pct")
    fx_pct = fx.get("change_pct")

    THRESHOLD = 0.05

    parts: list[str] = []

    if dow_pct is not None and nas_pct is not None:
        dow_up, dow_dn = dow_pct > THRESHOLD, dow_pct < -THRESHOLD
        nas_up, nas_dn = nas_pct > THRESHOLD, nas_pct < -THRESHOLD
        if dow_up and nas_up:
            parts.append("米株堅調")
        elif dow_dn and nas_dn:
            parts.append("米株軟調")
        elif dow_up and nas_dn:
            parts.append("ダウ高・NAS安")
        elif dow_dn and nas_up:
            parts.append("ダウ安・NAS高")
        else:
            parts.append("米株小動き")
    elif dow_pct is not None:
        parts.append("ダウ堅調" if dow_pct > THRESHOLD else "ダウ軟調" if dow_pct < -THRESHOLD else "ダウ小動き")
    elif nas_pct is not None:
        parts.append("NAS堅調" if nas_pct > THRESHOLD else "NAS軟調" if nas_pct < -THRESHOLD else "NAS小動き")

    if fx_pct is not None:
        if abs(fx_pct) <= THRESHOLD:
            parts.append("ドル円は横ばい")
        elif fx_pct > 0:
            parts.append("円安方向")
        else:
            parts.append("円高方向")

    return "、".join(parts)


def _format_data_line(target: dict, data: dict | None) -> str:
    """1つの指数のデータ行をフォーマットする"""
    short = target["short_name"]

    if not data or data.get("value") is None:
        return f"{target['emoji']} サンデー{short}"

    value = data["value"]
    change = data.get("change")
    change_pct = data.get("change_pct")

    if target["is_fx"]:
        val_str = f"{value:.2f}"
    else:
        val_str = f"{value:,.0f}"

    direction = 0
    if change is not None:
        direction = 1 if change > 0 else (-1 if change < 0 else 0)
    elif change_pct is not None:
        direction = 1 if change_pct > 0 else (-1 if change_pct < 0 else 0)
    indicator = "🟢" if direction > 0 else "🔴" if direction < 0 else "⚪"

    if change is not None and change_pct is not None:
        chg_str = f"{change:+.2f}" if target["is_fx"] else f"{change:+,.0f}"
        pct_str = f"{change_pct:+.1f}%"
        return f"{indicator} {short} {val_str} ({chg_str} / {pct_str})"
    if change is not None:
        chg_str = f"{change:+.2f}" if target["is_fx"] else f"{change:+,.0f}"
        return f"{indicator} {short} {val_str} ({chg_str})"
    return f"⚪ {short} {val_str}"


def _static_tweet_text(date_str: str) -> str:
    """フォールバック: データなしの静的テキスト"""
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


def generate_tweet_text(market_data: dict | None = None) -> str:
    """ツイート本文を生成する（280文字以内）

    market_data がある場合はハイブリッド形式（サマリー＋数値行）、
    なければ従来の静的テキストにフォールバックする。
    """
    now = datetime.now(JST)
    date_str = f"{now.month}/{now.day}"

    has_data = market_data and any(
        market_data.get(t["name"]) for t in TARGETS
    )
    if not has_data:
        return _static_tweet_text(date_str)

    summary = _generate_summary(market_data)

    lines = [f"📊 サンデー指数 速報（{date_str}）", ""]
    if summary:
        lines.append(summary)
        lines.append("")
    for target in TARGETS:
        lines.append(_format_data_line(target, market_data.get(target["name"])))
    lines.extend(["", "#サンデーダウ #投資 #株式投資 #マーケット"])
    tweet = "\n".join(lines)

    if len(tweet) > 280:
        lines_short = [f"📊 サンデー指数 速報（{date_str}）", ""]
        for target in TARGETS:
            lines_short.append(_format_data_line(target, market_data.get(target["name"])))
        lines_short.extend(["", "#サンデーダウ #投資 #マーケット"])
        tweet = "\n".join(lines_short)

    if len(tweet) > 280:
        return _static_tweet_text(date_str)

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

    screenshots, market_data = capture_charts(output_dir, chart_timeout_ms=args.chart_timeout)
    print(f"\nCaptured {len(screenshots)}/{len(TARGETS)} charts")

    if market_data:
        print(f"\nMarket data ({len(market_data)}/{len(TARGETS)}):")
        for name, d in market_data.items():
            print(f"  {name}: value={d.get('value')}, change={d.get('change')}, pct={d.get('change_pct')}")
    else:
        print("\nNo market data scraped (will use static text)")

    if not screenshots:
        print("ERROR: No charts were captured")
        sys.exit(1)

    if args.capture_only:
        print("\nCapture-only mode — skipping post")
        sys.exit(0)

    tweet = generate_tweet_text(market_data)
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
