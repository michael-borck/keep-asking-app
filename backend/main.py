"""
keep-asking prototype - FastAPI backend

Handles:
- Student login (student number -> session code + condition assignment)
- Chat relay to frontier model (with system prompt suppressing engagement hooks)
- Nudge append for nudge condition (server-side, invisible to model)
- Full transcript logging (SQLite)
- Session export and de-identification

Run: uvicorn main:app --reload --port 8000
"""

import os
import random
import string
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from anthropic import Anthropic

import db


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Test student number - always accepted, flagged as test data
TEST_STUDENT = "TEST000"

# Nudge variants - randomly selected each turn to reduce habituation.
NUDGE_VARIANTS = [
    "Does that match what you expected? If something seems off, tell me what seems wrong.",
    "Before you move on - does that actually answer your question, or just part of it?",
    "Is there anything in that response that doesn't quite fit with what you already know?",
    "What would you challenge in that answer if you were reviewing someone else's work?",
    "Does that feel complete, or is there a gap worth pushing on?",
    "If you had to argue the opposite, what would you say?",
    "Is that specific enough to be useful, or is it still too general?",
    "What's the weakest part of that response?",
    "Does that account for the details in your task, or is it a generic answer?",
    "Would you trust that answer enough to use it without checking? Why or why not?",
]

NUDGE_PREFIX = "\n\n---\n*"
NUDGE_SUFFIX = "*"


def get_nudge() -> str:
    variant = random.choice(NUDGE_VARIANTS)
    return f"{NUDGE_PREFIX}{variant}{NUDGE_SUFFIX}"


SYSTEM_PROMPT = """You are an AI assistant helping a university student complete a structured task.

IMPORTANT INSTRUCTIONS FOR YOUR RESPONSE STYLE:
- Answer the student's question directly and completely.
- Do NOT end your response with follow-up questions.
- Do NOT offer to elaborate, explain further, or help with anything else.
- Do NOT append phrases like "Would you like me to...", "Let me know if...", "I can also...", "Feel free to ask...", or similar engagement hooks.
- Do NOT use bullet points listing "next steps" or "things to consider" unless the student specifically asked for them.
- Simply answer what was asked, then stop.

Your goal is to be helpful and accurate, but to let the student drive the conversation. If they want more, they will ask."""

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="keep-asking prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory conversation histories keyed by session_code.
# Only used for building the messages list sent to the AI model.
# Everything persistent lives in SQLite.
_conversation_cache: dict[str, list[dict]] = {}


@app.on_event("startup")
def startup():
    db.init_db(DATA_DIR)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    student_number: str = ""
    condition: str | None = None
    consented: bool = True

class LoginResponse(BaseModel):
    session_code: str
    condition: str

class ChatRequest(BaseModel):
    session_code: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    turn_number: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_session_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def assign_condition() -> str:
    return random.choice(["nudge", "control"])


def call_ai(messages: list[dict], system: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _get_conversation(session_code: str) -> list[dict]:
    """Return the in-memory conversation history, rebuilding from DB if needed."""
    if session_code not in _conversation_cache:
        transcript = db.get_full_transcript(session_code)
        messages = []
        for t in transcript:
            if t["role"] == "user":
                messages.append({"role": "user", "content": t["content"]})
            elif t["role"] == "assistant_raw":
                messages.append({"role": "assistant", "content": t["content"]})
        _conversation_cache[session_code] = messages
    return _conversation_cache[session_code]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest):
    student_number = req.student_number.strip()
    consented = req.consented

    # Non-consented sessions are treated like test sessions — no data linked
    is_test = not consented or student_number.upper() == TEST_STUDENT

    if consented and not student_number:
        raise HTTPException(400, "Student number is required when consenting")

    # Check if this student already has a session (skip for test/non-consented)
    if not is_test:
        existing = db.get_session_code_for_student(student_number)
        if existing:
            session = db.get_session(existing)
            return LoginResponse(session_code=existing, condition=session["condition"])

    session_code = generate_session_code()
    condition = req.condition if req.condition in ("nudge", "control") else assign_condition()

    db.create_session(session_code, condition, is_test)

    if not is_test:
        db.create_linkage(student_number, session_code)

    if not consented:
        label = "NO-CONSENT session"
    elif is_test:
        label = "TEST session"
    else:
        label = "Session"
    db.log_turn(session_code, "system", f"{label} started. Condition: {condition}", 0)

    return LoginResponse(session_code=session_code, condition=condition)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session = db.get_session(req.session_code)
    if not session:
        raise HTTPException(404, "Session not found")

    message = req.message.strip()
    if not message:
        raise HTTPException(400, "Message is required")

    # Determine turn number from existing turns
    conversation = _get_conversation(req.session_code)
    turn_number = sum(1 for m in conversation if m["role"] == "user") + 1

    # Log and append user message
    db.log_turn(req.session_code, "user", message, turn_number)
    conversation.append({"role": "user", "content": message})

    # Call AI
    ai_response = call_ai(conversation, SYSTEM_PROMPT)

    # Log raw AI response
    db.log_turn(req.session_code, "assistant_raw", ai_response, turn_number)

    # Append nudge if nudge condition
    if session["condition"] == "nudge":
        display_response = ai_response + get_nudge()
    else:
        display_response = ai_response

    # Log what the student sees
    db.log_turn(req.session_code, "assistant_display", display_response, turn_number)

    # Cache raw response for AI context (model never sees the nudge)
    conversation.append({"role": "assistant", "content": ai_response})

    return ChatResponse(reply=display_response, turn_number=turn_number)


@app.get("/api/sessions")
def list_sessions():
    rows = db.list_sessions()
    return {
        r["session_code"]: {
            "condition": r["condition"],
            "turn_count": r["turn_count"],
            "created_at": r["created_at"],
            "is_test": bool(r["is_test"]),
        }
        for r in rows
    }


@app.get("/api/history/{session_code}")
def get_history(session_code: str):
    session = db.get_session(session_code)
    if not session:
        raise HTTPException(404, "Session not found")
    messages = db.get_display_history(session_code)
    turn_count = sum(1 for m in messages if m["role"] == "user")
    return {"messages": messages, "turn_count": turn_count}


@app.get("/api/export/{session_code}")
def export_session(session_code: str):
    transcript = db.get_full_transcript(session_code)
    if not transcript:
        raise HTTPException(404, "Session log not found")
    return transcript



# ---------------------------------------------------------------------------
# Static file serving (production: built React frontend in ./static)
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = STATIC_DIR / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
