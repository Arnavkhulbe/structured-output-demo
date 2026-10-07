"""Step 3: FastAPI app exposing POST /api/schedule."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from llm_service import LLMServiceError, MissingAPIKeyError, extract_meeting_details
from models import MeetingDetails

app = FastAPI(
    title="Meeting Structured Output Demo",
    description="Natural language in, validated JSON out.",
)


class MeetingRequest(BaseModel):
    message: str = Field(
        min_length=1,
        examples=["Schedule a meeting with Ravi tomorrow at 4 PM"],
    )


@app.post("/api/schedule", response_model=MeetingDetails)
def schedule(request: MeetingRequest) -> MeetingDetails:
    """Convert a natural-language meeting request into structured JSON."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="The message must not be empty.")

    try:
        return extract_meeting_details(request.message.strip())
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
