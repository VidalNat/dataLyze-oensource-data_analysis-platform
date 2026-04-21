"""
modules/pages/analysis.py — Main analysis selection & chart generation page.

KEY ARCHITECTURE NOTE:
  data_quality uses st.button() widgets internally, so it CANNOT be called
  inside st.form(). It is handled in a separate code path outside the form.
  Any future analysis module that uses st.button/st.selectbox interactively
  should be added to _NO_FORM in modules/analysis/__init__.py.
"""

import streamlit as st
from modules.database import validate_token, log_activity
from modules.analysis import (
    ANALYSIS_OPTIONS, _NEEDS_AXES, _NO_FORM,
    _axis_selector, _run,
)
from modules.analysis.runners import run_descriptive
from modules.analysis.data_quality import run_data_quality
from modules.analysis.outlier import OUTLIER_HELP
from modules.charts import generate_chart_insights
import uuid


def page_analysis():
    token = st.query_params.get("t", "")
    if token and "user_id" not in st.session_state:
        restored = validate_token(token)
        if restored:
            st.session_state.user_id  = restored[0]
            st.session_state.username = restored[1]
            st.session_state.page     = "analysis"
            st.rerun()

    df = st.session_state.get("df")
    if df is None:
        st.session_state.page = "upload"; st.rerun()

    if "charts"             not in st.session_state: st.session_state.charts             = []
    if "selected_analyses"  not in st.session_state: st.session_state.selected_analyses  = []

    a, b = st.columns([1, 10])
    with a:
        if st.button("← Home"):
            st.session_state.page = "home"; st.rerun()

    st.markdown("## 🔬 Select Analysis Type")
    done   = set(st.session_state.selected_analyses)
    active = st.session_state.get("_active_analysis")
    cols   = st.columns(4)

    for i, opt in enumerate(ANALYSIS_OPTIONS):
        with cols[i % 4]:
            border = ("border-color:#4f6ef7;box-shadow:0 0 0 3px rgba(79,110,247,0.15);"
                      if opt["id"] == active else "")
            st.markdown(
                f'<div class="ag-card" style="{border}">'
                f'<h4>{opt["icon"]} {opt["name"]}</h4>'
                f'<small>{opt["desc"]}</small></div>',
                unsafe_allow_html=True)
            if st.button("▶ Run", key=f"btn_{opt['id']}"):
                st.session_state["_active_analysis"] = opt["id"]; st.rerun()

    # ── Active analysis panel ──────────────────────────────────────────────────
    if active:
        st.markdown("---")
        analysis_name = next(o["name"] for o in ANALYSIS_OPTIONS if o["id"] == active)

        # ── data_quality: runs OUTSIDE st.form (contains st.button widgets) ───
        if active in _NO_FORM:
            st.markdown(f"### {analysis_name}")
            df_current = st.session_state.get("df", df)
            new_charts_raw = run_data_quality(df_current)
            new_charts = [(str(uuid.uuid4())[:8], title, fig) for title, fig in new_charts_raw]

            st.markdown("---")
            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                if st.button("✅ Add Charts to Analysis", key="dq_submit"):
                    if new_charts:
                        st.session_state.charts.extend(new_charts)
                        st.session_state._last_analysis_type = active
                        if active not in st.session_state.selected_analyses:
                            st.session_state.selected_analyses.append(active)
                        log_activity(st.session_state.get("user_id", 0), "analysis_run",
                                     f"type={active} charts_added={len(new_charts)}")
                    st.session_state["_active_analysis"] = None
                    st.rerun()
            with c2:
                if st.button("✕ Close", key="dq_cancel"):
                    st.session_state["_active_analysis"] = None; st.rerun()

        # ── All other analyses: safe to use st.form ───────────────────────────
        else:
            with st.form(key=f"config_form_{active}"):
                st.markdown(f"### Configure {analysis_name}")
                kwargs = {}
                if active in _NEEDS_AXES:
                    kwargs = _axis_selector(active, df)

                c1, c2, _ = st.columns([1, 1, 4])
                with c1: submitted = st.form_submit_button("▶ Generate Charts")
                with c2: cancelled = st.form_submit_button("✕ Close")

                if submitted:
                    if active == "descriptive":
                        if active not in st.session_state.selected_analyses:
                            st.session_state.selected_analyses.append(active)
                        log_activity(st.session_state.get("user_id", 0), "analysis_run",
                                     "type=descriptive")
                        st.session_state["_active_analysis"] = None
                        st.rerun()
                    else:
                        new_charts = _run(active, df, **kwargs)
                        if new_charts is not None:
                            if new_charts:
                                st.session_state.charts.extend(new_charts)
                                st.session_state._last_analysis_type = active
                                if active not in st.session_state.selected_analyses:
                                    st.session_state.selected_analyses.append(active)
                                log_activity(
                                    st.session_state.get("user_id", 0), "analysis_run",
                                    f"type={active} charts_added={len(new_charts)} "
                                    f"kwargs={str(kwargs)[:200]}")
                            st.session_state["_active_analysis"] = None
                            st.rerun()
                elif cancelled:
                    st.session_state["_active_analysis"] = None; st.rerun()

    # ── Descriptive output ─────────────────────────────────────────────────────
    if "descriptive" in st.session_state.selected_analyses:
        st.markdown("---")
        st.markdown("### 🗂️ Descriptive Output")
        run_descriptive(df)

    # ── Generated charts ───────────────────────────────────────────────────────
    if st.session_state.charts:
        st.markdown("---")
        h1, h2 = st.columns([5, 1])
        with h1: st.markdown("## 📈 Generated Charts")
        with h2:
            if st.button("🗑️ Clear All"):
                n = len(st.session_state.charts)
                log_activity(st.session_state.get("user_id", 0), "charts_cleared_all", f"count={n}")
                st.session_state.charts = []
                st.session_state.selected_analyses = []
                st.rerun()

        for uid, title, fig in st.session_state.charts:
            c1, c2 = st.columns([11, 1])
            with c1: st.markdown(f"#### {title}")
            with c2:
                if st.button("✕", key=f"del_{uid}"):
                    log_activity(st.session_state.get("user_id", 0), "chart_deleted",
                                 f"title='{title}'")
                    st.session_state.charts = [c for c in st.session_state.charts if c[0] != uid]
                    st.rerun()
            st.plotly_chart(fig, use_container_width=True)

            # Outlier help banner shown directly below outlier charts
            if "outlier" in title.lower() or "Outliers:" in title:
                st.info(OUTLIER_HELP)

            chart_type = st.session_state.get("_last_analysis_type", "")
            col_descs  = st.session_state.get("col_descriptions", {})
            insights   = generate_chart_insights(chart_type, title, fig, col_descs)
            if insights:
                with st.expander("💡 Auto Insights", expanded=True):
                    for ins in insights:
                        st.markdown(f"- {ins}")

            st.text_area(
                "✍️ Chart Notes & Insights (Will be saved to Dashboard)",
                value=st.session_state.get(f"desc_{uid}", ""),
                key=f"desc_{uid}",
                placeholder="Add your own findings or observations here...")

        if st.button("🎯 Proceed to Dashboard →"):
            log_activity(st.session_state.get("user_id", 0), "proceed_to_dashboard",
                         f"charts={len(st.session_state.charts)}")
            st.session_state.page = "dashboard"; st.rerun()
