"""
app.py -- Lytrize application entry point.
==========================================

This is the ONLY file Streamlit runs directly:
    streamlit run app.py

What it does?
  1. Configure the Streamlit page (title, icon, layout).
  2. Restore the logged-in user from a URL token on browser refresh.
  3. Restore an in-progress analysis draft from the database (fix #9).
  4. Guard every route -- unauthenticated users always land on "auth".
  5. Sync the current page name into the URL (?p=...) for browser history.
  6. Route to the correct page module based on st.session_state.page.

──────────────────────────────────────────────────────────────────────
ROUTING MAP  (st.session_state.page  →  function called)
──────────────────────────────────────────────────────────────────────
  "auth"      → modules/pages/auth.py      :: page_auth()
  "home"      → modules/pages/home.py      :: page_home()
  "upload"    → modules/pages/upload.py    :: page_upload()
  "analysis"  → modules/pages/analysis.py  :: page_analysis()
  "dashboard" → modules/pages/dashboard.py :: page_dashboard()
  "profile"   → modules/pages/auth.py      :: page_profile()

──────────────────────────────────────────────────────────────────────
URL QUERY PARAMETERS
──────────────────────────────────────────────────────────────────────
  ?t=<token>   -- persistent login token written by auth.py after sign-in
  ?p=<page>    -- current page slug; synced on every rerun
  ?sid=<int>   -- session ID to open in view-only dashboard mode
  ?nav=home    -- logo link signal to force-navigate to home

──────────────────────────────────────────────────────────────────────
CONTRIBUTING -- adding a new page
──────────────────────────────────────────────────────────────────────
  1. Create  modules/pages/my_page.py  with a  page_my_page()  function.
  2. Import it below.
  3. Add  elif p == "my_page": page_my_page()  in the router section.
  4. Navigate to it anywhere with:
       st.session_state.page = "my_page"; st.rerun()
"""
import streamlit as st

# Hide Streamlit's default loading spinner
st.markdown("""
<style>
[data-testid="stLoadingContainer"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

import warnings
import json

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Lytrize",
    page_icon="assets/lytrize.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from modules.database import init_db as _init_db, validate_token, get_draft

@st.cache_resource
def init_db():
    """Run once per server process."""
    _init_db()

from modules.ui.css import inject_css
from modules.pages.auth      import page_auth, page_profile
from modules.pages.home      import page_home
from modules.pages.upload    import page_upload
from modules.pages.analysis  import page_analysis
from modules.pages.dashboard import page_dashboard

def _restore_draft(user_id: int) -> None:
    """Reload an in-progress analysis session from the database."""
    import plotly.io as pio
    draft = get_draft(user_id)
    if not draft: return

    st.session_state.page = draft.get("page", "home")
    st.session_state.file_name       = draft.get("file_name", "")
    st.session_state.dashboard_title = draft.get("dashboard_title", "")
    st.session_state.layout_mode     = draft.get("layout_mode", "portrait")

    try: st.session_state.kpis = json.loads(draft.get("kpis_json", "[]"))
    except Exception: st.session_state.kpis = []

    if draft.get("editing_session_id"):
        st.session_state.editing_session_id   = draft["editing_session_id"]
        st.session_state.editing_session_name = draft.get("editing_session_name", "")

    try:
        charts_raw = json.loads(draft.get("charts_json", "[]"))
        charts = []
        for item in charts_raw:
            uid, title, fig_json = item.get("uid", ""), item.get("title", ""), item.get("fig_json", "")
            try:
                fig = pio.from_json(fig_json)
                charts.append((uid, title, fig))
                st.session_state[f"desc_{uid}"]          = item.get("desc", "")
                st.session_state[f"auto_insights_{uid}"] = item.get("auto_insights", [])
                st.session_state[f"chart_type_{uid}"]    = item.get("chart_type", "")
                st.session_state[f"chart_meta_{uid}"]    = item.get("meta", {})
            except Exception: pass
        if charts: st.session_state.charts = charts
    except Exception: pass

    try:
        meta_map = json.loads(draft.get("chart_meta_json", "{}"))
        for k, v in meta_map.items():
            if k not in st.session_state: st.session_state[k] = v
    except Exception: pass

def main() -> None:
    init_db()
    inject_css()

    url_token      = st.query_params.get("t", "")
    url_page       = st.query_params.get("p", "auth")
    url_session_id = st.query_params.get("sid", "")
    url_nav        = st.query_params.get("nav", "")

    if url_token and "user_id" not in st.session_state:
        restored = validate_token(url_token)
        if restored:
            st.session_state.user_id  = restored[0]
            st.session_state.username = restored[1]
            _restore_draft(restored[0])
            if url_page not in ("auth", "home") or url_session_id:
                st.session_state.page = url_page
            if url_session_id:
                try:
                    st.session_state.view_session_id = int(url_session_id)
                    st.session_state.pop("_view_charts", None)
                    st.session_state.pop("_view_session_id_loaded", None)
                except Exception: pass

    if "user_id" not in st.session_state:
        st.session_state.page = "auth"
    elif "page" not in st.session_state:
        st.session_state.page = "home"

    if "user_id" in st.session_state and url_nav == "home":
        for k in ["view_session_id", "_view_charts", "_vsid", "_view_session_id_loaded", "dashboard_title", "kpis", "layout_mode"]:
            st.session_state.pop(k, None)
        st.session_state.page = "home"
        st.query_params.pop("nav", None)

    st.query_params["p"] = st.session_state.page
    if st.session_state.get("view_session_id"):
        st.query_params["sid"] = st.session_state.view_session_id
    else:
        st.query_params.pop("sid", None)

    p = st.session_state.page
    if   p == "auth":      page_auth()
    elif p == "home":      page_home()
    elif p == "upload":    page_upload()
    elif p == "analysis":  page_analysis()
    elif p == "dashboard": page_dashboard()
    elif p == "profile":   page_profile()

if __name__ == "__main__":
    main()