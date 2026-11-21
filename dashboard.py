"""
Step 4 - Dash dashboard.

Tells the story top to bottom: where the problem is (Q1), where profit breaks,
when to test and what to keep (Q2), the ML check, and the recommendation.
The dropdown in Q2 lets you pick any sub-category (callback).

Run:  python dashboard.py   then open http://127.0.0.1:8050
"""

from dash import Dash, Input, Output, callback, dcc, html

import figures
from story import build_story, money, pct

story = build_story()
R, ML, F = story["results"], story["ml"], story["facts"]
K = R["kpis"]
GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


def graph(fig, graph_id=None):
    """A Dash graph whose box is exactly as tall as the figure (otherwise sections overlap)."""
    kwargs = {"id": graph_id} if graph_id else {}
    return dcc.Graph(figure=fig, config=GRAPH_CONFIG, style={"height": f"{fig.layout.height}px"}, **kwargs)


def kpi(value, label):
    return html.Div([html.B(value), html.Span(label)], className="kpi")


def table(df):
    return html.Table([
        html.Thead(html.Tr([html.Th(c) for c in df.columns])),
        html.Tbody([html.Tr([html.Td(str(v)) for v in row]) for row in df.values]),
    ])


header = html.Header(className="band head", children=html.Div(className="wrap", children=[
    html.P(f"Superstore discount analysis · Kaggle Superstore · {K['lines']:,} order lines", className="meta"),
    html.H1(f"Discounts above 20% lose money on {F['deep_loss_share']} of lines. "
            f"Five strong-selling sub-categories need smaller discounts."),
    html.P("Decision: where should Superstore keep its discounts, and where should it test smaller "
           "ones to improve profit while protecting sales?", className="lede"),
    html.Div(className="kpis", children=[
        kpi(money(K["total_sales"]), "Sales"),
        kpi(money(K["total_profit"]), "Profit"),
        kpi(F["store_margin"], "Store margin"),
        kpi(pct(K["loss_lines_share"]), "Order lines losing money"),
        kpi(f"{F['no_discount_losses']} of {F['no_discount_lines']:,}", "Undiscounted lines losing money"),
    ]),
]))

q1 = html.Section(className="band", id="q1", children=html.Div(className="wrap", children=[
    html.H2("Q1 · Which sub-categories sell well but earn little?"),
    html.P(f"Strong sales = at or above the median sub-category. Weak profit = margin below the store's {F['store_margin']}.",
           className="q"),
    html.Div(className="pair", children=[
        html.Div([
            html.H3(f"{F['n_flagged']} of {F['n_subcats']} sub-categories bring {F['flagged_sales_share']} "
                    f"of sales at a {F['flagged_margin']} margin"),
            graph(figures.q1_scatter(R["summary"], K["store_margin"])),
            html.P(f"Flagged: {F['flagged_names']}.", className="note"),
        ]),
        html.Div([
            html.H3(f"They lose {F['flagged_discount_loss']} on discounted lines that lose money"),
            graph(figures.q1_discount_loss(R["summary"])),
            html.P(f"In the flagged groups, lines discounted up to 20% earn {F['flagged_profit_low']}; lines above 20% "
                   f"lose {F['flagged_profit_deep'].lstrip('-')}. {F['biggest_loss_subcat']} loses the most "
                   f"({F['biggest_loss_value']}) but is not flagged: its overall margin ({F['biggest_loss_margin']}) "
                   f"stays above the store's.", className="note"),
        ]),
    ]),
]))

choices = ["Whole store"] + R["flagged"] + sorted(set(R["summary"].index) - set(R["flagged"]))

q2 = html.Section(className="band", id="q2", children=html.Div(className="wrap", children=[
    html.H2("Q2 · Where does profit break, when to test, what to keep?"),
    html.H3(f"Profit turns negative above 20% discount; for {F['early_break_names']} already at 20%"),
    html.Div(className="controls", children=[
        html.Label("Show margin by discount band for", htmlFor="band-choice"),
        dcc.Dropdown(id="band-choice", options=choices, value="Whole store", clearable=False),
    ]),
    graph(figures.q2_band_single(R["bands_store"]), graph_id="band-chart"),
    html.P(id="band-note", className="note"),
    html.Div(className="pair", children=[
        html.Div([
            html.H3(f"Sales peak in {F['peak_months']} ({F['peak_low']}-{F['peak_high']}x an average month), "
                    f"yet discounts stay at {F['discount_month_low']}-{F['discount_month_high']} all year"),
            graph(figures.q2_seasonality(R["season_store"], R["season_flagged"])),
            html.P("Peak months are the time to test smaller discounts: demand is strongest, and the extra "
                   f"volume gives a faster answer. {F['quiet_month']} is the quietest month ({F['quiet_value']}x).",
                   className="note"),
        ]),
        html.Div([
            html.H3(f"Few loss-making discounts are rescued by the basket: {F['rescue_low']} "
                    f"({F['rescue_low_name']}) to {F['rescue_high']} ({F['rescue_high_name']})"),
            graph(figures.q2_rescue(R["rescue"], R["flagged"])),
            html.P("Basket rescue rate: of the orders holding a discounted line that loses money, the share still "
                   f"profitable overall. {F['single_line_share']} of orders have a single line, so most discounts "
                   "cannot pull in other products.", className="note"),
        ]),
    ]),
]))

tree, base = F["tree"], F["baseline"]
ml_section = html.Section(className="band", id="ml", children=html.Div(className="wrap", children=[
    html.H2("ML check · A decision tree predicts which lines lose money"),
    html.P("Inputs: discount, quantity, month, sub-category, region, segment, ship mode. 70% train / 30% test "
           f"({F['test_lines']:,} lines). Its predicted probability is the loss-risk indicator.", className="q"),
    html.Div(className="pair", children=[
        html.Div([
            html.H3(f"Discount carries {F['discount_importance']} of the model's decisions; Storage is the main exception"),
            graph(figures.ml_importance(ML["importance"])),
            html.Table(className="metrics", children=[
                html.Thead(html.Tr([html.Th("Test set, loss lines"), html.Th("Decision tree"),
                                    html.Th("Rule: discount above 20%")])),
                html.Tbody([
                    html.Tr([html.Td(name), html.Td(pct(tree[key])), html.Td(pct(base[key]))])
                    for name, key in [("Precision: flagged lines that really lose", "precision"),
                                      ("Recall: losing lines the model catches", "recall"),
                                      ("F1: balance of the two", "f1")]
                ]),
            ]),
            html.P("The tree's first split falls between 20% and 30% discount, confirming the break point found in "
                   f"Q2. It catches more losing lines than the simple rule (recall {pct(tree['recall'])} vs "
                   f"{pct(base['recall'])}) because it learns that Storage loses money at 20%.", className="note"),
        ]),
        html.Div([
            html.H3("Predicted loss risk by discount band, flagged sub-categories"),
            graph(figures.ml_risk(ML["risk_by_band"], R["flagged"])),
            html.Details([html.Summary("Full tree rules"), html.Pre(ML["rules"])]),
        ]),
    ]),
]))

recommendation = html.Section(className="band", id="recommendation", children=html.Div(className="wrap", children=[
    html.H2("Recommendation"),
    html.P([html.B("Where: "), "stop discounts above 20% in the flagged sub-categories, and test 10% where 20% "
            "already loses money or leaves a thin margin. ", html.B("When: "), f"run the tests in {F['peak_months']}. ",
            html.B("Keep: "), "discounts up to 20% where the margin stays healthy; basket rescue is too low to "
            "justify loss-making discounts."], className="when"),
    table(story["recommendations"]),
    html.P([html.B("Limit: "), "this is historical data, not an experiment. Deeply discounted orders may differ in "
            "region or size, so we cannot prove a smaller discount keeps sales. That is why we recommend tests, "
            "not cuts."], className="note"),
]))

app = Dash(__name__, title="Superstore discount dashboard")
app.layout = html.Div([header, q1, q2, ml_section, recommendation])


@callback(Output("band-chart", "figure"), Output("band-note", "children"), Input("band-choice", "value"))
def update_band_chart(choice):
    """Interaction: redraw the margin-by-band chart for the chosen group."""
    if choice == "Whole store":
        bands = R["bands_store"]
    else:
        bands = R["bands_all"][R["bands_all"]["sub_category"] == choice]
    negative = bands[bands["margin"] < 0]["discount_band"].astype(str).tolist()
    breaks = f"profit turns negative at {negative[0]}" if negative else "profit stays positive in every band"
    quantities = ", ".join(f"{b} {q:.1f}" for b, q in zip(bands["discount_band"].astype(str), bands["avg_quantity"]))
    note = f"{choice}: {breaks}. Units per order line by band: {quantities}."
    return figures.q2_band_single(bands), note


if __name__ == "__main__":
    app.run(debug=True)
