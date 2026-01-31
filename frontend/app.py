import streamlit as st
import requests

API_URL = "http://api:8000"

st.set_page_config(
    page_title="Gemini RAG System",
    layout="wide"
)

st.title("🤖 Gemini Document Q&A")

# ---------------- SESSION STATE ----------------

if "session_id" not in st.session_state:
    st.session_state.session_id = "chat1"

if "document_ids" not in st.session_state:
    st.session_state.document_ids = []

# ---------------- SIDEBAR MENU ----------------

st.sidebar.title("📂 Menu")

menu = st.sidebar.radio(
    "Navigate",
    ["Upload Document", "Conversation History", "Download PDF"]
)

# ---------------- UPLOAD (HIDDEN IN MENU) ----------------

if menu == "Upload Document":
    st.sidebar.subheader("Upload a file")

    uploaded_file = st.sidebar.file_uploader(
        "Upload PDF, TXT, DOCX",
        type=["pdf", "txt", "docx"]
    )

    if uploaded_file:
        response = requests.post(
            f"{API_URL}/upload",
            files={"file": uploaded_file}
        )

        if response.status_code == 202:
            data = response.json()
            st.sidebar.success(f"Uploaded: {data['filename']}")
            st.session_state.document_ids.append(data["document_id"])

# ---------------- HISTORY (HIDDEN) ----------------

if menu == "Conversation History":
    st.sidebar.subheader("Chat History")

    r = requests.get(f"{API_URL}/session/{st.session_state.session_id}")

    if r.status_code == 200:
        history = r.json()["history"]

        if not history:
            st.sidebar.info("No conversation yet")

        for msg in history:
            st.sidebar.write(f"**{msg['role'].capitalize()}:** {msg['content']}")

# ---------------- PDF EXPORT (HIDDEN) ----------------

if menu == "Download PDF":
    st.sidebar.subheader("Export Conversation")

    pdf = requests.get(
        f"{API_URL}/session/{st.session_state.session_id}/export"
    )

    if pdf.status_code == 200:
        st.sidebar.download_button(
            "📄 Download PDF",
            pdf.content,
            file_name=f"session_{st.session_state.session_id}.pdf",
            mime="application/pdf"
        )
    else:
        st.sidebar.info("No conversation to export yet")

# ================= MAIN SCREEN =================

st.subheader("Ask a Question")

if not st.session_state.document_ids:
    st.warning("Upload a document from the menu first 👈")

question = st.text_input("Type your question here")

if st.button("Ask Gemini"):
    if not question:
        st.warning("Enter a question")

    elif not st.session_state.document_ids:
        st.warning("Upload a document first")

    else:
        payload = {
            "session_id": st.session_state.session_id,
            "document_ids": st.session_state.document_ids,
            "question": question
        }

        res = requests.post(f"{API_URL}/ask", json=payload)
        data = res.json()

        st.markdown("### ✅ Answer")
        st.success(data["answer"])

        st.markdown("### 📊 Token Usage")
        st.json(data["tokens_used"])

        st.markdown("### 📚 Source Chunks")
        for c in data["source_chunks"]:
            st.info(f"Chunk {c['chunk_id']}: {c['text']}")
