"""Download 2026 Winter Olympics schedule from TidyTuesday 2026-02-10."""

from pathlib import Path
import urllib.request

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

URL = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday"
    "/main/data/2026/2026-02-10/schedule.csv"
)

dest = DATA_DIR / "schedule.csv"

print(f"Downloading: {URL}")
urllib.request.urlretrieve(URL, dest)
print(f"Saved: {dest}  ({dest.stat().st_size:,} bytes)")
