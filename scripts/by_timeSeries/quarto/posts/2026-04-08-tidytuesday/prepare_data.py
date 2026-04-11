"""Download TidyTuesday 2026-03-31 Coastal Ocean Temperature data."""

import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/data/2026/2026-03-31"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

for name in ["ocean_temperature.csv", "ocean_temperature_deployments.csv"]:
    dest = DATA_DIR / name
    if not dest.exists():
        urllib.request.urlretrieve(f"{BASE}/{name}", dest)
        print(f"Downloaded: {name}")
    else:
        print(f"Already exists: {name}")
