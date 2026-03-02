# FAQ Chatbot

An end-to-end FAQ chatbot system with an **Admin Portal** for document ingestion and a **floating chat widget** that can be embedded into any webpage with a single `<script>` tag.

Each admin user gets an isolated knowledge base — the widget only answers from documents uploaded by the user whose `data-user-id` matches.

---

## Architecture

```
Admin Portal (Streamlit :8502)
  └── Login → POST /auth/login (MongoDB)
  └── Upload documents (PDF, DOCX, TXT, XLSX)
  └── Auto-generate Q&A via Google Gemini
  └── Review / Edit / Delete Q&A
  └── Q&A tagged with uploader's user_id → stored in MongoDB

Chat API (FastAPI :8000)
  └── POST /auth/login          → user authentication
  └── POST /chat                → filtered keyword search + Gemini answer
  └── GET/POST/PUT/DELETE /faqs       → Q&A CRUD
  └── GET/POST/DELETE   /documents    → document registry CRUD
  └── GET  /widget.js           → serves embeddable widget

MongoDB
  └── users             → login credentials + roles
  └── faqs              → Q&A pairs (each tagged with user_id)
  └── document_registry → uploaded document metadata

Any Webpage
  └── <script data-user-id="admin" ...>
  └── Widget sends user_id → backend filters FAQs by user_id
  └── Floating 💬 chat bubble (bottom-right)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini — `gemini-2.5-flash` |
| Admin UI | Streamlit |
| Chat API | FastAPI + Uvicorn |
| Document Parsing | pdfplumber, python-docx, openpyxl |
| Auth | MongoDB (`users` collection) via FastAPI |
| Storage | MongoDB Atlas (FAQs + registry + users) |
| Multi-tenancy | `user_id` field on every FAQ document |
| Widget | Vanilla JS + Shadow DOM |

---

## Project Structure

```
FAQ-CHATBOT/
├── src/
│   ├── config.py               # Environment settings (Gemini + MongoDB)
│   ├── database.py             # MongoDB client + shared collections
│   ├── document_processor.py   # Extract + chunk text from documents
│   ├── qa_generator.py         # Gemini Q&A generation
│   ├── chat.py                 # Chat search + answer logic (filtered by user_id)
│   └── main.py                 # FastAPI app (all API endpoints)
├── ui/
│   └── admin.py                # Streamlit admin portal (calls FastAPI)
├── public/
│   └── widget.js               # Embeddable floating chat widget
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
# Google Gemini
GEMINI_API_KEY=56ygza...

# MongoDB Atlas
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=faq_chatbot
MONGODB_COLLECTION=faqs

# API URL (used by Streamlit to call FastAPI)
API_URL=http://localhost:8000
```

---

## Running

### Terminal 1 — Chat API

```bash
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

On first startup, default admin users are automatically seeded into MongoDB.

API docs available at: `http://localhost:8000/docs`

### Terminal 2 — Admin Portal

```bash
source .venv/bin/activate
streamlit run ui/admin.py --server.port 8502
```

Admin portal at: `http://localhost:8502`

> **Note:** The FastAPI server must be running before launching the admin portal.

---

## Admin Portal

### Login

<!-- SCREENSHOT: Login page -->
> ![Login Page](assets/login_page.png)

---

### Upload & Extract Q&A

1. Log in to the admin portal
2. Upload a document (PDF, DOCX, TXT, or XLSX) in the left panel
3. Click **Extract Q&A** — the system will:
   - Extract and chunk the document text
   - Send each chunk to Google Gemini
   - Generate 2–5 Q&A pairs per chunk
   - Save all Q&A to MongoDB, tagged with the logged-in user's `username` as `user_id`
4. Q&A pairs appear in the right panel

<!-- SCREENSHOT: Upload and extraction in progress -->
> ![Upload & Extract](assets/upload_extract.png)

---

### Q&A Management

Each extracted Q&A can be:
- **Edited** — inline edit form with Save / Cancel (calls `PUT /faqs/{faq_id}`)
- **Deleted** — shows confirmation prompt before deleting (calls `DELETE /faqs/{faq_id}`)

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
- **Delete Document** — removes document and all its Q&A from MongoDB (with confirmation)

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
<script
  src="http://localhost:8000/widget.js"
  data-api="http://localhost:8000"
  data-user-id="admin">
</script>
```

Paste this into `<head>` or before `</body>`. A floating 💬 bubble appears in the bottom-right corner.

### Widget attributes

| Attribute | Required | Description |
|-----------|----------|-------------|
| `data-api` | Yes | Base URL of the FastAPI server |
| `data-user-id` | Recommended | Username whose documents to search. If omitted, searches all users' documents. |

> ![Chat Bubble](assets/chat_bubble.png)

### Chat in action

Click the bubble to open the chat panel. Type a question — the bot searches only that user's Q&A and replies using Google Gemini.

> ![Chat Window](assets/chat_window.png)

> ![Bot Answer](assets/bot_answer.png)

---

## How the Chat Works

```
User types a question
        ↓
POST /chat  { message, user_id: "admin" }
        ↓
MongoDB: faqs.find({ user_id: "admin" })
        ↓
Keyword scoring → top 4 relevant Q&A selected
        ↓
Google Gemini generates a grounded answer
        ↓
Reply shown in chat widget
```

---

## Multi-Tenancy (Per-User Isolation)

Every FAQ document stored in MongoDB has a `user_id` field equal to the username of the admin who uploaded it.

```
Admin "alice" uploads → FAQs stored with  user_id: "alice"
Admin "bob"   uploads → FAQs stored with  user_id: "bob"

Widget with data-user-id="alice" → only searches alice's FAQs
Widget with data-user-id="bob"   → only searches bob's FAQs
Widget with no data-user-id      → searches all FAQs (no filter)
```

This lets you embed different widgets on different customer sites while sharing a single backend.

---

## Managing Admin Users

Users are stored in the MongoDB `users` collection. To add or change users, connect to your MongoDB cluster and update the collection directly:

```js
// MongoDB Shell
db.users.insertOne({
  username: "yourname",
  password: "yourpassword",
  role: "admin",
  name: "Your Full Name"
})
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | Verify credentials, return user record |
| `POST` | `/chat` | Send a question, get an answer (filter by `user_id`) |
| `GET` | `/faqs` | List Q&A pairs (filter by `?stem=` and/or `?user_id=`) |
| `POST` | `/faqs/bulk` | Replace all Q&A for a document stem |
| `PUT` | `/faqs/{faq_id}` | Update a Q&A pair |
| `DELETE` | `/faqs/{faq_id}` | Delete a Q&A pair |
| `GET` | `/documents` | List document registry |
| `POST` | `/documents` | Upsert a document record |
| `DELETE` | `/documents/{stem}` | Delete document and all its Q&A |
| `GET` | `/widget.js` | Serve the embeddable widget script |
| `GET` | `/health` | Liveness check |

### POST /chat

**Request:**
```json
{ "message": "What is your refund policy?", "user_id": "admin" }
```

**Response:**
```json
{ "reply": "We offer a 30-day money-back guarantee..." }
```

### POST /auth/login

**Request:**
```json
{ "username": "admin", "password": "admin123" }
```

**Response:**
```json
{ "username": "admin", "role": "admin", "name": "Admin User" }
```
