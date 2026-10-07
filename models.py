"""Step 1: The predefined schema the LLM must follow."""

from pydantic import BaseModel, Field


class MeetingDetails(BaseModel):
    """Structured output for a meeting request.

    This schema is the contract between the LLM and our application.
    The LLM must fill every field, and Pydantic validates the result.
    Fields that the user did not mention stay null instead of being invented.
    """

    title: str = Field(
        description="Short meeting title. Generate a simple one if the user did not provide it."
    )
    attendee: str | None = Field(
        default=None,
        description="Name of the attendee. null if the user did not mention one. Never invent it.",
    )
    date: str | None = Field(
        default=None,
        description="Meeting date in YYYY-MM-DD format. null if the user did not mention a date. Never invent it.",
    )
    time: str | None = Field(
        default=None,
        description="Meeting time in 24-hour HH:MM format. null if the user did not mention a time. Never invent it.",
    )
    duration_in_minutes: int = Field(
        default=30,
        description="Meeting duration in minutes. Use 30 if the user did not provide one.",
    )
