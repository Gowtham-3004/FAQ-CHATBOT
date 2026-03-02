"""
Chat logic — loads Q&A from extracted JSON files, finds relevant matches
via keyword scoring, then calls Google Gemini to generate an answer.

No vector DB needed — works directly off the admin portal's saved Q&A files.
"""

import re

from google import genai
from src.config import settings
from src.database import faqs_col

_client = genai.Client(api_key=settings.gemini_api_key)

SYSTEM_PROMPT = """You are a helpful customer support chatbot.
Answer the user's question based ONLY on the FAQ context provided below.
If the context does not contain a relevant answer, say:
"I'm sorry, I don't have information on that. Please contact our support team."
Be concise, friendly, and accurate. Never make up information."""


# ---------------------------------------------------------------------------
# Load Q&A
# ---------------------------------------------------------------------------

def load_all_qa() -> list[dict]:
    """Load all Q&A pairs from MongoDB."""
    return list(faqs_col.find({}, {"_id": 0, "stem": 0}))


# ---------------------------------------------------------------------------
# Keyword-based relevance scoring
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    return set(re.findall(r'\b\w{3,}\b', text.lower()))


def _score(query_tokens: set[str], faq: dict) -> float:
    """Score a FAQ item by keyword overlap with the user query."""
    faq_tokens = _tokenize(faq["question"]) | _tokenize(faq["answer"])
    overlap = query_tokens & faq_tokens
    if not query_tokens:
        return 0.0
    return len(overlap) / len(query_tokens)


def find_relevant(question: str, all_qa: list[dict], top_k: int = 4) -> list[dict]:
    """Return top_k most keyword-relevant FAQ items."""
    tokens = _tokenize(question)
    scored = sorted(all_qa, key=lambda f: _score(tokens, f), reverse=True)
    # Only return items with at least one keyword match
    return [f for f in scored[:top_k] if _score(tokens, f) > 0]


# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------

def answer_question(question: str) -> str:
    """Full pipeline: load Q&A → find relevant → generate GPT answer."""
    all_qa = load_all_qa()

    if not all_qa:
        return (
            "I don't have any FAQ data loaded yet. "
            "Please ask an admin to upload documents first."
        )

    relevant = find_relevant(question, all_qa)

    if not relevant:
        return (
            "I'm sorry, I couldn't find relevant information for your question. "
            "Please contact our support team for assistance."
        )

    context = "\n\n".join(
        f"Q: {f['question']}\nA: {f['answer']}" for f in relevant
    )

    prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}"
    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()
