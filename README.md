# Superstore discount analysis

Data Science Toolbox (QM505E) project, Rennes School of Business.

**Dataset:** [Superstore Dataset on Kaggle](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final): 9,994 order lines, 21 columns, orders from 2014 to 2017.

**Decision:** where should Superstore keep its discounts, and where should it test smaller ones to improve profit while protecting sales?

- **Q1.** Which sub-categories generate strong sales but weak profit margins, and how much of that weakness is linked to discounting?
- **Q2.** Within those sub-categories, at what discount level does profit turn negative, and when should Superstore test smaller discounts while keeping the ones that still produce profitable baskets?

## How to run

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python data_exam.py               # 1. examine + clean  -> data/clean/superstore_clean.csv
python indicators.py              # 2. indicators       -> reports/metrics/*.csv
python ml_model.py                # 3. ML loss risk     -> reports/ml_evaluation.json, tree_rules.txt
python export_report.py           # 4. static report   -> reports/report.html
python dashboard.py               # 5. Dash app         -> http://127.0.0.1:8050
```

## Project structure

| File | Role |
| --- | --- |
| `data_exam.py` | Examines every column (ranges, groups, nulls, duplicates) and saves the cleaned data |
| `indicators.py` | One function per indicator; each takes the dataframe as a parameter |
| `ml_model.py` | Decision tree predicting loss-making lines; its probability is the loss-risk indicator |
| `story.py` | Turns indicators and ML results into findings and recommendations (no number typed by hand) |
| `figures.py` | Plotly charts shared by the dashboard and the report |
| `dashboard.py` | Dash app with the full story and a sub-category dropdown |
| `export_report.py` | Same story as one static HTML file, for the GitHub Actions artifact |
| `batch_simulator.py` | Course BatchLoader: sends the data in batches and pushes each one to GitHub |
| `assets/style.css` | Dashboard styling (loaded by Dash automatically) |

## Definitions

- **Product group:** Sub-Category (17 groups).
- **Strong sales, weak profit:** sales at or above the median sub-category AND margin below the store margin.
- **Discount bands:** 0%, 1-20%, 21-40%, above 40%.
- **Basket:** all lines with the same Order ID. **Basket rescue rate:** share of orders with a discounted loss-making line whose total profit is still positive.
- **Seasonality index:** sales in a calendar month / average monthly sales.

## Automation (GitHub Actions)

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `.github/workflows/simulate.yml` | **Run workflow** button in Actions (choose 1–4 batches) | Runs `batch_simulator.py` in the cloud: sends the next batch(es), commits and pushes them, then starts `pipeline.yml`. |
| `.github/workflows/pipeline.yml` | Push of a new file in `data/batches/`, or started by `simulate.yml` | Four jobs chained with `needs`: clean → indicators → ml → report. Uploads `report.html` as the `superstore-report` artifact. |
| `.github/workflows/ci.yml` | Every pull request to `main` | Runs all scripts on the full dataset so broken code never reaches `main`. |

### Simulating new data

**From GitHub (no laptop needed):** Actions → **simulate-batch** → **Run workflow** → choose how many batches. A push made with the workflow’s own token does not start other workflows, so `simulate.yml` starts `pipeline.yml` itself.

**From a laptop**, with the course BatchLoader (`batch_simulator.py`, adapted to this project):

```bash
python batch_simulator.py              # writes data/batches/batch_XXX.csv (2,500 lines, in date order), commits and pushes it
python batch_simulator.py --batches 4  # sends all four batches, 3 s apart
```

Each push triggers `pipeline.yml`. `data_exam.py` reads **all** batches received so far (or the full Kaggle file when there are none), so no state is saved between runs and a failed run is fixed by rerunning. When batches arrive quickly, `concurrency` cancels the older runs: only the run with the newest data finishes. To start over, delete `data/batches/batch_*.csv`.
