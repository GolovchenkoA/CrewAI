from typing import Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    statement: str = Field(description="One factual claim about the topic.")
    evidence: str = Field(description="The fact or quote from the research that supports it.")
    source: str = Field(description="URL or note file name the evidence came from.")
    confidence: Literal["high", "medium", "low"]


class Analysis(BaseModel):
    topic: str
    summary: str = Field(description="Three sentences summarising the findings.")
    claims: list[Claim]
    open_questions: list[str] = Field(default_factory=list)
