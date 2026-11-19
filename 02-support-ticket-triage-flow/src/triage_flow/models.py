"""Structured outputs of the classifier and sentiment crews."""

from typing import Literal

from pydantic import BaseModel, Field


class Classification(BaseModel):
    category: Literal["billing", "bug", "how-to"]
    confidence: float = Field(
        ge=0.0, le=1.0, description="0.0 = pure guess, 1.0 = certain"
    )
    reasoning: str = Field(description="One sentence explaining the label")


class Sentiment(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    urgency: Literal["low", "medium", "high"]
