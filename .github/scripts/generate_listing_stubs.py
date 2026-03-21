"""Generate minimal QMD stubs for posts without source files.

Used by CI to ensure the Quarto listing page (analysis.qmd) includes
all posts, even those whose source is gitignored (e.g. weekly reviews).

Reads metadata from search.json and creates frontmatter-only stubs.
"""

import json
import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 4:
        print("Usage: generate_listing_stubs.py <search.json> <docs_posts_dir> <src_posts_dir>")
        sys.exit(1)

    search_json = Path(sys.argv[1])
    docs_posts = Path(sys.argv[2])
    src_posts = Path(sys.argv[3])

    if not search_json.exists() or not docs_posts.exists():
        print("search.json or docs/posts not found, skipping stub generation")
        return

    with open(search_json) as f:
        entries = json.load(f)

    meta = {}
    for e in entries:
        href = e.get("href", "")
        if href.startswith("posts/") and href.endswith("/index.html"):
            post_dir = href.split("/")[1]
            if post_dir not in meta:
                meta[post_dir] = e

    created = []
    for post_dir in sorted(os.listdir(docs_posts)):
        src_qmd = src_posts / post_dir / "index.qmd"
        if src_qmd.exists():
            continue
        if not (docs_posts / post_dir / "index.html").exists():
            continue

        src_qmd.parent.mkdir(parents=True, exist_ok=True)
        entry = meta.get(post_dir, {})
        title = entry.get("title", post_dir).replace('"', '\\"')
        date = post_dir[:10] if len(post_dir) >= 10 else ""
        desc = entry.get("description", "").replace('"', '\\"')
        cats = entry.get("categories", "")

        lines = ["---"]
        lines.append(f'title: "{title}"')
        if date:
            lines.append(f'date: "{date}"')
        if desc:
            lines.append(f'description: "{desc}"')
        lines.append('author: "chokotto"')
        img_name = "thumbnail.svg"
        for ext in ("svg", "jpg", "jpeg", "png"):
            if (docs_posts / post_dir / f"thumbnail.{ext}").exists():
                img_name = f"thumbnail.{ext}"
                break
        lines.append(f'image: "{img_name}"')
        if cats:
            lines.append(f"categories: {json.dumps(cats)}")
        lines.append("---")
        lines.append("")

        src_qmd.write_text("\n".join(lines), encoding="utf-8")
        created.append(str(post_dir))

    stubs_file = src_posts / ".generated_stubs"
    if created:
        stubs_file.write_text("\n".join(created), encoding="utf-8")
        print(f"Created {len(created)} listing stubs")
        for s in created:
            print(f"  stub: {s}")
    else:
        print("No stubs needed (all posts have source files)")


if __name__ == "__main__":
    main()
