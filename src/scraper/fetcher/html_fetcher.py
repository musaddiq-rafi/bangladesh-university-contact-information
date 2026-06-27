"""Phase 2: Fetch university website HTML with multi-page crawling and raw email extraction."""

import json
import logging
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from scraper.config import FETCH_TIMEOUT, HTML_CACHE_DIR, USER_AGENT
from scraper.models import PageData

logger = logging.getLogger(__name__)

RELEVANT_KEYWORDS = [
    "registrar", "contact", "about", "cse", "computer",
    "ict", "faculty", "department", "info", "science",
]

SUB_PAGES = ["", "/contact", "/contact-us", "/about", "/about-us", "/registrar"]

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

STRIP_TAGS = ["script", "style", "noscript"]


def _make_session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    adapter = requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(total=2, backoff_factor=0.5)
    )
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _cache_path(acronym: str) -> str:
    safe = re.sub(r'[^\w\-]', '_', acronym)
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


def _extract_emails_from_raw_html(raw_html: str) -> list[str]:
    """Extract all email addresses from raw HTML source."""
    raw = EMAIL_REGEX.findall(raw_html)
    cleaned = []
    false_pos = {".png@", ".jpg@", ".jpeg@", ".gif@", ".svg@",
                 ".pdf@", ".doc@", ".mp3@", ".mp4@", ".css@", ".js@"}
    for email in raw:
        el = email.lower()
        if any(fp in el for fp in false_pos):
            continue
        if len(email) > 5 and "." in email.split("@")[1]:
            cleaned.append(email.lower())
    return list(set(cleaned))


def _clean_html(soup: BeautifulSoup) -> str:
    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _extract_mailto_links(soup: BeautifulSoup) -> list[str]:
    emails = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.lower().startswith("mailto:"):
            email = href[7:].split("?")[0].strip()
            if "@" in email:
                emails.append(email.lower())
    return list(set(emails))


def _extract_relevant_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
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


def _fetch_single_page(url: str, session: requests.Session) -> tuple[str, str, list[str], dict[str, str]] | None:
    """Fetch a single URL and return (raw_html, cleaned_text, mailto_links, relevant_links)."""
    for attempt_url in [url, url.replace("https://", "http://", 1)]:
        if attempt_url != url and url.startswith("https://"):
            logger.debug("Retrying with HTTP: %s", attempt_url)
        try:
            resp = session.get(attempt_url, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
        except requests.RequestException as e:
            if attempt_url == url:
                logger.debug("Fetch failed %s: %s", attempt_url, e)
                continue
            logger.debug("Fetch failed %s: %s", attempt_url, e)
            return None
        break

    raw_html = resp.text
    soup = BeautifulSoup(raw_html, "lxml")
    cleaned_text = _clean_html(soup)
    mailto_links = _extract_mailto_links(soup)
    relevant_links = _extract_relevant_links(soup, url)

    return raw_html, cleaned_text, mailto_links, relevant_links


def _domain_resolves(url: str) -> bool:
    """Quick DNS check — skip domains that don't resolve at all."""
    host = urlparse(url).hostname
    if not host:
        return False
    try:
        socket.getaddrinfo(host, 80, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_ADDRCONFIG)
        return True
    except socket.gaierror:
        return False


def fetch_page(url: str, acronym: str, session: requests.Session) -> PageData | None:
    """Fetch a university's main page plus contact subpages, merge results."""
    cached = _load_cache(acronym)
    if cached:
        logger.debug("Cache hit for %s", acronym)
        return cached

    if not _domain_resolves(url):
        logger.warning("Domain does not resolve for %s (%s)", acronym, urlparse(url).hostname)
        return None

    base_url = url.rstrip("/")
    all_raw_html = ""
    all_cleaned_text = ""
    all_mailto = []
    all_relevant: dict[str, str] = {}
    emails_from_raw: list[str] = []

    for sub in SUB_PAGES:
        page_url = base_url + sub
        result = _fetch_single_page(page_url, session)
        if result is None:
            continue

        raw, cleaned, mailto, relinks = result
        all_raw_html += "\n" + raw
        all_cleaned_text += "\n" + cleaned
        all_mailto.extend(mailto)
        for k, v in relinks.items():
            if k not in all_relevant:
                all_relevant[k] = v

        raw_emails = _extract_emails_from_raw_html(raw)
        emails_from_raw.extend(raw_emails)

        if sub == "":
            primary_url = page_url

    if not all_cleaned_text.strip():
        return None

    all_mailto = list(set(all_mailto))
    emails_from_raw = list(set(emails_from_raw))

    all_cleaned_text += "\n\n[RAW EMAILS FOUND]: " + " ".join(emails_from_raw) if emails_from_raw else ""

    page = PageData(
        url=base_url,
        raw_html=all_raw_html,
        cleaned_text=all_cleaned_text.strip(),
        mailto_links=all_mailto,
        relevant_links=all_relevant,
    )
    _save_cache(acronym, page)
    return page


def fetch_all(
    websites: list[dict[str, str]],
    workers: int = 5,
) -> list[tuple[dict[str, str], PageData | None]]:
    """Fetch HTML for all universities with websites using concurrent workers."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    session = _make_session()
    results: list[tuple[dict[str, str], PageData | None]] = []

    to_fetch = [(w, w["website"]) for w in websites if w.get("website")]
    skipped = [w for w in websites if not w.get("website")]

    for w in skipped:
        results.append((w, None))

    logger.info(
        "Fetching %d pages with %d workers (%d skipped - no URL)",
        len(to_fetch), workers, len(skipped),
    )

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
            if (i + 1) % 10 == 0 or (i + 1) == len(to_fetch):
                logger.info("Fetched %d/%d pages", i + 1, len(to_fetch))

    found = sum(1 for _, p in results if p is not None)
    logger.info(
        "Phase 2 complete: %d/%d pages retrieved successfully",
        found, len(to_fetch),
    )
    return results
