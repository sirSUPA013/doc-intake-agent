"""Structured-output contract for the agent.

This Pydantic model is the JSON schema every extraction must satisfy. It is the
Python equivalent of the Zod schemas I use on the TypeScript side — define the
shape once, and any data that does not match is rejected with a clear error
instead of silently flowing downstream.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ExtractedDoc(BaseModel):
    """The fields we pull out of a raw document."""

    doc_type: str = Field(..., min_length=1, description="e.g. invoice, letter, report")
    title: str = Field(..., min_length=1)
    date: str = Field(..., description="ISO-8601 date, YYYY-MM-DD")
    entities: list[str] = Field(default_factory=list)
    total_amount: float | None = Field(default=None, ge=0)

    @field_validator("total_amount", mode="before")
    @classmethod
    def _coerce_amount(cls, v: object) -> object:
        # Guard against a known model-output failure mode: models often return
        # money as a string like "$1,234.56", and a bare float() raises on the
        # "$" and commas. Strip the formatting before coercion.
        if isinstance(v, str):
            cleaned = v.strip().replace("$", "").replace(",", "")
            return None if cleaned == "" else float(cleaned)
        return v
