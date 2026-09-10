"""
app/services/ai_service.py — LLM-based complaint triage.

Calls Groq's OpenAI-compatible chat completions endpoint and asks for
strict JSON output: corrected category, urgency, a clean title, and a
one-line reasoning for the urgency call.

This function never raises: on any failure (missing key, network error,
timeout, bad JSON, invalid values) it logs the error and returns a safe
default so complaint creation is never blocked by the AI layer.
"""
from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {"plumbing", "electrical", "security", "other"}
ALLOWED_URGENCY = {"low", "medium", "high"}

SYSTEM_PROMPT = (
    "You are a triage assistant for a housing society complaint tracker. "
    "Given a resident's raw complaint text and the category they selected, "
    "respond with ONLY a JSON object (no markdown, no prose, no code fences) "
    "with exactly these keys:\n"
    '"category": one of "plumbing", "electrical", "security", "other" — '
    "correct the resident's category only if the text clearly indicates a "
    "different one, otherwise keep it as submitted.\n"
    '"urgency": one of "low", "medium", "high" — use "high" for anything '
    "suggesting immediate safety risk such as gas leaks, exposed live wiring, "
    "fire hazards, or a break-in in progress.\n"
    '"title": a short, clean, human-readable summary of the complaint, '
    "under 12 words.\n"
    '"reasoning": one short sentence explaining why that urgency level was '
    "chosen."
)


def _default_result(description: str, submitted_category: str) -> dict:
    category = submitted_category if submitted_category in ALLOWED_CATEGORIES else "other"
    title = (description[:57] + "...") if len(description) > 60 else description
    return {
        "category": category,
        "urgency": "medium",
        "title": title,
        "reasoning": "AI triage unavailable — default values applied.",
    }


async def triage_complaint(description: str, submitted_category: str) -> dict:
    """Classify a complaint via LLM. Never raises — falls back to safe defaults."""
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — skipping AI triage, using defaults.")
        return _default_result(description, submitted_category)

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Submitted category: {submitted_category}\n"
                    f"Complaint text: {description}"
                ),
            },
        ],
        "temperature": 0.2,
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

        category = parsed.get("category", submitted_category)
        urgency = parsed.get("urgency", "medium")
        title = parsed.get("title") or description[:60]
        reasoning = parsed.get("reasoning", "")

        if category not in ALLOWED_CATEGORIES:
            logger.warning("LLM returned invalid category '%s', falling back.", category)
            category = submitted_category if submitted_category in ALLOWED_CATEGORIES else "other"

        if urgency not in ALLOWED_URGENCY:
            logger.warning("LLM returned invalid urgency '%s', falling back to medium.", urgency)
            urgency = "medium"

        return {
            "category": category,
            "urgency": urgency,
            "title": str(title)[:200],
            "reasoning": str(reasoning)[:500],
        }

    except Exception as exc:  # noqa: BLE001 — deliberately broad; AI layer must never break complaint creation
        logger.exception("LLM triage failed: %s", exc)
        return _default_result(description, submitted_category)