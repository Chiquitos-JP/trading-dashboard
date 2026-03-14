"""
TidyTuesday 2026-03-10: How likely is 'likely'?
CAPphrase dataset - probability phrase interpretation

Downloads the 3 CSV files from the TidyTuesday GitHub repo
and saves them to the data/ directory for R/Quarto rendering.

Data source: https://github.com/adamkucharski/CAPphrase/
TidyTuesday: https://github.com/rfordatascience/tidytuesday/blob/main/data/2026/2026-03-10/readme.md

Output:
  data/absolute_judgements.csv   -- probability estimates (0-100) per phrase per respondent
  data/pairwise_comparisons.csv  -- which phrase conveys higher probability
  data/respondent_metadata.csv   -- demographics (age, education, country)

Usage:
    python prepare_data.py          # download if not cached
    python prepare_data.py --force  # re-download
"""

import argparse
from pathlib import Path

import pandas as pd

BASE_URL = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/main/data/2026/2026-03-10"

DATASETS = [
    "absolute_judgements.csv",
    "pairwise_comparisons.csv",
    "respondent_metadata.csv",
]

OUTPUT_DIR = Path(__file__).resolve().parent / "data"


def main():
    parser = argparse.ArgumentParser(description="Download CAPphrase data for TidyTuesday")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename in DATASETS:
        out_path = OUTPUT_DIR / filename
        if out_path.exists() and not args.force:
            df = pd.read_csv(out_path)
            print(f"  [cached] {filename}: {len(df)} rows")
            continue

        url = f"{BASE_URL}/{filename}"
        print(f"  Downloading {filename}...")
        try:
            df = pd.read_csv(url)
            df.to_csv(out_path, index=False)
            print(f"  [ok] {filename}: {len(df)} rows")
        except Exception as e:
            print(f"  [error] {filename}: {e}")

    print(f"\nOutput: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
