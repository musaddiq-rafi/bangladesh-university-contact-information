"""Regex-based email extraction from page text and raw HTML."""

import re

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

FALSE_POSITIVE_EXT = {
    ".png@", ".jpg@", ".jpeg@", ".gif@", ".svg@",
    ".pdf@", ".doc@", ".mp3@", ".mp4@", ".css@", ".js@",
}

REGISTRAR_KEYWORDS = ["registrar"]
CSE_KEYWORDS = [
    "cse", "cs", "computer science", "computer",
    "ict", "information technology", "software",
]
HEAD_KEYWORDS = ["head", "chair", "chairman"]


def extract_emails(text: str) -> list[str]:
    """Extract all email addresses from text via regex."""
    raw = EMAIL_PATTERN.findall(text)
    cleaned = []
    for email in raw:
        email_lower = email.lower()
        skip = False
        for ext in FALSE_POSITIVE_EXT:
            if ext in email_lower:
                skip = True
                break
        if not skip and len(email) > 5:
            cleaned.append(email)
    return list(set(cleaned))


def _text_around(text: str, email: str, window: int = 120) -> str:
    """Get text surrounding an email address for keyword matching."""
    idx = text.lower().find(email.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(email) + window)
    return text[start:end].lower()


def _email_domain_matches_uni(email: str, text: str) -> bool:
    """Check if email domain seems related to the university."""
    domain = email.split("@")[1] if "@" in email else ""
    if not domain:
        return False
    uni_domains = ["edu.bd", "ac.bd"]
    return any(d in domain for d in uni_domains)


def classify_emails(
    emails: list[str],
    text: str,
    mailto_links: list[str],
    website_url: str = "",
) -> dict[str, str | None]:
    """
    Classify found emails by keyword context and domain matching.

    Returns dict with keys: registrar_email, cse_dept_email, cse_dept_head_email
    """
    result: dict[str, str | None] = {
        "registrar_email": None,
        "cse_dept_email": None,
        "cse_dept_head_email": None,
    }

    all_emails = list(set(emails + mailto_links))

    uni_domain = ""
    if website_url:
        parsed = website_url.replace("https://", "").replace("http://", "")
        uni_domain = parsed.split("/")[0].replace("www.", "")

    registrar_candidates = []
    cse_candidates = []
    head_candidates = []
    other_candidates = []

    for email in all_emails:
        context = _text_around(text, email)
        domain = email.split("@")[1] if "@" in email else ""

        is_registrar = any(kw in context for kw in REGISTRAR_KEYWORDS)
        is_head = any(kw in context for kw in HEAD_KEYWORDS)
        is_cse = any(kw in context for kw in CSE_KEYWORDS)
        domain_match = uni_domain and uni_domain in domain

        if is_registrar:
            registrar_candidates.append((email, domain_match, context))
        if is_head and is_cse:
            head_candidates.append((email, domain_match, context))
        elif is_cse:
            cse_candidates.append((email, domain_match, context))
        else:
            other_candidates.append((email, domain_match, context))

    def pick_best(candidates):
        if not candidates:
            return None
        domain_matched = [c for c in candidates if c[1]]
        if domain_matched:
            return domain_matched[0][0]
        return candidates[0][0]

    result["registrar_email"] = pick_best(registrar_candidates)
    result["cse_dept_email"] = pick_best(cse_candidates)
    result["cse_dept_head_email"] = pick_best(head_candidates)

    if not result["cse_dept_email"] and not result["cse_dept_head_email"]:
        for email, domain_match, context in other_candidates:
            domain = email.split("@")[1] if "@" in email else ""
            local = email.split("@")[0] if "@" in email else ""
            if any(kw in local for kw in ["cse", "cs", "ict", "computer"]):
                if not result["cse_dept_email"]:
                    result["cse_dept_email"] = email
            elif any(kw in local for kw in ["head", "chair"]):
                if not result["cse_dept_head_email"]:
                    result["cse_dept_head_email"] = email

    return result
