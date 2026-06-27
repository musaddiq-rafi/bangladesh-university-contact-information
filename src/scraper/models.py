"""Structured data types for the scraper pipeline."""

from dataclasses import dataclass, field


@dataclass
class UniversityRecord:
    name: str
    acronym: str
    website: str | None = None
    registrar_email: str | None = None
    cse_dept_email: str | None = None
    cse_dept_head_email: str | None = None
    email_source: str = "not_found"
    cse_dept_url: str | None = None
    confidence: str = "low"
    notes: str = ""


@dataclass
class PageData:
    url: str
    raw_html: str
    cleaned_text: str
    mailto_links: list[str] = field(default_factory=list)
    relevant_links: dict[str, str] = field(default_factory=dict)
