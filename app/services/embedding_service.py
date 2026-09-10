"""
app/services/embedding_service.py — embeddings + semantic duplicate detection.

get_embedding() calls Google's Gemini embedding API. cosine_similarity()
computes vector similarity with numpy. find_possible_duplicate() searches
active (open/in_progress) complaints in the same category and returns the
best match above the similarity threshold, if any.

Every public function here is fault-tolerant: on any failure, it logs the
error and returns None rather than raising — the AI layer must never
block complaint creation.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
import numpy as np

from app.core.config import settings
from app.models.complaint import Complaint

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ["open", "in_progress"]


async def get_embedding(text: str) -> Optional[list[float]]:
    """Return a dense embedding vector for text using Gemini, or None on failure."""
    if not settings.embedding_api_key:
        logger.warning("EMBEDDING_API_KEY not set — skipping embedding generation.")
        return None

    url = (
        f"{settings.embedding_base_url}/models/{settings.embedding_model}:embedContent"
        f"?key={settings.embedding_api_key}"
    )
    payload = {"content": {"parts": [{"text": text}]}}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]
    except Exception as exc:  # noqa: BLE001 — must never raise out of this function
        logger.exception("Embedding generation failed: %s", exc)
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity between two vectors, or 0.0 if either has zero magnitude."""
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


async def find_possible_duplicate(
    new_embedding: list[float],
    category: str,
    exclude_id=None,
    threshold: float = 0.85,
) -> Optional[dict]:
    """Return {'complaint_id': str, 'similarity': float} for the best match
    above threshold among active same-category complaints, or None.
    Never raises.
    """
    try:
        query = {"category": category, "status": {"$in": ACTIVE_STATUSES}}
        candidates = await Complaint.find(query).to_list()

        best_match: Optional[dict] = None
        for candidate in candidates:
            if exclude_id is not None and str(candidate.id) == str(exclude_id):
                continue
            if not candidate.embedding:
                continue

            score = cosine_similarity(new_embedding, candidate.embedding)
            if score >= threshold:
                if best_match is None or score > best_match["similarity"]:
                    best_match = {"complaint_id": str(candidate.id), "similarity": score}

        return best_match
    except Exception as exc:  # noqa: BLE001 — must never raise out of this function
        logger.exception("Duplicate detection failed: %s", exc)
        return None