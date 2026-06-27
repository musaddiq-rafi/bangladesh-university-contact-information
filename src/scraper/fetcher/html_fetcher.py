"""Phase 2: Fetch university website HTML and extract clean text + links."""

import json
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from scraper.config import FETCH_TIMEOUT, HTML_CACHE_DIR, USER_AGENT
from scraper.models import PageData

logger = logging.getLogger(__name__)

RELEVANT_KEYWORDS = [
    "registrar", "contact", "about", "cse", "computer",
    "ict", "faculty", "department", "info", "science",
]

STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _cache_path(acronym: str) -> str:
    safe = acronym.replace("/", "_").replace("\\", "_")
    return str(HTML_CACHE_DIR / f"{safe}.json")


def _load_cache(acronym: str) -> PageData | None:
    path = _cache_path(acronym)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return PageData(
            url=data["url"],
            raw_html=data["raw_html"],
            cleaned_text=data["cleaned_text"],
            mailto_links=data.get("mailto_links", []),
            relevant_links=data.get("relevant_links", {}),
        )
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_cache(acronym: str, page: PageData) -> None:
    HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "url": page.url,
        "raw_html": page.raw_html,
        "cleaned_text": page.cleaned_text,
        "mailto_links": page.mailto_links,
        "relevant_links": page.relevant_links,
    }
    with open(_cache_path(acronym), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _clean_html(soup: BeautifulSoup) -> str:
    """Strip unwanted tags and return cleaned text."""
    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _extract_mailto_links(soup: BeautifulSoup) -> list[str]:
    """Extract all email addresses from mailto: links."""
    emails = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.lower().startswith("mailto:"):
            email = href[7:].split("?")[0].strip()
            if "@" in email:
                emails.append(email)
    return list(set(emails))


def _extract_relevant_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    """Extract links matching relevant keywords."""
    links: dict[str, str] = {}
    base_domain = urlparse(base_url).netloc

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        if parsed.netloc and parsed.netloc != base_domain:
            continue

        text_lower = (a_tag.get_text() + " " + href).lower()

        for keyword in RELEVANT_KEYWORDS:
            if keyword in text_lower and keyword not in links:
                links[keyword] = full_url
                break

    return links


def fetch_page(url: str, acronym: str, session: requests.Session) -> PageData | None:
    """Fetch a single page and return structured PageData."""
    cached = _load_cache(acronym)
    if cached:
        logger.debug("Cache hit for %s", acronym)
        return cached

    try:
        resp = session.get(url, timeout=FETCH_TIMEOUT, verify=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
    except requests.RequestException as e:
        logger.warning("Fetch failed for %s (%s): %s", acronym, url, e)
        return None

    raw_html = resp.text
    soup = BeautifulSoup(raw_html, "lxml")
    cleaned_text = _clean_html(soup)
    mailto_links = _extract_mailto_links(soup)
    relevant_links = _extract_relevant_links(soup, url)

    page = PageData(
        url=url,
        raw_html=raw_html,
        cleaned_text=cleaned_text,
        mailto_links=mailto_links,
        relevant_links=relevant_links,
    )

    _save_cache(acronym, page)
    return page


def fetch_all(
    websites: list[dict[str, str]],
    workers: int = 5,
) -> list[tuple[dict[str, str], PageData | None]]:
    """
    Fetch HTML for all universities with websites.

    Returns list of (university_dict, PageData_or_None) tuples.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    session = _make_session()
    results: list[tuple[dict[str, str], PageData | None]] = []

    to_fetch = [(w, w["website"]) for w in websites if w.get("website")]
    skipped = [w for w in websites if not w.get("website")]

    for w in skipped:
        results.append((w, None))

    logger.info("Fetching %d pages (%d skipped, no URL)", len(to_fetch), len(skipped))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_uni = {
            executor.submit(fetch_page, url, uni["acronym"], session): uni
            for uni, url in to_fetch
        }

        for i, future in enumerate(as_completed(future_to_uni)):
            uni = future_to_uni[future]
            try:
                page = future.result()
            except Exception as e:
                logger.error("Unexpected error fetching %s: %s", uni["acronym"], e)
                page = None

            results.append((uni, page))
            if (i + 1) % 10 == 0:
                logger.info("Fetched %d/%d pages", i + 1, len(to_fetch))

    found = sum(1 for _, p in results if p is not None)
    logger.info("Fetch complete: %d/%d pages retrieved", found, len(to_fetch))
    return results
