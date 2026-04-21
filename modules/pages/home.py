"""modules/pages/home.py — Home dashboard page."""

import streamlit as st
from modules.database import (
    validate_token, revoke_token, log_activity,
    get_user_sessions, get_session_charts,
    rename_session_db, delete_session_db,
)


def page_home():
    token = st.query_params.get("t", "")
    if token and "user_id" not in st.session_state:
        restored = validate_token(token)
        if restored:
            st.session_state.user_id  = restored[0]
            st.session_state.username = restored[1]
            st.session_state.page     = "home"
            st.rerun()

    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown('<div class="brand">📊 DataLyze</div>', unsafe_allow_html=True)
    with c2:
        if st.button("Logout"):
            tok = st.query_params.get("t", "")
            if tok: revoke_token(tok)
            log_activity(st.session_state.get("user_id", 0), "logout")
            st.query_params.clear()
            st.session_state.clear()
            st.session_state.page = "auth"
            st.rerun()
    st.markdown("---")

    st.markdown(f"""
    <div class="welcome-banner">
        <div style="font-size:0.8rem;opacity:0.8;margin-bottom:0.4rem;">DASHBOARD OVERVIEW</div>
        <div style="font-size:2.2rem;font-weight:800;font-family:'Sora';margin-bottom:0.5rem;">
            Welcome to Datalyze !!
        </div>
        <div style="font-size:1rem;opacity:0.9;">
            Hello, {st.session_state.username}! Your data intelligence workspace is ready.
        </div>
    </div>""", unsafe_allow_html=True)

    sessions = get_user_sessions(st.session_state.user_id)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{len(sessions)}</div>'
                    f'<div class="metric-lbl">Analysis Sessions</div></div>', unsafe_allow_html=True)
    with m2:
        unique_files = len(set(s[2] for s in sessions)) if sessions else 0
        st.markdown(f'<div class="metric-card"><div class="metric-val">{unique_files}</div>'
                    f'<div class="metric-lbl">Datasets</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown('<div class="metric-card"><div class="metric-val">9</div>'
                    '<div class="metric-lbl">Analysis Types</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Start New Analysis", use_container_width=True):
        log_activity(st.session_state.user_id, "new_analysis_started")
        st.session_state.page = "upload"; st.rerun()

    st.markdown('<div class="sec-label">📁 Previous Sessions</div>', unsafe_allow_html=True)

    if not sessions:
        st.info("No saved sessions yet. Start your first analysis above!")
    else:
        for s in sessions[:8]:
            sid, sname, fname, rows, cols, atypes, created = s
            sa, sb, sc, sd, se = st.columns([3, 1, 1, 1, 1])
            with sa:
                st.markdown(
                    f'<div class="sess-card"><b>{sname}</b><br>'
                    f'<small>{fname} · {rows}×{cols} · {created[:16]}</small></div>',
                    unsafe_allow_html=True)
            with sb:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("View", key=f"v_{sid}"):
                    st.session_state.view_session_id   = sid
                    st.session_state.view_session_name = sname
                    log_activity(st.session_state.user_id, "session_viewed", f"session_id={sid}", sid)
                    st.session_state.page = "dashboard"; st.rerun()
            with sc:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✏️ Edit", key=f"edit_btn_{sid}"):
                    saved = get_session_charts(sid)
                    st.session_state.charts = [(uid, title, fig) for uid, title, fig, desc in saved]
                    for uid, title, fig, desc in saved:
                        st.session_state[f"desc_{uid}"] = desc
                    st.session_state.selected_analyses      = []
                    st.session_state.editing_session_id     = sid
                    st.session_state.editing_session_name   = sname
                    st.session_state.setdefault("file_name", fname)
                    log_activity(st.session_state.user_id, "session_edit_started", f"session_id={sid}", sid)
                    st.session_state.page = "dashboard"; st.rerun()
            with sd:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔤", key=f"rename_btn_{sid}", help="Rename this session"):
                    st.session_state[f"renaming_{sid}"] = True
            with se:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_btn_{sid}", help="Delete this session"):
                    st.session_state[f"confirm_del_{sid}"] = True

            if st.session_state.get(f"renaming_{sid}"):
                new_name = st.text_input("New session name", value=sname, key=f"new_name_{sid}")
                r1, r2 = st.columns(2)
                with r1:
                    if st.button("✅ Save", key=f"save_rename_{sid}"):
                        rename_session_db(sid, new_name)
                        log_activity(st.session_state.user_id, "session_renamed",
                                     f"id={sid} new='{new_name}'", sid)
                        st.session_state.pop(f"renaming_{sid}", None)
                        st.success(f"Renamed to '{new_name}'")
                        st.rerun()
                with r2:
                    if st.button("Cancel", key=f"cancel_rename_{sid}"):
                        st.session_state.pop(f"renaming_{sid}", None); st.rerun()

            if st.session_state.get(f"confirm_del_{sid}"):
                st.warning(f"⚠️ Delete **{sname}**? This cannot be undone.")
                d1, d2 = st.columns(2)
                with d1:
                    if st.button("🗑️ Yes, delete", key=f"confirm_yes_{sid}"):
                        delete_session_db(sid, st.session_state.user_id)
                        st.session_state.pop(f"confirm_del_{sid}", None)
                        st.success("Session deleted."); st.rerun()
                with d2:
                    if st.button("Cancel", key=f"confirm_no_{sid}"):
                        st.session_state.pop(f"confirm_del_{sid}", None); st.rerun()
