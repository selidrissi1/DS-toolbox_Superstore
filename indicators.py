"""
Step 2 - Indicators for Q1 and Q2.

Every indicator is a function that takes the cleaned dataframe as a parameter.
Line-level indicators are added as new columns; group-level indicators return
small tables. Running the file saves every table to reports/metrics/.

Q1: Which sub-categories generate strong sales but weak profit margins,
    and how much of that weakness is linked to discounting?
Q2: Within those sub-categories, at what discount level does profit turn negative,
    and when should Superstore test smaller discounts while keeping the ones
    that still produce profitable baskets?

Run:  python indicators.py
"""

import os

import pandas as pd

CLEAN_PATH = "data/clean/superstore_clean.csv"
METRICS_DIR = "reports/metrics"
BAND_ORDER = ["0%", "1-20%", "21-40%", ">40%"]


def load_clean(path=CLEAN_PATH):
    return pd.read_csv(path, parse_dates=["order_date", "ship_date"])


# ---------------------------------------------------------------- line level

def add_line_indicators(df):
    """Add per-line columns: profit margin, loss flag, discounted-loss flag, basket profit."""
    df = df.copy()
    df["margin"] = df["profit"] / df["sales"]
    df["is_loss"] = (df["profit"] < 0).astype(int)
    df["discounted_loss"] = (df["discount"] > 0) & (df["profit"] < 0)
    # Basket = every line of the same order. Basket profit = total profit of the order.
    df["basket_profit"] = df.groupby("order_id")["profit"].transform("sum")
    return df


# ---------------------------------------------------------------- store level

def store_kpis(df):
    """Headline numbers for the whole store."""
    sales, profit = df["sales"].sum(), df["profit"].sum()
    return {
        "total_sales": sales,
        "total_profit": profit,
        "store_margin": profit / sales,
        "orders": df["order_id"].nunique(),
        "lines": len(df),
        "loss_lines_share": (df["profit"] < 0).mean(),
    }


# ---------------------------------------------------------------- Q1

def subcategory_summary(df):
    """
    Indicators 1-5, one row per sub-category:
    sales share, profit margin, average discount, discount-linked loss, problem flag.
    """
    table = df.groupby("sub_category").agg(
        sales=("sales", "sum"),
        profit=("profit", "sum"),
        avg_discount=("discount", "mean"),
        lines=("sales", "size"),
    )
    table["sales_share"] = table["sales"] / table["sales"].sum()
    table["margin"] = table["profit"] / table["sales"]

    # Indicator 4: money lost on lines that were discounted AND lost money.
    discounted_losses = df[(df["discount"] > 0) & (df["profit"] < 0)]
    table["discount_linked_loss"] = discounted_losses.groupby("sub_category")["profit"].sum()
    table["discount_linked_loss"] = table["discount_linked_loss"].fillna(0)

    # Indicator 5: strong sales (top half: at or above the median sub-category)
    # AND weak profit (margin below the store-wide margin).
    store_margin = df["profit"].sum() / df["sales"].sum()
    strong_sales = table["sales"] >= table["sales"].median()
    weak_profit = table["margin"] < store_margin
    table["flagged"] = strong_sales & weak_profit

    return table.sort_values("sales", ascending=False)


def flagged_subcategories(summary):
    return summary[summary["flagged"]].index.tolist()


# ---------------------------------------------------------------- Q2

def margin_by_band(df, sub_categories=None):
    """
    Indicators 6 and 8: profit margin and average quantity per line in each discount band.
    sub_categories=None gives the whole store.
    """
    data = df if sub_categories is None else df[df["sub_category"].isin(sub_categories)]
    keys = ["discount_band"] if sub_categories is None else ["sub_category", "discount_band"]
    table = data.groupby(keys).agg(
        lines=("sales", "size"),
        sales=("sales", "sum"),
        profit=("profit", "sum"),
        avg_quantity=("quantity", "mean"),
    ).reset_index()
    table["margin"] = table["profit"] / table["sales"]
    table["discount_band"] = pd.Categorical(table["discount_band"], BAND_ORDER, ordered=True)
    return table.sort_values(keys).reset_index(drop=True)


def break_even_band(band_table):
    """Indicator 7: the first (smallest) discount band where the margin turns negative."""
    negative = band_table[band_table["margin"] < 0].sort_values("discount_band")
    return negative.groupby("sub_category")["discount_band"].first().astype(str)


def seasonality_index(df, sub_categories=None):
    """
    Indicator 9: sales in each calendar month / average monthly sales.
    Above 1 = busier than an average month. One row per sub-category (or the store).
    """
    data = df if sub_categories is None else df[df["sub_category"].isin(sub_categories)]
    if sub_categories is None:
        monthly = data.groupby("order_month")["sales"].sum()
        return (monthly / monthly.mean()).rename("seasonality_index").to_frame()
    monthly = data.groupby(["sub_category", "order_month"])["sales"].sum().unstack()
    return monthly.div(monthly.mean(axis=1), axis=0)


def discount_by_month(df):
    """Average discount given in each calendar month (does Superstore discount less when demand is high?)."""
    return df.groupby("order_month")["discount"].mean().rename("avg_discount").to_frame()


def basket_rescue_rate(df):
    """
    Indicator 10: among orders that contain a discounted line that loses money,
    the share whose whole basket is still profitable. One row per sub-category.
    A high rate means the discount may pull in other profitable items (worth keeping).
    """
    if "basket_profit" not in df.columns:
        df = add_line_indicators(df)
    loss_lines = df[(df["discount"] > 0) & (df["profit"] < 0)]
    orders = loss_lines.groupby("sub_category")["order_id"].nunique()
    rescued = loss_lines[loss_lines["basket_profit"] > 0].groupby("sub_category")["order_id"].nunique()
    table = pd.DataFrame({"orders_with_discounted_loss": orders, "rescued_orders": rescued}).fillna(0)
    table["rescue_rate"] = table["rescued_orders"] / table["orders_with_discounted_loss"]
    return table.sort_values("rescue_rate")


def single_line_order_share(df):
    """Share of orders that contain only one line (no basket effect possible)."""
    return (df.groupby("order_id").size() == 1).mean()


# ---------------------------------------------------------------- run all

def compute_all(df):
    """Compute every indicator and return them in one dictionary."""
    df = add_line_indicators(df)
    summary = subcategory_summary(df)
    flagged = flagged_subcategories(summary)
    bands_flagged = margin_by_band(df, flagged)
    return {
        "lines": df,
        "kpis": store_kpis(df),
        "summary": summary,
        "flagged": flagged,
        "bands_store": margin_by_band(df),
        "bands_flagged": bands_flagged,
        "bands_all": margin_by_band(df, sorted(df["sub_category"].unique())),
        "break_even": break_even_band(bands_flagged),
        "season_store": seasonality_index(df),
        "season_flagged": seasonality_index(df, flagged),
        "discount_month": discount_by_month(df),
        "rescue": basket_rescue_rate(df),
        "single_line_share": single_line_order_share(df),
    }


if __name__ == "__main__":
    results = compute_all(load_clean())
    os.makedirs(METRICS_DIR, exist_ok=True)

    print("=== Store KPIs ===")
    for name, value in results["kpis"].items():
        print(f"{name}: {value:,.3f}")

    print("\n=== Q1: sub-category summary ===")
    print(results["summary"].round(3))
    print(f"\nFlagged (strong sales, weak profit): {results['flagged']}")

    print("\n=== Q2: margin by discount band, whole store ===")
    print(results["bands_store"].round(3))
    print("\n=== Q2: margin by discount band, flagged sub-categories ===")
    print(results["bands_flagged"].round(3))
    print("\n=== Q2: first band with a negative margin ===")
    print(results["break_even"])
    print("\n=== Q2: seasonality index (store) and average discount by month ===")
    print(results["season_store"].join(results["discount_month"]).round(3))
    print("\n=== Q2: basket rescue rate ===")
    print(results["rescue"].round(3))
    print(f"\nOrders with a single line: {results['single_line_share']:.1%}")

    # Save the tables used by the dashboard and the report.
    results["summary"].to_csv(f"{METRICS_DIR}/q1_subcategory_summary.csv")
    results["bands_store"].to_csv(f"{METRICS_DIR}/q2_margin_by_band_store.csv", index=False)
    results["bands_all"].to_csv(f"{METRICS_DIR}/q2_margin_by_band_subcategory.csv", index=False)
    results["break_even"].to_csv(f"{METRICS_DIR}/q2_break_even_band.csv")
    results["season_flagged"].to_csv(f"{METRICS_DIR}/q2_seasonality_flagged.csv")
    results["season_store"].join(results["discount_month"]).to_csv(f"{METRICS_DIR}/q2_seasonality_store.csv")
    results["rescue"].to_csv(f"{METRICS_DIR}/q2_basket_rescue_rate.csv")
    print(f"\nSaved tables to {METRICS_DIR}/")
