"""
AQ — Answer the Question · Admin Portal (Streamlit)

Production-grade SaaS UI with Shadcn/Tailwind aesthetic.
Pages: Overview · Documents · Q&A Manager · Analytics · Chat Preview

Persistence: MongoDB via FastAPI backend (API_URL).
"""

import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.document_processor import process_document
from src.qa_generator import generate_qa_from_document

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────────────────────────────────────
# THEME / CSS
# ─────────────────────────────────────────────────────────────────────────────

def get_css() -> str:
    # Fixed light theme — no toggle.
    root = (
        ":root {\n"
        "  --bg:        #ffffff;\n"
        "  --card:      #f9fafb;\n"
        "  --border:    #e5e7eb;\n"
        "  --text:      #1f2937;\n"
        "  --muted:     #6b7280;\n"
        "  --primary:   #818cf8;\n"
        "  --primary-h: #6366f1;\n"
        "  --success:   #10b981;\n"
        "  --danger:    #ef4444;\n"
        "  --warning:   #f59e0b;\n"
        "  --radius:    10px;\n"
        "  --shadow:    0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04);\n"
        "}"
    )
    light_extra = (
        ".stTabs [aria-selected='true'] { background: #ede9fe !important; }\n"
        ".stButton > button:hover { background: #f3f4f6 !important; }\n"
        "[data-testid='stFileUploader'] { background: #f5f3ff !important; }\n"
        "[data-testid='stFileUploader']:hover { background: #f5f3ff !important; }\n"
        ".nav-item.active { background: #ede9fe !important; }\n"
    )

    # Main CSS body — plain string, no f-string needed.
    body = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');


/* ── Global ── */
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, sans-serif !important;
  color: var(--text);
}

.main .block-container {
  padding-top: 1.5rem;
  padding-bottom: 2rem;
  background: var(--bg);
  max-width: 1400px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--card) !important;
  border-right: 1px solid var(--border) !important;
  padding-top: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding-top: 0 !important;
}

/* ── Hide default Streamlit chrome completely ── */
#MainMenu, footer, header { visibility: hidden; }
/* Hide the sidebar collapse/expand toggle — sidebar is always pinned */
[data-testid="collapsedControl"] { display: none !important; }
button[kind="header"] { display: none !important; }
/* Prevent sidebar from collapsing — always full width */
[data-testid="stSidebar"] {
  min-width: 220px !important;
  max-width: 220px !important;
  width: 220px !important;
  transform: none !important;
  transition: none !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
  margin-left: 0 !important;
  transform: none !important;
  display: flex !important;
}

/* ── Buttons ── */
.stButton > button {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  border-radius: 7px !important;
  border: 1px solid var(--border) !important;
  background: var(--card) !important;
  color: var(--text) !important;
  padding: 0.35rem 0.85rem !important;
  transition: all 0.15s ease !important;
  box-shadow: none !important;
}
.stButton > button:hover {
  border-color: var(--primary) !important;
  color: var(--primary) !important;
  background: #f3f4f6 !important;
}

/* Primary button variant via key prefix "primary_" */
[data-testid*="primary_"] > button,
.stButton > button[kind="primary"] {
  background: var(--primary) !important;
  color: #fff !important;
  border-color: var(--primary) !important;
}
[data-testid*="primary_"] > button:hover,
.stButton > button[kind="primary"]:hover {
  background: var(--primary-h) !important;
  border-color: var(--primary-h) !important;
  color: #fff !important;
}

/* Danger button */
[data-testid*="danger_"] > button {
  background: #fee2e2 !important;
  color: var(--danger) !important;
  border-color: #fecaca !important;
}
[data-testid*="danger_"] > button:hover {
  background: var(--danger) !important;
  color: #fff !important;
  border-color: var(--danger) !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
  font-family: 'Inter', sans-serif !important;
  border-radius: 7px !important;
  border: 1px solid var(--border) !important;
  font-size: 0.875rem !important;
  background: var(--card) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  border-radius: 7px !important;
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
}
.streamlit-expanderContent {
  border: 1px solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 7px 7px !important;
  background: var(--card) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
  border-radius: var(--radius) !important;
  overflow: hidden !important;
  border: 1px solid var(--border) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] {
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: .05em !important;
  color: var(--muted) !important;
}
[data-testid="stMetricValue"] {
  font-size: 1.75rem !important;
  font-weight: 700 !important;
  color: var(--text) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  border-radius: var(--radius) !important;
  border: 2px dashed var(--border) !important;
  background: #f5f3ff !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--primary) !important;
  background: #f3f4f6 !important;
}

/* ── Progress ── */
.stProgress > div > div > div {
  background: var(--primary) !important;
  border-radius: 99px !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 0.5rem 1rem !important;
  border-radius: 7px 7px 0 0 !important;
}
.stTabs [aria-selected="true"] {
  background: #ede9fe !important;
  color: var(--primary) !important;
  border-bottom: 2px solid var(--primary) !important;
}

/* ── Chat messages ── */
.chat-bubble-user {
  display: flex;
  justify-content: flex-end;
  margin: 0.4rem 0;
}
.chat-bubble-user span {
  background: var(--primary);
  color: #fff;
  padding: 0.55rem 0.9rem;
  border-radius: 16px 16px 4px 16px;
  max-width: 70%;
  font-size: 0.875rem;
  line-height: 1.5;
  word-break: break-word;
}
.chat-bubble-bot {
  display: flex;
  justify-content: flex-start;
  margin: 0.4rem 0;
}
.chat-bubble-bot span {
  background: var(--card);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 0.55rem 0.9rem;
  border-radius: 16px 16px 16px 4px;
  max-width: 70%;
  font-size: 0.875rem;
  line-height: 1.5;
  word-break: break-word;
}

/* ── Stat card (custom HTML) ── */
.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.2rem 1.4rem;
  box-shadow: var(--shadow);
}
.stat-card .label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--muted);
  margin-bottom: 0.4rem;
}
.stat-card .value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}
.stat-card .sub {
  font-size: 0.75rem;
  color: var(--muted);
  margin-top: 0.35rem;
}

/* ── Badge ── */
.badge {
  display: inline-block;
  padding: 0.18rem 0.6rem;
  border-radius: 99px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: .03em;
}
.badge-primary { background: #ede9fe; color: var(--primary); }
.badge-success { background: #dcfce7; color: #166534; }
.badge-warning { background: #fef3c7; color: #b45309; }
.badge-danger  { background: #fee2e2; color: #991b1b; }
.badge-neutral { background: var(--bg); color: var(--muted); border: 1px solid var(--border); }

/* ── Page header ── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}
.page-header h2 {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}
.page-header .sub {
  font-size: 0.82rem;
  color: var(--muted);
  margin-top: 0.1rem;
}

/* ── Sidebar nav ── */
.nav-brand {
  padding: 1.2rem 1rem 0.8rem 1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.5rem;
}
.nav-brand .logo-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.nav-brand .logo-icon {
  width: 32px; height: 32px;
  background: var(--primary);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 1rem;
}
.nav-brand .logo-text {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}
.nav-brand .logo-sub {
  font-size: 0.7rem;
  color: var(--muted);
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.75rem;
  border-radius: 7px;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.12s;
  margin: 0.1rem 0.5rem;
  text-decoration: none;
}
.nav-item:hover { background: var(--bg); color: var(--text); }
.nav-item.active { background: #ede9fe; color: var(--primary); }
.nav-footer {
  position: absolute;
  bottom: 0;
  left: 0; right: 0;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border);
  background: var(--card);
}
.nav-footer .user-row {
  display: flex; align-items: center; gap: 0.6rem;
}
.nav-footer .avatar {
  width: 28px; height: 28px;
  background: var(--primary);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 0.72rem; font-weight: 700;
  flex-shrink: 0;
}
.nav-footer .user-name { font-size: 0.8rem; font-weight: 600; color: var(--text); }
.nav-footer .user-role { font-size: 0.7rem; color: var(--muted); }

/* ── Login card ── */
.login-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 2.5rem 2rem;
  box-shadow: 0 4px 24px rgba(0,0,0,.07);
  max-width: 420px;
  margin: 0 auto;
}
.login-logo {
  display: flex; align-items: center; justify-content: center;
  gap: 0.6rem; margin-bottom: 1.5rem;
}
.login-logo .icon {
  width: 44px; height: 44px;
  background: var(--primary);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem;
}
.login-logo .text { font-size: 1.2rem; font-weight: 700; color: var(--text); }
.login-card h3 { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.2rem; }
.login-card p  { font-size: 0.82rem; color: var(--muted); margin-bottom: 1.2rem; }

/* ── Table row actions ── */
.action-row { display: flex; gap: 0.4rem; align-items: center; }

/* ── Section card ── */
.section-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
}
.section-card h4 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.75rem;
}

/* ── Upload zone ── */
.upload-zone {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  box-shadow: var(--shadow);
}

/* ── Chat container ── */
.chat-container {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
  min-height: 480px;
  max-height: 480px;
  overflow-y: auto;
  margin-bottom: 0.75rem;
}
.chat-empty {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 420px;
  color: var(--muted);
  font-size: 0.85rem;
  gap: 0.5rem;
}
.chat-empty .icon { font-size: 2.5rem; }

/* ── Toast override ── */
[data-testid="stNotification"] {
  border-radius: var(--radius) !important;
  font-size: 0.85rem !important;
}

/* ── Activity feed ── */
.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--border);
}
.activity-item:last-child { border-bottom: none; }
.activity-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--primary);
  margin-top: 5px;
  flex-shrink: 0;
}
.activity-text { font-size: 0.83rem; color: var(--text); }
.activity-time { font-size: 0.75rem; color: var(--muted); }

/* ── Login page: full-page background, form blends into card ── */
.login-page .main .block-container {
  background: var(--bg) !important;
}
/* Remove the default form border/bg so it looks part of the card */
[data-testid="stForm"] {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}
/* Input labels on login */
.stTextInput label {
  font-size: 0.82rem !important;
  font-weight: 500 !important;
  color: var(--muted) !important;
}
"""

    return "<style>\n" + root + "\n" + body + light_extra + "\n</style>"

# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def api_get(path: str, **params) -> list | dict:
    r = requests.get(f"{API_URL}{path}", params=params or None, timeout=15)
    r.raise_for_status()
    return r.json()


def api_post(path: str, data: dict) -> dict:
    r = requests.post(f"{API_URL}{path}", json=data, timeout=15)
    r.raise_for_status()
    return r.json()


def api_put(path: str, data: dict) -> dict:
    r = requests.put(f"{API_URL}{path}", json=data, timeout=15)
    r.raise_for_status()
    return r.json()


def api_delete(path: str) -> dict:
    r = requests.delete(f"{API_URL}{path}", timeout=15)
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def load_registry() -> list[dict]:
    try:
        return api_get("/documents")
    except Exception:
        return []


def load_all_qa() -> list[dict]:
    try:
        return api_get("/faqs")
    except Exception:
        return []


def load_qa_for_doc(stem: str) -> list[dict]:
    try:
        return api_get("/faqs", stem=stem)
    except Exception:
        return []


def save_qa_for_doc(stem: str, qa_pairs: list[dict]) -> None:
    api_post("/faqs/bulk", {"stem": stem, "qa_pairs": qa_pairs})


def delete_document(stem: str) -> None:
    api_delete(f"/documents/{stem}")


def refresh_state() -> None:
    st.session_state.registry = load_registry()
    st.session_state.all_qa   = load_all_qa()
    if st.session_state.get("current_doc"):
        stem = Path(st.session_state.current_doc).stem
        st.session_state.current_qa = load_qa_for_doc(stem)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def verify_login(username: str, password: str) -> dict | str | None:
    """Return user dict on success, 'connection_error' string if backend unreachable, None if wrong credentials."""
    try:
        r = requests.post(
            f"{API_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        return r.json() if r.status_code == 200 else None
    except requests.exceptions.ConnectionError:
        return "connection_error"
    except Exception:
        return "connection_error"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE BOOTSTRAP
# ─────────────────────────────────────────────────────────────────────────────

SESSION_TTL = timedelta(hours=1)

_DEFAULTS = {
    "logged_in":         False,
    "current_user":      None,
    "login_time":        None,
    "page":              "overview",
    "registry":          [],
    "all_qa":            [],
    "current_qa":        [],
    "current_doc":       None,
    "editing_faq_id":    None,
    "confirm_delete_id": None,
    "confirm_delete_doc":None,
    "chat_history":      [],
    "qa_page":           0,
}


def _expire_session() -> None:
    """Clear session state and force back to login."""
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v


def check_session_expiry() -> bool:
    """Return True if session is still valid, False (and expire it) if timed out."""
    login_time = st.session_state.get("login_time")
    if not login_time:
        return False
    if datetime.now(timezone.utc) - login_time > SESSION_TTL:
        _expire_session()
        st.warning("Your session has expired. Please sign in again.")
        st.rerun()
    return True

for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Lazy-load data once per session after login
if st.session_state.logged_in and not st.session_state.registry:
    st.session_state.registry = load_registry()
    st.session_state.all_qa   = load_all_qa()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AQ · Answer the Question",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown(get_css(), unsafe_allow_html=True)


def badge(text: str, kind: str = "neutral") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def stat_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f"""
    <div class="stat-card">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      {sub_html}
    </div>"""


def page_header(title: str, subtitle: str = ""):
    sub_html = f'<div class="sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="page-header"><div><h2>{title}</h2>{sub_html}</div></div>',
        unsafe_allow_html=True,
    )


def render_sidebar():
    user = st.session_state.current_user
    initials = "".join(w[0].upper() for w in user["name"].split()[:2])

    with st.sidebar:
        # Brand
        st.markdown("""
        <div class="nav-brand">
          <div class="logo-row">
            <div class="logo-icon">💬</div>
            <div>
              <div class="logo-text">AQ</div>
              <div class="logo-sub">Answer the Question</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Nav items
        pages = [
            ("overview",   "📊", "Overview"),
            ("documents",  "📄", "Documents"),
            ("qa",         "💬", "Q&A Manager"),
            ("analytics",  "📈", "Analytics"),
            ("chat",       "🤖", "Chat Preview"),
        ]

        for page_id, icon, label in pages:
            active = "active" if st.session_state.page == page_id else ""
            # Render as button styled like a nav item
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{page_id}",
                width="stretch",
                help=label,
            ):
                st.session_state.page = page_id
                st.rerun()

        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

        # User footer
        role_badge = badge(user["role"], "primary" if user["role"] == "admin" else "neutral")
        st.markdown(f"""
        <div class="nav-footer">
          <div class="user-row">
            <div class="avatar">{initials}</div>
            <div>
              <div class="user-name">{user['name']}</div>
              <div class="user-role">{role_badge}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Logout", key="sidebar_logout", width="stretch"):
            for k in ("logged_in", "current_user", "registry", "all_qa",
                      "current_qa", "current_doc", "chat_history", "page"):
                st.session_state[k] = _DEFAULTS.get(k)
            st.session_state.page = "overview"
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def page_login():
    inject_css()

    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        # ── Brand header ──
        st.markdown("""
        <div style="text-align:center;margin-bottom:1.5rem;">
          <div style="display:inline-flex;align-items:center;justify-content:center;
                      width:52px;height:52px;background:var(--primary);border-radius:14px;
                      font-size:1.6rem;margin-bottom:0.75rem;">💬</div>
          <div style="font-size:1.4rem;font-weight:700;color:var(--text);letter-spacing:-.01em;">AQ Admin</div>
          <div style="font-size:0.82rem;color:var(--muted);margin-top:.2rem;">Answer the Question</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Card wrapper start ──
        st.markdown("""
        <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;
                    padding:2rem 1.75rem;box-shadow:0 4px 24px rgba(0,0,0,.07);">
          <div style="font-size:1rem;font-weight:600;color:var(--text);margin-bottom:.2rem;">Welcome back</div>
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:1.25rem;">Sign in to manage your knowledge base</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Form (rendered directly below the card header — same visual block via CSS adjacency) ──
        with st.form("login_form", clear_on_submit=False, border=False):
            st.markdown('<div style="margin-top:-.5rem"></div>', unsafe_allow_html=True)
            username  = st.text_input("Username", placeholder="your-username", label_visibility="visible")
            password  = st.text_input("Password", type="password", placeholder="••••••••", label_visibility="visible")
            st.markdown('<div style="margin-top:.25rem"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Sign in →", width="stretch", type="primary")

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                with st.spinner("Authenticating…"):
                    result = verify_login(username.strip(), password.strip())
                if result == "connection_error":
                    st.error(
                        f"Cannot connect to the backend at `{API_URL}`.  \n"
                        "Make sure the FastAPI server is running:  \n"
                        "`uvicorn src.main:app --reload`"
                    )
                elif result:
                    st.session_state.logged_in    = True
                    st.session_state.current_user = result
                    st.session_state.login_time   = datetime.now(timezone.utc)
                    st.session_state.page         = "overview"
                    with st.spinner("Loading data…"):
                        refresh_state()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")



# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW PAGE
# ─────────────────────────────────────────────────────────────────────────────

def page_overview():
    registry = st.session_state.registry
    all_qa   = st.session_state.all_qa

    total_docs   = len(registry)
    total_qa     = len(all_qa)
    total_chunks = sum(d.get("chunks", 0) for d in registry)
    avg_qa       = round(total_qa / total_docs, 1) if total_docs else 0

    page_header("Overview", "Your knowledge base at a glance")

    # ── Stat cards ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(stat_card("Documents", str(total_docs), "uploaded"), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_card("Q&A Pairs", str(total_qa), "total extracted"), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_card("Text Chunks", str(total_chunks), "processed"), unsafe_allow_html=True)
    with c4:
        st.markdown(stat_card("Avg Q&A / Doc", str(avg_qa), "per document"), unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Two-column lower section ──
    left, right = st.columns([1.5, 1], gap="large")

    with left:
        st.markdown('<div class="section-card"><h4>Recent Uploads</h4>', unsafe_allow_html=True)
        if not registry:
            st.info("No documents uploaded yet. Go to **Documents** to upload your first file.")
        else:
            recent = sorted(registry, key=lambda d: d.get("uploaded_at", ""), reverse=True)[:8]
            df_recent = pd.DataFrame([{
                "Filename":    d["filename"],
                "Uploaded By": d.get("uploaded_by", "—"),
                "Date":        d.get("uploaded_at", "")[:10],
                "Q&A":         d.get("qa_count", 0),
                "Chunks":      d.get("chunks", 0),
            } for d in recent])
            st.dataframe(df_recent, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("+ Upload Document", type="primary", width="stretch"):
                st.session_state.page = "documents"
                st.rerun()

    with right:
        st.markdown('<div class="section-card"><h4>Recent Activity</h4>', unsafe_allow_html=True)
        if not registry:
            st.markdown("<p style='color:var(--muted);font-size:.83rem'>No activity yet.</p>",
                        unsafe_allow_html=True)
        else:
            items = sorted(registry, key=lambda d: d.get("uploaded_at", ""), reverse=True)[:6]
            feed_html = ""
            for doc in items:
                date_str = doc.get("uploaded_at", "")[:10]
                feed_html += f"""
                <div class="activity-item">
                  <div class="activity-dot"></div>
                  <div>
                    <div class="activity-text"><b>{doc['filename']}</b> uploaded</div>
                    <div class="activity-time">{date_str} · {doc.get('qa_count', 0)} Q&A pairs · by {doc.get('uploaded_by', '—')}</div>
                  </div>
                </div>"""
            st.markdown(feed_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENTS PAGE
# ─────────────────────────────────────────────────────────────────────────────

@st.dialog("Confirm Delete Document")
def confirm_delete_doc_dialog(stem: str, filename: str):
    st.markdown(
        f"Are you sure you want to delete **{filename}** and all its Q&A pairs? "
        "This action cannot be undone.",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Delete", type="primary", width="stretch", key="dlg_del_yes"):
            with st.spinner("Deleting…"):
                delete_document(stem)
                refresh_state()
            if st.session_state.current_doc and Path(st.session_state.current_doc).stem == stem:
                st.session_state.current_doc = None
                st.session_state.current_qa  = []
            st.toast(f"'{filename}' deleted.", icon="🗑️")
            st.session_state.confirm_delete_doc = None
            st.rerun()
    with c2:
        if st.button("Cancel", width="stretch", key="dlg_del_no"):
            st.session_state.confirm_delete_doc = None
            st.rerun()


def page_documents():
    user     = st.session_state.current_user
    registry = st.session_state.registry

    page_header("Documents", f"{len(registry)} document{'s' if len(registry) != 1 else ''} in your knowledge base")

    # ── Upload panel ──
    with st.expander("Upload New Document", expanded=not bool(registry)):
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Drag & drop a file here, or click to browse",
            type=["pdf", "docx", "txt", "xlsx"],
            label_visibility="visible",
        )
        if uploaded:
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.caption(f"**{uploaded.name}** — {uploaded.size / 1024:.1f} KB")
            with col_btn:
                extract = st.button("Extract Q&A", type="primary", width="stretch")

            if extract:
                file_bytes = uploaded.read()
                stem       = Path(uploaded.name).stem

                with st.status("Processing document…", expanded=True) as status:
                    try:
                        chunks = process_document(file_bytes, uploaded.name)
                        status.update(label=f"Split into {len(chunks)} chunks.", state="running")
                    except Exception as e:
                        status.update(label=f"Failed: {e}", state="error")
                        st.stop()

                    progress = st.progress(0, text="Generating Q&A pairs…")

                    def _cb(current, total):
                        progress.progress(current / total, text=f"Chunk {current} / {total}…")

                    try:
                        qa_pairs = generate_qa_from_document(chunks, progress_callback=_cb)
                        status.update(label=f"Generated {len(qa_pairs)} Q&A pairs.", state="complete")
                    except Exception as e:
                        status.update(label=f"Q&A generation failed: {e}", state="error")
                        st.stop()

                    progress.empty()

                try:
                    save_qa_for_doc(stem, qa_pairs)
                    api_post("/documents", {
                        "filename":    uploaded.name,
                        "stem":        stem,
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                        "uploaded_by": user["username"],
                        "chunks":      len(chunks),
                        "qa_count":    len(qa_pairs),
                    })
                except Exception as e:
                    st.error(f"Failed to save to database: {e}")
                    st.stop()

                st.session_state.current_doc = uploaded.name
                refresh_state()
                st.toast(f"Extracted {len(qa_pairs)} Q&A pairs from {uploaded.name}!", icon="✅")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)

    # ── Document table ──
    if not registry:
        st.info("No documents yet. Use the upload panel above to add your first document.")
        return

    for doc in registry:
        with st.expander(f"📄 {doc['filename']}", expanded=False):
            col_meta, col_actions = st.columns([3, 1])

            with col_meta:
                date_str = doc.get("uploaded_at", "")[:10]
                qa_badge  = badge(f"{doc.get('qa_count', 0)} Q&A", "success")
                ch_badge  = badge(f"{doc.get('chunks', 0)} chunks", "neutral")
                by_badge  = badge(doc.get('uploaded_by', '—'), "primary")
                st.markdown(
                    f"{qa_badge} {ch_badge} {by_badge} "
                    f"<span style='font-size:.78rem;color:var(--muted);margin-left:.5rem'>{date_str}</span>",
                    unsafe_allow_html=True,
                )

            with col_actions:
                bcol1, bcol2 = st.columns(2)
                with bcol1:
                    if st.button("View Q&A", key=f"view_{doc['stem']}", width="stretch"):
                        st.session_state.current_qa  = load_qa_for_doc(doc["stem"])
                        st.session_state.current_doc = doc["filename"]
                        st.session_state.page        = "qa"
                        st.rerun()
                with bcol2:
                    if st.button("Delete", key=f"del_{doc['stem']}", width="stretch"):
                        st.session_state.confirm_delete_doc = doc["stem"]
                        confirm_delete_doc_dialog(doc["stem"], doc["filename"])


# ─────────────────────────────────────────────────────────────────────────────
# Q&A MANAGER PAGE
# ─────────────────────────────────────────────────────────────────────────────

QA_PAGE_SIZE = 20


def page_qa():
    all_qa   = st.session_state.all_qa
    registry = st.session_state.registry

    page_header("Q&A Manager", f"{len(all_qa)} Q&A pairs across {len(registry)} documents")

    if not all_qa:
        st.info("No Q&A pairs found. Upload a document on the Documents page first.")
        return

    # ── Filters row ──
    fc1, fc2, fc3 = st.columns([2, 2, 1])
    with fc1:
        search = st.text_input("Search questions…", placeholder="Type to filter…", label_visibility="collapsed")
    with fc2:
        sources = ["All Documents"] + sorted({q["source"] for q in all_qa})
        sel_src = st.selectbox("Filter by document", sources, label_visibility="collapsed")
    with fc3:
        if st.button("Refresh", width="stretch"):
            refresh_state()
            st.session_state.qa_page = 0
            st.rerun()

    # ── Filter data ──
    df = pd.DataFrame(all_qa)
    if sel_src != "All Documents":
        df = df[df["source"] == sel_src]
    if search:
        mask = df["question"].str.contains(search, case=False, na=False)
        df = df[mask]

    total   = len(df)
    n_pages = max(1, -(-total // QA_PAGE_SIZE))  # ceiling div
    page_n  = st.session_state.qa_page

    # ── Pagination controls ──
    pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
    with pcol1:
        if page_n > 0 and st.button("← Previous", width="stretch"):
            st.session_state.qa_page -= 1
            st.rerun()
    with pcol2:
        st.markdown(
            f"<p style='text-align:center;font-size:.82rem;color:var(--muted);margin:.3rem 0'>"
            f"Page {page_n + 1} of {n_pages} · {total} results</p>",
            unsafe_allow_html=True,
        )
    with pcol3:
        if page_n < n_pages - 1 and st.button("Next →", width="stretch"):
            st.session_state.qa_page += 1
            st.rerun()

    start = page_n * QA_PAGE_SIZE
    page_df = df.iloc[start : start + QA_PAGE_SIZE]

    # ── Download buttons ──
    dl1, dl2, _ = st.columns([1, 1, 3])
    with dl1:
        st.download_button(
            "Download JSON",
            data=json.dumps(all_qa if sel_src == "All Documents" else df.to_dict("records"), indent=2).encode(),
            file_name="qa_export.json",
            mime="application/json",
            width="stretch",
        )
    with dl2:
        buf = io.BytesIO()
        exp_df = df if not df.empty else pd.DataFrame(all_qa)
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            exp_df[["faq_id", "question", "answer", "source", "chunk_index"]].to_excel(
                w, sheet_name="Q&A", index=False
            )
        st.download_button(
            "Download Excel",
            data=buf.getvalue(),
            file_name="qa_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

    st.divider()

    # ── Q&A list ──
    for _, row in page_df.iterrows():
        faq_id     = row["faq_id"]
        is_editing = st.session_state.editing_faq_id == faq_id

        src_badge = badge(row["source"], "neutral")
        title_md  = f"{row['question']}"

        with st.expander(title_md, expanded=is_editing):
            st.markdown(src_badge + f" &nbsp; <span style='font-size:.72rem;color:var(--muted)'>chunk {row['chunk_index']} · {faq_id}</span>", unsafe_allow_html=True)

            if is_editing:
                new_q = st.text_area("Question", value=row["question"], key=f"eq_{faq_id}", height=80)
                new_a = st.text_area("Answer",   value=row["answer"],   key=f"ea_{faq_id}", height=110)
                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.button("Save", key=f"save_{faq_id}", type="primary", width="stretch"):
                        api_put(f"/faqs/{faq_id}", {"question": new_q.strip(), "answer": new_a.strip()})
                        refresh_state()
                        st.session_state.editing_faq_id = None
                        st.toast("Q&A updated.", icon="✅")
                        st.rerun()
                with sc2:
                    if st.button("Cancel", key=f"cancel_{faq_id}", width="stretch"):
                        st.session_state.editing_faq_id = None
                        st.rerun()
            else:
                st.markdown(row["answer"])

                if st.session_state.confirm_delete_id == faq_id:
                    st.warning("Delete this Q&A pair permanently?")
                    yc, nc = st.columns(2)
                    with yc:
                        if st.button("Yes, Delete", key=f"yes_{faq_id}", type="primary", width="stretch"):
                            api_delete(f"/faqs/{faq_id}")
                            refresh_state()
                            st.session_state.confirm_delete_id = None
                            st.toast("Q&A deleted.", icon="🗑️")
                            st.rerun()
                    with nc:
                        if st.button("Cancel", key=f"no_{faq_id}", width="stretch"):
                            st.session_state.confirm_delete_id = None
                            st.rerun()
                else:
                    ec, dc = st.columns(2)
                    with ec:
                        if st.button("Edit", key=f"edit_{faq_id}", width="stretch"):
                            st.session_state.editing_faq_id = faq_id
                            st.rerun()
                    with dc:
                        if st.button("Delete", key=f"del_{faq_id}", width="stretch"):
                            st.session_state.confirm_delete_id = faq_id
                            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS PAGE
# ─────────────────────────────────────────────────────────────────────────────

def page_analytics():
    registry = st.session_state.registry
    all_qa   = st.session_state.all_qa

    page_header("Analytics", "Insights across your knowledge base")

    if not registry:
        st.info("No data yet. Upload documents to see analytics.")
        return

    total_docs   = len(registry)
    total_qa     = len(all_qa)
    total_chunks = sum(d.get("chunks", 0) for d in registry)
    avg_qa       = round(total_qa / total_docs, 1) if total_docs else 0

    # ── Summary metrics ──
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total Documents",  total_docs)
    mc2.metric("Total Q&A Pairs",  total_qa)
    mc3.metric("Total Chunks",     total_chunks)
    mc4.metric("Avg Q&A / Doc",    avg_qa)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Charts row ──
    ch_left, ch_right = st.columns(2, gap="large")

    with ch_left:
        st.markdown('<div class="section-card"><h4>Q&A Pairs per Document</h4>', unsafe_allow_html=True)
        df_qa = (
            pd.DataFrame(all_qa)[["source"]]
            .value_counts()
            .reset_index()
            .rename(columns={"source": "Document", "count": "Q&A Pairs"})
        ) if all_qa else pd.DataFrame(columns=["Document", "Q&A Pairs"])
        if not df_qa.empty:
            st.bar_chart(df_qa.set_index("Document"), height=280, color="#6366f1")
        else:
            st.caption("No data.")
        st.markdown("</div>", unsafe_allow_html=True)

    with ch_right:
        st.markdown('<div class="section-card"><h4>Uploads Over Time</h4>', unsafe_allow_html=True)
        df_reg = pd.DataFrame(registry)
        if not df_reg.empty and "uploaded_at" in df_reg.columns:
            df_reg["date"] = pd.to_datetime(df_reg["uploaded_at"], errors="coerce").dt.date
            df_time = (
                df_reg.dropna(subset=["date"])
                .groupby("date")
                .size()
                .reset_index(name="Documents Uploaded")
            )
            if not df_time.empty:
                st.line_chart(df_time.set_index("date"), height=280, color="#6366f1")
            else:
                st.caption("No date data available.")
        else:
            st.caption("No data.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Top documents table ──
    st.markdown('<div class="section-card"><h4>Top Documents by Q&A Count</h4>', unsafe_allow_html=True)
    df_top = (
        pd.DataFrame(registry)
        .sort_values("qa_count", ascending=False)
        .head(10)[["filename", "uploaded_by", "uploaded_at", "chunks", "qa_count"]]
        .rename(columns={
            "filename":    "Filename",
            "uploaded_by": "Uploaded By",
            "uploaded_at": "Date",
            "chunks":      "Chunks",
            "qa_count":    "Q&A",
        })
    )
    df_top["Date"] = df_top["Date"].str[:10]
    st.dataframe(df_top, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Most active uploader ──
    if registry:
        from collections import Counter
        uploaders = Counter(d.get("uploaded_by", "unknown") for d in registry)
        most_active = uploaders.most_common(1)[0]
        st.markdown(
            f"<p style='font-size:.83rem;color:var(--muted);margin-top:.5rem'>"
            f"Most active uploader: <strong>{most_active[0]}</strong> "
            f"({most_active[1]} document{'s' if most_active[1] != 1 else ''})</p>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# CHAT PREVIEW PAGE
# ─────────────────────────────────────────────────────────────────────────────

def page_chat():
    page_header("Chat Preview", "Test your FAQ chatbot in real-time")

    # Controls row
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("Clear Chat", width="stretch"):
            st.session_state.chat_history = []
            st.rerun()
    with cc2:
        # Health check indicator
        try:
            r = requests.get(f"{API_URL}/health", timeout=4)
            ok = r.status_code == 200
        except Exception:
            ok = False
        status_html = (
            badge("API Online", "success") if ok
            else badge("API Offline", "danger")
        )
        st.markdown(f"<div style='padding:.35rem 0'>{status_html}</div>", unsafe_allow_html=True)

    # Chat window
    history = st.session_state.chat_history

    if not history:
        st.markdown("""
        <div class="chat-container">
          <div class="chat-empty">
            <div class="icon">🤖</div>
            <div>Ask a question to test your chatbot</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        bubbles = ""
        for msg in history:
            # HTML-escape content for safety
            content = (
                msg["content"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            if msg["role"] == "user":
                bubbles += f'<div class="chat-bubble-user"><span>{content}</span></div>'
            else:
                bubbles += f'<div class="chat-bubble-bot"><span>{content}</span></div>'

        st.markdown(
            f'<div class="chat-container">{bubbles}</div>',
            unsafe_allow_html=True,
        )

    # Input
    prompt = st.chat_input("Ask a question…")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.spinner("Thinking…"):
            try:
                resp = api_post("/chat", {"message": prompt})
                reply = resp.get("reply", "Sorry, I couldn't get a response.")
            except Exception as e:
                reply = f"Error: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────

inject_css()

if not st.session_state.logged_in:
    page_login()
else:
    check_session_expiry()
    render_sidebar()
    page = st.session_state.page

    if page == "overview":
        page_overview()
    elif page == "documents":
        page_documents()
    elif page == "qa":
        page_qa()
    elif page == "analytics":
        page_analytics()
    elif page == "chat":
        page_chat()
    else:
        page_overview()
