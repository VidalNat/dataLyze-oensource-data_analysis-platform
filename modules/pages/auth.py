"""
modules/pages/auth.py -- Login, registration, and profile management page.
==========================================================================

Exposes two entry-point functions called by app.py:
    page_auth()    -- sign-in / sign-up form for unauthenticated users
    page_profile() -- account settings, password change, account deletion

Authentication flow:
    1. User submits credentials → login_user() validates them.
    2. On success, create_token() issues a 7-day persistent token.
    3. The token is written to ?t= in the URL via st.query_params.
    4. Every subsequent page load validates the token via validate_token().
    5. Sign-out calls revoke_token() and clears session_state.

CONTRIBUTING -- to add a new profile setting:
    Add a new st.expander() block in page_profile() below the existing sections.
    Use the same confirm-before-action pattern as the account deletion block.
Logo is text-only on the auth page per spec (#10).
"""

import streamlit as st
from modules.database import (
    login_user, register_user, validate_token, create_token,
    log_activity, delete_user_db,
)
from modules.ui.css import BRAND_NAME, inject_footer, logo_data_uri


def page_auth():
    token = st.query_params.get("t", "")
    if token and "user_id" not in st.session_state:
        restored = validate_token(token)
        if restored:
            st.session_state.user_id  = restored[0]
            st.session_state.username = restored[1]
            st.session_state.page     = "home"
            st.rerun()
        else:
            st.query_params.clear()

    tab = st.query_params.get("tab", "login")
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = tab
    is_login = st.session_state.auth_tab == "login"

    # Style the middle column to look like a glass card
    st.markdown("""
    <style>
    div[data-testid="column"]:nth-child(2) > div > div > div {
        background: var(--surface-raised) !important;
        backdrop-filter: blur(24px) saturate(200%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(200%) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: var(--radius-xl) !important;
        box-shadow: var(--shadow-lg) !important;
        padding: 2rem 1.6rem 2.2rem !important;
        animation: fadeUp .4s cubic-bezier(0.4,0,0.2,1) both;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 0.9, 1])
    with col:
        logo_src  = logo_data_uri()
        icon_html = (
            f'<img src="{logo_src}" alt="{BRAND_NAME} logo" '
            'style="width:2.6rem;height:2.6rem;object-fit:contain;">'
            if logo_src else '<span style="font-size:2.4rem;">&#128202;</span>'
        )
        st.markdown(
            '<div style="text-align:center;padding:.5rem 0 1.4rem;">'
            f'<div style="margin-bottom:.6rem;">{icon_html}</div>'
            f'<div class="brand" style="font-size:2rem;">{BRAND_NAME}</div>'
            '<div style="font-size:.82rem;margin-top:.35rem;opacity:.5;font-weight:500;">'
            'Your quick data analysis platform</div>'
            '</div>',
            unsafe_allow_html=True)

        t1, t2 = st.columns(2)
        with t1:
            if st.button("🔐  Sign In", use_container_width=True,
                         type="primary" if is_login else "secondary"):
                st.session_state.auth_tab = "login"; st.rerun()
        with t2:
            if st.button("✨  Register", use_container_width=True,
                         type="primary" if not is_login else "secondary"):
                st.session_state.auth_tab = "register"; st.rerun()

        st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)

        if is_login:
            username = st.text_input("Username", key="l_user", placeholder="Enter your username")
            password = st.text_input("Password", type="password", key="l_pass",
                                     placeholder="Enter your password")
            remember = st.checkbox("Stay signed in for 7 days", value=True, key="remember_me")
            st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
            if st.button("Sign In →", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Please fill in both fields.")
                else:
                    user = login_user(username, password)
                    if user:
                        st.session_state.user_id  = user[0]
                        st.session_state.username = user[1]
                        st.session_state.page     = "home"
                        log_activity(user[0], "login", f"user={username}")
                        if remember:
                            tok = create_token(user[0], user[1])
                            st.query_params["t"] = tok
                        else:
                            st.query_params.clear()
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")
        else:
            ru  = st.text_input("Username",         key="r_u",  placeholder="Choose a username")
            re  = st.text_input("Email",            key="r_e",  placeholder="your@email.com")
            rp  = st.text_input("Password",         type="password", key="r_p",
                                 placeholder="Minimum 6 characters")
            rp2 = st.text_input("Confirm Password", type="password", key="r_p2",
                                 placeholder="Repeat your password")
            st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
            if st.button("Create Account →", use_container_width=True, type="primary"):
                if not all([ru, re, rp, rp2]):
                    st.error("All fields are required.")
                elif rp != rp2:
                    st.error("Passwords don't match.")
                elif len(rp) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    ok, msg = register_user(ru, re, rp)
                    if ok:
                        st.toast("Account created! Please sign in.", icon="✅")
                        log_activity(0, "register", f"new user={ru}")
                        st.session_state.auth_tab = "login"
                        st.rerun()
                    else:
                        st.error(msg)

    inject_footer()


def page_profile():
    """User profile page -- account info and danger-zone actions."""
    from modules.ui.css import render_logo
    render_logo()

    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()

    username = st.session_state.get("username", "")
    user_id  = st.session_state.get("user_id")

    st.markdown(f"## 👤 Profile -- {username}")
    st.markdown("---")

    # ── Danger Zone ───────────────────────────────────────────────────────────
    st.markdown(
        '<div style="border:1.5px solid #ef4444;border-radius:12px;padding:1rem 1.2rem;'
        'background:rgba(239,68,68,0.04);margin-top:1rem;">'
        '<p style="color:#ef4444;font-weight:700;font-size:0.95rem;margin:0 0 0.5rem 0;">'
        '⚠️ Danger Zone</p>'
        '<p style="font-size:0.84rem;opacity:0.8;margin:0;">'
        'Deleting your account is <strong>permanent and irreversible</strong>. '
        'All saved sessions, charts, KPIs, and your login will be erased immediately.'
        '</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # Two-step confirmation: show confirm UI only after first button press
    if "confirm_delete_account" not in st.session_state:
        st.session_state.confirm_delete_account = False

    if not st.session_state.confirm_delete_account:
        if st.button("🗑️ Delete My Account", type="secondary"):
            st.session_state.confirm_delete_account = True
            st.rerun()
    else:
        st.warning(
            "Are you sure? This will permanently delete your account and **all saved sessions**. "
            "This cannot be undone."
        )
        col_yes, col_no, _ = st.columns([1, 1, 4])
        with col_yes:
            if st.button("✅ Yes, delete everything", type="primary",
                         use_container_width=True):
                ok = delete_user_db(user_id)
                if ok:
                    for k in list(st.session_state.keys()):
                        del st.session_state[k]
                    st.query_params.clear()
                    st.session_state.page = "auth"
                    st.toast("Your account has been deleted.", icon="🗑️")
                    st.rerun()
                else:
                    st.error("Something went wrong -- account could not be deleted. Try again.")
        with col_no:
            if st.button("✗ Cancel", use_container_width=True):
                st.session_state.confirm_delete_account = False
                st.rerun()

    inject_footer()