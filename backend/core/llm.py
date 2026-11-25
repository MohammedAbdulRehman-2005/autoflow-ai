"""
AutoFlow AI X — Resilient LLM Client & Model Resolution
========================================================
Handles Groq model deprecation/rotation (e.g. August 2026 EOL of
`llama-3.3-70b-versatile` and `llama-3.1-8b-instant`) with:
  1. Automatic remapping of deprecated model IDs to current production models
     (`openai/gpt-oss-120b`).
  2. Multi-model fallback chain (`openai/gpt-oss-120b` -> `qwen/qwen3.8-27b` ->
     `openai/gpt-oss-20b`).
  3. Dynamic runtime model discovery via `client.models.list()` if catalog IDs
     shift on the active Groq account.
  4. Automatic fallback when `response_format={"type": "json_object"}` is not
     supported by a specific reasoning model.
"""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from groq import AsyncGroq, Groq

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

DEPRECATED_GROQ_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "gemma-7b-it",
}

GROQ_FALLBACK_CHAIN = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

_NON_CHAT_KEYWORDS = (
    "whisper",
    "tts",
    "guard",
    "playai",
    "embed",
    "orpheus",
    "distil-whisper",
)


@dataclass
class _FallbackMessage:
    content: str


@dataclass
class _FallbackChoice:
    message: _FallbackMessage


@dataclass
class _FallbackUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class _FallbackCompletionResponse:
    choices: list[_FallbackChoice]
    usage: _FallbackUsage
    model: str


def resolve_groq_model(requested_model: Optional[str] = None) -> str:
    """
    Resolve a requested model name into an active Groq production model.
    Automatically upgrades deprecated model IDs (such as `llama-3.3-70b-versatile`)
    to the configured primary production model (`openai/gpt-oss-120b`).
    """
    settings = get_settings()
    configured_default = getattr(settings, "GROQ_MODEL", DEFAULT_GROQ_MODEL) or DEFAULT_GROQ_MODEL
    if configured_default in DEPRECATED_GROQ_MODELS:
        configured_default = DEFAULT_GROQ_MODEL

    if not requested_model or requested_model in DEPRECATED_GROQ_MODELS:
        return configured_default

    return requested_model


def _build_candidate_models(requested_model: Optional[str] = None) -> list[str]:
    primary = resolve_groq_model(requested_model)
    candidates = [primary]
    for fallback in GROQ_FALLBACK_CHAIN:
        if fallback not in candidates:
            candidates.append(fallback)
    if requested_model and requested_model not in candidates:
        candidates.append(requested_model)
    return candidates


def _is_model_unavailable_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "model_not_found",
            "does not exist",
            "do not have access",
            "decommissioned",
            "model_decommissioned",
            "not found",
            "404",
            "413",
            "429",
            "rate_limit_exceeded",
            "request too large",
            "tokens per minute",
        )
    )


def _is_json_mode_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "response_format",
            "json_object",
            "json_validate_failed",
            "failed to generate json",
        )
    )


def _discover_account_chat_models(client: Groq) -> list[str]:
    """Query the live Groq `/models` endpoint to find accessible chat models."""
    try:
        models_resp = client.models.list()
        discovered: list[str] = []
        for item in getattr(models_resp, "data", []) or []:
            model_id = getattr(item, "id", "")
            if not model_id:
                continue
            lower_id = model_id.lower()
            if any(k in lower_id for k in _NON_CHAT_KEYWORDS):
                continue
            discovered.append(model_id)
        return discovered
    except Exception as exc:
        logger.warning("[Groq] Could not list dynamic models from Groq API: %s", exc)
        return []


def _try_gemini_fallback(messages: list[dict[str, Any]]) -> Optional[_FallbackCompletionResponse]:
    """Last-resort fallback to Google Gemini if GEMINI_API_KEY is configured."""
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai

        gclient = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt_parts = [
            f"[{m.get('role', 'user').upper()}]\n{m.get('content', '')}"
            for m in messages
        ]
        combined_prompt = "\n\n".join(prompt_parts)
        resp = gclient.models.generate_content(
            model="gemini-2.5-flash",
            contents=combined_prompt,
        )
        text = (resp.text or "").strip()
        if text:
            logger.info("[LLM] Completed request via Gemini 2.5 Flash fallback.")
            return _FallbackCompletionResponse(
                choices=[_FallbackChoice(message=_FallbackMessage(content=text))],
                usage=_FallbackUsage(),
                model="gemini-2.5-flash",
            )
    except Exception as exc:
        logger.warning("[LLM] Gemini fallback also failed: %s", exc)
    return None


def groq_chat_completion(
    client: Groq,
    messages: list[dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    response_format: Optional[dict[str, Any]] = None,
) -> Any:
    """
    Execute a synchronous Groq chat completion with automatic model fallback,
    dynamic account model discovery, and JSON-mode compatibility retry.
    """
    candidates = _build_candidate_models(model)
    last_error: Optional[Exception] = None
    tried: set[str] = set()

    def _attempt_model(candidate_model: str) -> Any:
        kwargs: dict[str, Any] = {
            "model": candidate_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            if response_format is not None and _is_json_mode_error(exc):
                logger.warning(
                    "[Groq] Model '%s' rejected response_format (%s); retrying without response_format.",
                    candidate_model,
                    exc,
                )
                kwargs.pop("response_format", None)
                return client.chat.completions.create(**kwargs)
            raise

    for candidate in candidates:
        tried.add(candidate)
        try:
            return _attempt_model(candidate)
        except Exception as exc:
            last_error = exc
            if _is_model_unavailable_error(exc):
                logger.warning(
                    "[Groq] Model '%s' unavailable (%s). Trying next production model...",
                    candidate,
                    exc,
                )
                continue
            raise

    # All static candidates were unavailable — discover accessible models dynamically
    for dynamic_model in _discover_account_chat_models(client):
        if dynamic_model in tried:
            continue
        tried.add(dynamic_model)
        try:
            logger.info("[Groq] Attempting dynamically discovered model '%s'", dynamic_model)
            return _attempt_model(dynamic_model)
        except Exception as exc:
            last_error = exc
            if _is_model_unavailable_error(exc):
                continue
            raise

    # Optional Gemini backup if configured
    gemini_resp = _try_gemini_fallback(messages)
    if gemini_resp is not None:
        return gemini_resp

    if last_error is not None:
        raise last_error
    raise RuntimeError("No available Groq models could complete the request.")


async def async_groq_chat_completion(
    client: AsyncGroq,
    messages: list[dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> Any:
    """Execute an async Groq chat completion with automatic model fallback."""
    candidates = _build_candidate_models(model)
    last_error: Optional[Exception] = None

    for candidate in candidates:
        try:
            return await client.chat.completions.create(
                model=candidate,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            last_error = exc
            if _is_model_unavailable_error(exc):
                logger.warning(
                    "[Groq Async] Model '%s' unavailable (%s). Trying next production model...",
                    candidate,
                    exc,
                )
                continue
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("No available Groq models could complete the async request.")
