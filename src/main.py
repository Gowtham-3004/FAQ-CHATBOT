"""
FAQ Chatbot — FastAPI backend

Endpoints:
  POST   /auth/login          → verify credentials, return user record
  POST   /chat                → answer a question using Q&A from MongoDB + Gemini
  GET    /faqs                → list all FAQ pairs (filter by ?stem=)
  POST   /faqs/bulk           → replace all FAQs for a document stem
  PUT    /faqs/{faq_id}       → update a Q&A pair
  DELETE /faqs/{faq_id}       → delete a Q&A pair
  GET    /documents           → list document registry
  POST   /documents           → upsert a document record
  DELETE /documents/{stem}    → delete document + all its FAQs
  GET    /widget.js           → serve the embeddable chat widget script
  GET    /health              → liveness check
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.chat import answer_question
from src.database import faqs_col, registry_col, users_col

_DEFAULT_USERS = [
    {"username": "admin",  "password": "admin123",  "role": "admin",  "name": "Admin User"},
    {"username": "editor", "password": "editor456", "role": "editor", "name": "Content Editor"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if users_col.count_documents({}) == 0:
        users_col.insert_many(_DEFAULT_USERS)
    yield


app = FastAPI(title="FAQ Chatbot API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WIDGET_PATH = Path(__file__).parent.parent / "public" / "widget.js"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class DocumentRecord(BaseModel):
    filename: str
    stem: str
    uploaded_at: str
    uploaded_by: str
    chunks: int
    qa_count: int


class BulkFAQRequest(BaseModel):
    stem: str
    qa_pairs: list[dict]


class FAQUpdate(BaseModel):
    question: str
    answer: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/login")
def login(req: LoginRequest):
    user = users_col.find_one(
        {"username": req.username, "password": req.password},
        {"_id": 0},
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        return ChatResponse(reply="Please type a question.")
    reply = answer_question(req.message.strip())
    return ChatResponse(reply=reply)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@app.get("/documents")
def list_documents():
    return list(registry_col.find({}, {"_id": 0}))


@app.post("/documents", status_code=201)
def upsert_document(doc: DocumentRecord):
    registry_col.replace_one({"stem": doc.stem}, doc.model_dump(), upsert=True)
    return {"ok": True}


@app.delete("/documents/{stem}")
def delete_document(stem: str):
    registry_col.delete_one({"stem": stem})
    faqs_col.delete_many({"stem": stem})
    return {"ok": True}


# ---------------------------------------------------------------------------
# FAQs
# ---------------------------------------------------------------------------

@app.get("/faqs")
def list_faqs(stem: Optional[str] = None):
    query = {"stem": stem} if stem else {}
    return list(faqs_col.find(query, {"_id": 0, "stem": 0}))


@app.post("/faqs/bulk", status_code=201)
def bulk_replace_faqs(payload: BulkFAQRequest):
    faqs_col.delete_many({"stem": payload.stem})
    if payload.qa_pairs:
        docs = [{**qa, "stem": payload.stem} for qa in payload.qa_pairs]
        faqs_col.insert_many(docs)
    return {"inserted": len(payload.qa_pairs)}


@app.put("/faqs/{faq_id}")
def update_faq(faq_id: str, payload: FAQUpdate):
    result = faqs_col.update_one(
        {"faq_id": faq_id},
        {"$set": {"question": payload.question, "answer": payload.answer}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"ok": True}


@app.delete("/faqs/{faq_id}")
def delete_faq(faq_id: str):
    faq = faqs_col.find_one({"faq_id": faq_id}, {"stem": 1})
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    faqs_col.delete_one({"faq_id": faq_id})
    registry_col.update_one({"stem": faq["stem"]}, {"$inc": {"qa_count": -1}})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Widget + Health
# ---------------------------------------------------------------------------

@app.get("/widget.js", include_in_schema=False)
def serve_widget():
    return FileResponse(WIDGET_PATH, media_type="application/javascript; charset=utf-8")


@app.get("/health")
def health():
    return {"status": "ok"}
