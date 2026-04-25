"""Download TidyTuesday 2026-04-21 Global Health Spending (WHO GHED) datasets."""
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/"
    "data/2026/2026-04-21"
)

for name in ["health_spending.csv", "financing_schemes.csv", "spending_purpose.csv"]:
    url = f"{BASE}/{name}"
    dest = DATA_DIR / name
    if not dest.exists():
        print(f"Downloading {name}...")
        urllib.request.urlretrieve(url, dest)
        print(f"  Saved to {dest}")
    else:
        print(f"  {name} already exists, skipping")

print("Done!")
