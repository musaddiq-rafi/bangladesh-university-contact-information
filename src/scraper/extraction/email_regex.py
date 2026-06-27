"""Regex-based email pre-extraction from page text."""

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
    "ict", "information", "software", "engineering",
]
HEAD_KEYWORDS = ["head", "chair", "chairman", "professor", "dean"]


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


def _text_around(text: str, email: str, window: int = 80) -> str:
    """Get text surrounding an email address for keyword matching."""
    idx = text.lower().find(email.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(email) + window)
    return text[start:end].lower()


def classify_emails(
    emails: list[str],
    text: str,
    mailto_links: list[str],
) -> dict[str, str | None]:
    """
    Classify found emails by keyword context.

    Returns dict with keys: registrar_email, cse_dept_email, cse_dept_head_email
    """
    result: dict[str, str | None] = {
        "registrar_email": None,
        "cse_dept_email": None,
        "cse_dept_head_email": None,
    }

    all_emails = list(set(emails + mailto_links))

    for email in all_emails:
        context = _text_around(text, email)

        if not result["registrar_email"]:
            if any(kw in context for kw in REGISTRAR_KEYWORDS):
                result["registrar_email"] = email

        if not result["cse_dept_head_email"]:
            if any(kw in context for kw in HEAD_KEYWORDS):
                if any(kw in context for kw in CSE_KEYWORDS):
                    result["cse_dept_head_email"] = email

        if not result["cse_dept_email"]:
            if any(kw in context for kw in CSE_KEYWORDS):
                result["cse_dept_email"] = email

    return result
