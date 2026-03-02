"""
FAQ Chatbot — Admin Portal (Streamlit)

Persistence:
  All Q&A and document registry data is stored in MongoDB.
  Data is read/written through the FastAPI backend (API_URL).
"""

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.document_processor import process_document
from src.qa_generator import generate_qa_from_document

API_URL = os.getenv("API_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(path: str, **params) -> list | dict:
    r = requests.get(f"{API_URL}{path}", params=params or None)
    r.raise_for_status()
    return r.json()


def api_post(path: str, data: dict) -> dict:
    r = requests.post(f"{API_URL}{path}", json=data)
    r.raise_for_status()
    return r.json()


def api_put(path: str, data: dict) -> dict:
    r = requests.put(f"{API_URL}{path}", json=data)
    r.raise_for_status()
    return r.json()


def api_delete(path: str) -> dict:
    r = requests.delete(f"{API_URL}{path}")
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Data helpers (via API)
# ---------------------------------------------------------------------------

def load_registry() -> list[dict]:
    return api_get("/documents")


def load_qa_for_doc(stem: str) -> list[dict]:
    return api_get("/faqs", stem=stem)


def load_all_qa() -> list[dict]:
    return api_get("/faqs")


def save_qa_for_doc(stem: str, qa_pairs: list[dict], user_id: str = "") -> None:
    api_post("/faqs/bulk", {"stem": stem, "user_id": user_id, "qa_pairs": qa_pairs})


def delete_document(stem: str) -> None:
    api_delete(f"/documents/{stem}")


def refresh_state() -> None:
    """Reload registry, all Q&A, and current doc Q&A from the API."""
    st.session_state.registry = load_registry()
    st.session_state.all_qa   = load_all_qa()
    if st.session_state.current_doc:
        stem = Path(st.session_state.current_doc).stem
        st.session_state.current_qa = load_qa_for_doc(stem)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def verify_login(username: str, password: str) -> dict | None:
    try:
        r = requests.post(f"{API_URL}/auth/login", json={"username": username, "password": password})
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in    = False
    st.session_state.current_user = None

if "registry" not in st.session_state:
    st.session_state.registry = load_registry()

if "all_qa" not in st.session_state:
    st.session_state.all_qa = load_all_qa()

if "current_qa" not in st.session_state:
    st.session_state.current_qa = []

if "current_doc" not in st.session_state:
    st.session_state.current_doc = None

if "editing_faq_id" not in st.session_state:
    st.session_state.editing_faq_id = None

if "confirm_delete_id" not in st.session_state:
    st.session_state.confirm_delete_id = None

if "confirm_delete_doc" not in st.session_state:
    st.session_state.confirm_delete_doc = None


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="FAQ Admin Portal",
    page_icon="🛠️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# LOGIN PAGE
# ---------------------------------------------------------------------------

def show_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## 🛠️ FAQ Admin Portal")
        st.markdown("---")
        with st.form("login_form"):
            username  = st.text_input("Username", placeholder="Enter username")
            password  = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                user = verify_login(username.strip(), password.strip())
                if user:
                    st.session_state.logged_in    = True
                    st.session_state.current_user = user
                    refresh_state()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

def show_dashboard():
    user = st.session_state.current_user

    # ── Top bar ───────────────────────────────────────────────────────────────
    col_title, col_user, col_logout = st.columns([4, 2, 1])
    with col_title:
        st.markdown("## 🛠️ FAQ Admin Portal")
    with col_user:
        st.markdown(f"**Logged in as:** {user['name']} `({user['role']})`")
    with col_logout:
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in    = False
            st.session_state.current_user = None
            st.session_state.current_qa   = []
            st.session_state.current_doc  = None
            st.rerun()

    st.divider()

    left, right = st.columns([1, 2], gap="large")

    # ──────────────────────────────────────────────────────────────────────────
    # LEFT — Upload + Document Library
    # ──────────────────────────────────────────────────────────────────────────
    with left:

        # ── Upload ─────────────────────────────────────────────────────────────
        st.subheader("Upload Document")
        uploaded = st.file_uploader(
            "Drag & drop a document",
            type=["pdf", "docx", "txt", "xlsx"],
        )

        if uploaded:
            st.caption(f"{uploaded.name} — {uploaded.size / 1024:.1f} KB")

            if st.button("Extract Q&A", use_container_width=True, type="primary"):
                file_bytes = uploaded.read()
                stem = Path(uploaded.name).stem

                with st.status("Extracting and chunking text...") as status:
                    try:
                        chunks = process_document(file_bytes, uploaded.name)
                        status.update(label=f"Split into {len(chunks)} chunks.", state="complete")
                    except Exception as e:
                        status.update(label=f"Failed: {e}", state="error")
                        st.stop()

                progress_bar = st.progress(0, text="Generating Q&A pairs...")

                def update_progress(current, total):
                    progress_bar.progress(
                        current / total,
                        text=f"Chunk {current}/{total}...",
                    )

                try:
                    qa_pairs = generate_qa_from_document(chunks, progress_callback=update_progress)
                except Exception as e:
                    st.error(f"Q&A generation failed: {e}")
                    st.stop()

                progress_bar.empty()

                try:
                    # Save Q&A to MongoDB via API (tagged with uploader's username)
                    save_qa_for_doc(stem, qa_pairs, user_id=user["username"])

                    # Upsert document record in registry
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

                st.success(f"Generated **{len(qa_pairs)}** Q&A pairs from {len(chunks)} chunks.")

        st.divider()

        # ── Stats ──────────────────────────────────────────────────────────────
        c1, c2 = st.columns(2)
        c1.metric("Documents", len(st.session_state.registry))
        c2.metric("Total Q&A", len(st.session_state.all_qa))

        st.divider()

        # ── Document Library ───────────────────────────────────────────────────
        st.subheader("Document Library")

        if not st.session_state.registry:
            st.info("No documents uploaded yet.")
        else:
            for doc in st.session_state.registry:
                with st.expander(f"📄 {doc['filename']}", expanded=False):
                    uploaded_at = doc.get("uploaded_at", "")[:10]
                    st.caption(
                        f"Uploaded: {uploaded_at} by `{doc.get('uploaded_by', '—')}`  \n"
                        f"Chunks: {doc['chunks']} | Q&A: {doc['qa_count']}"
                    )

                    if st.button("View Q&A", key=f"view_{doc['stem']}", use_container_width=True):
                        st.session_state.current_qa  = load_qa_for_doc(doc["stem"])
                        st.session_state.current_doc = doc["filename"]
                        st.rerun()

                    if st.session_state.confirm_delete_doc == doc["stem"]:
                        st.warning(f"Are you sure you want to delete **{doc['filename']}** and all its Q&A?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Yes, Delete", key=f"docdel_yes_{doc['stem']}",
                                         use_container_width=True, type="primary"):
                                delete_document(doc["stem"])
                                if st.session_state.current_doc == doc["filename"]:
                                    st.session_state.current_qa  = []
                                    st.session_state.current_doc = None
                                refresh_state()
                                st.session_state.confirm_delete_doc = None
                                st.rerun()
                        with col_no:
                            if st.button("Cancel", key=f"docdel_no_{doc['stem']}",
                                         use_container_width=True):
                                st.session_state.confirm_delete_doc = None
                                st.rerun()
                    else:
                        if st.button("Delete Document", key=f"del_{doc['stem']}",
                                     use_container_width=True):
                            st.session_state.confirm_delete_doc = doc["stem"]
                            st.rerun()

    # ──────────────────────────────────────────────────────────────────────────
    # RIGHT — Q&A Viewer
    # ──────────────────────────────────────────────────────────────────────────
    with right:
        current_label = f"Current Doc ({len(st.session_state.current_qa)})"
        if st.session_state.current_doc:
            current_label = f"{st.session_state.current_doc} ({len(st.session_state.current_qa)})"

        tab_current, tab_all = st.tabs([
            current_label,
            f"All Documents ({len(st.session_state.all_qa)})",
        ])

        # ── Tab 1: Selected / just-processed document ─────────────────────────
        with tab_current:
            if not st.session_state.current_qa:
                st.info("Upload a document or click **View Q&A** on a document from the library.")
            else:
                search = st.text_input("Search questions...", key="search_current")
                df = pd.DataFrame(st.session_state.current_qa)
                if search:
                    df = df[df["question"].str.contains(search, case=False, na=False)]

                st.caption(f"Showing {len(df)} Q&A pairs")

                for _, row in df.iterrows():
                    faq_id = row["faq_id"]
                    is_editing = st.session_state.editing_faq_id == faq_id

                    with st.expander(row["question"], expanded=is_editing):
                        if is_editing:
                            new_q = st.text_area("Question", value=row["question"],
                                                 key=f"eq_{faq_id}", height=80)
                            new_a = st.text_area("Answer", value=row["answer"],
                                                 key=f"ea_{faq_id}", height=100)
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("Save", key=f"save_{faq_id}",
                                             use_container_width=True, type="primary"):
                                    api_put(f"/faqs/{faq_id}", {
                                        "question": new_q.strip(),
                                        "answer":   new_a.strip(),
                                    })
                                    refresh_state()
                                    st.session_state.editing_faq_id = None
                                    st.rerun()
                            with col_cancel:
                                if st.button("Cancel", key=f"cancel_{faq_id}",
                                             use_container_width=True):
                                    st.session_state.editing_faq_id = None
                                    st.rerun()
                        else:
                            st.markdown(row["answer"])
                            st.caption(f"ID: `{faq_id}` | Chunk: {row['chunk_index']}")

                            if st.session_state.confirm_delete_id == faq_id:
                                st.warning("Are you sure you want to delete this Q&A?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("Yes, Delete", key=f"yes_{faq_id}",
                                                 use_container_width=True, type="primary"):
                                        api_delete(f"/faqs/{faq_id}")
                                        refresh_state()
                                        st.session_state.confirm_delete_id = None
                                        st.rerun()
                                with col_no:
                                    if st.button("Cancel", key=f"no_{faq_id}",
                                                 use_container_width=True):
                                        st.session_state.confirm_delete_id = None
                                        st.rerun()
                            else:
                                col_edit, col_del = st.columns(2)
                                with col_edit:
                                    if st.button("Edit", key=f"edit_{faq_id}",
                                                 use_container_width=True):
                                        st.session_state.editing_faq_id = faq_id
                                        st.rerun()
                                with col_del:
                                    if st.button("Delete", key=f"delqa_{faq_id}",
                                                 use_container_width=True):
                                        st.session_state.confirm_delete_id = faq_id
                                        st.rerun()

                # Downloads
                st.divider()
                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button(
                        "Download JSON",
                        data=json.dumps(st.session_state.current_qa, indent=2).encode(),
                        file_name=f"{Path(st.session_state.current_doc or 'qa').stem}_qa.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                with dl2:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
                        pd.DataFrame(st.session_state.current_qa)[
                            ["faq_id", "question", "answer", "source", "chunk_index"]
                        ].to_excel(w, sheet_name="Q&A", index=False)
                    st.download_button(
                        "Download Excel",
                        data=buf.getvalue(),
                        file_name=f"{Path(st.session_state.current_doc or 'qa').stem}_qa.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

        # ── Tab 2: All documents combined ─────────────────────────────────────
        with tab_all:
            if not st.session_state.all_qa:
                st.info("No Q&A extracted yet.")
            else:
                search_all = st.text_input("Search all questions...", key="search_all")
                df_all = pd.DataFrame(st.session_state.all_qa)

                sources = sorted(df_all["source"].unique().tolist())
                sel = st.selectbox("Filter by document", ["All"] + sources, key="src_filter")
                if sel != "All":
                    df_all = df_all[df_all["source"] == sel]

                if search_all:
                    df_all = df_all[df_all["question"].str.contains(search_all, case=False, na=False)]

                st.caption(f"Showing {len(df_all)} Q&A pairs")

                for _, row in df_all.iterrows():
                    faq_id   = row["faq_id"]
                    is_editing_all = st.session_state.editing_faq_id == f"all_{faq_id}"

                    with st.expander(f"[{row['source']}]  {row['question']}", expanded=is_editing_all):
                        if is_editing_all:
                            new_q = st.text_area("Question", value=row["question"],
                                                 key=f"aeq_{faq_id}", height=80)
                            new_a = st.text_area("Answer", value=row["answer"],
                                                 key=f"aea_{faq_id}", height=100)
                            col_s, col_c = st.columns(2)
                            with col_s:
                                if st.button("Save", key=f"asave_{faq_id}",
                                             use_container_width=True, type="primary"):
                                    api_put(f"/faqs/{faq_id}", {
                                        "question": new_q.strip(),
                                        "answer":   new_a.strip(),
                                    })
                                    refresh_state()
                                    st.session_state.editing_faq_id = None
                                    st.rerun()
                            with col_c:
                                if st.button("Cancel", key=f"acancel_{faq_id}",
                                             use_container_width=True):
                                    st.session_state.editing_faq_id = None
                                    st.rerun()
                        else:
                            st.markdown(row["answer"])
                            st.caption(f"ID: `{faq_id}`")

                            if st.session_state.confirm_delete_id == f"all_{faq_id}":
                                st.warning("Are you sure you want to delete this Q&A?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("Yes, Delete", key=f"ayes_{faq_id}",
                                                 use_container_width=True, type="primary"):
                                        api_delete(f"/faqs/{faq_id}")
                                        refresh_state()
                                        st.session_state.confirm_delete_id = None
                                        st.rerun()
                                with col_no:
                                    if st.button("Cancel", key=f"ano_{faq_id}",
                                                 use_container_width=True):
                                        st.session_state.confirm_delete_id = None
                                        st.rerun()
                            else:
                                col_e, col_d = st.columns(2)
                                with col_e:
                                    if st.button("Edit", key=f"aedit_{faq_id}",
                                                 use_container_width=True):
                                        st.session_state.editing_faq_id = f"all_{faq_id}"
                                        st.rerun()
                                with col_d:
                                    if st.button("Delete", key=f"adelqa_{faq_id}",
                                                 use_container_width=True):
                                        st.session_state.confirm_delete_id = f"all_{faq_id}"
                                        st.rerun()

                st.divider()
                al1, al2 = st.columns(2)
                with al1:
                    st.download_button(
                        "Download All (JSON)",
                        data=json.dumps(st.session_state.all_qa, indent=2).encode(),
                        file_name="all_qa.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                with al2:
                    buf_all = io.BytesIO()
                    with pd.ExcelWriter(buf_all, engine="xlsxwriter") as w:
                        df_all[["faq_id", "question", "answer", "source", "chunk_index"]].to_excel(
                            w, sheet_name="All Q&A", index=False
                        )
                    st.download_button(
                        "Download All (Excel)",
                        data=buf_all.getvalue(),
                        file_name="all_qa.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if not st.session_state.logged_in:
    show_login()
else:
    show_dashboard()
