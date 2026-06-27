"""Phase 1: Discover university websites via DuckDuckGo search."""

import csv
import logging
import time
from urllib.parse import urlparse

from duckduckgo_search import DDGS

from scraper.config import (
    DDG_BATCH_PAUSE,
    DDG_BATCH_SIZE,
    DDG_SEARCH_DELAY,
    INPUT_CSV,
    WEBSITES_CACHE,
)

logger = logging.getLogger(__name__)


def load_input_csv() -> list[dict[str, str]]:
    """Read the input CSV and return list of university dicts."""
    rows: list[dict[str, str]] = []
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("University", "").strip()
            acronym = row.get("Acronym", "").strip()
            if name:
                rows.append({"name": name, "acronym": acronym, **row})
    return rows


def load_websites_cache() -> dict[str, str]:
    """Load already-discovered websites from cache CSV. Key: acronym."""
    cache: dict[str, str] = {}
    if WEBSITES_CACHE.exists():
        with open(WEBSITES_CACHE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row.get('name', '')}||{row.get('acronym', '')}"
                url = row.get("website", "").strip()
                if url:
                    cache[key] = url
    return cache


def save_websites_cache(results: list[dict[str, str]]) -> None:
    """Write discovered websites to cache CSV."""
    with open(WEBSITES_CACHE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "acronym", "website"])
        writer.writeheader()
        writer.writerows(results)


def _prefer_acbd(results: list[str]) -> str | None:
    """Pick the best URL from search results, preferring .ac.bd domains."""
    if not results:
        return None

    acbd = [u for u in results if ".ac.bd" in u]
    if acbd:
        return acbd[0]

    edu = [u for u in results if ".edu" in u or ".edu.bd" in u]
    if edu:
        return edu[0]

    return results[0] if results else None


def _search_university(ddgs: DDGS, name: str, acronym: str) -> str | None:
    """Search DuckDuckGo for a university's website."""
    query = f"{name} {acronym} official website Bangladesh"
    try:
        results = ddgs.text(query, max_results=5)
        urls = [r["href"] for r in results if "href" in r]
        return _prefer_acbd(urls)
    except Exception as e:
        logger.warning("DDG search failed for %s: %s", name, e)
        return None


def discover_websites(resume: bool = True) -> list[dict[str, str]]:
    """
    Phase 1: Discover websites for all universities.

    Returns list of dicts with keys: name, acronym, website
    """
    universities = load_input_csv()
    cache = load_websites_cache() if resume else {}
    results: list[dict[str, str]] = []

    total = len(universities)
    cached = 0
    searched = 0

    logger.info("Starting website discovery for %d universities", total)

    with DDGS() as ddgs:
        for i, uni in enumerate(universities):
            key = f"{uni['name']}||{uni['acronym']}"

            if resume and key in cache:
                results.append({
                    "name": uni["name"],
                    "acronym": uni["acronym"],
                    "website": cache[key],
                })
                cached += 1
                continue

            url = _search_university(ddgs, uni["name"], uni["acronym"])
            results.append({
                "name": uni["name"],
                "acronym": uni["acronym"],
                "website": url or "",
            })
            searched += 1

            if url:
                logger.info("[%d/%d] %s -> %s", i + 1, total, uni["acronym"], url)
            else:
                logger.warning("[%d/%d] %s -> NOT FOUND", i + 1, total, uni["acronym"])

            if searched % DDG_BATCH_SIZE == 0:
                logger.info("Batch pause after %d searches...", DDG_BATCH_SIZE)
                time.sleep(DDG_BATCH_PAUSE)
            else:
                time.sleep(DDG_SEARCH_DELAY)

    save_websites_cache(results)

    found = sum(1 for r in results if r["website"])
    logger.info(
        "Discovery complete: %d/%d websites found (%d cached, %d searched)",
        found, total, cached, searched,
    )
    return results
