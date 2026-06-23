#!/usr/bin/env python3
"""
Verification of the privacy invariant for keep-asking:

    A TEST session (valid token) and a NON-CONSENTING session must write
    NOTHING to the database — no turns, no survey, no equity indicators.
    Only a real, consenting session is recorded.

It exercises the actual login/chat/finish/survey endpoint logic with the model
call stubbed out (no API key or network needed). Self-contained — no pytest/httpx.

Usage:
    cd backend
    source venv/bin/activate          # the app's own deps must be importable
    python verify_privacy_invariant.py

Exit code 0 = all checks pass; 1 = a check failed.
"""
import os
import sys
import tempfile

# Env must be set before importing main (read at module import time).
os.environ["TEST_TOKEN"] = "verify-secret-token"
os.environ["DEMO_ENABLED"] = "1"
os.environ.setdefault("ANTHROPIC_API_KEY", "unused-stub")
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="keepasking-verify-")

import main  # noqa: E402
import db     # noqa: E402

TOKEN = os.environ["TEST_TOKEN"]
db.init_db(main.DATA_DIR)

# Stub the model call so no network / API key is needed; record the model used.
_calls = []


def _stub_call_ai(messages, system, model=None):
    _calls.append(model)
    return "Canned reply for verification."


main.call_ai = _stub_call_ai

_failures = []


def check(label, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        _failures.append(label)


def transcript(code):
    return db.get_full_transcript(code)


def run_session(*, consented, token=None, condition="nudge", equity=None):
    """Drive a full session: login -> chat -> finish -> survey. Returns the code."""
    body = {"condition": condition, "consented": consented, "token": token}
    if equity:
        body.update(equity)
    code = main.login(main.LoginRequest(**body)).session_code
    main.chat(main.ChatRequest(session_code=code, message="Please help with the task."))
    main.finish_session(main.FinishRequest(session_code=code))
    try:
        main.submit_survey(main.SurveyRequest(
            session_code=code,
            responses={f: "x" for f in main.REQUIRED_SURVEY_FIELDS},
        ))
    except Exception:
        pass
    return code


# --- Scenario 1: token (test) session writes nothing, even if "consented" ---
print("\n[1] Token (test) session — even when 'consented' — writes nothing:")
code = run_session(consented=True, token=TOKEN,
                   equity={"first_in_family": "No", "low_ses": "Yes"})
s = db.get_session(code)
check("flagged is_test", s["is_test"] == 1)
check("no rows in turns", transcript(code) == [])
check("survey not recorded", s["survey_completed"] == 0)
check("equity indicators not stored", s["first_in_family"] is None and s["low_ses"] is None)

# --- Scenario 2: decline (during an active lab window) writes nothing ---
print("\n[2] Non-consenting session — during an active lab window — writes nothing:")
_orig_lab = main.is_lab_accepting_logins
main.is_lab_accepting_logins = lambda lab_id=None: (True, {"lab_id": "VERIFY-LAB"}, "active")
try:
    code = run_session(consented=False, condition="control")
    s = db.get_session(code)
    check("flagged is_test", s["is_test"] == 1)
    check("no rows in turns", transcript(code) == [])

    # --- Scenario 3: real consenting session IS recorded (positive control) ---
    print("\n[3] Real consenting session — during a lab window — IS recorded:")
    code = run_session(consented=True, condition="nudge",
                       equity={"first_in_family": "Yes", "low_ses": "No"})
    s = db.get_session(code)
    roles = {r["role"] for r in transcript(code)}
    check("not flagged is_test", s["is_test"] == 0)
    check("user turn logged", "user" in roles)
    check("assistant_raw logged", "assistant_raw" in roles)
    check("assistant_display logged", "assistant_display" in roles)
    check("equity indicators stored", s["first_in_family"] == "Yes" and s["low_ses"] == "No")
finally:
    main.is_lab_accepting_logins = _orig_lab

# --- Scenario 4: public demo session — token-free, writes nothing, Haiku, capped ---
print("\n[4] Demo session (DEMO_ENABLED) — token-free — writes nothing, Haiku-pinned, capped:")
# Lab is inactive at test time, proving demo bypasses the time gate without a token.
code = main.login(main.LoginRequest(condition="nudge", consented=True, demo=True)).session_code
s = db.get_session(code)
check("flagged is_test", s["is_test"] == 1)
check("flagged is_demo", s["is_demo"] == 1)
_calls.clear()
for i in range(main.DEMO_TURN_CAP):
    main.chat(main.ChatRequest(session_code=code, message=f"demo message {i + 1}"))
check(f"{main.DEMO_TURN_CAP} turns made {main.DEMO_TURN_CAP} AI calls", len(_calls) == main.DEMO_TURN_CAP)
check("demo pinned to the cheap model", all(m == main.DEMO_MODEL for m in _calls))
before = len(_calls)
capped_reply = main.chat(main.ChatRequest(session_code=code, message="one too many")).reply
check("turn over the cap makes no AI call", len(_calls) == before)
check("cap message shown", "demo limit" in capped_reply.lower())
check("demo wrote nothing to turns", transcript(code) == [])

print()
if _failures:
    print(f"FAILED ({len(_failures)} check(s)): {_failures}")
    sys.exit(1)
print("ALL CHECKS PASSED — test/decline sessions write nothing; real sessions are recorded.")
sys.exit(0)
