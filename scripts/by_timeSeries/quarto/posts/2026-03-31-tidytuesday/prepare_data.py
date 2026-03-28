"""Download TidyTuesday 2026-03-24: One Million Digits of Pi."""

from pathlib import Path
import urllib.request

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

URL = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday"
    "/main/data/2026/2026-03-24/pi_digits.csv"
)

dest = DATA_DIR / "pi_digits.csv"

print(f"Downloading: {URL}")
urllib.request.urlretrieve(URL, dest)
print(f"Saved: {dest}  ({dest.stat().st_size:,} bytes)")
