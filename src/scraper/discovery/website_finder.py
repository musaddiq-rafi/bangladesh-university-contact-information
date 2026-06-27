"""Phase 1: Discover university websites via DuckDuckGo HTML search."""

import csv
import logging
import time
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from scraper.config import (
    DDG_BATCH_PAUSE,
    DDG_BATCH_SIZE,
    DDG_SEARCH_DELAY,
    INPUT_CSV,
    USER_AGENT,
    WEBSITES_CACHE,
)

logger = logging.getLogger(__name__)

DDG_HTML_URL = "https://html.duckduckgo.com/html/"

JUNK_DOMAINS = {
    "bing.com", "google.com", "duckduckgo.com", "yahoo.com",
    "facebook.com", "twitter.com", "linkedin.com", "youtube.com",
    "instagram.com", "reddit.com", "wikipedia.org", "wikidata.org",
}


def load_input_csv() -> list[dict[str, str]]:
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
    with open(WEBSITES_CACHE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "acronym", "website"])
        writer.writeheader()
        writer.writerows(results)


def _is_junk_url(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        for junk in JUNK_DOMAINS:
            if domain == junk or domain.endswith("." + junk):
                return True
    except Exception:
        return True
    return False


def _resolve_ddg_url(href: str) -> str | None:
    """Resolve DuckDuckGo redirect URL to actual URL."""
    if not href:
        return None
    if "uddg=" in href:
        try:
            qs = parse_qs(urlparse(href).query)
            if "uddg" in qs:
                return unquote(qs["uddg"][0])
        except Exception:
            pass
    if href.startswith("http"):
        return href
    return None


def _pick_best(links: list[str]) -> str | None:
    clean = [u for u in links if not _is_junk_url(u)]
    if not clean:
        return None
    for domain in [".ac.bd", ".edu.bd", ".edu", ".gov.bd"]:
        match = [u for u in clean if domain in u]
        if match:
            return match[0]
    return clean[0]


def _search_ddg(query: str) -> str | None:
    """Search DuckDuckGo HTML endpoint and return best URL."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        resp = requests.post(
            DDG_HTML_URL,
            data={"q": query},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Search failed: %s", e)
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    links = []

    for a in soup.find_all("a", class_="result__a", href=True):
        url = _resolve_ddg_url(a["href"])
        if url and not _is_junk_url(url):
            links.append(url)

    return _pick_best(links)


def discover_websites(resume: bool = True) -> list[dict[str, str]]:
    """Phase 1: Discover websites for all universities."""
    universities = load_input_csv()
    cache = load_websites_cache() if resume else {}
    results: list[dict[str, str]] = []

    total = len(universities)
    cached = 0
    searched = 0
    found = 0

    logger.info("Searching for %d university websites...", total)
    print()

    for i, uni in enumerate(universities):
        key = f"{uni['name']}||{uni['acronym']}"

        if resume and key in cache:
            results.append({
                "name": uni["name"],
                "acronym": uni["acronym"],
                "website": cache[key],
            })
            cached += 1
            logger.info("[%d/%d] %s -> %s (cached)", i + 1, total, uni["acronym"], cache[key])
            found += 1
            continue

        query = f"{uni['name']} {uni['acronym']}"
        url = _search_ddg(query)
        results.append({
            "name": uni["name"],
            "acronym": uni["acronym"],
            "website": url or "",
        })
        searched += 1

        if url:
            found += 1
            logger.info("[%d/%d] %s -> %s", i + 1, total, uni["acronym"], url)
        else:
            logger.warning("[%d/%d] %s -> NOT FOUND", i + 1, total, uni["acronym"])

        if searched % DDG_BATCH_SIZE == 0:
            logger.info("Batch pause %.0fs after %d searches...", DDG_BATCH_PAUSE, DDG_BATCH_SIZE)
            time.sleep(DDG_BATCH_PAUSE)
        else:
            time.sleep(DDG_SEARCH_DELAY)

    save_websites_cache(results)

    print()
    logger.info(
        "Phase 1 complete: %d/%d websites found (%d from cache, %d new searches)",
        found, total, cached, searched,
    )
    return results
