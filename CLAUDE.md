# CLAUDE.md - Bassets Support Agent

> Project knowledge base for Claude Code. Updated automatically as the project evolves.
> Last updated: 2026-02-26

---

## Project Overview

**Bassets Support Agent** is a RAG-powered AI customer support system for [Bassets.net](https://bassets.net) Fixed Asset Management Software. It ingests company documents into a Pinecone vector database and uses Claude to answer customer questions. The public-facing product is a **standalone help center page** at `help.bassets.net` with a modern search/chat interface and common query cards.

## Tech Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| Backend API | FastAPI + Uvicorn | REST + SSE streaming, rate limiting via slowapi |
| Vector DB | Pinecone Serverless | AWS us-east-1, cosine similarity, 1024 dims |
| Embeddings | Voyage AI (voyage-3) | 1024 dimensions, query/document optimized |
| LLM | Anthropic Claude | claude-sonnet-4-6, 1024 max tokens |
| Tokenizer | tiktoken (cl100k_base) | Used for accurate chunk sizing |
| Frontend | Vanilla JS (ES modules) | Full help center page + legacy embeddable widget |
| CLI | Typer + Rich | Ingestion pipeline with progress bars |
| Config | python-dotenv | All secrets via .env file |
| Deployment | Docker + Railway | Dockerfile + railway.toml |

## Directory Structure

```
bassets-support-agent/
├── agent/                     # RAG agent core
│   ├── rag.py                 # Retrieval + generation pipeline
│   ├── prompts.py             # System prompt + context template
│   └── __init__.py
├── utils/                     # Data processing utilities
│   ├── embedder.py            # Voyage AI embedding wrapper
│   ├── parsers.py             # Multi-format document parsers
│   ├── chunker.py             # Token-aware text chunking with overlap
│   ├── tagger.py              # Keyword-based product area tagging
│   └── __init__.py
├── config/                    # Configuration
│   └── __init__.py            # Env vars, chunking params, product areas
├── static/                    # Help center frontend (served by FastAPI)
│   ├── index.html             # Main help center page
│   ├── css/styles.css         # Bassets-branded stylesheet (CSS custom properties)
│   ├── js/
│   │   ├── app.js             # Main controller (state transitions, init)
│   │   ├── chat.js            # SSE streaming engine, message rendering
│   │   ├── session.js         # Session + localStorage persistence
│   │   ├── cards.js           # 8 common query cards with icons
│   │   └── markdown.js        # XSS-safe markdown renderer
│   └── images/                # Logo (user-provided)
├── widget/                    # Legacy embeddable chat widget
│   ├── widget.js              # Self-contained IIFE widget
│   ├── test.html              # Local test page
│   └── test.py                # Widget test script
├── data/                      # Source documents (gitignored)
│   ├── pdfs/                  # Product manuals
│   ├── docs/                  # Claude project exports
│   ├── transcripts/           # Whisper transcripts
│   └── zoho/                  # Zoho Desk CSV exports
├── server.py                  # FastAPI backend (main entry point)
├── middleware.py               # Security headers, logging, rate limiting
├── ingest.py                  # Document ingestion pipeline (CLI)
├── setup_pinecone.py          # One-time Pinecone index creation
├── test_query.py              # Vector search testing utility
├── export_zoho.py             # Zoho Desk API data exporter
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Production container
├── railway.toml               # Railway deployment config
├── .env                       # API keys (NEVER commit)
├── .env.example               # Template for .env
├── .gitignore                 # Ignores .env, data/*, __pycache__
└── README.md                  # Setup and usage docs
```

## Key Files & Their Roles

### Server & Middleware
- **server.py** — FastAPI app. Routes: `GET /` (help center), `POST /chat`, `POST /chat/stream`, `GET /health`, `GET /widget.js`. Rate limited, security headers, structured logging. Mounts `static/` directory. Disables `/docs` and `/widget-test` in production.
- **middleware.py** — `SecurityHeadersMiddleware` (CSP, X-Frame-Options), `RequestLoggingMiddleware` (request ID, timing), `limiter` (slowapi, 20 req/min on chat).

### Help Center Frontend (static/)
- **static/index.html** — Semantic HTML5 page: header, hero with search input, 8 query cards, chat section (hidden initially), footer. ARIA landmarks, skip-link, screen reader live region.
- **static/css/styles.css** — Bassets branding via CSS custom properties. Fonts: Lora (headings), Plus Jakarta Sans (body). Colors: #1A5276 primary, #2C3E50 text. Responsive: 4-col → 2-col → 1-col cards. `prefers-reduced-motion` support.
- **static/js/app.js** — Main controller. Initializes cards, forms, session restore. Manages browse↔chat state transitions. Keyboard shortcuts (Escape stops streaming).
- **static/js/chat.js** — SSE streaming engine with AbortController for stop-generation. Fallback to `/chat` on SSE failure. Rate limit countdown, retry buttons, partial response preservation, auto-scroll.
- **static/js/session.js** — Manages server session ID + localStorage backup (last 20 messages, 2hr TTL). Restores previous conversation on page load.
- **static/js/cards.js** — 8 common query cards: Depreciation, Installation, Reports, Assets, Import/Export, Section 179, Login, Cloud. Click auto-fills and submits the question.
- **static/js/markdown.js** — XSS-safe markdown renderer (escapes HTML first). Supports bold, italic, code, lists, links, paragraphs. Source citation pills.

### RAG Pipeline (agent/)
- **agent/rag.py** — Embed question → Pinecone top-6 search (score > 0.5) → build context → Claude (streaming or sync). Lazy-initialized clients.
- **agent/prompts.py** — System prompt: professional, honest, concise. Context template with source attribution.

### Data Processing (utils/)
- **utils/embedder.py** — Voyage AI wrapper. Batch embed (32/batch) with retry. Separate query/document types.
- **utils/parsers.py** — 5 formats: PDF, Zoho tickets, Zoho KB, Text/Markdown, Transcripts. Returns `Document(text, metadata)`.
- **utils/chunker.py** — 512-token chunks, 64-token overlap, 800 max. Sentence-boundary aware.
- **utils/tagger.py** — Keyword matching → product area classification.

## Configuration

### Environment Variables (.env)
```
APP_ENV=development              # development | production
RATE_LIMIT_CHAT=20/minute        # Rate limit for chat endpoints
RATE_LIMIT_GENERAL=60/minute     # Rate limit for other endpoints
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=bassets-support
VOYAGE_API_KEY=...
ANTHROPIC_API_KEY=...
ZOHO_DESK_ORG_ID=...             # Optional
ZOHO_DESK_API_TOKEN=...          # Optional
```

### CORS Origins (server.py)
- Production: `https://bassets.net`, `https://www.bassets.net`, `https://help.bassets.net`
- Development: adds localhost:3000, localhost:8000, localhost:8080, 127.0.0.1:5500

## Common Commands

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env          # Fill in API keys
python setup_pinecone.py      # Create vector index (one-time)

# Run server (visit http://localhost:8000)
python server.py

# Ingest documents
python ingest.py --source ./data
python ingest.py --source ./data --dry-run

# Test queries
python test_query.py --interactive

# Deploy
docker build -t bassets-help .
docker run -p 8000:8000 --env-file .env bassets-help
```

## Architecture Decisions

1. **Standalone help center page** (not just a widget) — mapped to help.bassets.net subdomain
2. **Vanilla JS (ES modules)** — no build step, no bundler; each file has a single responsibility
3. **CSS custom properties** — entire color/font scheme configurable from `:root`
4. **Browse→Chat state transition** — hero contracts, cards hide, chat appears; single-page UX
5. **localStorage session backup** — conversation survives page refreshes (last 20 messages, 2hr TTL)
6. **Rate limiting (slowapi)** — 20 req/min per IP on chat; friendly countdown UX on 429
7. **Security headers middleware** — CSP, X-Frame-Options, nosniff, etc.
8. **Sanitized errors** — no `str(e)` in user-facing responses; full exceptions logged server-side

## Known Limitations & Tech Debt

- [ ] Sessions are in-memory — swap for Redis in production
- [ ] No tests — need unit + integration test suite
- [ ] `_strip_html` duplicated in `parsers.py` and `export_zoho.py`
- [ ] Tagger is keyword-only — could use embedding-based classification
- [ ] Single-threaded ingestion — could benefit from async embedding
- [x] ~~No rate limiting~~ — Added via slowapi middleware
- [x] ~~No logging~~ — Added request logging middleware
- [x] ~~CORS too permissive~~ — Tightened methods/headers, prod removes localhost
- [x] ~~Widget-only frontend~~ — Built full help center page

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-02-26 | Built standalone help center (static/), middleware.py, Dockerfile, railway.toml | Deploy as public page at help.bassets.net |
| 2026-02-26 | Created CLAUDE.md | Initial project documentation |

## Lessons Learned

> Tracks mistakes, gotchas, and hard-won insights. Update as issues are found.

*No entries yet.*

<!--
INSTRUCTIONS FOR UPDATING THIS FILE:
1. When a bug is fixed, add root cause and fix to "Lessons Learned"
2. When architecture changes, update "Architecture Decisions" + "Change Log"
3. When tech debt is resolved, check it off in "Known Limitations"
4. When new files are added, update "Directory Structure" and "Key Files"
5. Keep Change Log in reverse chronological order (newest first)
6. Keep this file under 300 lines — move details to separate memory files
-->
