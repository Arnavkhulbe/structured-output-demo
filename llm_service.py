"""Step 2: Sends the message to Groq (OpenAI-compatible API) and returns a validated MeetingDetails."""

import os
from datetime import date

from dotenv import load_dotenv
from openai import APIError, AuthenticationError, OpenAI

from models import MeetingDetails

load_dotenv()

# Groq exposes an OpenAI-compatible API, so the OpenAI client works with just a new base_url.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"  # a Groq model that supports strict structured outputs


class LLMServiceError(Exception):
    """Something went wrong while calling the LLM or reading its output."""


class MissingAPIKeyError(LLMServiceError):
    """GROQ_API_KEY is not set (or still the placeholder)."""


SYSTEM_PROMPT = """You extract meeting information from a user's request.

Today's date is {today}.

Rules:
- Extract the meeting information from the user's request.
- Convert relative dates such as "today" and "tomorrow" into an actual date in YYYY-MM-DD format.
- Convert times into 24-hour format (HH:MM).
- If no duration is provided, use 30 minutes.
- If the title is missing, generate a simple title.
- Do NOT invent the attendee. Use null if no attendee is mentioned.
- Do NOT invent the date. Use null if no date is mentioned.
- Do NOT invent the time. Use null if no time is mentioned.
- Missing information must be null, never guessed.
"""


def extract_meeting_details(message: str) -> MeetingDetails:
    """Turn a natural-language message into a validated MeetingDetails object."""

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key":
        raise MissingAPIKeyError(
            "GROQ_API_KEY is missing. Add your real key to the .env file."
        )

    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    system_prompt = SYSTEM_PROMPT.format(today=date.today().isoformat())
    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

    try:
        # .parse() sends the MeetingDetails schema to Groq as response_format
        # (strict json_schema) and validates the response with Pydantic automatically.
        completion = client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            response_format=MeetingDetails,
        )
    except AuthenticationError as exc:
        raise LLMServiceError("Groq rejected the API key. Check your .env file.") from exc
    except APIError as exc:
        raise LLMServiceError(f"The LLM API call failed ({type(exc).__name__}).") from exc
    except Exception as exc:
        # e.g. truncation or refusal errors raised by the SDK while parsing.
        raise LLMServiceError(
            f"Could not read the LLM output ({type(exc).__name__})."
        ) from exc

    meeting = completion.choices[0].message.parsed
    if meeting is None:
        raise LLMServiceError("The LLM did not return valid structured output.")

    return meeting
