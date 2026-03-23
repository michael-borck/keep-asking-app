"""
keep-asking prototype - FastAPI backend

Handles:
- Student login (student number -> session code + condition assignment)
- Chat relay to frontier model (with system prompt suppressing engagement hooks)
- Nudge append for nudge condition (server-side, invisible to model)
- Full transcript logging (every turn, timestamped)
- Session export and de-identification

Run: uvicorn main:app --reload --port 8000
"""

import json
import os
import random
import string
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Optional: import the AI client
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Which provider to use: "anthropic" or "openai"
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")

# API keys - set via environment variables, never hardcode in production
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Models
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# The nudge text appended to every AI response in the nudge condition
NUDGE_TEXT = (
    "\n\n---\n"
    "*Does that match what you expected? "
    "If something seems off, tell me what seems wrong.*"
)

# System prompt: suppresses the model's natural tendency to append
# follow-up suggestions, offers to elaborate, or engagement hooks.
SYSTEM_PROMPT = """You are an AI assistant helping a university student complete a structured task.

IMPORTANT INSTRUCTIONS FOR YOUR RESPONSE STYLE:
- Answer the student's question directly and completely.
- Do NOT end your response with follow-up questions.
- Do NOT offer to elaborate, explain further, or help with anything else.
- Do NOT append phrases like "Would you like me to...", "Let me know if...", "I can also...", "Feel free to ask...", or similar engagement hooks.
- Do NOT use bullet points listing "next steps" or "things to consider" unless the student specifically asked for them.
- Simply answer what was asked, then stop.

Your goal is to be helpful and accurate, but to let the student drive the conversation. If they want more, they will ask."""

# Data directory for logs
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

# In-memory session store (use a database for production)
sessions: dict[str, dict] = {}

# Linkage table (student_number -> session_code) - destroyed after de-identification
linkage_table: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    student_number: str
    condition: str | None = None  # "nudge" or "control"; if None, randomly assigned


class LoginResponse(BaseModel):
    session_code: str
    condition: str  # "nudge" or "control" - NOT sent to student in production


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
    """Generate a random 8-character alphanumeric session code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def assign_condition() -> str:
    """Randomly assign nudge or control with equal probability."""
    return random.choice(["nudge", "control"])


def log_turn(session_code: str, role: str, content: str, turn_number: int):
    """Append a turn to the session's log file."""
    log_path = DATA_DIR / f"{session_code}.jsonl"
    entry = {
        "session_code": session_code,
        "turn_number": turn_number,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "epoch": time.time(),
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def call_ai(messages: list[dict], system: str) -> str:
    """Call the configured AI provider and return the response text."""

    if AI_PROVIDER == "anthropic":
        if not HAS_ANTHROPIC:
            raise HTTPException(500, "anthropic package not installed")
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

    elif AI_PROVIDER == "openai":
        if not HAS_OPENAI:
            raise HTTPException(500, "openai package not installed")
        if not OPENAI_API_KEY:
            raise HTTPException(500, "OPENAI_API_KEY not set")
        client = OpenAI(api_key=OPENAI_API_KEY)
        oai_messages = [{"role": "system", "content": system}] + messages
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=1024,
            messages=oai_messages,
        )
        return response.choices[0].message.content

    else:
        raise HTTPException(500, f"Unknown AI_PROVIDER: {AI_PROVIDER}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """
    Student enters their student number.
    Returns a session code and assigns a condition.
    The student number is stored in the linkage table only.
    """
    student_number = req.student_number.strip()
    if not student_number:
        raise HTTPException(400, "Student number is required")

    # Check if this student already has a session
    if student_number in linkage_table:
        session_code = linkage_table[student_number]
        session = sessions[session_code]
        return LoginResponse(
            session_code=session_code,
            condition=session["condition"],
        )

    session_code = generate_session_code()
    if req.condition in ("nudge", "control"):
        condition = req.condition
    else:
        condition = assign_condition()

    # Store linkage (for equity flag matching later)
    linkage_table[student_number] = session_code

    # Store session (no student number here - only session code)
    sessions[session_code] = {
        "condition": condition,
        "messages": [],  # conversation history for AI context
        "turn_count": 0,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Log the session start
    log_turn(session_code, "system", f"Session started. Condition: {condition}", 0)

    return LoginResponse(session_code=session_code, condition=condition)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Student sends a message. Backend relays to AI, optionally appends nudge,
    logs everything, returns response.
    """
    session = sessions.get(req.session_code)
    if not session:
        raise HTTPException(404, "Session not found")

    message = req.message.strip()
    if not message:
        raise HTTPException(400, "Message is required")

    # Increment turn count
    session["turn_count"] += 1
    turn_number = session["turn_count"]

    # Log student turn
    log_turn(req.session_code, "user", message, turn_number)

    # Add to conversation history
    session["messages"].append({"role": "user", "content": message})

    # Call AI
    ai_response = call_ai(session["messages"], SYSTEM_PROMPT)

    # Log the raw AI response (before nudge)
    log_turn(req.session_code, "assistant_raw", ai_response, turn_number)

    # Append nudge if nudge condition
    if session["condition"] == "nudge":
        display_response = ai_response + NUDGE_TEXT
    else:
        display_response = ai_response

    # Log what the student actually sees
    log_turn(req.session_code, "assistant_display", display_response, turn_number)

    # Add raw response to conversation history (AI doesn't see the nudge)
    session["messages"].append({"role": "assistant", "content": ai_response})

    return ChatResponse(reply=display_response, turn_number=turn_number)


@app.get("/api/sessions")
def list_sessions():
    """List all sessions (admin endpoint for facilitator)."""
    return {
        code: {
            "condition": s["condition"],
            "turn_count": s["turn_count"],
            "created_at": s["created_at"],
        }
        for code, s in sessions.items()
    }


@app.get("/api/history/{session_code}")
def get_history(session_code: str):
    """
    Return the conversation history for a session (what the student saw).
    Used by the frontend to restore chat after a page reload.
    """
    session = sessions.get(session_code)
    if not session:
        raise HTTPException(404, "Session not found")

    # Rebuild the display history from the log file
    log_path = DATA_DIR / f"{session_code}.jsonl"
    messages = []
    if log_path.exists():
        for line in log_path.read_text().strip().split("\n"):
            entry = json.loads(line)
            if entry["role"] == "user":
                messages.append({"role": "user", "content": entry["content"]})
            elif entry["role"] == "assistant_display":
                messages.append({"role": "assistant", "content": entry["content"]})
    return {"messages": messages, "turn_count": session["turn_count"]}


@app.get("/api/export/{session_code}")
def export_session(session_code: str):
    """Export full transcript for a session (admin)."""
    log_path = DATA_DIR / f"{session_code}.jsonl"
    if not log_path.exists():
        raise HTTPException(404, "Session log not found")
    lines = log_path.read_text().strip().split("\n")
    return [json.loads(line) for line in lines]


@app.post("/api/deidentify")
def deidentify():
    """
    Destroy the linkage table. After this, there is no way to connect
    session codes back to student numbers.

    In production, this would:
    1. Export linkage table to a secure location for equity flag matching
    2. Run the equity flag matching script
    3. Destroy the linkage table
    4. Log the destruction with timestamp
    """
    global linkage_table
    count = len(linkage_table)
    linkage_table = {}
    timestamp = datetime.utcnow().isoformat()

    # Log the destruction
    destruction_log = {
        "event": "linkage_table_destroyed",
        "records_destroyed": count,
        "timestamp": timestamp,
    }
    log_path = DATA_DIR / "deidentification_log.json"
    with open(log_path, "w") as f:
        json.dump(destruction_log, f, indent=2)

    return {"message": f"Linkage table destroyed. {count} records removed.", "timestamp": timestamp}
