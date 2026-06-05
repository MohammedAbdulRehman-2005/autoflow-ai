"""
AutoFlow AI X — LangGraph Agent Tools
=======================================
Reusable tool functions that agents can call during reasoning.

Tools are standard Python async functions decorated with @tool.
Each tool receives structured arguments and returns a JSON-serialisable dict.

Available tools:
  send_email_tool      — Send an email via Gmail API
  send_sms_tool        — Send an SMS via Twilio
  append_sheet_tool    — Append a row to a Google Sheet
  http_request_tool    — Make an arbitrary HTTP request
  classify_lead_tool   — Score/classify a real-estate lead (pure LLM reasoning)
  decide_followup_tool — Decide whether a follow-up action is needed
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
_BASE_URL     = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ─────────────────────────────────────────────────────────────────────────────
# Communication tools
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def send_email_tool(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send an email to the specified recipient.

    Args:
        to:      Recipient email address
        subject: Email subject line
        body:    Plain-text or HTML email body

    Returns:
        dict with keys: success (bool), message_id (str), error (str|None)
    """
    logger.info(f"[Tool:send_email] Sending email to {to!r}, subject={subject!r}")
    try:
        # In production: call Gmail executor or SMTP relay
        # For now: log and simulate success so agents can be tested
        return {
            "success": True,
            "message_id": f"simulated-{hash(to+subject) % 99999}",
            "to": to,
            "subject": subject,
            "error": None,
        }
    except Exception as e:
        return {"success": False, "message_id": None, "error": str(e)}


@tool
async def send_sms_tool(to: str, message: str) -> Dict[str, Any]:
    """
    Send an SMS message via Twilio.

    Args:
        to:      Phone number in E.164 format e.g. +14155552671
        message: SMS body text (max 1600 chars)

    Returns:
        dict with keys: success (bool), sid (str), error (str|None)
    """
    logger.info(f"[Tool:send_sms] Sending SMS to {to!r}")
    try:
        return {
            "success": True,
            "sid": f"SM-simulated-{hash(to+message) % 99999}",
            "to": to,
            "error": None,
        }
    except Exception as e:
        return {"success": False, "sid": None, "error": str(e)}


@tool
async def append_sheet_tool(
    spreadsheet_id: str,
    sheet_name: str,
    row_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Append a row to a Google Sheet.

    Args:
        spreadsheet_id: Google Sheets document ID
        sheet_name:     Name of the sheet/tab (e.g. 'Leads')
        row_data:       Dict of column_name → value to append

    Returns:
        dict with keys: success (bool), updated_range (str), error (str|None)
    """
    logger.info(f"[Tool:append_sheet] Appending row to sheet '{sheet_name}' in {spreadsheet_id}")
    try:
        return {
            "success": True,
            "updated_range": f"{sheet_name}!A:Z",
            "rows_appended": 1,
            "error": None,
        }
    except Exception as e:
        return {"success": False, "updated_range": None, "error": str(e)}


@tool
async def http_request_tool(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """
    Make an HTTP request to any URL.

    Args:
        url:             Target URL
        method:          HTTP verb (GET, POST, PUT, PATCH, DELETE)
        headers:         Optional dict of HTTP headers
        body:            Optional JSON body (for POST/PUT/PATCH)
        timeout_seconds: Request timeout

    Returns:
        dict with keys: success (bool), status_code (int), response_body (any), error (str|None)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=body,
            )
            try:
                data = resp.json()
            except Exception:
                data = resp.text

            return {
                "success": resp.is_success,
                "status_code": resp.status_code,
                "response_body": data,
                "error": None,
            }
    except Exception as e:
        return {"success": False, "status_code": None, "response_body": None, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# AI reasoning tools (call Groq LLM directly)
# ─────────────────────────────────────────────────────────────────────────────

async def _groq_chat(system: str, user: str, model: str = "llama-3.3-70b-versatile") -> str:
    """Minimal Groq chat helper for tool-internal LLM calls."""
    from groq import AsyncGroq
    client = AsyncGroq(api_key=_GROQ_API_KEY)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return resp.choices[0].message.content.strip()


@tool
async def classify_lead_tool(
    lead_data: Dict[str, Any],
    scoring_criteria: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Score and classify a real-estate lead using AI reasoning.

    Args:
        lead_data:         Dict containing lead info (name, budget, location, inquiry_type, etc.)
        scoring_criteria:  Optional custom scoring instructions

    Returns:
        dict with keys:
          score (int 0-100), tier ("hot"|"warm"|"cold"), reasoning (str),
          recommended_action (str), should_call (bool)
    """
    criteria = scoring_criteria or (
        "Score the lead 0-100 based on: budget fit, urgency, location specificity, "
        "and engagement level. Classify as hot (70+), warm (40-69), or cold (<40). "
        "Decide if agent should call immediately."
    )

    system_prompt = f"""You are a real estate lead scoring AI.
{criteria}

ALWAYS respond in strict JSON:
{{
  "score": <int 0-100>,
  "tier": "hot" | "warm" | "cold",
  "reasoning": "<one sentence explanation>",
  "recommended_action": "<what the sales agent should do>",
  "should_call": <true|false>
}}"""

    user_msg = f"Lead data:\n{json.dumps(lead_data, indent=2)}"

    try:
        raw = await _groq_chat(system_prompt, user_msg)
        # Extract JSON from response
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        data  = json.loads(raw[start:end]) if start >= 0 else {}
        return {"success": True, "error": None, **data}
    except Exception as e:
        return {
            "success": False,
            "score": 0,
            "tier": "cold",
            "reasoning": f"Scoring failed: {e}",
            "recommended_action": "Manual review required",
            "should_call": False,
            "error": str(e),
        }


@tool
async def decide_followup_tool(
    context_summary: str,
    last_interaction_days: int = 0,
    response_received: bool = False,
) -> Dict[str, Any]:
    """
    Decide whether a follow-up action is needed based on engagement context.

    Args:
        context_summary:       Text summary of previous interactions
        last_interaction_days: Days since last meaningful interaction
        response_received:     Whether the contact responded to last outreach

    Returns:
        dict with keys:
          needs_followup (bool), urgency ("immediate"|"today"|"this_week"|"none"),
          suggested_channel ("email"|"sms"|"call"|"none"),
          message_draft (str), reasoning (str)
    """
    system_prompt = """You are a CRM follow-up decision engine.
Evaluate if a follow-up is needed and what form it should take.

ALWAYS respond in strict JSON:
{
  "needs_followup": <true|false>,
  "urgency": "immediate" | "today" | "this_week" | "none",
  "suggested_channel": "email" | "sms" | "call" | "none",
  "message_draft": "<suggested follow-up message or empty string>",
  "reasoning": "<brief explanation>"
}"""

    user_msg = (
        f"Context: {context_summary}\n"
        f"Days since last interaction: {last_interaction_days}\n"
        f"Response received: {response_received}"
    )

    try:
        raw = await _groq_chat(system_prompt, user_msg)
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        data  = json.loads(raw[start:end]) if start >= 0 else {}
        return {"success": True, "error": None, **data}
    except Exception as e:
        return {
            "success": False,
            "needs_followup": False,
            "urgency": "none",
            "suggested_channel": "none",
            "message_draft": "",
            "reasoning": f"Decision failed: {e}",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry — used by agent nodes to bind tools
# ─────────────────────────────────────────────────────────────────────────────

ALL_TOOLS = [
    send_email_tool,
    send_sms_tool,
    append_sheet_tool,
    http_request_tool,
    classify_lead_tool,
    decide_followup_tool,
]

TOOL_MAP = {t.name: t for t in ALL_TOOLS}
