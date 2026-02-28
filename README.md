# FAQ Chatbot

An end-to-end FAQ chatbot system with an **Admin Portal** for document ingestion and a **floating chat widget** that can be embedded into any webpage with a single `<script>` tag.

---

## Architecture

```
Admin Portal (Streamlit :8502)
  └── Upload documents (PDF, DOCX, TXT, XLSX)
  └── Auto-generate Q&A via Azure GPT-4o-mini
  └── Review / Edit / Delete Q&A
  └── Saved to data/extracted_qa/*.json

Chat API (FastAPI :8000)
  └── POST /chat  → keyword search + Azure GPT answer
  └── GET  /widget.js → serves embeddable widget

Any Webpage
  └── <script src="http://localhost:8000/widget.js">
  └── Floating 💬 chat bubble (bottom-right)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Azure OpenAI — `gpt-4o-mini` |
| Admin UI | Streamlit |
| Chat API | FastAPI + Uvicorn |
| Document Parsing | pdfplumber, python-docx, openpyxl |
| Auth | JSON file (`data/users.json`) |
| Storage | JSON files (`data/extracted_qa/`) |
| Widget | Vanilla JS + Shadow DOM |

---

## Project Structure

```
FAQ-CHATBOT/
├── src/
│   ├── config.py               # Environment settings (Azure keys)
│   ├── document_processor.py   # Extract + chunk text from documents
│   ├── qa_generator.py         # GPT-4o-mini Q&A generation
│   ├── chat.py                 # Chat search + answer logic
│   └── main.py                 # FastAPI app
├── ui/
│   └── admin.py                # Streamlit admin portal
├── public/
│   └── widget.js               # Embeddable floating chat widget
├── data/
│   ├── users.json              # Admin login credentials
│   ├── document_registry.json  # Uploaded document metadata
│   └── extracted_qa/           # Q&A JSON files per document
├── screenshots/                # → place your screenshots here
├── floating_faq.html           # Test page for the chat widget
└── requirements.txt
```

---

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
PROMPT_GENERATION_ENDPOINT=https://your-resource.openai.azure.com/
API_VERSION=2024-02-01
PROMPT_SUBSCRIPTION_KEY=your-azure-key
```

---

## Running

### Terminal 1 — Chat API

```bash
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Terminal 2 — Admin Portal

```bash
source .venv/bin/activate
streamlit run ui/admin.py --server.port 8502
```

Admin portal at: `http://localhost:8502`

---

## Admin Portal

### Login

Default credentials (edit `data/users.json` to change):

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| editor | editor456 | editor |

<!-- SCREENSHOT: Login page -->
> ![Login Page](assets/login_page.png)

---

### Upload & Extract Q&A

1. Log in to the admin portal
2. Upload a document (PDF, DOCX, TXT, or XLSX) in the left panel
3. Click **Extract Q&A** — the system will:
   - Extract and chunk the document text
   - Send each chunk to Azure GPT-4o-mini
   - Generate 2–5 Q&A pairs per chunk
4. Q&A pairs appear in the right panel

<!-- SCREENSHOT: Upload and extraction in progress -->
> ![Upload & Extract](assets/upload_extract.png)

---

### Q&A Management

Each extracted Q&A can be:
- **Edited** — inline edit form with Save / Cancel
- **Deleted** — shows confirmation prompt before deleting

<!-- SCREENSHOT: Q&A list with Edit and Delete buttons -->
> ![Q&A List](assets/list_q&a.png)

<!-- SCREENSHOT: Inline edit form open -->
> ![Edit Q&A](assets/edit_q&a.png)

<!-- SCREENSHOT: Delete confirmation dialog -->
> ![Delete Confirmation](assets/delete_confirm.png)

---

### Document Library

All uploaded documents are listed in the left sidebar with:
- Upload date and uploader name
- Chunk count and Q&A count
- **View Q&A** — load that document's Q&A into the viewer
- **Delete Document** — removes document and all its Q&A (with confirmation)

<!-- SCREENSHOT: Document library with documents listed -->
> ![Document Library](assets/doc_library.png)

---

### Download Q&A

Extracted Q&A can be downloaded as:
- **JSON** — for programmatic use
- **Excel (.xlsx)** — for sharing / editing in spreadsheets

<!-- SCREENSHOT: Download buttons -->
> ![Download](assets/download.png)

---

## Chat Widget

### Embed in any webpage

```html
<script src="http://localhost:8000/widget.js" data-api="http://localhost:8000"></script>
```

Paste this into `<head>` or before `</body>`. A floating 💬 bubble appears in the bottom-right corner.

> ![Chat Bubble](assets/chat_bubble.png)

### Chat in action

Click the bubble to open the chat panel. Type a question — the bot searches the extracted Q&A and replies using Azure GPT.


> ![Chat Window](assets/chat_window.png)

> ![Bot Answer](assets/bot_answer.png)

---

## How the Chat Works

```
User types a question
        ↓
POST /chat → src/chat.py
        ↓
Load all Q&A from data/extracted_qa/*.json
        ↓
Keyword scoring → top 4 relevant Q&A selected
        ↓
Azure GPT-4o-mini generates a grounded answer
        ↓
Reply shown in chat widget
```

---

## Adding / Changing Admin Users

Edit `data/users.json`:

```json
[
  {
    "username": "yourname",
    "password": "yourpassword",
    "role": "admin",
    "name": "Your Full Name"
  }
]
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a question, get an answer |
| `GET` | `/widget.js` | Serve the embeddable widget script |
| `GET` | `/health` | Liveness check |

### POST /chat

**Request:**
```json
{ "message": "What is your refund policy?" }
```

**Response:**
```json
{ "reply": "We offer a 30-day money-back guarantee..." }
```
