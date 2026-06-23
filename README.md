# keep-asking

Chat interface for the conversational nudge study (HREC 83897). Students complete a
short, course-relevant task with an AI assistant; in the treatment arm a one-line
nudge is appended below every AI reply. **Anonymous by design — no name, email, or
student number is collected.**

## Architecture

```
Browser (React)  -->  FastAPI backend  -->  Anthropic API
                                       |
                                       +--> SQLite (sessions, turns, survey_responses)
```

**Key design decisions:**

- **Anonymous:** no name, email, or student number is collected. Each session is a
  random 8-character code; optional equity indicators are stored against that code only.
- API key lives on the server only (never exposed to the browser).
- System prompt instructs the model to answer directly without engagement hooks.
- The nudge is appended **server-side** after the AI response; the model never sees it
  (it is not added to the conversation history).
- Full transcript logging: every turn stores the student message, the raw AI response,
  and what the student saw (raw + nudge).
- Access is gated by a **lab-session time window** (server clock); a **test token**
  bypasses the window for facilitator/co-investigator testing only.

## Access & conditions

Routes (React Router):

- `/session` — random condition assignment (what students use)
- `/session/a` — force **nudge** (treatment) — facilitator/test override
- `/session/b` — force **control** (silent) — facilitator/test override

Logins are accepted only during a configured lab-session window
(`backend/lab_sessions.json`, server clock, UTC). Outside a window students see a
"no active session" screen. For testing outside a window, append
`?token=<TEST_TOKEN>` (set on the server). The token is for facilitators /
co-investigators only.

Sessions started via the token or in demo mode, and any non-consenting sessions,
are flagged `is_test` and excluded from analysis.

**Demo mode (optional).** With `DEMO_ENABLED=true`, append `?demo=1` to share a
token-free, throwaway session (e.g. `/session/a?demo=1` for nudge, `/session/b?demo=1`
for control). Demo sessions write **nothing** to the database, are pinned to
`DEMO_MODEL` (a cheap model), and are capped at `DEMO_TURN_CAP` turns. Leave it
**off** during data collection — it shares the API key/quota — and set a spend limit
on the API account while it is on.

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."        # or set in backend/.env
uvicorn main:app --reload --port 8000
```

Config (env vars; see `.env.example`): `ANTHROPIC_MODEL` (default Haiku for
prototyping), `TEST_TOKEN`, `CONFIG_DIR` (where `lab_sessions.json` / `nudge_config.json`
/ `prompts.json` live in Docker), `DATA_DIR` (SQLite location).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173/session in your browser.

## How It Works

1. The student opens an anonymous session link (optionally `/session/a` or `/session/b`).
   During an active lab window the consent screen appears, with the Participant
   Information Sheet (HREC 83897) and optional equity indicators embedded.
2. On a consent choice, the backend creates a session with a random code and a
   condition (random, or forced by the route).
3. The student chats with the AI; all messages go through the backend.
4. **Nudge** arm: the backend appends the nudge below every AI reply (a visually
   distinct box). **Control** arm: the AI reply is passed through unchanged.
5. On **Finish Task** the chat locks and (for consenting students) the in-app exit
   survey is shown.
6. Every turn is logged to SQLite with timestamps.

## System Prompt

The system prompt suppresses the model's default behaviour of appending follow-up
suggestions:

> "Do NOT end your response with follow-up questions. Do NOT offer to elaborate.
> Simply answer what was asked, then stop."

This matters because frontier models are trained to keep users engaged, which would
contaminate both conditions (control students would get pseudo-nudges from the model
itself). System prompt and nudge pool are configurable via `prompts.json` and
`nudge_config.json`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/version` | GET | Build stamp (short commit SHA + build time) of the running image |
| `/api/session-status` | GET | Is a lab session active? (a valid `token` bypasses the time check) |
| `/api/login` | POST | Start a session; returns a random session code + condition |
| `/api/chat` | POST | Send a message, get the AI reply (with nudge for the nudge arm) |
| `/api/finish` | POST | Lock the chat (student clicked Finish Task) |
| `/api/survey` | POST | Submit the in-app exit survey |
| `/api/sessions` | GET | List sessions (admin) |
| `/api/history/{code}` | GET | Display history for a session (restore chat) |
| `/api/export/{code}` | GET | Export the full transcript for a session |

## Data (SQLite, `data/keep-asking.db`)

- **`sessions`** — one row per login: `session_code`, `condition`, `is_test`,
  `lab_id`, optional equity indicators, timestamps, and `chat_locked` /
  `survey_completed` flags.
- **`turns`** — every message, three rows per turn: `user` (what the student said),
  `assistant_raw` (what the model returned), `assistant_display` (what the student
  saw, including the nudge for the nudge arm).
- **`survey_responses`** — one row per completed exit survey.

Sessions are keyed only by a random code; no name, email, or student number is
collected or written.

## Versioning

The GitHub Actions build injects the short commit SHA and build time into the image
(`build.yml` → `Dockerfile` build args). They surface two ways, so you can confirm
which build the VPS is running:

- a small **version badge** in the bottom-right of the UI (`v<sha>`), and
- **`GET /api/version`** → `{"version": "<sha>", "built": "<UTC time>"}`.

Local/dev builds with no build arg show `dev build`.
