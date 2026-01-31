from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
import uuid, os, re
from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from pypdf import PdfReader
from docx import Document

from google import genai

# ---------------- APP ----------------

app = FastAPI()

# ---------------- STORAGE ----------------

documents = {}
sessions = {}

# ---------------- GEMINI ----------------

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "models/gemini-flash-latest"

# ---------------- HEALTH ----------------

@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------- HELPERS ----------------

def extract_text(path, ext):
    if ext == ".txt":
        return open(path, "r", encoding="utf-8").read()

    if ext == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    return ""

def process_document(doc_id, path, ext):
    try:
        text = extract_text(path, ext)

        chunks = []
        size = 500

        for i in range(0, len(text), size):
            chunks.append({
                "chunk_id": len(chunks),
                "text": text[i:i+size]
            })

        documents[doc_id]["chunks"] = chunks
        documents[doc_id]["status"] = "completed"

        os.remove(path)

    except:
        documents[doc_id]["status"] = "failed"

def clean(t):
    return re.sub(r"[^a-z0-9\s]", "", t.lower())

def retrieve_chunks(document_ids, question):
    q_words = clean(question).split()
    results = []

    for doc_id in document_ids:
        if doc_id not in documents:
            continue

        for chunk in documents[doc_id]["chunks"]:
            chunk_text = clean(chunk["text"])

            if any(w in chunk_text for w in q_words):
                results.append({
                    "document_id": doc_id,
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"]
                })

    return results

# ---------------- MODELS ----------------

class AskRequest(BaseModel):
    session_id: str
    document_ids: List[str]
    question: str

# ---------------- UPLOAD ----------------

@app.post("/upload", status_code=202)
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in [".txt", ".pdf", ".docx"]:
        raise HTTPException(400, "Unsupported file type")

    doc_id = str(uuid.uuid4())

    os.makedirs("uploads", exist_ok=True)
    path = f"uploads/{doc_id}{ext}"

    with open(path, "wb") as f:
        f.write(await file.read())

    documents[doc_id] = {
        "filename": file.filename,
        "status": "processing",
        "chunks": []
    }

    background_tasks.add_task(process_document, doc_id, path, ext)

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "message": "Document accepted for processing."
    }

# ---------------- STATUS ----------------

@app.get("/documents/{doc_id}/status")
def status(doc_id: str):
    if doc_id not in documents:
        raise HTTPException(404, "Not found")

    return {
        "document_id": doc_id,
        "status": documents[doc_id]["status"]
    }

# ---------------- CHUNKS ----------------

@app.get("/documents/{doc_id}/chunks")
def chunks(doc_id: str):
    if doc_id not in documents:
        raise HTTPException(404, "Not found")

    if documents[doc_id]["status"] != "completed":
        raise HTTPException(400, "Not processed yet")

    return {
        "document_id": doc_id,
        "chunks": documents[doc_id]["chunks"]
    }

# ---------------- ASK (RAG + GEMINI) ----------------

@app.post("/ask")
def ask(req: AskRequest):

    if req.session_id not in sessions:
        sessions[req.session_id] = []

    relevant_chunks = retrieve_chunks(req.document_ids, req.question)

    if not relevant_chunks:
        return {
            "answer": "Answer not found in the provided documents.",
            "session_id": req.session_id,
            "source_chunks": [],
            "batch_size": 0,
            "tokens_used": {
                "prompt_tokens": 0,
                "candidates_tokens": 0,
                "total_tokens": 0
            }
        }

    context = ""
    for c in relevant_chunks:
        context += f"[CHUNK {c['chunk_id']}]: {c['text']}\n"

    prompt = f"""
You are a helpful assistant.
Answer ONLY using the context.

QUESTION:
{req.question}

CONTEXT:
{context}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    answer = response.text

    usage = response.usage_metadata

    tokens_used = {
        "prompt_tokens": getattr(usage, "prompt_token_count", 0),
        "candidates_tokens": getattr(usage, "candidates_token_count", 0),
        "total_tokens": getattr(usage, "total_token_count", 0),
    }

    sessions[req.session_id].append({
        "role": "user",
        "content": req.question
    })

    sessions[req.session_id].append({
        "role": "assistant",
        "content": answer
    })

    return {
        "answer": answer,
        "session_id": req.session_id,
        "source_chunks": relevant_chunks,
        "batch_size": len(relevant_chunks),
        "tokens_used": tokens_used
    }

# ---------------- SESSION HISTORY ----------------

@app.get("/session/{session_id}")
def session_history(session_id: str):
    return {
        "session_id": session_id,
        "history": sessions.get(session_id, [])
    }

# ---------------- GEMINI TEST ----------------

@app.get("/gemini-test")
def gemini_test():
    r = client.models.generate_content(
        model=MODEL_NAME,
        contents="Say hello in one sentence."
    )
    return {"reply": r.text}

# ---------------- GEMINI MODELS ----------------

@app.get("/gemini-models")
def gemini_models():
    return [m.name for m in client.models.list()]

@app.get("/session/{session_id}/export")
def export_pdf(session_id: str):

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    os.makedirs("pdfs", exist_ok=True)
    file_path = f"pdfs/session_{session_id}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(file_path)

    content = []

    for msg in sessions[session_id]:
        role = msg["role"].upper()
        text = msg["content"]

        content.append(Paragraph(f"<b>{role}:</b> {text}", styles["Normal"]))
        content.append(Spacer(1, 12))

    doc.build(content)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"session_{session_id}.pdf"
    )

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return {
        "session_id": session_id,
        "history": sessions.get(session_id, [])
    }
