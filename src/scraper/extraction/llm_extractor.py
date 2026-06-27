"""Phase 3 & 4: LLM-based email extraction from page content."""

import json
import logging
import re

from scraper.config import LLM_MAX_TEXT_CHARS
from scraper.extraction.email_regex import classify_emails, extract_emails
from scraper.extraction.llm_client import call_llm
from scraper.models import PageData, UniversityRecord

logger = logging.getLogger(__name__)

PASS1_SYSTEM = """You are an expert at extracting contact information from Bangladeshi university websites.
You must find email addresses for: (1) registrar office, (2) CSE department, (3) CSE department head.
Return ONLY valid JSON. If an email is not found, use null. Look carefully at ALL the content provided."""

PASS1_PROMPT = """Extract contact information from this Bangladeshi university website.

University: {name} ({acronym})
Website: {url}

Website content (from main page + contact/about pages):
---
{text_content}
---

Email addresses found via mailto links:
{mailto_links}

Relevant page URLs found:
{relevant_urls}

TASKS:
1. Find the REGISTRAR office email (registrar@, admission@, or similar official email)
2. Find the CSE/CS/ICT DEPARTMENT email (cse@, cs@, info@cse.*, department.*)
3. Find the CSE DEPARTMENT HEAD/CHAIR email (head.cse@, chairman.cse@, prof.cse@, head@cs.*)
4. Find the URL to the CSE/CS/ICT department page

Common patterns for Bangladeshi universities:
- registrar@university.edu.bd
- cse@university.edu.bd or cse@dept.university.edu.bd
- head.cse@university.edu.bd or chairman@university.edu.bd
- info@university.edu.bd (for general contact if no specific registrar email)

Return ONLY this JSON:
{{
  "registrar_email": "email or null",
  "cse_dept_email": "email or null",
  "cse_dept_head_email": "email or null",
  "cse_dept_url": "URL or null",
  "confidence": "high" or "medium" or "low"
}}"""

PASS2_SYSTEM = """You are an expert at extracting CSE department contact information from Bangladeshi university department pages.
Look for email addresses of the department and department head/chair.
Return ONLY valid JSON."""

PASS2_PROMPT = """Extract CSE department contact information from this page.

University: {name} ({acronym})
Page URL: {url}

Page content:
---
{text_content}
---

Email addresses found on this page:
{mailto_links}

Find:
1. CSE department email (cse@, cs@, info@cse.*)
2. CSE department HEAD/CHAIR email (head.cse@, chairman@, head@cs.*)

Look for patterns like:
- "Department of Computer Science & Engineering" followed by an email
- Faculty member names with "Head" or "Chair" title near an email
- Contact section with department-specific email

Return ONLY this JSON:
{{
  "cse_dept_email": "email or null",
  "cse_dept_head_email": "email or null",
  "confidence": "high" or "medium" or "low"
}}"""


def _format_links(links: dict[str, str]) -> str:
    if not links:
        return "None found"
    return "\n".join(f"  {k}: {v}" for k, v in links.items())


def _format_mailto(mailto: list[str]) -> str:
    if not mailto:
        return "None found"
    return "\n".join(f"  {e}" for e in mailto)


def _validate_email(email: str | None) -> str | None:
    if not email:
        return None
    if isinstance(email, dict):
        return None
    email = str(email).strip()
    if re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
        return email
    return None


def llm_extract_pass1(
    uni: dict[str, str],
    page: PageData,
) -> UniversityRecord:
    """Phase 3: LLM extraction from main university website."""
    record = UniversityRecord(name=uni["name"], acronym=uni["acronym"], website=page.url)

    logger.info("  Scanning %s for emails via regex...", uni["acronym"])

    regex_emails = extract_emails(page.cleaned_text)
    classified = classify_emails(regex_emails, page.cleaned_text, page.mailto_links, page.url)
    record.registrar_email = classified["registrar_email"]
    record.cse_dept_email = classified["cse_dept_email"]
    record.cse_dept_head_email = classified["cse_dept_head_email"]

    if record.registrar_email or record.cse_dept_email:
        record.email_source = "regex_extracted"
        record.confidence = "medium"
        logger.info("  %s regex found: reg=%s cse=%s head=%s",
                     uni["acronym"], record.registrar_email or "-",
                     record.cse_dept_email or "-", record.cse_dept_head_email or "-")

    text_len = min(len(page.cleaned_text), LLM_MAX_TEXT_CHARS)
    logger.info("  Sending %s to LLM (text: %d chars)...", uni["acronym"], text_len)

    text_truncated = page.cleaned_text[:LLM_MAX_TEXT_CHARS]
    prompt = PASS1_PROMPT.format(
        name=uni["name"],
        acronym=uni["acronym"],
        url=page.url,
        text_content=text_truncated,
        mailto_links=_format_mailto(page.mailto_links),
        relevant_urls=_format_links(page.relevant_links),
    )

    llm_result = call_llm(prompt, system=PASS1_SYSTEM)
    if not llm_result:
        record.notes = "LLM call failed"
        logger.warning("  %s LLM returned no result", uni["acronym"])
        return record

    if not record.registrar_email:
        record.registrar_email = _validate_email(llm_result.get("registrar_email"))
    if not record.cse_dept_email:
        record.cse_dept_email = _validate_email(llm_result.get("cse_dept_email"))
    if not record.cse_dept_head_email:
        record.cse_dept_head_email = _validate_email(llm_result.get("cse_dept_head_email"))

    record.cse_dept_url = llm_result.get("cse_dept_url")
    if not record.email_source or record.email_source == "not_found":
        record.email_source = llm_result.get("email_source", "not_found")
    record.confidence = llm_result.get("confidence", record.confidence)

    logger.info("  %s LLM result: reg=%s cse=%s head=%s (conf=%s)",
                uni["acronym"], record.registrar_email or "-",
                record.cse_dept_email or "-", record.cse_dept_head_email or "-",
                record.confidence)

    return record


def llm_extract_pass2(
    record: UniversityRecord,
    page: PageData,
) -> UniversityRecord:
    """Phase 4: LLM extraction from CSE department page (fallback)."""
    logger.info("  Pass 2 for %s: %s", record.acronym, page.url)

    regex_emails = extract_emails(page.cleaned_text)
    classified = classify_emails(regex_emails, page.cleaned_text, page.mailto_links, page.url)

    new_cse = classified["cse_dept_email"]
    new_head = classified["cse_dept_head_email"]

    if new_cse and not record.cse_dept_email:
        record.cse_dept_email = new_cse
    if new_head and not record.cse_dept_head_email:
        record.cse_dept_head_email = new_head

    if record.cse_dept_email and record.cse_dept_head_email:
        record.confidence = "medium"
        return record

    text_truncated = page.cleaned_text[:LLM_MAX_TEXT_CHARS]
    prompt = PASS2_PROMPT.format(
        name=record.name,
        acronym=record.acronym,
        url=page.url,
        text_content=text_truncated,
        mailto_links=_format_mailto(page.mailto_links),
    )

    llm_result = call_llm(prompt, system=PASS2_SYSTEM)
    if not llm_result:
        record.notes += " | Pass 2 LLM failed"
        return record

    new_cse_email = _validate_email(llm_result.get("cse_dept_email"))
    new_head_email = _validate_email(llm_result.get("cse_dept_head_email"))

    if new_cse_email and not record.cse_dept_email:
        record.cse_dept_email = new_cse_email
    if new_head_email and not record.cse_dept_head_email:
        record.cse_dept_head_email = new_head_email

    if new_cse_email or new_head_email:
        record.confidence = llm_result.get("confidence", "medium")

    return record
