"""
app/services/search_service.py — natural language admin search.

parse_search_query() converts a plain-English admin query into a
structured filter (category, status, days_back) using an LLM, then
strictly validates every field against a whitelist before it's used
anywhere near a database query. The raw LLM output is never trusted
directly — this is what keeps the feature safe.

build_query() (added separately) turns the validated filter into an
actual MongoDB query dict.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {"plumbing", "electrical", "security", "other"}
ALLOWED_STATUSES = {"open", "in_progress", "resolved"}

SYSTEM_PROMPT = (
    "You convert a housing society admin's natural language search request "
    "into a JSON object. Respond with ONLY a JSON object (no markdown, no "
    "prose) with exactly these keys:\n"
    '"category": one of "plumbing", "electrical", "security", "other", or '
    "null if no category is mentioned or implied.\n"
    '"status": one of "open", "in_progress", "resolved", or null if no '
    "status is mentioned or implied.\n"
    '"days_back": an integer number of days to look back if a time period '
    "is mentioned (e.g. \"last week\" -> 7, \"last 3 days\" -> 3, "
    '"this month" -> 30), or null if no time period is mentioned.\n'
    "Only use these exact values — never invent categories or statuses "
    "outside this list."
)

_DEFAULT_RESULT = {"category": None, "status": None, "days_back": None}


async def parse_search_query(query: str) -> dict:
    """Convert a natural language query into a validated filter dict.
    Never raises — returns an all-null filter on any failure.
    """
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — skipping NL search parsing.")
        return dict(_DEFAULT_RESULT)

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.groq_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

        # --- Strict validation. The raw LLM output is never trusted as-is. ---
        category = parsed.get("category")
        if category not in ALLOWED_CATEGORIES:
            category = None

        status_value = parsed.get("status")
        if status_value not in ALLOWED_STATUSES:
            status_value = None

        days_back = parsed.get("days_back")
        if not isinstance(days_back, int) or days_back <= 0:
            days_back = None

        return {"category": category, "status": status_value, "days_back": days_back}

    except Exception as exc:  # noqa: BLE001 — must never raise out of this function
        logger.exception("NL search parsing failed: %s", exc)
        return dict(_DEFAULT_RESULT)


def build_query(parsed: dict) -> dict:
    """Turn a validated filter dict into a MongoDB query dict."""
    query: dict = {}
    if parsed.get("category"):
        query["category"] = parsed["category"]
    if parsed.get("status"):
        query["status"] = parsed["status"]
    if parsed.get("days_back"):
        cutoff = datetime.now(timezone.utc) - timedelta(days=parsed["days_back"])
        query["created_at"] = {"$gte": cutoff}
    return query