"""
Step 1 - Data examination and cleaning.

Reads the raw Kaggle Superstore CSV, prints what we learn about every column,
cleans the data, and saves the result to data/clean/superstore_clean.csv.

Run:  python data_exam.py
"""

import pandas as pd

RAW_PATH = "data/raw/Sample - Superstore.csv"
CLEAN_PATH = "data/clean/superstore_clean.csv"

CATEGORICAL_COLUMNS = ["Ship Mode", "Segment", "Country", "Region", "Category", "Sub-Category"]
NUMERIC_COLUMNS = ["Sales", "Quantity", "Discount", "Profit"]

# Discount bands used everywhere in the project (upper edge included).
BAND_EDGES = [-0.01, 0.0, 0.20, 0.40, 1.0]
BAND_LABELS = ["0%", "1-20%", "21-40%", ">40%"]


def load_raw(path=RAW_PATH):
    """Load the raw CSV. The file contains special characters, so it needs latin-1."""
    return pd.read_csv(path, encoding="latin-1")


def examine(df):
    """Print the checks we use to understand the data."""
    print("=== Shape (rows, columns) ===")
    print(df.shape)

    print("\n=== Column types ===")
    print(df.dtypes)

    print("\n=== Numeric columns: min, max, mean, quartiles ===")
    print(df[NUMERIC_COLUMNS].describe().round(2))

    print("\n=== Missing values per column ===")
    print(df.isnull().sum())

    print("\n=== Duplicated rows (ignoring Row ID) ===")
    print(df.drop(columns=["Row ID"]).duplicated().sum())

    print("\n=== Groups in each categorical column (look for misspellings) ===")
    for column in CATEGORICAL_COLUMNS:
        print(f"{column} ({df[column].nunique()} values): {sorted(df[column].unique())}")

    print("\n=== Discount values used ===")
    print(sorted(df["Discount"].unique()))

    print("\n=== Lines with a loss (Profit < 0) ===")
    print(f"{(df['Profit'] < 0).sum()} of {len(df)} lines")


def clean(df):
    """Apply our cleaning decisions and return a new dataframe."""
    df = df.copy()

    # 1. Remove exact duplicates (same order, product, sales, ...). Row ID is only an index.
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "Row ID"])

    # 2. Dates are text like "11/8/2016": convert them to real dates.
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%m/%d/%Y")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="%m/%d/%Y")

    # 3. A product cannot ship before it is ordered: drop such lines if any.
    df = df[df["Ship Date"] >= df["Order Date"]]

    # 4. Drop columns that carry no information for our questions.
    #    Row ID is an index; Country has a single value ("United States").
    df = df.drop(columns=["Row ID", "Country"])

    # 5. Remove stray spaces in text columns.
    text_columns = [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]
    for column in text_columns:
        df[column] = df[column].str.strip()

    # 6. Rename columns to snake_case so every script uses the same names.
    df.columns = [c.lower().replace(" ", "_").replace("-", "_") for c in df.columns]

    # 7. Helper columns used by the indicators.
    df["order_year"] = df["order_date"].dt.year
    df["order_month"] = df["order_date"].dt.month
    df["discount_band"] = pd.cut(df["discount"], bins=BAND_EDGES, labels=BAND_LABELS).astype(str)

    # Negative profit is kept on purpose: it is real data and our questions depend on it.
    return df


if __name__ == "__main__":
    raw = load_raw()
    examine(raw)

    clean_df = clean(raw)
    clean_df.to_csv(CLEAN_PATH, index=False)

    print("\n=== Cleaning summary ===")
    print(f"Rows before: {len(raw)}  |  rows after: {len(clean_df)}")
    print(f"Order dates: {clean_df['order_date'].min().date()} to {clean_df['order_date'].max().date()}")
    print(f"Saved to {CLEAN_PATH}")
