"""
AutoFlow AI X — AI Agent Executor
=====================================
Calls Groq or OpenAI for LLM operations: generate, classify, extract.
Used in "ai_agent" type nodes.
"""

import logging
from typing import Any

from groq import Groq

from backend.core.config import get_settings
from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)
settings = get_settings()

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.7


class LLMGenerateExecutor(BaseExecutor):
    """
    Generates text using an LLM (Groq).

    Required params:
        user_prompt   : The user prompt (supports template vars)

    Optional params:
        system_prompt : System instructions for the LLM
        model         : Model name (default: llama-3.3-70b-versatile)
        max_tokens    : Max output tokens (default: 1024)
        temperature   : Sampling temperature 0.0–1.0 (default: 0.7)
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        user_prompt = resolved_params.get("user_prompt", "")
        system_prompt = resolved_params.get("system_prompt", "You are a helpful assistant.")
        model = resolved_params.get("model", DEFAULT_MODEL)
        max_tokens = int(resolved_params.get("max_tokens", DEFAULT_MAX_TOKENS))
        temperature = float(resolved_params.get("temperature", DEFAULT_TEMPERATURE))

        if not user_prompt:
            return ExecutorResult.fail("'user_prompt' is required for llm_generate.")

        logger.info(f"[AI] Calling Groq model='{model}' max_tokens={max_tokens}")

        client = Groq(api_key=settings.GROQ_API_KEY)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        generated_text = response.choices[0].message.content
        usage = response.usage

        logger.info(f"[AI] Generated {usage.completion_tokens} tokens")

        return ExecutorResult.ok(
            output={
                "text": generated_text,
                "model": model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
        )


class LLMClassifyExecutor(BaseExecutor):
    """
    Classifies input into one of a set of labels using an LLM.

    Required params:
        text    : Text to classify
        labels  : List of possible classification labels

    Optional params:
        model, system_prompt
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        text = resolved_params.get("text", "")
        labels = resolved_params.get("labels", [])
        model = resolved_params.get("model", DEFAULT_MODEL)

        if not text or not labels:
            return ExecutorResult.fail("'text' and 'labels' are required for llm_classify.")

        labels_str = ", ".join(f'"{l}"' for l in labels)
        system_prompt = (
            f"You are a classification engine. Classify the given text into EXACTLY one "
            f"of these labels: {labels_str}. Respond with ONLY the label, nothing else."
        )

        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=50,
            temperature=0.0,  # Deterministic for classification
        )

        label = response.choices[0].message.content.strip().strip('"')
        confidence = 1.0 if label in labels else 0.0

        return ExecutorResult.ok(
            output={"label": label, "confidence": confidence, "labels": labels}
        )


class LLMExtractExecutor(BaseExecutor):
    """
    Extracts structured fields from unstructured text using an LLM.

    Required params:
        text   : Text to extract from
        fields : List of field names to extract (e.g. ["name", "date", "amount"])

    Returns:
        output: { "name": "...", "date": "...", "amount": "..." }
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        import json

        text = resolved_params.get("text", "")
        fields = resolved_params.get("fields", [])
        model = resolved_params.get("model", DEFAULT_MODEL)

        if not text or not fields:
            return ExecutorResult.fail("'text' and 'fields' are required for llm_extract.")

        fields_str = ", ".join(f'"{f}"' for f in fields)
        system_prompt = (
            f"You are a data extraction engine. Extract the following fields from the text: "
            f"{fields_str}. Return a JSON object with exactly these keys. "
            f"If a field is not found, set its value to null. "
            f"Return ONLY valid JSON, nothing else."
        )

        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=500,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        try:
            extracted = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            extracted = {}

        return ExecutorResult.ok(output=extracted)
