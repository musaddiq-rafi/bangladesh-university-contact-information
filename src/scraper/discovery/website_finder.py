"""Phase 1: Load verified university websites from CSV."""

import csv
import logging

from scraper.config import INPUT_CSV, OUTPUT_DIR, WEBSITES_CACHE

logger = logging.getLogger(__name__)


def _read_csv() -> list[dict[str, str]]:
    rows = []
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("University", "").strip()
            acronym = row.get("Acronym", "").strip()
            website = row.get("Website", "").strip()
            if name:
                rows.append({"name": name, "acronym": acronym, "website": website})
    return rows


def _save_cache(results: list[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(WEBSITES_CACHE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "acronym", "website"])
        w.writeheader()
        w.writerows(results)


def discover_websites(resume: bool = True) -> list[dict[str, str]]:
    """
    Phase 1: Load websites from the verified CSV data.

    The CSV now includes a Website column populated from verified
    UGC (University Grants Commission) sources. No search needed.
    """
    universities = _read_csv()
    total = len(universities)
    found = sum(1 for u in universities if u.get("website"))

    logger.info("Loaded %d universities from CSV (%d with websites)", total, found)

    for i, uni in enumerate(universities):
        if uni["website"]:
            logger.info("[%d/%d] %s -> %s", i + 1, total, uni["acronym"], uni["website"])
        else:
            logger.warning("[%d/%d] %s -> NO WEBSITE", i + 1, total, uni["acronym"])

    if found < total:
        logger.info("%d universities have no website in the verified data", total - found)

    _save_cache(universities)
    return universities
