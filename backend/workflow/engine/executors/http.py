"""
AutoFlow AI X — HTTP Executor
================================
Makes generic outbound HTTP requests. Used for webhooks and custom API calls.
"""

import logging
from typing import Any

import httpx

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds


class HttpRequestExecutor(BaseExecutor):
    """
    Makes an outbound HTTP request.

    Required params:
        url    : Target URL
        method : HTTP method (GET, POST, PUT, PATCH, DELETE)

    Optional params:
        headers : dict of request headers
        body    : request body (dict → JSON, string → raw)
        params  : URL query parameters
        timeout : request timeout in seconds (default 30)
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        url = resolved_params.get("url", "")
        method = resolved_params.get("method", "POST").upper()
        headers = resolved_params.get("headers", {})
        body = resolved_params.get("body")
        query_params = resolved_params.get("params", {})
        timeout = int(resolved_params.get("timeout", DEFAULT_TIMEOUT))

        if not url:
            return ExecutorResult.fail("'url' is required for http_request.")

        logger.info(f"[HTTP] {method} {url}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                kwargs: dict[str, Any] = {
                    "url": url,
                    "headers": headers,
                    "params": query_params,
                }
                if body is not None:
                    if isinstance(body, dict):
                        kwargs["json"] = body
                    else:
                        kwargs["content"] = str(body)

                response = await client.request(method, **kwargs)
                response.raise_for_status()

                # Try to parse JSON response
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text

                logger.info(f"[HTTP] {method} {url} → {response.status_code}")

                return ExecutorResult.ok(
                    output={
                        "status_code": response.status_code,
                        "response": response_data,
                        "headers": dict(response.headers),
                        "url": url,
                    }
                )

            except httpx.HTTPStatusError as e:
                msg = f"HTTP {e.response.status_code} from {url}: {e.response.text[:300]}"
                logger.warning(f"[HTTP] {msg}")
                return ExecutorResult.fail(msg, output={"status_code": e.response.status_code})

            except httpx.RequestError as e:
                msg = f"Request error for {url}: {e}"
                logger.error(f"[HTTP] {msg}")
                return ExecutorResult.fail(msg)
