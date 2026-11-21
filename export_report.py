"""
Step 4b - Static HTML report.

Builds the same story as the Dash app into one HTML file (reports/report.html).
The GitHub Actions workflow runs this script and publishes the file as an artifact,
because a live Dash app needs a running server and an HTML file opens anywhere.

Run:  python export_report.py
"""

import html
import os

import plotly.offline

import figures
from story import build_story, money, pct

OUTPUT = "reports/report.html"
CONFIG = {"displayModeBar": False, "responsive": True}


def chart(fig):
    return fig.to_html(full_html=False, include_plotlyjs=False, config=CONFIG, default_width="100%")


def table_html(df):
    head = "".join(f"<th>{html.escape(c)}</th>" for c in df.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>" for row in df.values
    )
    return f'<div class="scroll"><table class="stack"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def build_html(story):
    r, ml, f = story["results"], story["ml"], story["facts"]
    k = r["kpis"]
    lines = r["lines"]
    first, last = lines["order_date"].min(), lines["order_date"].max()
    tree, base = f["tree"], f["baseline"]
    mb, qb = f["margin_bands"], f["qty_bands"]

    kpis = [
        (money(k["total_sales"]), "Sales"),
        (money(k["total_profit"]), "Profit"),
        (f["store_margin"], "Store margin"),
        (pct(k["loss_lines_share"]), "Order lines losing money"),
        (f"{f['no_discount_losses']} of {f['no_discount_lines']:,}", "Undiscounted lines losing money"),
    ]
    kpi_html = "".join(f'<div class="kpi"><b>{v}</b><span>{label}</span></div>' for v, label in kpis)

    ml_table = (
        "<table class='metrics'><thead><tr><th>Test set, loss lines</th><th>Decision tree</th>"
        "<th>Rule: discount above 20%</th></tr></thead><tbody>"
        + "".join(
            f"<tr><td>{name}</td><td>{pct(tree[key])}</td><td>{pct(base[key])}</td></tr>"
            for name, key in [("Precision: flagged lines that really lose", "precision"),
                              ("Recall: losing lines the model catches", "recall"),
                              ("F1: balance of the two", "f1")]
        )
        + "</tbody></table>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Superstore discount report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@500;600&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-{plotly.offline.get_plotlyjs_version()}.min.js"></script>
<style>
/* VOICE: a newspaper graphics desk - the finding first, then the evidence, then what to do.
   IDEA: a printed analyst brief handed to a store manager.
   PICTURE: the sales-vs-margin map that circles the five problem sub-categories.
   COLOUR and TYPE: white page, near-black ink, mist band; blue = flagged / positive, red = loss. Space Grotesk + Inter.
   LAYOUT: headline band with key figures, then Q1, Q2, ML check and the recommendation table. */
:root{{color-scheme:light;--bg:#ffffff;--ink:#0b0b10;--ink2:#52514e;--mist:#eafaf2;--rule:#e1e0d9;--blue:#2a78d6;--red:#e34948}}
*{{box-sizing:border-box;min-width:0}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 Inter,system-ui,sans-serif;overflow-x:clip}}
.band{{padding:clamp(28px,4vw,56px) max(5vw,16px)}}
.wrap{{max-width:1240px;margin:0 auto}}
header.band{{background:var(--mist)}}
h1,h2,h3{{font-family:"Space Grotesk",Inter,sans-serif;font-weight:600;text-wrap:balance;margin:0}}
h1{{font-size:clamp(30px,4vw,48px);line-height:1.05;max-width:22ch}}
h2{{font-size:30px;line-height:1.1;margin-bottom:8px}}
h3{{font-size:21px;line-height:1.25;margin:32px 0 4px;font-weight:500}}
.lede{{font-size:19px;color:var(--ink2);max-width:62ch;margin:16px 0 0}}
.meta{{font-size:14px;color:var(--ink2);margin:0 0 12px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,180px),1fr));border-top:1px solid var(--ink);margin-top:28px}}
.kpi{{padding:14px 16px 4px 0;border-right:1px solid var(--rule)}}
.kpi:last-child{{border-right:0}}
.kpi b{{display:block;font:600 clamp(26px,3vw,36px)/1.1 "Space Grotesk",Inter,sans-serif;white-space:nowrap}}
.kpi span{{font-size:14px;color:var(--ink2)}}
nav{{display:flex;flex-wrap:wrap;gap:8px 24px;padding:14px max(5vw,16px);border-bottom:1px solid var(--rule);font-size:15px}}
nav a{{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}}
.q{{font-size:18px;color:var(--ink2);max-width:70ch;margin:0}}
.note{{font-size:15px;color:var(--ink2);max-width:75ch;margin:4px 0 0}}
.pair{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,520px),1fr));gap:24px 40px}}
section+section{{border-top:1px solid var(--rule)}}
table{{border-collapse:collapse;width:100%;font-size:15px}}
th,td{{text-align:left;padding:10px 12px 10px 0;border-bottom:1px solid var(--rule);vertical-align:top}}
th{{font-weight:600;border-bottom:1px solid var(--ink)}}
.metrics td:not(:first-child),.metrics th:not(:first-child){{text-align:right;white-space:nowrap}}
details{{margin-top:16px;font-size:14px}} pre{{overflow-x:auto;background:#f6f6f3;padding:12px;font-size:13px}}
.when{{font-size:18px;max-width:70ch}}
footer{{font-size:14px;color:var(--ink2)}}
.scroll{{overflow-x:auto}}
@media(max-width:600px){{table{{font-size:13px}}.stack thead{{display:none}}.stack tr{{display:grid;padding-block:10px}}.stack td{{display:flow-root;border:0;padding:3px 0;padding-inline-start:8em}}.stack td::before{{content:attr(data-l);float:inline-start;width:7.5em;margin-inline-start:-8em}}.kpi{{border-right:0}}}}
</style>
<script>new MutationObserver(()=>{{for(const c of document.querySelectorAll('.stack td:not([data-l])')){{let i=0,p=c;while(p=p.previousElementSibling)i+=p.colSpan;c.dataset.l=c.closest('table').rows[0].cells[i]?.textContent||''}}}}).observe(document,{{childList:true,subtree:true}})</script>
</head>
<body>
<header class="band"><div class="wrap">
<p class="meta">Superstore discount analysis &middot; Kaggle Superstore, {first:%b %Y} to {last:%b %Y} &middot; {k['lines']:,} order lines</p>
<h1>Discounts above 20% lose money on {f['deep_loss_share']} of lines. Five strong-selling sub-categories need smaller discounts.</h1>
<p class="lede">Decision: where should Superstore keep its discounts, and where should it test smaller ones to improve profit while protecting sales?</p>
<div class="kpis">{kpi_html}</div>
</div></header>
<nav><a href="#q1">Q1 Where is the problem</a><a href="#q2">Q2 Where it breaks, when to test, what to keep</a><a href="#ml">ML check</a><a href="#recommendation">Recommendation</a></nav>

<section class="band" id="q1"><div class="wrap">
<h2>Q1 &middot; Which sub-categories sell well but earn little?</h2>
<p class="q">Strong sales = at or above the median sub-category. Weak profit = margin below the store's {f['store_margin']}.</p>
<div class="pair">
<div><h3>{f['n_flagged']} of {f['n_subcats']} sub-categories bring {f['flagged_sales_share']} of sales at a {f['flagged_margin']} margin</h3>
{chart(figures.q1_scatter(r['summary'], k['store_margin']))}
<p class="note">Flagged: {f['flagged_names']}.</p></div>
<div><h3>They lose {f['flagged_discount_loss']} on discounted lines that lose money</h3>
{chart(figures.q1_discount_loss(r['summary']))}
<p class="note">In the flagged groups, lines discounted up to 20% earn {f['flagged_profit_low']}; lines above 20% lose {f['flagged_profit_deep'].lstrip('-')}.
{f['biggest_loss_subcat']} loses the most ({f['biggest_loss_value']}) but is not flagged: its overall margin ({f['biggest_loss_margin']}) stays above the store's.</p></div>
</div>
</div></section>

<section class="band" id="q2"><div class="wrap">
<h2>Q2 &middot; Where does profit break, when to test, what to keep?</h2>
<h3>Profit turns negative above 20% discount; for {f['early_break_names']} already at 20%</h3>
{chart(figures.q2_band_grid(r['bands_store'], r['bands_flagged'], r['flagged']))}
<p class="note">Whole store margin by band: {mb['0%']} with no discount, {mb['1-20%']} at 1-20%, {mb['21-40%']} at 21-40%, {mb['>40%']} above 40%.
Units per order line stay flat ({qb['0%']}, {qb['1-20%']}, {qb['21-40%']}, {qb['>40%']}): deeper discounts do not sell more units per line.</p>
<div class="pair">
<div><h3>Sales peak in {f['peak_months']} ({f['peak_low']}-{f['peak_high']}x an average month), yet discounts stay at {f['discount_month_low']}-{f['discount_month_high']} all year</h3>
{chart(figures.q2_seasonality(r['season_store'], r['season_flagged']))}
<p class="note">Peak months are the time to test smaller discounts: demand is strongest, and the extra volume gives a faster answer. {f['quiet_month']} is the quietest month ({f['quiet_value']}x).</p></div>
<div><h3>Few loss-making discounts are rescued by the basket: {f['rescue_low']} ({f['rescue_low_name']}) to {f['rescue_high']} ({f['rescue_high_name']})</h3>
{chart(figures.q2_rescue(r['rescue'], r['flagged']))}
<p class="note">Basket rescue rate: of the orders holding a discounted line that loses money, the share still profitable overall. {f['single_line_share']} of orders have a single line, so most discounts cannot pull in other products.</p></div>
</div>
</div></section>

<section class="band" id="ml"><div class="wrap">
<h2>ML check &middot; A decision tree predicts which lines lose money</h2>
<p class="q">Inputs: discount, quantity, month, sub-category, region, segment, ship mode. 70% train / 30% test ({f['test_lines']:,} lines). Its predicted probability is the loss-risk indicator.</p>
<div class="pair">
<div><h3>Discount carries {f['discount_importance']} of the model's decisions; Storage is the main exception</h3>
{chart(figures.ml_importance(ml['importance']))}
{ml_table}
<p class="note">The tree's first split falls between 20% and 30% discount, confirming the break point found in Q2. It catches more losing lines than the simple rule (recall {pct(tree['recall'])} vs {pct(base['recall'])}) because it learns that Storage loses money at 20%.</p></div>
<div><h3>Predicted loss risk by discount band, flagged sub-categories</h3>
{chart(figures.ml_risk(ml['risk_by_band'], r['flagged']))}
<details><summary>Full tree rules</summary><pre>{html.escape(ml['rules'])}</pre></details></div>
</div>
</div></section>

<section class="band" id="recommendation"><div class="wrap">
<h2>Recommendation</h2>
<p class="when"><b>Where:</b> stop discounts above 20% in the flagged sub-categories, and test 10% where 20% already loses money or leaves a thin margin.
<b>When:</b> run the tests in {f['peak_months']}. <b>Keep:</b> discounts up to 20% where the margin stays healthy; basket rescue is too low to justify loss-making discounts.</p>
{table_html(story['recommendations'])}
<p class="note"><b>Limit:</b> this is historical data, not an experiment. Deeply discounted orders may differ in region or size, so we cannot prove a smaller discount keeps sales. That is why we recommend tests, not cuts.</p>
</div></section>

<footer class="band"><div class="wrap">
Source: Kaggle Superstore dataset (vivek468). Generated by export_report.py from data/clean/superstore_clean.csv.
Discount bands: 0%, 1-20%, 21-40%, above 40%. Margin = profit / sales.
</div></footer>
<script>{{window.addEventListener('load',()=>{{for(const g of document.querySelectorAll('.plotly-graph-div'))Plotly.Plots.resize(g)}})}}</script>
</body>
</html>"""


if __name__ == "__main__":
    story = build_story()
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(build_html(story))
    print(f"Report written to {OUTPUT}")
