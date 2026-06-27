"""OpenRouter API client for LLM-based extraction."""

import json
import logging
import time

import httpx

from scraper.config import (
    LLM_RATE_LIMIT,
    LLM_RETRIES,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)

logger = logging.getLogger(__name__)

_last_request_time = 0.0


def _rate_limit() -> None:
    """Enforce rate limiting between LLM calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < LLM_RATE_LIMIT:
        time.sleep(LLM_RATE_LIMIT - elapsed)
    _last_request_time = time.time()


def call_llm(prompt: str, system: str = "You are a helpful assistant.") -> dict | None:
    """
    Call OpenRouter API with the given prompt.

    Returns parsed JSON dict or None on failure.
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set")
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/bd-university-scraper",
        "X-Title": "BD University Scraper",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    for attempt in range(LLM_RETRIES + 1):
        _rate_limit()

        try:
            resp = httpx.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                logger.warning(
                    "Rate limited (429), retrying in %ds (attempt %d/%d)",
                    retry_after, attempt + 1, LLM_RETRIES + 1,
                )
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            return _parse_json_response(content)

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error %d: %s (attempt %d/%d)", e.response.status_code, e, attempt + 1, LLM_RETRIES + 1)
            if attempt < LLM_RETRIES:
                time.sleep(2 ** attempt)
        except (httpx.RequestError, KeyError, IndexError) as e:
            logger.error("Request error: %s (attempt %d/%d)", e, attempt + 1, LLM_RETRIES + 1)
            if attempt < LLM_RETRIES:
                time.sleep(2 ** attempt)

    return None


def _parse_json_response(content: str) -> dict | None:
    """Parse JSON from LLM response, handling markdown code fences."""
    text = content.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    logger.warning("Failed to parse LLM response as JSON: %.200s...", content)
    return None
