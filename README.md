# keep-asking Prototype

Proof of concept chat interface for the conversational nudge study.

## Architecture

```
Browser (React)  -->  FastAPI backend  -->  Frontier model API
                                       |
                                       +--> Transcript logs (JSONL)
                                       +--> Session/condition tracking
                                       +--> Student number linkage table
```

**Key design decisions:**

- API key lives on the server only (never exposed to browser)
- System prompt instructs the model to answer directly without engagement hooks
- Nudge is appended server-side after the AI response, before sending to the student
- The AI model never sees the nudge (it is not in the conversation history)
- Full transcript logging: every turn is logged with timestamps, both the raw AI response and what the student sees
- Student number is stored in a temporary linkage table, separate from research data

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
# Or: export AI_PROVIDER=openai OPENAI_API_KEY="sk-..."

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## How It Works

1. Student enters their student number on the login screen
2. Backend assigns a random session code and randomly assigns nudge or control condition
3. Student chats with the AI. All messages go through the backend.
4. For **nudge** condition: the backend appends the nudge text to every AI response before sending it to the student. The nudge is visually distinct (blue box, italic).
5. For **control** condition: the AI response is passed through unchanged.
6. Every turn is logged to `data/{session_code}.jsonl` with timestamps.

## System Prompt

The system prompt suppresses the model's default behaviour of appending follow-up suggestions:

> "Do NOT end your response with follow-up questions. Do NOT offer to elaborate. Simply answer what was asked, then stop."

This is critical because frontier models are trained to keep users engaged, which would contaminate both conditions (control students would get pseudo-nudges from the model itself).

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login` | POST | Student login, returns session code |
| `/api/chat` | POST | Send message, get AI response |
| `/api/sessions` | GET | List all sessions (admin) |
| `/api/export/{code}` | GET | Export transcript for a session |
| `/api/deidentify` | POST | Destroy the linkage table |

## Log Format

Each turn is logged as a JSONL entry:

```json
{"session_code": "AB12CD34", "turn_number": 1, "role": "user", "content": "...", "timestamp": "2026-05-15T10:30:00", "epoch": 1747308600.0}
{"session_code": "AB12CD34", "turn_number": 1, "role": "assistant_raw", "content": "...", "timestamp": "...", "epoch": ...}
{"session_code": "AB12CD34", "turn_number": 1, "role": "assistant_display", "content": "...(with nudge if applicable)", "timestamp": "...", "epoch": ...}
```

Three entries per turn: what the student said, what the AI actually returned, and what the student saw.
