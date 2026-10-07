# Meeting Structured Output Demo

A small, beginner-friendly FastAPI project that demonstrates **Structured Output from an LLM**,
using **Groq** through its OpenAI-compatible API.

```
Natural Language
      ↓
     LLM
      ↓
Pydantic Schema
      ↓
Structured Output
      ↓
     JSON
```

You send a sentence like:

```
Schedule a meeting with Ravi tomorrow at 4 PM
```

And you get back validated JSON like:

```json
{
  "title": "Meeting with Ravi",
  "attendee": "Ravi",
  "date": "2026-10-02",
  "time": "16:00",
  "duration_in_minutes": 30
}
```

The project does **not** actually schedule anything. It only demonstrates the pipeline:

```
User
 ↓
FastAPI
 ↓
llm_service.py
 ↓
Groq
 ↓
Pydantic MeetingDetails
 ↓
Structured JSON
 ↓
FastAPI response
```

---

## 1. What this project demonstrates

LLMs produce free text. Free text is unreliable for software: the model might reply
`Sure! The meeting is tomorrow at 4pm 😊` instead of JSON, and your code cannot use that.

**Structured output** solves this: you give the LLM a fixed schema, and the API *guarantees*
the response matches that schema — every time.

## 2. What structured output means

Instead of asking the model "please return JSON" and hoping for the best, you hand the
provider a machine-readable schema. The provider constrains the model's decoding so the
output is valid against that schema by construction. In this project that happens in
`llm_service.py` via:

```python
client.chat.completions.parse(..., response_format=MeetingDetails)
```

The OpenAI SDK converts `MeetingDetails` into a JSON schema and sends it to Groq's
OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`) with `strict: true`, then
hands back a ready-made, Pydantic-validated object.

**Which Groq model?** The default is `openai/gpt-oss-120b`, one of the Groq models that
supports *strict* structured outputs (constrained decoding = guaranteed schema match).
Other strict-capable options: `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`. Override with the
`GROQ_MODEL` environment variable if you like.

## 3. Why we need a schema

- The shape of the data is decided by **us**, not by the model.
- Downstream code can rely on `meeting.date` always existing with the right type.
- The model has no room to add extra fields, forget fields, or return prose.

## 4. What Pydantic is doing

`MeetingDetails` in `models.py` is a Pydantic model. Pydantic:

1. Defines the schema (field names and types).
2. Validates whatever the LLM returns against that schema.
3. Turns the result into a normal Python object you can use (`meeting.time`).

If the output does not match the schema, Pydantic raises a validation error instead of
letting bad data flow through your app.

## 5. How the LLM is involved

`extract_meeting_details(message)` in `llm_service.py` sends:

- a **system prompt** explaining the job and the rules (convert "tomorrow" to a real date,
  24-hour time, default duration 30, never invent attendee/date/time), including today's
  date so relative words can be interpreted;
- the **user message**;
- the **MeetingDetails schema** as `response_format`.

The request goes to `https://api.groq.com/openai/v1` using the OpenAI Python client with
`base_url` pointed at Groq — the same SDK, just a different provider. The LLM does the
*understanding*; the schema does the *guaranteeing*.

## 6. Missing information

Test case 3 shows the important behaviour. For:

```
Schedule a meeting with Rahul
```

there is no date or time, and the model is explicitly told **not to invent them**. The
response looks like:

```json
{
  "title": "Meeting with Rahul",
  "attendee": "Rahul",
  "date": null,
  "time": null,
  "duration_in_minutes": 30
}
```

`null` is a clear, honest signal that the information was not provided — your code can
detect it and ask the user, instead of silently trusting a fabricated date.

---

## Project structure

```
structured-output-demo/
│
├── main.py            # FastAPI app + POST /api/schedule
├── models.py          # Pydantic schema (MeetingDetails)
├── llm_service.py     # Calls Groq with structured output
├── requirements.txt   # Dependencies
├── .env               # Your API key (never committed)
├── .gitignore         # Keeps .env and caches out of git
└── README.md
```

## Setup and run (Windows)

Requires Python 3.12+.

```bat
cd structured-output-demo

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

Put your real Groq API key in `.env` (get one at <https://console.groq.com/keys>):

```
GROQ_API_KEY=gsk_...
```

Start the server:

```bat
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> for the interactive API docs.

macOS/Linux equivalent:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Testing with Postman

1. Start the server (`uvicorn main:app --reload`).
2. Create a new **POST** request to `http://127.0.0.1:8000/api/schedule`.
3. In **Body → raw → JSON**, send:

```json
{
  "message": "Schedule a meeting with Ravi tomorrow at 4 PM"
}
```

4. You should get a `200 OK` response like:

```json
{
  "title": "Meeting with Ravi",
  "attendee": "Ravi",
  "date": "2026-10-02",
  "time": "16:00",
  "duration_in_minutes": 30
}
```

("tomorrow" resolves against the server's current date.)

## Test cases

**TEST 1** — `Schedule a meeting with Ravi tomorrow at 4 PM`

| Field | Expected |
|---|---|
| attendee | `Ravi` |
| date | tomorrow's actual date (e.g. `2026-10-02`) |
| time | `16:00` |
| duration | `30` |

**TEST 2** — `Schedule a meeting with Priya today at 10 AM for 60 minutes`

| Field | Expected |
|---|---|
| attendee | `Priya` |
| date | today's actual date |
| time | `10:00` |
| duration | `60` |

**TEST 3** — `Schedule a meeting with Rahul`

| Field | Expected |
|---|---|
| attendee | `Rahul` |
| date | `null` (not invented) |
| time | `null` (not invented) |
| duration | `30` (default) |

## Error responses

| Case | Status | Where handled |
|---|---|---|
| Empty/blank `message` | `400` / `422` | `main.py` + Pydantic `min_length` |
| Missing or placeholder `GROQ_API_KEY` | `503` | `MissingAPIKeyError` in `llm_service.py` |
| LLM API failure (auth, network, rate limit) | `502` | `LLMServiceError` in `llm_service.py` |
| Invalid structured output (model returned nothing usable) | `502` | `llm_service.py` checks `message.parsed` |

## Security notes

- Never hardcode or print your API key.
- `.env` is listed in `.gitignore`, so it is never committed.
- Only the placeholder `your_groq_api_key` lives in the committed `.env`.
