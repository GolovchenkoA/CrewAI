"""Create LLM objects; switch Claude / local Ollama with LLM_PROVIDER=claude|local.

Each call returns a NEW LLM object (token usage is counted per LLM instance).
"""

import os

from crewai import LLM


def make_llm(
    provider: str | None = None, temperature: float = 0.2, vision: bool = False
) -> LLM:
    """The agent's text model, or with vision=True the model that looks at images."""
    provider = (provider or os.getenv("LLM_PROVIDER") or "local").strip().lower()
    if provider == "claude":
        return LLM(
            model=os.getenv("CLAUDE_MODEL", "anthropic/claude-sonnet-5-5"),
            # explicit cap: crewai's default (128000 for Sonnet 5) makes the anthropic SDK refuse
            # non-streaming calls ("Streaming is required for operations that may take longer than 10 minutes")
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "8192")),
        )
    if provider == "local":
        return LLM(
            model=os.getenv(
                "VISION_MODEL" if vision else "LOCAL_MODEL",
                "ollama/qwen2.5vl:7b" if vision else "ollama/qwen3:4b",
            ),
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
