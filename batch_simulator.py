"""
Stand-in batch simulator: REPLACE with the version from Moodle, keeping the same output.

Each run writes the next month of orders to data/batches/YYYY-MM.csv.
Commit and push that file: the push triggers .github/workflows/pipeline.yml.

Run:  python batch_simulator.py            (one month)
      python batch_simulator.py --months 3 (three months)
"""

import argparse
import glob
import os

import pandas as pd

RAW_PATH = "data/raw/Sample - Superstore.csv"
BATCH_DIR = "data/batches"


def next_batches(n_months):
    df = pd.read_csv(RAW_PATH, encoding="latin-1")
    month = pd.to_datetime(df["Order Date"], format="%m/%d/%Y").dt.strftime("%Y-%m")
    done = {os.path.basename(f)[:-4] for f in glob.glob(f"{BATCH_DIR}/*.csv")}
    todo = [m for m in sorted(month.unique()) if m not in done][:n_months]
    os.makedirs(BATCH_DIR, exist_ok=True)
    for m in todo:
        df[month == m].to_csv(f"{BATCH_DIR}/{m}.csv", index=False, encoding="latin-1")
        print(f"Wrote batch {m}: {(month == m).sum()} lines")
    if not todo:
        print("All months already delivered.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=1)
    next_batches(parser.parse_args().months)
