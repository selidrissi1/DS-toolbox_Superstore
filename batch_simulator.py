"""
Batch simulator (course BatchLoader, adapted to this project).

Each batch is a slice of the raw Superstore orders, saved as its own file
data/batches/batch_XXX.csv, then committed and pushed to GitHub. Every push
triggers .github/workflows/pipeline.yml, which reprocesses all batches so far.

Changes from the course version, and why:
- reads the Superstore file with latin-1 (special characters in product names);
- orders arrive in date order, like real new data;
- one file per batch instead of overwriting batch.csv, so the pipeline can
  rebuild the store from every batch received so far (no saved state);
- index=False, so no extra "Unnamed: 0" column reaches data_exam.py;
- restarts where it stopped: rows already sent are counted from data/batches/;
- adds the new batch file to git (add(update=True) only stages files git
  already tracks, so a new file would never be pushed).

Run (from the repository root, after `pip install -r requirements.txt`):
    python batch_simulator.py              # push the next batch
    python batch_simulator.py --batches 4  # push the next 4 batches, 3 s apart
"""

import argparse
import glob
import os
import time

import pandas as pd
from git import Repo

DATA_FILE = "data/raw/Sample - Superstore.csv"
BATCH_DIR = "data/batches"
BATCH_SIZE = 2500  # 4 batches cover the 9,994 lines

PATH_OF_GIT_REPO = r"./.git"


class BatchLoader:
    def __init__(self, data_file, batch_size) -> None:
        self.data_file = data_file
        self.data = None
        self.batch_size = batch_size
        self.idx = self.rows_already_sent()

    @staticmethod
    def rows_already_sent():
        files = glob.glob(f"{BATCH_DIR}/batch_*.csv")
        return sum(len(pd.read_csv(f, encoding="latin-1")) for f in files)

    def done(self):
        return self.data is not None and self.idx >= self.data.shape[0]

    def generate(self):
        """Write the next batch to its own file; return its path, or None when all rows are sent."""
        if self.data is None:
            data = pd.read_csv(self.data_file, encoding="latin-1")
            order_date = pd.to_datetime(data["Order Date"], format="%m/%d/%Y")
            self.data = data.loc[order_date.sort_values(kind="stable").index].reset_index(drop=True)
        if self.idx >= self.data.shape[0]:
            return None
        min_idx = min([self.idx + self.batch_size, self.data.shape[0]])
        selected = self.data.iloc[self.idx:min_idx]

        os.makedirs(BATCH_DIR, exist_ok=True)
        number = len(glob.glob(f"{BATCH_DIR}/batch_*.csv")) + 1
        path = f"{BATCH_DIR}/batch_{number:03d}.csv"
        selected.to_csv(path, index=False, encoding="latin-1")
        print(f"Wrote {path}: rows {self.idx + 1}-{min_idx} of {self.data.shape[0]}")
        self.idx = min_idx
        return path


def git_push(path):
    try:
        repo = Repo(PATH_OF_GIT_REPO)
        repo.git.add(path)
        repo.index.commit(f"new batch: {os.path.basename(path)}")
        origin = repo.remote(name="origin")
        origin.push()
        print("Pushed: GitHub Actions now runs the pipeline")
    except Exception as error:
        print(f"Some error occured while pushing the code: {error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=1, help="how many batches to push")
    args = parser.parse_args()

    bl = BatchLoader(DATA_FILE, BATCH_SIZE)
    for i in range(args.batches):
        path = bl.generate()
        if path is None:
            print("All rows already sent: delete data/batches/batch_*.csv to start over.")
            break
        git_push(path)
        if i < args.batches - 1:
            time.sleep(3)
