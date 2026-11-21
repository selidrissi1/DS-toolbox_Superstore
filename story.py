"""
Puts the indicators and the ML results together into the story told by the
dashboard and the HTML report: findings with their numbers, and the recommendation.

Nothing is typed by hand: every number comes from the data, so the text
updates by itself when new batches arrive.
"""

import pandas as pd

import indicators
import ml_model

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PEAK_THRESHOLD = 1.5   # a month is a "peak" when sales are at least 1.5x an average month
THIN_MARGIN = 0.05     # a positive margin under 5% is too thin to leave untested


def money(value):
    """$2.30M, $286k, $950."""
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.1f}k"
    return f"{sign}${value:.0f}"


def pct(value, digits=1):
    return f"{value * 100:.{digits}f}%"


def recommendations(results):
    """One row per flagged sub-category: what happens today and what to do."""
    bands = results["bands_flagged"]
    rescue = results["rescue"]["rescue_rate"]
    rows = []
    for sub in results["flagged"]:
        b = bands[bands["sub_category"] == sub].set_index("discount_band")
        breaks_at = results["break_even"].get(sub, "none")
        low_band_margin = b.loc["1-20%", "margin"] if "1-20%" in b.index else None

        has_deep_discounts = any(band in b.index for band in ["21-40%", ">40%"])
        stop_deep = "Stop discounts above 20%. " if has_deep_discounts else ""

        if breaks_at == "1-20%":
            action = stop_deep + "Test a smaller discount (e.g. 10%) instead of 20%"
        elif low_band_margin is not None and low_band_margin < THIN_MARGIN:
            action = stop_deep + "Keep up to 20%, but test 10% (thin margin)"
        else:
            action = stop_deep + "Keep discounts up to 20%"

        rows.append({
            "Sub-category": sub,
            "Margin at 1-20%": pct(low_band_margin) if low_band_margin is not None else "no lines",
            "Profit turns negative at": breaks_at,
            "Basket rescue rate": pct(rescue.get(sub, 0), 0),
            "Recommendation": action,
        })
    return pd.DataFrame(rows)


def findings(results, ml):
    """Short findings, each with its number, used as chart titles and notes."""
    k = results["kpis"]
    summary = results["summary"]
    flagged = results["flagged"]
    lines = results["lines"]
    bands = results["bands_store"].set_index("discount_band")
    season = results["season_store"]["seasonality_index"]
    disc_month = results["discount_month"]["avg_discount"]
    ev = ml["evaluation"]

    flagged_lines = lines[lines["sub_category"].isin(flagged)]
    f_sales = flagged_lines["sales"].sum()
    f_profit = flagged_lines["profit"].sum()
    peak_months = [MONTH_NAMES[m - 1] for m in season.index if season[m] >= PEAK_THRESHOLD]
    quiet_month = MONTH_NAMES[season.idxmin() - 1]
    no_discount = lines[lines["discount"] == 0]
    deep = lines[lines["discount"] > 0.20]
    rescue_flagged = results["rescue"].loc[[s for s in flagged if s in results["rescue"].index], "rescue_rate"]

    early_break = [s for s in flagged if results["break_even"].get(s) == "1-20%"]

    return {
        "early_break_names": " and ".join(early_break) if early_break else "none",
        "n_subcats": len(summary),
        "n_flagged": len(flagged),
        "flagged_names": ", ".join(flagged),
        "store_margin": pct(k["store_margin"]),
        "flagged_sales_share": pct(f_sales / k["total_sales"], 0),
        "flagged_margin": pct(f_profit / f_sales),
        "flagged_discount_loss": money(-flagged_lines[flagged_lines["discounted_loss"]]["profit"].sum()),
        "flagged_profit_low": money(flagged_lines[flagged_lines["discount"] <= 0.20]["profit"].sum()),
        "flagged_profit_deep": money(flagged_lines[flagged_lines["discount"] > 0.20]["profit"].sum()),
        "biggest_loss_subcat": summary["discount_linked_loss"].idxmin(),
        "biggest_loss_value": money(-summary["discount_linked_loss"].min()),
        "biggest_loss_margin": pct(summary.loc[summary["discount_linked_loss"].idxmin(), "margin"]),
        "margin_bands": {band: pct(bands.loc[band, "margin"]) for band in bands.index},
        "qty_bands": {band: f"{bands.loc[band, 'avg_quantity']:.1f}" for band in bands.index},
        "no_discount_losses": int((no_discount["profit"] < 0).sum()),
        "no_discount_lines": len(no_discount),
        "deep_lines": len(deep),
        "deep_loss_share": pct((deep["profit"] < 0).mean(), 0),
        "peak_months": ", ".join(peak_months),
        "peak_low": f"{season[season >= PEAK_THRESHOLD].min():.1f}",
        "peak_high": f"{season.max():.1f}",
        "quiet_month": quiet_month,
        "quiet_value": f"{season.min():.1f}",
        "discount_month_low": pct(disc_month.min()),
        "discount_month_high": pct(disc_month.max()),
        "single_line_share": pct(results["single_line_share"], 0),
        "rescue_low": pct(rescue_flagged.min(), 0),
        "rescue_high": pct(rescue_flagged.max(), 0),
        "rescue_low_name": rescue_flagged.idxmin(),
        "rescue_high_name": rescue_flagged.idxmax(),
        "tree": ev["tree"],
        "baseline": ev["baseline_rule"],
        "discount_importance": pct(ml["importance"].get("discount", 0), 0),
        "test_lines": ev["test_lines"],
    }


def build_story():
    """Load the clean data, compute every indicator, train the model, write the findings."""
    df = indicators.load_clean()
    results = indicators.compute_all(df)
    ml = ml_model.run(results["lines"])
    return {
        "results": results,
        "ml": ml,
        "facts": findings(results, ml),
        "recommendations": recommendations(results),
    }


if __name__ == "__main__":
    story = build_story()
    for key, value in story["facts"].items():
        print(f"{key}: {value}")
    print()
    print(story["recommendations"].to_string(index=False))
