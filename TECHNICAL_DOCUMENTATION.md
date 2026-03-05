# AI-Powered Offline Learning Micro-Server — Technical Documentation

---

## 1. Project Purpose

This is a **self-contained, fully offline AI-powered educational platform** designed to run on a local machine or Raspberry Pi without any internet connection. It acts as a private "micro-server" for classrooms, remote schools, or low-connectivity environments. Students connect to it over a local Wi-Fi network, upload study materials, query an AI chatbot grounded in those materials, take quizzes, and download resources — all without ever touching the internet after initial setup.

---

## 2. All Implemented Features

| Feature | Description |
|---|---|
| **User Auth** | Login, signup, logout with hashed passwords and session cookies |
| **Role System** | Two roles — `student` (read-only) and `admin` (full access) |
| **Resource Library** | Upload, browse, download, view PDFs and documents |
| **AI Chat** | RAG-powered chatbot answers questions from uploaded materials |
| **Conversation History** | Persistent chat conversations per user, stored in database |
| **PDF Indexing** | Admin can trigger indexing of PDFs for AI search |
| **Quizzes** | Multiple choice quizzes with scoring and result tracking |
| **Admin Dashboard** | Real-time CPU, RAM, disk stats + user/resource/quiz counts |
| **Mobile Access** | CORS + network binding (`0.0.0.0`) allows phone/tablet access |
| **Response Caching** | TTL cache on AI responses, LRU cache on vector search queries |
| **File Download** | Direct file downloads with MIME type handling |
| **Notifications** | Admin can broadcast notifications shown on dashboard |

---

## 3. Frontend Technologies

| Technology | Version | Purpose |
|---|---|---|
| **React** | 18.3.1 | Core UI framework (SPA) |
| **React Router DOM** | 6.26.0 | Client-side routing (6 pages) |
| **Axios** | 1.7.2 | HTTP client for all API calls |
| **Framer Motion** | 11.3.0 | Animations and transitions |
| **Lucide React** | 0.400.0 | Icon library |
| **Tailwind CSS** | 3.4.4 | Utility-first CSS styling |
| **Vite** | 5.3.3 | Build tool and dev server (port 3000) |

**Pages:** `Home`, `Chat`, `Resources`, `Quizzes`, `Admin`, `Login`  
**Components:** `Navbar`, `ChatSidebar`

---

## 4. Backend Framework

**Flask 3.0.0** (Python 3.13)

| Extension | Purpose |
|---|---|
| `Flask-SQLAlchemy 3.1.1` | ORM for SQLite database |
| `Flask-CORS 4.0.0` | Cross-origin requests from React dev server |
| `Flask-Compress 1.14` | Gzip/Brotli response compression |
| `Werkzeug 3.0.1` | Password hashing, file utilities |
| `python-dotenv 1.0.0` | `.env` config management |
| `psutil 7.1.0` | System stats (CPU, RAM, disk) |

The backend runs on **port 5000**, binds to `0.0.0.0` (all network interfaces), and serves both the REST API and the production React build when present.

---

## 5. AI Model Used

**TinyLlama 1.1B Chat v1.0** — quantized to 4-bit (Q4_K_M format)

- File: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
- Size on disk: **~669 MB**
- Parameters: **1.1 billion**
- Loaded via the **GPT4All** Python library (`gpt4all==2.0.2`)

---

## 6. Local vs. API-Based AI

**100% Local / Offline.** The model:
- Is loaded from a `.gguf` file stored in `backend/models/`
- Runs entirely on **CPU** (no GPU required)
- Has `allow_download=False` to prevent any network calls
- Uses `device='cpu'` and `n_threads = cpu_count - 1` for threading
- Has **zero external API calls** — no OpenAI, no Hugging Face inference

---

## 7. File Upload Implementation

**Endpoint:** `POST /api/admin/upload`

Flow:
1. Admin authentication is verified via `session['user_id']` + `is_admin` check
2. File is received via `multipart/form-data` using `request.files['file']`
3. Filename is sanitized with `werkzeug.utils.secure_filename()`
4. Extension is validated against an allowlist: `{pdf, ppt, pptx, doc, docx, txt, mp4, avi, mkv}`
5. File is saved to `backend/resources/uploads/`
6. A `Resource` database record is created with title, category, file path, size, and type
7. Max file size: **100 MB**

---

## 8. Study Materials Processing

**Endpoint:** `POST /api/index-resources` (admin only)

Pipeline:
```
PDF File
  → pdfplumber (extract raw text page-by-page)
  → Light cleaning (collapse excess blank lines)
  → chunk_text() splits into 512-word chunks with 50-word overlap
  → Each chunk tagged with metadata {source: filepath, chunk_id: N}
  → Passed to EmbeddingsManager.add_documents()
  → Sentence-Transformers encodes chunks into 384-dim float32 vectors
  → FAISS index updated and saved to disk
  → Resource.indexed = True in database
```

Supported formats for indexing: **PDF only** (other file types are stored but not indexed for AI search).

---

## 9. RAG (Retrieval-Augmented Generation)

**Yes — full RAG pipeline is implemented.**

Every chat request follows this pattern:

```
User Question
  → EmbeddingsManager.search(question, top_k=5)
     → Encode question with all-MiniLM-L6-v2
     → FAISS cosine similarity search over indexed chunks
     → Returns top-5 (text, metadata, score) tuples
  → ChatBot.chat_with_context(question, search_results)
     → Builds context string from retrieved chunks
     → Injects context into LLM prompt template
  → TinyLlama generates grounded answer
```

If no relevant chunks are found (empty index), the model answers from its own knowledge with higher temperature (`0.5` vs `0.1`).

---

## 10. How Embeddings are Generated

**Model:** `all-MiniLM-L6-v2` from `sentence-transformers==3.3.1`

- Produces **384-dimensional** dense float32 vectors
- Vectors are **L2-normalized** at encode time (`normalize_embeddings=True`)
- Batch size: **32 chunks per batch** for memory efficiency
- Both documents and queries are encoded with the same model for symmetric similarity

---

## 11. Vector Database

**FAISS** (`faiss-cpu==1.9.0.post1`)

- Index type: `IndexFlatIP` (flat inner product — equivalent to cosine similarity on normalized vectors)
- No approximation — exact nearest neighbor search (appropriate for small-medium datasets)
- Index persisted to: `backend/embeddings_cache/faiss_index.bin`
- Metadata (text + source info) persisted separately to: `backend/embeddings_cache/embeddings.pkl` (Python pickle)
- **LRU cache** of the last 50 search queries avoids redundant FAISS lookups

---

## 12. How Questions are Answered

Step-by-step answer generation:

1. User sends `POST /api/chat` with `{ question, conversation_id }`
2. Question is encoded into a 384-dim vector
3. FAISS returns top-5 most similar document chunks by cosine similarity
4. Code-question detection checks for keywords (`program`, `function`, `python`, etc.)
   - Code questions: up to 5 chunks, 800-char limit per chunk, 200 max tokens
   - Theory questions: up to 3 chunks, 500-char limit per chunk, 120 max tokens
5. A structured prompt is built:
   ```
   You are a precise educational assistant. Use ONLY the context below...
   Context: [retrieved chunks]
   Question: [user question]
   Answer:
   ```
6. TinyLlama generates a response with `temp=0.1`, `top_k=40`, `top_p=0.4`, `repeat_penalty=1.18`
7. Response is cached in a **TTL cache** (100 entries, 1-hour expiry) keyed by MD5 hash of `(prompt + context + tokens + temp)`
8. Chat saved to `ChatHistory` table with `conversation_id`
9. Response returned with `answer`, `sources`, `generation_time`, `total_time`

---

## 13. Libraries Used

### Backend (Python)

| Library | Version | Role |
|---|---|---|
| `flask` | 3.0.0 | Web server |
| `flask-sqlalchemy` | 3.1.1 | ORM |
| `flask-cors` | 4.0.0 | CORS |
| `flask-compress` | 1.14 | Response compression |
| `gpt4all` | 2.0.2 | LLM inference engine |
| `sentence-transformers` | 3.3.1 | Text embeddings |
| `faiss-cpu` | 1.9.0 | Vector similarity search |
| `transformers` | 4.46.3 | Tokenizer support |
| `huggingface-hub` | 0.26.2 | Model downloading |
| `pdfplumber` | 0.11.4 | PDF text extraction |
| `cachetools` | 5.5.0 | TTL + LRU caches |
| `diskcache` | 5.6.3 | Disk-based caching |
| `numpy` | 2.1.3 | Vector math |
| `psutil` | 7.1.0 | System monitoring |
| `python-dotenv` | 1.0.0 | Config from `.env` |
| `werkzeug` | 3.0.1 | Password hashing, file utils |

### Frontend (JavaScript)

| Library | Version | Role |
|---|---|---|
| `react` | 18.3.1 | UI framework |
| `react-router-dom` | 6.26.0 | Routing |
| `axios` | 1.7.2 | HTTP client |
| `framer-motion` | 11.3.0 | Animations |
| `lucide-react` | 0.400.0 | Icons |
| `tailwindcss` | 3.4.4 | CSS styling |
| `vite` | 5.3.3 | Build tool |

---

## 14. Project Architecture (Step-by-Step)

```
┌─────────────────────────────────────────────────────────────┐
│                     USER DEVICES                            │
│  Browser / Phone  →  http://localhost:3000 (dev)            │
│                   →  http://<server-ip>:5000 (prod build)   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / REST API
┌───────────────────────────▼─────────────────────────────────┐
│                   REACT FRONTEND (Vite)                     │
│  Pages: Home, Chat, Resources, Quizzes, Admin, Login        │
│  State: React hooks (useState, useEffect)                   │
│  HTTP: Axios → baseURL: http://localhost:5000               │
│  Auth: session cookie (withCredentials: true)               │
└───────────────────────────┬─────────────────────────────────┘
                            │ JSON REST
┌───────────────────────────▼─────────────────────────────────┐
│                   FLASK BACKEND (port 5000)                 │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────────┐ │
│  │   Auth   │  │  Resources │  │      Chat / RAG          │ │
│  │ /api/    │  │ /api/      │  │      /api/chat           │ │
│  │ login    │  │ resources  │  │                          │ │
│  │ signup   │  │ upload     │  │  EmbeddingsManager       │ │
│  │ logout   │  │ download   │  │  → FAISS search          │ │
│  └──────────┘  └────────────┘  │  ChatBot                 │ │
│  ┌──────────┐  ┌────────────┐  │  → TinyLlama GPT4All     │ │
│  │  Quizzes │  │   Admin    │  └──────────────────────────┘ │
│  │ /api/    │  │ /api/admin │                               │
│  │ quizzes  │  │ dashboard  │                               │
│  └──────────┘  └────────────┘                               │
└───────┬─────────────────────────┬───────────────────────────┘
        │                         │
┌───────▼──────────┐   ┌──────────▼──────────────────────────┐
│  SQLite Database │   │       AI Layer                      │
│  (SQLAlchemy)    │   │                                     │
│  • users         │   │  sentence-transformers              │
│  • resources     │   │  (all-MiniLM-L6-v2, 384-dim)        │
│  • quizzes       │   │  ↓                                  │
│  • quiz_results  │   │  FAISS IndexFlatIP                  │
│  • chat_history  │   │  (cosine similarity search)         │
│  • conversations │   │  ↓                                  │
│  • notifications │   │  GPT4All → TinyLlama 1.1B           │
└──────────────────┘   │  (CPU inference, Q4_K_M quant)      │
                        └─────────────────────────────────────┘
```

---

## 15. API Flow — Frontend to Backend

**Example: User sends a chat message**

```
1. User types question in Chat.jsx → clicks Send
2. axios.post('/api/chat', { question, conversation_id })
   Headers: Cookie: session=<flask_session_cookie>
3. Flask @app.before_request logs: user_id, origin, session data
4. api_chat() handler:
   a. Validates question is not empty
   b. get_embeddings_manager() → lazy-loads sentence-transformers + FAISS
   c. em.search(question, top_k=5)
      → Checks LRU query cache
      → Encodes question to 384-dim vector
      → FAISS.search() returns top-5 (text, metadata, score)
   d. get_chatbot() → lazy-loads TinyLlama model into RAM
   e. bot.chat_with_context(question, search_results)
      → Detects if code/theory question
      → Builds prompt with context
      → Checks TTL response cache (MD5 key)
      → GPT4All.generate() → response text
   f. Saves ChatHistory to SQLite if user logged in
5. Returns JSON: { answer, sources, generation_time, total_time }
6. Chat.jsx appends { role: 'assistant', content: answer } to messages
7. Framer Motion animates message into view
```

---

## 16. How Responses are Generated

The LLM uses a **constrained instruction prompt** to prevent hallucination:

```
System: You are a precise educational assistant. Use ONLY the context below.
        Do not add, assume, or create information not present.

Context: [top 3–5 FAISS-retrieved chunks, up to 800 chars each]

Question: [user's question]

Instructions:
  - For code: provide COMPLETE code exactly as shown in context
  - For theory: explain using exact context information
  - If not in context: say "I don't have this information..."
  - Preserve code formatting exactly

Answer:
```

**Generation parameters:**

| Parameter | Value | Effect |
|---|---|---|
| `temp` | 0.1 (with context) / 0.5 (no context) | Low = deterministic, fast |
| `top_k` | 40 | Token sampling diversity |
| `top_p` | 0.4 | Nucleus sampling cutoff |
| `repeat_penalty` | 1.18 | Discourages word repetition |
| `max_tokens` | 120 (theory) / 200 (code) | Response length cap |
| `streaming` | `False` | Full response returned at once |

---

## 17. Memory Usage and Model Size

| Component | RAM Usage | Disk Size |
|---|---|---|
| TinyLlama 1.1B Q4_K_M | ~600–700 MB RAM | 669 MB |
| all-MiniLM-L6-v2 | ~90 MB RAM | ~90 MB (HF cache) |
| FAISS index (empty) | < 1 MB | Varies by docs |
| SQLite database | < 5 MB | < 5 MB |
| Flask + Python runtime | ~50 MB | — |
| **Total minimum** | **~800 MB RAM** | **~760 MB disk** |

**CPU threads:** `os.cpu_count() - 1` (leaves 1 core free for OS)  
**Model loading:** Lazy — loads on **first chat request**, not at server startup  
**First response:** 10–30 seconds (model load) → subsequent responses: 3–10 seconds

---

## 18. Suggested Improvements

### Performance
- Use `llama-cpp-python` directly instead of GPT4All for finer control over context window and KV-cache
- Pre-warm the model at server startup in a background thread instead of lazy-loading on first request (avoids cold-start timeout errors)
- Switch FAISS to `IndexIVFFlat` with clustering for faster search as the document count grows

### Features
- Add support for `.docx` and `.pptx` text extraction (currently only PDFs are indexed despite being in the allowed list)
- Add an AI-generated quiz feature: index a resource → auto-generate MCQs from it
- Add per-user progress tracking (quiz streaks, topics studied)
- Add support for summarization endpoint (`POST /api/summarize/<resource_id>`)

### Architecture
- Move AI inference to a background task queue (e.g., `celery` + `redis`) with WebSocket progress updates — prevents 30-second HTTP timeouts on first load
- Replace SQLite with PostgreSQL for multi-user concurrent write performance
- Add a `POST /api/chat/stream` endpoint using `streaming=True` in GPT4All + Server-Sent Events for real-time token streaming in the UI

### Security
- Change `SECRET_KEY` and `ADMIN_PASSWORD` in `.env` from defaults
- Add rate limiting (`flask-limiter`) on `/api/chat` and `/api/login`
- Set `SESSION_COOKIE_SECURE=True` and serve over HTTPS in production

### DevOps
- Add a single `start.bat` / `start.sh` launcher script that activates the venv, starts Flask, and opens the browser automatically
- Add `pytest` test suite for API endpoints
- Add a `Dockerfile` for containerized deployment
