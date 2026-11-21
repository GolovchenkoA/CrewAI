from typing import Literal

from pydantic import BaseModel, Field


class Triage(BaseModel):
    severity: Literal["low", "high"]
    summary: str = Field(description="One sentence")
