"""modules/pages/dashboard.py — Dashboard view, save, export page."""

import streamlit as st
from modules.database import (
    validate_token, log_activity,
    save_session_db, update_session_db, get_session_charts,
)
from modules.charts import charts_to_json
from modules.export import generate_html_report, generate_pdf_report


def page_dashboard():
    token = st.query_params.get("t", "")
    if token and "user_id" not in st.session_state:
        restored = validate_token(token)
        if restored:
            st.session_state.user_id  = restored[0]
            st.session_state.username = restored[1]
            st.session_state.page     = "home"
            st.rerun()

    viewing_saved = "view_session_id" in st.session_state
    if viewing_saved:
        charts = get_session_charts(st.session_state.view_session_id)
        sname  = st.session_state.get("view_session_name", "Saved Session")
    else:
        charts = []
        for uid, title, fig in st.session_state.get("charts", []):
            charts.append((uid, title, fig, st.session_state.get(f"desc_{uid}", "")))
        sname = f"Analysis — {st.session_state.get('file_name','')}"

    if st.button("← Back"):
        if viewing_saved:
            st.session_state.pop("view_session_id", None)
        st.session_state.page = "home" if viewing_saved else "analysis"
        st.rerun()

    st.markdown(f"## 📊 {sname}")

    if not viewing_saved:
        is_editing = "editing_session_id" in st.session_state
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            default_name = st.session_state.get("editing_session_name", sname) if is_editing else sname
            sname_in = st.text_input("Session name", value=default_name)
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Save Session"):
                save_session_db(
                    st.session_state.user_id, sname_in,
                    st.session_state.file_name,
                    st.session_state.df.shape[0] if st.session_state.get("df") is not None else 0,
                    st.session_state.df.shape[1] if st.session_state.get("df") is not None else 0,
                    st.session_state.selected_analyses,
                    charts_to_json(st.session_state.charts))
                log_activity(st.session_state.user_id, "dashboard_saved",
                             f"charts={len(charts)} session='{sname_in}'")
                st.session_state.pop("editing_session_id", None)
                st.session_state.pop("editing_session_name", None)
                st.success("✅ Saved as new session!")
        with c3:
            if is_editing:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 Update Saved Session"):
                    eid = st.session_state.editing_session_id
                    update_session_db(
                        eid, sname_in,
                        charts_to_json(st.session_state.charts),
                        st.session_state.selected_analyses,
                        st.session_state.user_id)
                    st.success(f"✅ Session '{sname_in}' updated!")
                    st.session_state.pop("editing_session_id", None)
                    st.session_state.pop("editing_session_name", None)

    st.markdown("---")

    if charts:
        exp1, exp2, _ = st.columns([2, 2, 4])
        with exp1:
            html_data = generate_html_report(charts, sname)
            st.download_button(
                label="🌐 Download as Interactive HTML",
                data=html_data,
                file_name=f"{sname.replace(' ', '_')}.html",
                mime="text/html",
                use_container_width=True)
        with exp2:
            with st.spinner("Generating PDF..."):
                try:
                    pdf_data = generate_pdf_report(charts, sname)
                    st.download_button(
                        label="📄 Download as PDF",
                        data=pdf_data,
                        file_name=f"{sname.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True)
                except Exception as e:
                    st.error(f"⚠️ PDF generation failed (ensure kaleido is installed). Error: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    for i in range(0, len(charts), 2):
        col1, col2 = st.columns(2)
        with col1:
            if i < len(charts):
                st.markdown(f"#### {charts[i][1]}")
                st.plotly_chart(charts[i][2], use_container_width=True)
                if charts[i][3]: st.info(f"📝 **Notes:** {charts[i][3]}")
        with col2:
            if i + 1 < len(charts):
                st.markdown(f"#### {charts[i+1][1]}")
                st.plotly_chart(charts[i+1][2], use_container_width=True)
                if charts[i+1][3]: st.info(f"📝 **Notes:** {charts[i+1][3]}")
