"""
FAQ Chatbot — FastAPI backend

Endpoints:
  POST /chat      → answer a question using extracted Q&A + Azure GPT
  GET  /widget.js → serve the embeddable chat widget script
  GET  /health    → liveness check
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.chat import answer_question

app = FastAPI(title="FAQ Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WIDGET_PATH = Path(__file__).parent.parent / "public" / "widget.js"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        return ChatResponse(reply="Please type a question.")
    reply = answer_question(req.message.strip())
    return ChatResponse(reply=reply)


@app.get("/widget.js", include_in_schema=False)
def serve_widget():
    """Serve the embeddable chat widget JavaScript file."""
    return FileResponse(WIDGET_PATH, media_type="application/javascript; charset=utf-8")


@app.get("/health")
def health():
    return {"status": "ok"}
