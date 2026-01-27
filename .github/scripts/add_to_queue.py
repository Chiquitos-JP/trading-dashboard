#!/usr/bin/env python3
"""
X投稿キュー追加スクリプト

レンダリングされた記事をX投稿キューに追加する。
記事のYAMLフロントマターからタイトルと説明を抽出する。

使用方法:
    python add_to_queue.py --post-dir posts/2026-01-27-makeover-monday
    python add_to_queue.py --post-dir posts/2026-01-28-tidytuesday
"""

import os
import re
import json
import argparse
from pathlib import Path


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


def extract_frontmatter(qmd_file: Path) -> dict:
    """QMDファイルからYAMLフロントマターを抽出する"""
    with open(qmd_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # YAMLフロントマターを抽出
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    
    yaml_content = match.group(1)
    
    # 簡易的なYAMLパース（PyYAMLを使わない）
    frontmatter = {}
    
    # title
    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', yaml_content, re.MULTILINE)
    if title_match:
        frontmatter["title"] = title_match.group(1).strip('"\'')
    
    # description
    desc_match = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', yaml_content, re.MULTILINE)
    if desc_match:
        frontmatter["description"] = desc_match.group(1).strip('"\'')
    
    # date
    date_match = re.search(r'^date:\s*["\']?(.+?)["\']?\s*$', yaml_content, re.MULTILINE)
    if date_match:
        frontmatter["date"] = date_match.group(1).strip('"\'')
    
    # twitter-card description (優先)
    twitter_desc_match = re.search(r'twitter-card:.*?description:\s*["\']?(.+?)["\']?\s*$', yaml_content, re.DOTALL | re.MULTILINE)
    if twitter_desc_match:
        frontmatter["twitter_description"] = twitter_desc_match.group(1).strip('"\'')
    
    return frontmatter


def determine_post_type(post_dir: str) -> str | None:
    """投稿ディレクトリ名から投稿タイプを判定する"""
    if "makeover-monday" in post_dir:
        return "makeover-monday"
    elif "tidytuesday" in post_dir:
        return "tidytuesday"
    return None


def build_url(post_dir: str) -> str:
    """投稿URLを構築する"""
    # posts/2026-01-27-makeover-monday -> 2026-01-27-makeover-monday
    dir_name = Path(post_dir).name
    base_url = "https://chiquitos-jp.github.io/trading-dashboard/quarto/latest/posts"
    return f"{base_url}/{dir_name}/"


def find_chart_image(post_dir: str, project_root: Path) -> str | None:
    """レンダリング後のチャート画像を検索する（相対パスを返す）
    
    検索順序:
    1. docs/quarto/latest/posts/{post-dir}/index_files/figure-html/*.png（TidyTuesday）
    2. docs/quarto/latest/posts/{post-dir}/chart-1.png（MakeoverMonday）
    """
    dir_name = Path(post_dir).name
    docs_post_dir = project_root / "docs" / "quarto" / "latest" / "posts" / dir_name
    
    # 1. figure-html ディレクトリから最初のPNG（TidyTuesday/R）
    figure_html_dir = docs_post_dir / "index_files" / "figure-html"
    if figure_html_dir.exists():
        png_files = sorted(figure_html_dir.glob("*.png"))
        if png_files:
            # 相対パスを返す（docs/からの相対パス）
            rel_path = png_files[0].relative_to(project_root / "docs" / "quarto" / "latest")
            return str(rel_path)
    
    # 2. chart-1.png（MakeoverMonday/Python）
    chart_file = docs_post_dir / "chart-1.png"
    if chart_file.exists():
        rel_path = chart_file.relative_to(project_root / "docs" / "quarto" / "latest")
        return str(rel_path)
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Add post to X queue")
    parser.add_argument(
        "--post-dir",
        required=True,
        help="Path to post directory (e.g., posts/2026-01-27-makeover-monday)"
    )
    parser.add_argument(
        "--queue-file",
        default=".github/x-post-queue.json",
        help="Path to queue file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Add even if already in queue"
    )
    
    args = parser.parse_args()
    
    # プロジェクトルートを基準にパスを解決
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    queue_file = project_root / args.queue_file
    
    # 投稿タイプを判定
    post_type = determine_post_type(args.post_dir)
    if not post_type:
        print(f"ERROR: Cannot determine post type from: {args.post_dir}")
        print("Expected directory name to contain 'makeover-monday' or 'tidytuesday'")
        return 1
    
    print(f"Post type: {post_type}")
    print(f"Post directory: {args.post_dir}")
    
    # index.qmd を探す
    # まずQuartoプロジェクトディレクトリ内で探す
    quarto_dir = project_root / "scripts" / "by_timeSeries" / "quarto"
    qmd_file = quarto_dir / args.post_dir / "index.qmd"
    
    if not qmd_file.exists():
        # 直接パスとして解釈
        qmd_file = project_root / args.post_dir / "index.qmd"
    
    if not qmd_file.exists():
        print(f"ERROR: index.qmd not found at: {qmd_file}")
        return 1
    
    print(f"Found: {qmd_file}")
    
    # フロントマターを抽出
    frontmatter = extract_frontmatter(qmd_file)
    
    if not frontmatter.get("title"):
        print("ERROR: Could not extract title from frontmatter")
        return 1
    
    print(f"Title: {frontmatter.get('title')}")
    
    # キューを読み込む
    queue = load_queue(queue_file)
    
    # 既にキューに存在するかチェック
    date = frontmatter.get("date", Path(args.post_dir).name[:10])
    url = build_url(args.post_dir)
    
    existing = [item for item in queue.get(post_type, []) if item.get("date") == date]
    if existing and not args.force:
        print(f"Already in queue: {date}")
        print("Use --force to add anyway")
        return 0
    
    # チャート画像を検索
    image_path = find_chart_image(args.post_dir, project_root)
    if image_path:
        print(f"Found chart image: {image_path}")
    else:
        print("No chart image found")
    
    # 新しいエントリを作成
    new_entry = {
        "date": date,
        "title": frontmatter.get("title"),
        "description": frontmatter.get("twitter_description") or frontmatter.get("description", ""),
        "url": url,
        "posted": False
    }
    
    # 画像パスがある場合は追加
    if image_path:
        new_entry["image"] = image_path
    
    # キューに追加
    if post_type not in queue:
        queue[post_type] = []
    
    # 既存エントリを更新または追加
    if existing and args.force:
        for i, item in enumerate(queue[post_type]):
            if item.get("date") == date:
                queue[post_type][i] = new_entry
                print(f"Updated existing entry: {date}")
                break
    else:
        queue[post_type].append(new_entry)
        # 日付でソート
        queue[post_type].sort(key=lambda x: x.get("date", ""))
        print(f"Added to queue: {date}")
    
    # キューを保存
    save_queue(queue_file, queue)
    print(f"Queue saved: {queue_file}")
    
    # GitHub Actions用の出力
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"added=true\n")
            f.write(f"post_type={post_type}\n")
            f.write(f"post_date={date}\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
