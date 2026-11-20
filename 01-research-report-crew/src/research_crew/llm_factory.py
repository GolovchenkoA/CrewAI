"""Create LLM objects for CrewAI; switch Claude / local Ollama with env vars.

LLM_PROVIDER=claude|local selects the default provider. Each call returns a NEW
LLM object, because token usage is counted per LLM instance (one per agent).
"""

import os

from crewai import LLM


def make_llm(provider: str | None = None, temperature: float = 0.2) -> LLM:
    provider = (provider or os.getenv("LLM_PROVIDER") or "local").strip().lower()
    if provider == "claude":
        return LLM(
            model=os.getenv("CLAUDE_MODEL", "anthropic/claude-sonnet-5-5")
        )
    if provider == "local":
        return LLM(
            model=os.getenv("LOCAL_MODEL", "ollama/qwen3.5:9b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
            timeout=float(os.getenv("LLM_TIMEOUT", "600")),
        )
    raise ValueError(f"LLM_PROVIDER must be 'claude' or 'local', got {provider!r}")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
