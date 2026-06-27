"""Phase 3 & 4: LLM-based email extraction from page content."""

import json
import logging
import re

from scraper.config import LLM_MAX_TEXT_CHARS
from scraper.extraction.email_regex import classify_emails, extract_emails
from scraper.extraction.llm_client import call_llm
from scraper.models import PageData, UniversityRecord

logger = logging.getLogger(__name__)

PASS1_SYSTEM = "You extract contact information from Bangladeshi university websites. Return only valid JSON."

PASS1_PROMPT = """You are extracting contact information from a Bangladeshi university website.

University: {name} ({acronym})
Website: {url}

Here is the cleaned text content from the university website:
---
{text_content}
---

Here are mailto links found on the page:
{mailto_links}

Here are relevant URLs found:
{relevant_urls}

Extract the following and return ONLY valid JSON:
{{
  "university_name": "official name of the university",
  "registrar_email": "registrar office email address" or null,
  "cse_dept_email": "CSE/CS/ICT department email" or null,
  "cse_dept_head_email": "CSE department head email" or null,
  "email_source": "found_on_main_page" | "inferred_from_links" | "not_found",
  "cse_dept_url": "URL to CSE/CS/ICT department page" or null,
  "confidence": "high" | "medium" | "low"
}}"""

PASS2_SYSTEM = "You extract CSE department contact information from Bangladeshi university department pages. Return only valid JSON."

PASS2_PROMPT = """You are extracting CSE department contact information from a Bangladeshi university page.

University: {name} ({acronym})
Page URL: {url}
This is the CSE/CS/ICT department page of {name}.

Here is the cleaned text content from the page:
---
{text_content}
---

Here are mailto links found on the page:
{mailto_links}

Extract ONLY the following and return valid JSON:
{{
  "cse_dept_email": "CSE department email" or null,
  "cse_dept_head_email": "CSE department head/chair email" or null,
  "confidence": "high" | "medium" | "low"
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
    classified = classify_emails(regex_emails, page.cleaned_text, page.mailto_links)
    record.registrar_email = classified["registrar_email"]
    record.cse_dept_email = classified["cse_dept_email"]
    record.cse_dept_head_email = classified["cse_dept_head_email"]

    if record.registrar_email or record.cse_dept_email:
        record.email_source = "regex_extracted"
        record.confidence = "medium"
        logger.info("  %s regex found: reg=%s cse=%s head=%s",
                     uni["acronym"], record.registrar_email or "-",
                     record.cse_dept_email or "-", record.cse_dept_head_email or "-")

    logger.info("  Sending %s to LLM (text: %d chars)...", uni["acronym"], min(len(page.cleaned_text), LLM_MAX_TEXT_CHARS))

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
    logger.info("  Fetching CSE dept page for %s: %s", record.acronym, page.url)

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
        logger.warning("  %s Pass 2 LLM returned no result", record.acronym)
        return record

    new_cse_email = _validate_email(llm_result.get("cse_dept_email"))
    new_head_email = _validate_email(llm_result.get("cse_dept_head_email"))

    if new_cse_email and not record.cse_dept_email:
        record.cse_dept_email = new_cse_email
    if new_head_email and not record.cse_dept_head_email:
        record.cse_dept_head_email = new_head_email

    if new_cse_email or new_head_email:
        record.confidence = llm_result.get("confidence", "medium")

    logger.info("  %s Pass 2 result: cse=%s head=%s",
                record.acronym, record.cse_dept_email or "-",
                record.cse_dept_head_email or "-")

    return record
