# 📊 DataLyze — Intelligent Data Analysis Platform

> Upload a dataset. Explore it visually. Share findings as a dashboard. No code required.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)
![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen)

---

## What is DataLyze?

DataLyze is an open-source, browser-based data analysis tool built with Python and Streamlit. You upload a CSV or Excel file, choose what you want to explore, and the platform generates interactive charts, data quality reports, and statistical summaries — all without writing a single line of code.

Think of it as a lightweight, self-hosted alternative to tools like Tableau or Power BI, but fully open and extensible by anyone.

**Who is it for?**
- Analysts who want fast exploratory analysis without setting up notebooks
- Teams that want a shared, browser-accessible dashboard tool
- Developers who want to add new analysis types as plugins

---

## What can it currently do?

| Feature | Description |
|---|---|
| 📂 Data Import | Upload CSV or Excel files |
| 🛠️ Column Manager | Add calculated columns, remove columns |
| 🔍 Type Inspector | Detect and convert column data types |
| 🏷️ Column Classifier | Classify columns as Numeric, Categorical, or Date/Time |
| 🧹 Data Quality | Detect missing values, duplicates (with primary key support) |
| 🗂️ Descriptive Stats | Mean, median, std, min, max summary table |
| 📐 Statistical | Aggregation bar charts with group-by |
| 📊 Distribution | Histogram + box plot per column |
| 🔗 Correlation | Pearson heatmap |
| 🏷️ Categorical Bar | Value counts and metric bars |
| 🍩 Pie & Donut | Proportion and share charts |
| ⏱️ Time Series | Line charts with date-part grouping |
| 🚨 Outlier Detection | IQR-based anomaly scatter with business guidance |
| 💡 Auto Insights | Rule-based plain-English chart observations |
| 💾 Sessions | Save, rename, delete, edit analysis sessions |
| 🌐 Export | Download dashboard as interactive HTML or static PDF |

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI & App | [Streamlit](https://streamlit.io) |
| Data | [Pandas](https://pandas.pydata.org), [NumPy](https://numpy.org) |
| Charts | [Plotly](https://plotly.com/python/) |
| Database | SQLite (default) · PostgreSQL (optional) |
| PDF Export | [FPDF2](https://py-fpdf2.readthedocs.io) + [Kaleido](https://github.com/plotly/Kaleido) |

---

## Getting Started (Run Locally)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/datalyze.git
cd datalyze

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

**Minimum requirements:** Python 3.9+

**Optional — for PDF export:**
```bash
pip install kaleido

Use test.csv from repo for data-analysis testing.
```

---

## Project Structure

```
datalyze/
│
├── app.py                          # Entry point. ~50 lines — just wires pages together.
├── requirements.txt
├── README.md
│
└── modules/                        # All logic lives here, split by responsibility
    │
    ├── database.py                 # DB init, user auth, sessions, tokens, activity log
    ├── charts.py                   # Colour palettes, Plotly layout defaults, auto-insight engine
    ├── export.py                   # HTML & PDF report generation
    │
    ├── ui/                         # Reusable UI widgets (not full pages)
    │   ├── css.py                  # Adaptive CSS injected once at startup
    │   ├── column_manager.py       # Add / Remove column widget
    │   └── column_tools.py         # Dtype transformer + column classifier widget
    │
    ├── analysis/                   # ← One file per analysis type. Add yours here.
    │   ├── __init__.py             # Central registry — ANALYSIS_OPTIONS, _RUNNERS, axis selector
    │   ├── descriptive.py          # Stats summary table
    │   ├── statistical.py          # Aggregation bar charts
    │   ├── distribution.py         # Histograms + box plots
    │   ├── correlation.py          # Pearson heatmap
    │   ├── categorical.py          # Category bar charts
    │   ├── pie_chart.py            # Pie / donut charts
    │   ├── time_series.py          # Time series line charts
    │   ├── data_quality.py         # Missing values + duplicate detection
    │   └── outlier.py              # IQR outlier scatter
    │
    └── pages/                      # One file per app screen
        ├── auth.py                 # Login & Registration
        ├── home.py                 # Home dashboard + saved sessions list
        ├── upload.py               # File upload + pre-processing
        ├── analysis.py             # Analysis selection + chart generation
        └── dashboard.py            # Chart dashboard + save/export
```

---

## How to Switch to PostgreSQL

By default DataLyze uses SQLite — zero setup needed. To switch to PostgreSQL:

1. `pip install psycopg2-binary`
2. In `modules/database.py`, replace `_connect()` with:
   ```python
   import psycopg2, os
   def _connect():
       return psycopg2.connect(os.environ["DATALYZE_DB_URL"])
   ```
3. Replace all `?` placeholders in that file with `%s`
4. Set the environment variable:
   ```
   DATALYZE_DB_URL=postgresql://user:password@localhost:5432/datalyze
   ```

No other files need changes.

---

## 👋 Welcome, Contributors!

We are genuinely happy you are here. DataLyze is designed so that you do not need to understand the whole codebase to add something useful. Most contributions only touch one or two files.

### The single most important thing to understand

**Every analysis type is its own file in `modules/analysis/`.** If you want to add a new chart or analysis, you create one file and register it in one place. The rest of the platform — the page layout, chart gallery, session saving, and export — picks it up automatically. You do not need to touch any page code.

---

## How to Add a New Analysis Type

Let us walk through adding a **Box Plot comparison** as a real example.

### Step 1 — Create your module

Create `modules/analysis/box_plot.py`:

```python
"""
modules/analysis/box_plot.py
Box plot comparison — shows spread and outliers across categories.
"""
import plotly.express as px
from modules.charts import chart_layout, COLORS, num_cols as _num_cols

def run_box_plot(df, x_cols=None, y_cols=None, palette=None, **kwargs):
    charts = []
    num = y_cols or _num_cols()[:4]
    cat = x_cols[0] if x_cols else None
    pal = palette or COLORS

    for i, col in enumerate(num):
        fig = px.box(
            df, x=cat, y=col, color=cat,
            title=f"Box Plot: {col}" + (f" by {cat}" if cat else ""),
            color_discrete_sequence=pal)
        fig.update_layout(**chart_layout())
        charts.append((f"Box: {col}", fig))

    return charts
```

**Your function must follow these rules:**
- Signature: `(df, **kwargs)` — always accept keyword arguments even if you do not use them
- Return: a `list` of `(title_string, plotly_figure)` tuples
- Do not call `st.rerun()` or `st.button()` inside — see the `_NO_FORM` note below if you need that

### Step 2 — Register it

Open `modules/analysis/__init__.py` and make three small changes:

```python
# 1. Import your function at the top
from modules.analysis.box_plot import run_box_plot

# 2. Add an entry to ANALYSIS_OPTIONS
{"id": "box_plot", "icon": "📦", "name": "Box Plot", "desc": "Spread & outlier comparison"},

# 3. Add to the _RUNNERS dict
"box_plot": run_box_plot,
```

### Step 3 — (Optional) Add axis configuration

If you want users to pick columns before running, add a block to `_axis_selector()` in `__init__.py` and add your ID to `_NEEDS_AXES`:

```python
elif aid == "box_plot":
    c1, c2 = st.columns(2)
    with c1: x = st.multiselect("Group by (category)", cat, max_selections=1)
    with c2: y = st.multiselect("Metrics", num, default=num[:3])
    x = x or None; y = y or num[:3]
```

**Done. Your analysis now appears on the platform automatically.**

---

## The `_NO_FORM` flag

The analysis configuration panel runs inside a `st.form()`. This means you **cannot use `st.button()` or interactive widgets inside your runner function** — Streamlit will crash with an error.

Most runners just build and return Plotly charts, so this never comes up. But if your analysis genuinely needs interactive cleaning buttons (like `data_quality.py` does), add your ID to `_NO_FORM` in `__init__.py`:

```python
_NO_FORM = {"data_quality", "your_analysis_id"}
```

The page will run your function outside the form in its own separate code path.

---

## Other Ways to Contribute

You do not have to add a new analysis. Other useful contributions:

| Area | Where to look |
|---|---|
| UI improvements | `modules/ui/` and `modules/pages/` |
| New export formats (Excel, PPTX) | `modules/export.py` |
| Better auto-insights | `generate_chart_insights()` in `modules/charts.py` |
| Bug fixes | Check open Issues |
| Tests | We have none yet — `pytest` coverage would be hugely valuable |
| Documentation | Improve this README or add docstrings to existing files |

---

## Contribution Workflow

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/datalyze.git
cd datalyze

# 2. Create a branch for your change
git checkout -b feature/box-plot-analysis

# 3. Make your changes, then commit
git add .
git commit -m "feat: add box plot analysis module"

# 4. Push and open a Pull Request on GitHub
git push origin feature/box-plot-analysis
```

**Branch naming:**
- `feature/short-description` — new feature
- `fix/short-description` — bug fix
- `docs/short-description` — documentation only

**Commit messages:**
- `feat:` new feature
- `fix:` bug fix
- `refactor:` code change with no behaviour change
- `docs:` documentation only

---

## Pull Request Checklist

Before submitting, please confirm:

- [ ] Runs locally without errors (`streamlit run app.py`)
- [ ] New analysis modules follow the `(df, **kwargs) → list[(title, fig)]` signature
- [ ] No hardcoded colours — use `COLORS` or the `palette` argument from `modules/charts.py`
- [ ] No `st.button()` or `st.rerun()` inside runner functions (unless using `_NO_FORM`)
- [ ] Docstring at the top of any new file explaining what it does

---

## License

MIT — free to use, modify, and distribute. See `LICENSE`.

---

## Questions?

Open an [Issue](https://github.com/your-username/datalyze/issues) and we will get back to you.

---

*Built with Streamlit and Plotly. Designed to be simple, open, and easy to extend.*
