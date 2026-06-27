"""Phase 5: Merge results and export to CSV."""

import csv
import logging

from scraper.config import FINAL_OUTPUT
from scraper.models import UniversityRecord

logger = logging.getLogger(__name__)

OUTPUT_FIELDS = [
    "University",
    "Acronym",
    "Website",
    "Registrar_Email",
    "CSE_Dept_Email",
    "CSE_Dept_Head_Email",
    "Email_Source",
    "CSE_Dept_URL",
    "Notes",
]


def _record_to_row(rec: UniversityRecord) -> dict[str, str]:
    return {
        "University": rec.name,
        "Acronym": rec.acronym,
        "Website": rec.website or "",
        "Registrar_Email": rec.registrar_email or "",
        "CSE_Dept_Email": rec.cse_dept_email or "",
        "CSE_Dept_Head_Email": rec.cse_dept_head_email or "",
        "Email_Source": rec.email_source,
        "CSE_Dept_URL": rec.cse_dept_url or "",
        "Notes": rec.notes,
    }


def export_csv(records: list[UniversityRecord]) -> str:
    """Export merged results to CSV."""
    FINAL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Writing %d records to %s", len(records), FINAL_OUTPUT)

    with open(FINAL_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for rec in records:
            writer.writerow(_record_to_row(rec))

    total = len(records)
    with_email = sum(
        1 for r in records
        if r.registrar_email or r.cse_dept_email or r.cse_dept_head_email
    )
    logger.info(
        "Phase 5 complete: %d/%d universities have contact info -> %s",
        with_email, total, FINAL_OUTPUT,
    )

    _print_summary(records)
    return str(FINAL_OUTPUT)


def _print_summary(records: list[UniversityRecord]) -> None:
    total = len(records)
    registrar = sum(1 for r in records if r.registrar_email)
    cse = sum(1 for r in records if r.cse_dept_email)
    head = sum(1 for r in records if r.cse_dept_head_email)
    any_email = sum(
        1 for r in records
        if r.registrar_email or r.cse_dept_email or r.cse_dept_head_email
    )

    print()
    print(f"  {'=' * 56}")
    print(f"  EXTRACTION SUMMARY")
    print(f"  {'=' * 56}")
    print(f"  Total universities:   {total}")
    if total > 0:
        print(f"  With any email:       {any_email} ({any_email/total*100:.1f}%)")
        print(f"  Registrar emails:     {registrar} ({registrar/total*100:.1f}%)")
        print(f"  CSE dept emails:      {cse} ({cse/total*100:.1f}%)")
        print(f"  CSE head emails:      {head} ({head/total*100:.1f}%)")
    else:
        print(f"  With any email:       {any_email} (0.0%)")
        print(f"  Registrar emails:     {registrar} (0.0%)")
        print(f"  CSE dept emails:      {cse} (0.0%)")
        print(f"  CSE head emails:      {head} (0.0%)")
    print(f"  Output file:          {FINAL_OUTPUT}")
    print(f"  {'=' * 56}")
    print()
