"""
Bassets Support Agent - API Server

Powers the help center at help.bassets.net.

Endpoints:
- GET  /              -> Help center page
- POST /chat          -> Send a question, get an answer (JSON)
- POST /chat/stream   -> Send a question, get a streamed answer (SSE)
- GET  /health        -> Health check
- GET  /widget.js     -> Legacy embeddable widget (backward compat)

Run with:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

import json
import logging
import os
import re
import sys
import uuid
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.rag import generate_answer
from config import APP_ENV, RATE_LIMIT_CHAT, RATE_LIMIT_GENERAL
from middleware import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    limiter,
)

# ---- Logging Setup ----

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("bassets.api")

# ---- App Setup ----

app = FastAPI(
    title="Bassets Support Agent API",
    description="AI-powered support agent for Bassets Fixed Asset Management Software",
    version="2.0.0",
    docs_url=None if APP_ENV == "production" else "/docs",
    redoc_url=None if APP_ENV == "production" else "/redoc",
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security and logging middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# CORS
_origins = [
    "https://bassets.net",
    "https://www.bassets.net",
    "https://help.bassets.net",
]
if APP_ENV != "production":
    _origins += [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:5500",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Mount static files for the help center frontend
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ---- In-Memory Session Store ----

_sessions: dict[str, dict] = {}
SESSION_TTL_HOURS = 2
MAX_SESSIONS = 10_000

_UUID_RE = re.compile(r"^[a-f0-9\-]{1,64}$")


def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, list]:
    """Get existing session or create a new one."""
    now = time.time()

    # Clean up expired sessions periodically
    expired = [
        sid for sid, s in _sessions.items()
        if now - s["last_active"] > SESSION_TTL_HOURS * 3600
    ]
    for sid in expired:
        del _sessions[sid]

    # Validate session_id format
    if session_id and not _UUID_RE.match(session_id):
        session_id = None

    # Return existing session
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session["last_active"] = now
        return session_id, session["history"]

    # Cap total sessions to prevent memory exhaustion
    if len(_sessions) >= MAX_SESSIONS:
        oldest = min(_sessions, key=lambda k: _sessions[k]["last_active"])
        del _sessions[oldest]

    new_id = session_id or str(uuid.uuid4())
    _sessions[new_id] = {
        "history": [],
        "last_active": now,
        "created": now,
    }
    return new_id, []


# ---- Request/Response Models ----

class ChatRequest(BaseModel):
    """Customer's chat message."""
    message: str = Field(
        ..., min_length=1, max_length=2000,
        description="The customer's question",
    )
    session_id: Optional[str] = Field(
        None, max_length=64,
        description="Session ID for multi-turn conversations",
    )

    @field_validator("message")
    @classmethod
    def clean_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class ChatResponse(BaseModel):
    """Agent's response."""
    answer: str
    session_id: str
    sources: list[dict] = []
    timing: dict = {}


class HealthResponse(BaseModel):
    status: str
    timestamp: str


# ---- Endpoints ----

@app.get("/")
async def serve_help_center():
    """Serve the main help center page."""
    index_path = os.path.join(_static_dir, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Help center page not found")
    return FileResponse(index_path, media_type="text/html")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT_CHAT)
async def chat(request: Request, chat_request: ChatRequest):
    """
    Main chat endpoint.
    Send a question, get an answer grounded in the Bassets knowledge base.
    """
    try:
        session_id, history = get_or_create_session(chat_request.session_id)

        result = generate_answer(
            question=chat_request.message,
            conversation_history=history if history else None,
        )

        history.append({"role": "user", "content": chat_request.message})
        history.append({"role": "assistant", "content": result["answer"]})
        _sessions[session_id]["history"] = history

        return ChatResponse(
            answer=result["answer"],
            session_id=session_id,
            sources=result.get("sources", []),
            timing={
                "retrieval_ms": result.get("retrieval_time_ms", 0),
                "generation_ms": result.get("generation_time_ms", 0),
            },
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error in /chat endpoint")
        raise HTTPException(
            status_code=500,
            detail="I'm having trouble processing your question right now. Please try again in a moment.",
        )


@app.post("/chat/stream")
@limiter.limit(RATE_LIMIT_CHAT)
async def chat_stream(request: Request, chat_request: ChatRequest):
    """
    Streaming chat endpoint.
    Returns Server-Sent Events for real-time typewriter effect.
    """
    try:
        session_id, history = get_or_create_session(chat_request.session_id)

        result = generate_answer(
            question=chat_request.message,
            conversation_history=history if history else None,
            stream=True,
        )

        async def event_stream():
            full_answer = ""

            # Send session_id first
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            # Send sources
            yield f"data: {json.dumps({'type': 'sources', 'sources': result.get('sources', [])})}\n\n"

            # Stream the answer
            try:
                with result["stream"] as stream:
                    for text in stream.text_stream:
                        full_answer += text
                        yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
            except Exception:
                logger.exception("Error during streaming")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Connection interrupted. Your partial response is preserved above.'})}\n\n"

            # Send done signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            # Update session history after streaming completes
            if full_answer:
                history.append({"role": "user", "content": chat_request.message})
                history.append({"role": "assistant", "content": full_answer})
                _sessions[session_id]["history"] = history

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error in /chat/stream endpoint")
        raise HTTPException(
            status_code=500,
            detail="I'm having trouble right now. Please try again in a moment.",
        )


# ---- Legacy Widget (backward compatibility) ----

@app.get("/widget.js")
async def serve_widget():
    """Serve the embeddable chat widget JavaScript."""
    widget_path = os.path.join(os.path.dirname(__file__), "widget", "widget.js")
    if not os.path.exists(widget_path):
        raise HTTPException(status_code=404, detail="Widget not found")
    return FileResponse(widget_path, media_type="application/javascript")


if APP_ENV != "production":
    @app.get("/widget-test")
    async def serve_widget_test():
        """Serve the widget test page (development only)."""
        test_path = os.path.join(os.path.dirname(__file__), "widget", "test.html")
        if not os.path.exists(test_path):
            raise HTTPException(status_code=404, detail="Test page not found")
        return FileResponse(test_path, media_type="text/html")


# ---- Run directly ----

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=APP_ENV != "production",
    )
