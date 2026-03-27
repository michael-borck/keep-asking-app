"""
keep-asking prototype - FastAPI backend

Handles:
- Lab session time-gating (backend clock, JSON config)
- Student login (student number -> session code + condition assignment)
- Chat relay to frontier model (with system prompt suppressing engagement hooks)
- Nudge append for nudge condition (server-side, invisible to model)
- Exit survey collection
- Full transcript logging (SQLite)
- Session export and de-identification

Run: uvicorn main:app --reload --port 8000
"""

import json
import logging
import os
import random
import string
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from anthropic import Anthropic

import db

logger = logging.getLogger("keep-asking")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Test student number - always accepted, flagged as test data
TEST_STUDENT = "TEST000"

# Config file resolution: check CONFIG_DIR (Docker volume mount) first,
# then fall back to the backend directory (local dev).
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "/app/config"))
_BACKEND_DIR = Path(__file__).parent


def _config_path(filename: str) -> Path:
    """Return the path to a config file, preferring CONFIG_DIR over backend dir."""
    external = CONFIG_DIR / filename
    if external.exists():
        return external
    return _BACKEND_DIR / filename


# Nudge configuration — loaded from JSON config file.
# Supports multiple named pools and configurable count per turn.
#   count: "1", "2", "3"           → fixed number of nudges
#          "random"                 → random 1-2 nudges
#          "random:1-3"            → random in explicit range
NUDGE_CONFIG_FILE = _config_path("nudge_config.json")


_NUDGE_FALLBACK = {"active_pool": "default", "count": "1",
                    "prefix": "\n\n---\n*", "suffix": "*", "separator": "\n\n",
                    "pools": {"default": ["Take a moment to consider that response."]}}


def _load_nudge_config() -> dict:
    if not NUDGE_CONFIG_FILE.exists():
        logger.warning("nudge_config.json not found — using built-in defaults")
        return _NUDGE_FALLBACK
    try:
        with open(NUDGE_CONFIG_FILE) as f:
            cfg = json.load(f)
        if not isinstance(cfg.get("pools"), dict) or not cfg["pools"]:
            raise ValueError("'pools' must be a non-empty object")
        return cfg
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("nudge_config.json is invalid (%s) — using built-in defaults", e)
        return _NUDGE_FALLBACK


NUDGE_CONFIG: dict = _load_nudge_config()


def _resolve_nudge_count(count_spec: str) -> int:
    """Parse the count config value into an actual number for this turn."""
    if count_spec.isdigit():
        return int(count_spec)
    if count_spec == "random":
        return random.randint(1, 2)
    if count_spec.startswith("random:"):
        lo, hi = count_spec.split(":")[1].split("-")
        return random.randint(int(lo), int(hi))
    return 1


def get_nudge() -> str:
    pool_name = NUDGE_CONFIG.get("active_pool", "default")
    pool = NUDGE_CONFIG.get("pools", {}).get(pool_name, [])
    if not pool:
        return ""
    prefix = NUDGE_CONFIG.get("prefix", "\n\n---\n*")
    suffix = NUDGE_CONFIG.get("suffix", "*")
    separator = NUDGE_CONFIG.get("separator", "\n\n")
    count = _resolve_nudge_count(NUDGE_CONFIG.get("count", "1"))
    count = min(count, len(pool))  # don't exceed pool size
    selected = random.sample(pool, count)
    formatted = [f"{prefix}{nudge}{suffix}" for nudge in selected]
    return separator.join(formatted)


# System prompt — loaded from JSON config file.
# Supports multiple named prompts; set "active" to switch.
PROMPTS_CONFIG_FILE = _config_path("prompts.json")


_PROMPTS_FALLBACK = {"active": "default", "prompts": {
    "default": "You are an AI assistant. Answer the question directly. Do not ask follow-up questions."
}}


def _load_prompts_config() -> dict:
    if not PROMPTS_CONFIG_FILE.exists():
        logger.warning("prompts.json not found — using built-in defaults")
        return _PROMPTS_FALLBACK
    try:
        with open(PROMPTS_CONFIG_FILE) as f:
            cfg = json.load(f)
        if not isinstance(cfg.get("prompts"), dict) or not cfg["prompts"]:
            raise ValueError("'prompts' must be a non-empty object")
        return cfg
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("prompts.json is invalid (%s) — using built-in defaults", e)
        return _PROMPTS_FALLBACK


PROMPTS_CONFIG: dict = _load_prompts_config()


def get_system_prompt() -> str:
    name = PROMPTS_CONFIG.get("active", "default")
    return PROMPTS_CONFIG.get("prompts", {}).get(name, "")

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Lab session schedule — loaded from JSON config file at startup.
LAB_SESSIONS_FILE = _config_path("lab_sessions.json")


def _load_lab_sessions() -> list[dict]:
    if not LAB_SESSIONS_FILE.exists():
        logger.warning("lab_sessions.json not found — no lab sessions configured")
        return []
    try:
        with open(LAB_SESSIONS_FILE) as f:
            sessions = json.load(f)
        if not isinstance(sessions, list):
            raise ValueError("lab_sessions.json must be a JSON array")
        for s in sessions:
            for key in ("lab_id", "start_time", "end_time"):
                if key not in s:
                    raise ValueError(f"lab session missing required field '{key}'")
        return sessions
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("lab_sessions.json is invalid (%s) — no lab sessions loaded", e)
        return []


LAB_SESSIONS: list[dict] = _load_lab_sessions()


def get_active_lab_session(lab_id: str | None = None) -> dict | None:
    """Return a lab session whose time window contains UTC now, or None."""
    now = datetime.now(timezone.utc)
    for lab in LAB_SESSIONS:
        if lab_id and lab["lab_id"] != lab_id:
            continue
        start = datetime.fromisoformat(lab["start_time"])
        end = datetime.fromisoformat(lab["end_time"])
        if start <= now <= end:
            return lab
    return None


def is_lab_accepting_logins(lab_id: str | None = None) -> tuple[bool, dict | None, str]:
    """Check if there is an active lab session accepting new logins.
    Returns (active, lab_dict_or_none, message)."""
    lab = get_active_lab_session(lab_id)
    if lab:
        return True, lab, "Session active"
    return False, None, "No active session. Please wait for your facilitator."


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
    consented: bool
    lab_id: str | None = None

class ChatRequest(BaseModel):
    session_code: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    turn_number: int

class FinishRequest(BaseModel):
    session_code: str

class SurveyRequest(BaseModel):
    session_code: str
    responses: dict


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

@app.get("/api/session-status")
def session_status(lab: str | None = Query(None)):
    """Check whether a lab session is currently active (server clock)."""
    active, lab_data, message = is_lab_accepting_logins(lab)
    return {
        "active": active,
        "lab_id": lab_data["lab_id"] if lab_data else None,
        "message": message,
    }


@app.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest):
    student_number = req.student_number.strip()
    consented = req.consented

    # Non-consented sessions are treated like test sessions — no data linked
    is_test = not consented or student_number.upper() == TEST_STUDENT

    if consented and not student_number:
        raise HTTPException(400, "Student number is required when consenting")

    # Lab session gate — TEST000 bypasses
    lab_id = None
    if not (student_number.upper() == TEST_STUDENT):
        active, lab_data, msg = is_lab_accepting_logins()
        if not active:
            raise HTTPException(403, msg)
        lab_id = lab_data["lab_id"]

    # Check if this student already has a session (skip for test/non-consented)
    if not is_test:
        existing = db.get_session_code_for_student(student_number)
        if existing:
            session = db.get_session(existing)
            return LoginResponse(
                session_code=existing,
                condition=session["condition"],
                consented=consented,
                lab_id=session.get("lab_id"),
            )

    session_code = generate_session_code()
    condition = req.condition if req.condition in ("nudge", "control") else assign_condition()

    db.create_session(session_code, condition, is_test, lab_id=lab_id)

    if not is_test:
        db.create_linkage(student_number, session_code)

    if not consented:
        label = "NO-CONSENT session"
    elif is_test:
        label = "TEST session"
    else:
        label = "Session"
    db.log_turn(session_code, "system", f"{label} started. Condition: {condition}", 0)

    return LoginResponse(session_code=session_code, condition=condition, consented=consented, lab_id=lab_id)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session = db.get_session(req.session_code)
    if not session:
        raise HTTPException(404, "Session not found")

    if session.get("chat_locked"):
        raise HTTPException(403, "This session has been finished. No further messages accepted.")

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
    ai_response = call_ai(conversation, get_system_prompt())

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
    return {
        "messages": messages,
        "turn_count": turn_count,
        "chat_locked": bool(session.get("chat_locked")),
        "survey_completed": bool(session.get("survey_completed")),
    }


@app.get("/api/export/{session_code}")
def export_session(session_code: str):
    transcript = db.get_full_transcript(session_code)
    if not transcript:
        raise HTTPException(404, "Session log not found")
    return transcript


# ---------------------------------------------------------------------------
# Finish & Survey
# ---------------------------------------------------------------------------

@app.post("/api/finish")
def finish_session(req: FinishRequest):
    session = db.get_session(req.session_code)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.get("chat_locked"):
        return {"locked": True}  # idempotent
    db.lock_chat(req.session_code)
    db.log_turn(req.session_code, "system", "Student clicked Finish Task", 0)
    return {"locked": True}


REQUIRED_SURVEY_FIELDS = [
    "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q8a",
    "q9", "q10", "q11", "q12", "q13",
]


@app.post("/api/survey")
def submit_survey(req: SurveyRequest):
    session = db.get_session(req.session_code)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.get("survey_completed"):
        return {"submitted": True}  # idempotent

    # Validate required fields
    missing = [f for f in REQUIRED_SURVEY_FIELDS if not req.responses.get(f)]
    if missing:
        raise HTTPException(400, f"Missing required fields: {', '.join(missing)}")

    db.save_survey(req.session_code, session.get("lab_id"), req.responses)
    db.log_turn(req.session_code, "system", "Exit survey submitted", 0)
    return {"submitted": True}


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
