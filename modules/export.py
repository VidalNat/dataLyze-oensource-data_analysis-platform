"""
modules/export.py - HTML export engine.
========================================

Generates a self-contained HTML dashboard report from the active charts.
Open the downloaded file in any browser, then use File → Print → Save as PDF
for a pixel-perfect PDF with full chart rendering — no server-side dependencies.
"""

import re
import copy
import datetime
from html import escape
from modules.charts import clean_insight_text


# ── HTML helpers ──────────────────────────────────────────────────────────────
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FFFF"
    "\U00002500-\U00002BFF"
    "\U00002100-\U000024FF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]+", flags=re.UNICODE)

_ICON_MAP = {
    "💰": "$", "📊": "[chart]", "📐": "[med]", "🔢": "#",
    "⬇️": "v", "⬆️": "^", "📈": "%", "🔍": "[?]",
    "📅": "[dt]", "🏆": "1st", "📉": "[low]",
    "💡": "*", "📝": "Note:", "•": "-",
}

def _clean_pdf(text: str) -> str:
    s = str(text)
    for em, rep in _ICON_MAP.items():
        s = s.replace(em, rep)
    s = _EMOJI_RE.sub("", s)
    return s.encode("latin-1", "replace").decode("latin-1")


def _h(text) -> str:
    return escape(str(text), quote=True)


# ── HTML Export ───────────────────────────────────────────────────────────────
def generate_html_report(charts, session_name, orientation="portrait",  # Produces a self-contained HTML file; open in browser → print → PDF.
                         kpis=None, dashboard_title="", grid_cols_n=2,
                         inline_plotly=False):  # True = embed Plotly figures as JSON (smaller); False = CDN script.
    is_landscape = orientation == "landscape"  # Landscape uses a wider max-width and 3 columns instead of 2.
    max_width    = "1400px" if is_landscape else "1100px"
    # Use grid_cols_n for the CSS grid; full-width items span all columns
    grid_css_cols = f"repeat({grid_cols_n}, 1fr)"  # CSS grid column count matches the layout_mode setting.
    title        = dashboard_title or session_name
    safe_title   = _h(title)

    # KPI strip
    kpi_html = ""  # KPI strip rendered above the chart grid if any KPIs are defined.
    if kpis:
        change_style = lambda k: (
            f'color:{"#10b981" if k.get("change_pct",0)>=0 else "#ef4444"};font-weight:700'
            if "change_pct" in k else "")
        arrow = lambda k: ("▲ " if k.get("change_pct",0)>=0 else "▼ ") if "change_pct" in k else ""

        def _kpi_val_style(k, base_change):
            full = f'{k.get("prefix","")}{k.get("value","--")}{k.get("suffix","")}'
            size = "0.95rem" if len(full) > 16 else ("1.1rem" if len(full) > 12 else "1.4rem")
            wrap = "white-space:normal;word-break:break-word;overflow-wrap:anywhere;" if len(full) > 12 else ""
            return f"font-size:{size};{wrap}{base_change}"

        kpi_items = "".join(
            f'<div class="kpi-card">'
            f'<div class="kpi-icon">{_h(k.get("icon","📊"))}</div>'
            f'<div class="kpi-value" style="{_kpi_val_style(k, change_style(k))}">'
            f'{_h(arrow(k))}{_h(k.get("prefix",""))}{_h(k.get("value","--"))}{_h(k.get("suffix",""))}</div>'
            f'<div class="kpi-label">{_h(k.get("label","KPI"))}</div>'
            f'</div>'
            for k in kpis
        )
        kpi_html = f'<div class="kpi-row">{kpi_items}</div><hr>'

    # Chart blocks
    chart_blocks = ""
    for idx, item in enumerate(charts):
        uid, chart_title, fig, notes = item[:4]
        auto_insights = item[4] if len(item) > 4 else []
        meta          = item[6] if len(item) > 6 else {}

        display_title = meta.get("custom_title") or chart_title
        subtitle      = meta.get("subtitle", "")
        is_full       = meta.get("full_width", False)
        # Span all columns when full-width
        col_span      = f"grid-column: 1 / -1;" if is_full else ""

        # Make figure responsive -- clear the embedded title (rendered via <h2> below)
        fig_resp = copy.deepcopy(fig)
        fig_resp.update_layout(title_text="")   # title shown as <h2>, not inside chart
        is_horiz = any(getattr(t, "orientation", "v") == "h"
                       for t in fig_resp.data if hasattr(t, "orientation"))
        if is_horiz:
            fig_resp.update_yaxes(tickfont=dict(size=11), automargin=True)
            fig_resp.update_xaxes(tickfont=dict(size=11))
            fig_resp.update_layout(margin=dict(l=130, r=30, t=20, b=30))
        else:
            fig_resp.update_xaxes(tickangle=-35, tickfont=dict(size=11), automargin=True)
            fig_resp.update_yaxes(tickfont=dict(size=11), automargin=True)
            fig_resp.update_layout(margin=dict(l=30, r=30, t=20, b=80))
        fig_resp.update_layout(autosize=True, width=None, height=400,
                               paper_bgcolor="white", plot_bgcolor="white")

        # inline_plotly=True embeds the full JS so no CDN fetch is needed
        # (used by PDF path; CDN is fine for the HTML download).
        include_js  = (True if idx == 0 else False) if inline_plotly else ("cdn" if idx == 0 else False)
        chart_html  = fig_resp.to_html(full_html=False, include_plotlyjs=include_js,
                                       config={"responsive": True})

        insight_html = ""
        if auto_insights and meta.get("show_auto_insights", True):
            hidden  = set(meta.get("hidden_insights", []))
            visible = [ins for i, ins in enumerate(auto_insights) if i not in hidden]
            if visible:
                items_html = "".join(f"<li>{_h(clean_insight_text(ins))}</li>" for ins in visible)
                insight_html = (f'<div class="insights"><strong>Insights</strong>'
                                f'<ul>{items_html}</ul></div>')

        notes_str  = str(notes).strip() if notes else ""
        notes_html = (
            f'<div class="notes"><strong>Analysis Notes:</strong> {_h(notes_str)}</div>'
            if notes_str else ""
        )

        chart_blocks += (
            f'<div class="chart-card" style="{col_span}">'
            f'<h2>{_h(display_title)}</h2>'
            + (f'<p class="subtitle">{_h(subtitle)}</p>' if subtitle else "")
            + f'<div class="chart-wrap">{chart_html}</div>'
            + insight_html + notes_html
            + '</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} -- Lytrize</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    /* ── Base (screen) ───────────────────────────────────────────────── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      padding: 2rem;
      background: #f8fafc;
      color: #0f172a;
    }}
    .wrapper {{ max-width: {max_width}; margin: auto; width: 100%; }}

    .report-header {{ text-align: center; margin-bottom: 2rem; }}
    .report-header h1 {{ font-size: 2rem; font-weight: 800; color: #4f6ef7; }}
    .report-header .meta {{ font-size: 0.8rem; color: #64748b; margin-top: 0.4rem; }}

    .print-hint {{
       text-align: center;
      border: none;            
      padding: 0.5rem 3rem;   
      margin: 2rem auto 1.2rem;   
      width: fit-content;         
      font-size: 0.78rem;
      color: #94a3b8;
    }}

    .kpi-row {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; justify-content: center; }}
    .kpi-card {{
      background: white;
      border-radius: 12px;
      padding: 1rem 1.4rem;
      text-align: center;
      box-shadow: 0 2px 12px rgba(0,0,0,0.07);
      min-width: 130px;
      flex: 1;
      max-width: 220px;
      border: 1px solid #e2e8f0;
    }}
    .kpi-icon  {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
    .kpi-value {{ font-size: 1.4rem; font-weight: 800; color: #4f6ef7; line-height: 1.2; overflow: visible; }}
    .kpi-label {{ font-size: 0.72rem; color: #64748b; margin-top: 0.2rem; font-weight: 600;
                  text-transform: uppercase; letter-spacing: 0.06em; }}

    hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 1.5rem 0; }}

    .grid {{
      display: grid;
      grid-template-columns: {grid_css_cols};
      gap: 1.5rem;
      width: 100%;
    }}
    .chart-card {{
      background: white;
      border-radius: 14px;
      padding: 1.2rem;
      box-shadow: 0 2px 16px rgba(0,0,0,0.07);
      border: 1px solid #e2e8f0;
      min-width: 0;
      width: 100%;
      overflow: hidden;
    }}
    .chart-card h2 {{ font-size: 0.95rem; font-weight: 700; margin-bottom: 0.15rem; color: #1e293b; }}
    .subtitle {{ font-size: 0.78rem; color: #64748b; margin-bottom: 0.6rem; }}
    .chart-wrap {{ width: 100%; overflow: hidden; display: block; }}
    .chart-wrap .js-plotly-plot {{ width: 100% !important; display: block !important; }}
    .chart-wrap .plotly          {{ width: 100% !important; }}
    .chart-wrap .plot-container  {{ width: 100% !important; }}
    .chart-wrap svg.main-svg     {{ width: 100% !important; }}
    .insights {{
      background: #f0f4ff;
      border-left: 3px solid #4f6ef7;
      border-radius: 6px;
      padding: 0.6rem 0.9rem;
      margin-top: 0.7rem;
      font-size: 0.8rem;
    }}
    .insights strong {{ display: block; margin-bottom: 0.25rem; }}
    .insights ul {{ margin-left: 1rem; }}
    .insights li {{ margin-bottom: 0.2rem; line-height: 1.5; }}
    .notes {{
      background: #fdf4ff;
      padding: 0.6rem 0.9rem;
      border-left: 4px solid #8b5cf6;
      margin-top: 0.7rem;
      border-radius: 4px;
      font-size: 0.82rem;
      font-style: italic;
    }}

    /* ── Print styles ────────────────────────────────────────────────── */
    /* ── Print page preset: 6mm L/R, 5mm T/B (Overll best fit for dashboard) ───────────────────── */
    @page {{margin: 5mm 6mm;}}

    @media print {{
      /* Force browser to print backgrounds (colors, shadows) */
      * {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }}

      body {{
        background: white !important;
        padding: 0 !important;
        margin: 0 !important;
      }}

      /* Hide the on-screen hint when printing */
      .print-hint {{ display: none !important; }}

      .wrapper {{
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
      }}

      .report-header {{
        margin-bottom: 1rem;
        padding-top: 0.5rem;
      }}

      /* Keep each chart card on one page — never split mid-chart */
      .chart-card {{
        break-inside: avoid;
        page-break-inside: avoid;
        border: 1px solid #e2e8f0 !important;
        box-shadow: none !important;
        margin-bottom: 0.8rem;
      }}

      /* Keep KPI strip together */
      .kpi-row {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}

      .kpi-card {{
        box-shadow: none !important;
        border: 1px solid #e2e8f0 !important;
      }}

      /* Plotly SVGs: fill the card width in print */
      .chart-wrap svg.main-svg {{
        width: 100% !important;
        height: auto !important;
      }}

      hr {{ border-top: 1px solid #e2e8f0 !important; }}
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="report-header">
      <h1>&#128202; {safe_title}</h1>
      <div class="meta">Generated by Lytrize &middot; {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
    {kpi_html}
    <div class="grid">{chart_blocks}</div>
  </div>
   <div class="print-hint">
      &#128438; To save as PDF: <strong>Go to browser Setting/Ctrl+P &rarr; Print &rarr; Save as PDF.</strong>
      &nbsp;&middot; Keep <strong>Background graphics</strong> enabled for best results.
    </div>
  <script>
    function relayoutAll() {{
      if (typeof Plotly === 'undefined') return;
      document.querySelectorAll('.js-plotly-plot').forEach(function(el) {{
        try {{
          var w = el.closest('.chart-wrap');
          var width = w ? w.offsetWidth : el.offsetWidth;
          if (width > 0) Plotly.relayout(el, {{width: width, autosize: true}});
        }} catch(e) {{}}
      }});
    }}
    window.addEventListener('load', function() {{ setTimeout(relayoutAll, 200); }});
    window.addEventListener('resize', function() {{ setTimeout(relayoutAll, 100); }});
    window.addEventListener('beforeprint', function() {{ relayoutAll(); }});
  </script>
</body>
</html>"""


