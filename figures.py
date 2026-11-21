"""
Plotly figures shared by the Dash app (dashboard.py) and the static report (export_report.py).
Each function takes computed tables and returns one figure.

Colour rules: blue = the sub-categories we flag (and positive margins),
red = negative margins, grey = everything else. Chart titles live in the page,
not inside the figure, so each title can state the finding.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
RED = "#e34948"
GREY = "#b5b4ad"
INK = "#0b0b10"
INK_2 = "#52514e"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
NEUTRAL = "#f0efec"
BAND_ORDER = ["0%", "1-20%", "21-40%", ">40%"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FONT = "Inter, system-ui, -apple-system, Segoe UI, sans-serif"


def style(fig, height=420):
    """Common look: transparent background, hairline grid, readable type."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=16, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=14, color=INK_2),
        hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=FONT, size=13, color=INK)),
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, ticks="", automargin=True)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, ticks="", automargin=True)
    return fig


# ---------------------------------------------------------------- Q1

def q1_scatter(summary, store_margin):
    """Sales share vs profit margin, one dot per sub-category; flagged ones in blue."""
    s = summary.reset_index()
    s["share_pct"] = s["sales_share"] * 100
    s["margin_pct"] = s["margin"] * 100
    median_share = s["share_pct"].median()
    store_pct = store_margin * 100
    x_max = s["share_pct"].max() * 1.12
    y_min, y_max = s["margin_pct"].min() - 6, s["margin_pct"].max() + 4

    fig = go.Figure()
    # Zone of interest: strong sales (right of the median) and weak profit (under the store margin).
    fig.add_shape(type="rect", x0=median_share, x1=x_max, y0=y_min, y1=store_pct,
                  fillcolor="rgba(42,120,214,0.07)", line_width=0, layer="below")
    fig.add_hline(y=store_pct, line=dict(color=INK_2, width=1))
    fig.add_vline(x=median_share, line=dict(color=INK_2, width=1))
    fig.add_annotation(x=0, y=store_pct, text=f"Store margin {store_pct:.1f}%", showarrow=False,
                       xanchor="left", xshift=4, yanchor="bottom", font=dict(color=INK_2, size=13))
    fig.add_annotation(x=median_share, y=y_max, text="Median sub-category sales", showarrow=False,
                       xanchor="left", xshift=6, yanchor="top", font=dict(color=INK_2, size=13))
    fig.add_annotation(x=x_max, y=y_min, text="Strong sales, weak profit", showarrow=False,
                       xanchor="right", yanchor="bottom", font=dict(color=BLUE, size=14))

    hover = ("<b>%{customdata[0]}</b><br>Sales %{customdata[1]:$,.0f} (%{x:.1f}% of store)"
             "<br>Margin %{y:.1f}%<br>Average discount %{customdata[2]:.0%}"
             "<br>Lost on discounted lines %{customdata[3]:$,.0f}<extra></extra>")
    for flagged, color, size in [(False, GREY, 11), (True, BLUE, 15)]:
        part = s[s["flagged"] == flagged]
        fig.add_trace(go.Scatter(
            x=part["share_pct"], y=part["margin_pct"], mode="markers+text" if flagged else "markers",
            text=part["sub_category"] if flagged else None, textposition="middle right",
            textfont=dict(color=INK, size=14),
            marker=dict(color=color, size=size, line=dict(color="white", width=2)),
            customdata=part[["sub_category", "sales", "avg_discount", "discount_linked_loss"]].assign(
                discount_linked_loss=lambda d: -d["discount_linked_loss"]).values,
            hovertemplate=hover,
        ))
    # Name a few unflagged dots that the story mentions.
    for name, side in [("Binders", "left"), ("Phones", "right"), ("Copiers", "left")]:
        if name in summary.index:
            row = s[s["sub_category"] == name].iloc[0]
            fig.add_annotation(x=row["share_pct"], y=row["margin_pct"], text=name, showarrow=False,
                               xanchor=side, xshift=9 if side == "left" else -9,
                               font=dict(color=INK_2, size=13))

    fig.update_xaxes(title="Share of store sales (%)", range=[0, x_max])
    fig.update_yaxes(title="Profit margin (%)", range=[y_min, y_max])
    return style(fig, 460)


def q1_discount_loss(summary):
    """Money lost on discounted lines that lose money, by sub-category."""
    s = summary[summary["discount_linked_loss"] < 0].copy()
    s["loss_k"] = -s["discount_linked_loss"] / 1000
    s = s.sort_values("loss_k")
    colors = [BLUE if f else GREY for f in s["flagged"]]
    fig = go.Figure(go.Bar(
        x=s["loss_k"], y=s.index, orientation="h", marker=dict(color=colors, cornerradius=4),
        text=[f"${v:.1f}k" if v >= 0.1 else f"${v * 1000:.0f}" for v in s["loss_k"]],
        textposition="outside", cliponaxis=False, textfont=dict(color=INK, size=13),
        hovertemplate="<b>%{y}</b><br>Lost on discounted lines: $%{x:.1f}k<extra></extra>",
    ))
    fig.update_xaxes(title="Lost on discounted, loss-making lines ($ thousand)", range=[0, s["loss_k"].max() * 1.18])
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    return style(fig, 460)


# ---------------------------------------------------------------- Q2

def _band_bar(band_table, show_text=True):
    t = band_table.copy()
    t["margin_pct"] = t["margin"] * 100
    colors = [BLUE if m >= 0 else RED for m in t["margin_pct"]]
    return go.Bar(
        x=t["discount_band"].astype(str), y=t["margin_pct"], marker=dict(color=colors, cornerradius=4),
        text=[f"{m:.0f}%" for m in t["margin_pct"]] if show_text else None,
        textposition="outside", cliponaxis=False, textfont=dict(color=INK, size=13),
        customdata=t[["lines", "avg_quantity"]].values,
        hovertemplate=("Discount %{x}<br>Margin %{y:.1f}%<br>%{customdata[0]} lines"
                       "<br>Average quantity per line %{customdata[1]:.1f}<extra></extra>"),
    )


def q2_band_single(band_table):
    """Margin by discount band for one group (used with the dropdown in the Dash app)."""
    fig = go.Figure(_band_bar(band_table))
    fig.update_xaxes(title="Discount band", categoryorder="array", categoryarray=BAND_ORDER)
    fig.update_yaxes(title="Profit margin (%)", zeroline=True, zerolinewidth=1.5)
    return style(fig, 400)


def q2_band_grid(bands_store, bands_flagged, flagged):
    """Small multiples: the whole store, then each flagged sub-category, same scale."""
    order = ["Whole store"] + list(flagged)
    cols = 3
    rows = -(-len(order) // cols)
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=order, shared_yaxes=True,
                        horizontal_spacing=0.04, vertical_spacing=0.16)
    all_margins = [bands_store["margin"].min()] + [bands_flagged["margin"].min()]
    y_min = min(all_margins) * 100 - 15
    y_max = max(bands_store["margin"].max(), bands_flagged["margin"].max()) * 100 + 14
    for i, name in enumerate(order):
        r, c = i // cols + 1, i % cols + 1
        table = bands_store if name == "Whole store" else bands_flagged[bands_flagged["sub_category"] == name]
        fig.add_trace(_band_bar(table), row=r, col=c)
        fig.update_xaxes(categoryorder="array", categoryarray=BAND_ORDER, row=r, col=c)
    fig.update_yaxes(range=[y_min, y_max], zeroline=True, zerolinewidth=1.5)
    fig.update_yaxes(title="Margin (%)", col=1)
    fig.update_annotations(font=dict(size=15, color=INK))
    style(fig, 300 * rows + 60)
    fig.update_layout(margin=dict(t=48))
    return fig


def q2_seasonality(season_store, season_flagged):
    """Heatmap of the seasonality index: 1 = an average month."""
    z = [season_store["seasonality_index"].reindex(range(1, 13)).tolist()]
    names = ["Whole store"]
    for sub in season_flagged.index:
        z.append(season_flagged.loc[sub].reindex(range(1, 13)).tolist())
        names.append(sub)
    hi = max(max(row) for row in z)
    fig = go.Figure(go.Heatmap(
        z=z, x=MONTHS, y=names, zmid=1, zmin=0, zmax=max(2, hi),
        colorscale=[[0, RED], [0.5, NEUTRAL], [1, BLUE]], xgap=2, ygap=2,
        texttemplate="%{z:.1f}", textfont=dict(size=12),
        colorbar=dict(title=dict(text="vs average<br>month", font=dict(size=12)), thickness=12,
                      tickvals=[0, 1, 2], ticktext=["0", "1 = avg", "2x"]),
        hovertemplate="%{y}, %{x}<br>%{z:.2f}x an average month<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", side="top")
    return style(fig, 60 + 46 * len(names))


def q2_rescue(rescue, flagged):
    """Share of orders with a loss-making discounted line that still make money overall."""
    t = rescue.copy()
    t["rate_pct"] = t["rescue_rate"] * 100
    t = t.sort_values("rate_pct")
    colors = [BLUE if s in flagged else GREY for s in t.index]
    fig = go.Figure(go.Bar(
        x=t["rate_pct"], y=t.index, orientation="h", marker=dict(color=colors, cornerradius=4),
        text=[f"{v:.0f}%" for v in t["rate_pct"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK, size=13),
        customdata=t[["rescued_orders", "orders_with_discounted_loss"]].values,
        hovertemplate="<b>%{y}</b><br>%{customdata[0]:.0f} of %{customdata[1]:.0f} orders still profitable<extra></extra>",
    ))
    fig.update_xaxes(title="Orders still profitable overall (%)", range=[0, 100])
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    return style(fig, 440)


# ---------------------------------------------------------------- ML

def pretty_feature(name):
    for prefix, label in [("sub_category_", "Sub-category: "), ("region_", "Region: "),
                          ("segment_", "Segment: "), ("ship_mode_", "Ship mode: ")]:
        if name.startswith(prefix):
            return label + name[len(prefix):]
    return {"discount": "Discount", "quantity": "Quantity", "order_month": "Order month"}.get(name, name)


def ml_importance(importance, top=5):
    t = importance.head(top)[::-1]
    fig = go.Figure(go.Bar(
        x=t.values * 100, y=[pretty_feature(n) for n in t.index], orientation="h",
        marker=dict(color=BLUE, cornerradius=4),
        text=[f"{v * 100:.1f}%" for v in t.values], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK, size=13),
        hovertemplate="%{y}: %{x:.1f}% of the tree's decisions<extra></extra>",
    ))
    fig.update_xaxes(title="Share of the model's decision power (%)", range=[0, 112])
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    return style(fig, 300)


def ml_risk(risk_by_band, flagged):
    """Average predicted loss risk for each flagged sub-category and discount band."""
    t = risk_by_band[risk_by_band["sub_category"].isin(flagged)]
    pivot = t.pivot(index="sub_category", columns="discount_band", values="avg_loss_risk")
    pivot = pivot.reindex(index=flagged, columns=BAND_ORDER)
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=BAND_ORDER, y=pivot.index, zmin=0, zmax=1,
        colorscale=[[0, NEUTRAL], [0.5, "#f0a3a2"], [1, RED]], xgap=2, ygap=2,
        texttemplate="%{z:.0%}", textfont=dict(size=13),
        colorbar=dict(title=dict(text="loss risk", font=dict(size=12)), thickness=12, tickformat=".0%", len=0.85),
        hovertemplate="%{y}, discount %{x}<br>Predicted loss risk %{z:.0%}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", side="top", title="Discount band")
    return style(fig, 80 + 52 * len(flagged))
