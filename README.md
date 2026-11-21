# Superstore discount analysis

Data Science Toolbox (QM505E) group project, Rennes School of Business.

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
| `assets/style.css` | Dashboard styling (loaded by Dash automatically) |

## Definitions

- **Product group:** Sub-Category (17 groups).
- **Strong sales, weak profit:** sales at or above the median sub-category AND margin below the store margin.
- **Discount bands:** 0%, 1-20%, 21-40%, above 40%.
- **Basket:** all lines with the same Order ID. **Basket rescue rate:** share of orders with a discounted loss-making line whose total profit is still positive.
- **Seasonality index:** sales in a calendar month / average monthly sales.
