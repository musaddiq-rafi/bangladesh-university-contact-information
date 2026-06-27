"""Pipeline orchestrator - runs the full scraping pipeline (Phase 1->5)."""

import csv
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from scraper.config import (
    FETCH_WORKERS,
    HTML_CACHE_DIR,
    LLM_WORKERS,
    PASS1_CACHE,
    PASS2_CACHE,
    WEBSITES_CACHE,
)
from scraper.discovery.website_finder import discover_websites
from scraper.fetcher.html_fetcher import fetch_all, fetch_page, _make_session
from scraper.extraction.llm_extractor import llm_extract_pass1, llm_extract_pass2
from scraper.export.csv_exporter import export_csv
from scraper.models import UniversityRecord, PageData

logger = logging.getLogger(__name__)


def _phase_header(phase: int, title: str, description: str) -> None:
    print()
    print(f"  {'=' * 56}")
    print(f"  PHASE {phase}: {title}")
    print(f"  {description}")
    print(f"  {'=' * 56}")
    print()


def run(
    step: int | None = None,
    resume: bool = True,
    api_key: str | None = None,
) -> None:
    """Run the full pipeline or a specific step."""
    if api_key:
        import scraper.config as cfg
        cfg.OPENROUTER_API_KEY = api_key

    if step is None or step == 1:
        _run_phase1(resume)

    if step is None or step == 2:
        _run_phase2()

    if step is None or step == 3:
        _run_phase3()

    if step is None or step == 4:
        _run_phase4()

    if step is None or step == 5:
        _run_phase5()


def _run_phase1(resume: bool) -> None:
    _phase_header(1, "Website Discovery", "Loading websites from verified UGC data")
    discover_websites(resume=resume)


def _load_websites() -> list[dict[str, str]]:
    results = []
    if not WEBSITES_CACHE.exists():
        logger.error("No websites cache found. Run Phase 1 first.")
        return results
    with open(WEBSITES_CACHE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(dict(row))
    return results


def _run_phase2() -> None:
    _phase_header(2, "HTML Fetch", "Downloading main + contact/about pages per university")
    websites = _load_websites()
    if not websites:
        return
    fetch_all(websites, workers=FETCH_WORKERS)


def _run_phase3() -> None:
    _phase_header(3, "LLM Extraction - Pass 1", "Extracting emails from university websites")

    websites = _load_websites()
    if not websites:
        return

    session = _make_session()
    results: list[UniversityRecord] = []

    cached = _load_json_cache(PASS1_CACHE)
    cached_acronyms = {r.get("acronym") for r in cached}

    to_process = [w for w in websites if w.get("website") and w["acronym"] not in cached_acronyms]

    for uni in cached:
        results.append(_dict_to_record(uni))

    if cached:
        logger.info("Loaded %d cached results, processing %d new universities",
                     len(cached), len(to_process))
    else:
        logger.info("No cache found, processing all %d universities", len(to_process))

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        futures = {}
        for uni in to_process:
            page = fetch_page(uni["website"], uni["acronym"], session)
            if page:
                futures[executor.submit(llm_extract_pass1, uni, page)] = uni
            else:
                record = UniversityRecord(name=uni["name"], acronym=uni["acronym"], notes="Fetch failed")
                results.append(record)
                fail_count += 1

        for i, future in enumerate(as_completed(futures)):
            uni = futures[future]
            try:
                record = future.result()
                if record.registrar_email or record.cse_dept_email:
                    success_count += 1
            except Exception as e:
                logger.error("LLM extraction failed for %s: %s", uni["acronym"], e)
                record = UniversityRecord(name=uni["name"], acronym=uni["acronym"], notes=f"Error: {e}")

            results.append(record)
            if (i + 1) % 10 == 0 or (i + 1) == len(futures):
                logger.info("LLM progress: %d/%d (found: %d, failed: %d)",
                           i + 1, len(futures), success_count, fail_count)

    _save_json_cache(PASS1_CACHE, [_record_to_dict(r) for r in results])

    total_found = sum(1 for r in results if r.registrar_email or r.cse_dept_email)
    logger.info(
        "Phase 3 complete: %d/%d universities have contact info",
        total_found, len(results),
    )


def _run_phase4() -> None:
    _phase_header(4, "LLM Extraction - Pass 2", "Extracting emails from CSE department pages")

    pass1_records = _load_json_cache(PASS1_CACHE)
    if not pass1_records:
        logger.error("No pass 1 results found. Run Phase 3 first.")
        return

    session = _make_session()
    results: list[UniversityRecord] = []

    pass2_cached = _load_json_cache(PASS2_CACHE)
    pass2_acronyms = {r.get("acronym") for r in pass2_cached}

    for rec in pass2_cached:
        results.append(_dict_to_record(rec))

    to_process = [
        r for r in pass1_records
        if r.get("cse_dept_url") and r.get("cse_dept_url") != "null"
        and r["acronym"] not in pass2_acronyms
    ]

    if not to_process:
        logger.info("No CSE department pages to process")
    else:
        logger.info(
            "Found %d universities with CSE dept URLs (%d cached)",
            len(to_process), len(pass2_cached),
        )

    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        futures = {}
        for rec_dict in to_process:
            record = _dict_to_record(rec_dict)
            cse_url = rec_dict.get("cse_dept_url")
            if cse_url:
                page = fetch_page(cse_url, f"{rec_dict['acronym']}_cse", session)
                if page:
                    futures[executor.submit(llm_extract_pass2, record, page)] = record

        for i, future in enumerate(as_completed(futures)):
            record = futures[future]
            try:
                updated = future.result()
            except Exception as e:
                logger.error("Pass 2 failed for %s: %s", record.acronym, e)
                updated = record

            results.append(updated)
            if (i + 1) % 5 == 0 or (i + 1) == len(to_process):
                logger.info("Pass 2 progress: %d/%d CSE pages processed", i + 1, len(to_process))

    _save_json_cache(PASS2_CACHE, [_record_to_dict(r) for r in results])

    new_emails = sum(1 for r in results if r.cse_dept_email or r.cse_dept_head_email)
    logger.info(
        "Phase 4 complete: %d/%d universities now have CSE dept emails",
        new_emails, len(results),
    )


def _run_phase5() -> None:
    _phase_header(5, "Export CSV", "Merging results and writing final output")

    pass1_list = _load_json_cache(PASS1_CACHE)
    pass2_list = _load_json_cache(PASS2_CACHE)

    logger.info("Loaded %d pass 1 results, %d pass 2 results", len(pass1_list), len(pass2_list))

    pass1 = {(r["name"], r["acronym"]): r for r in pass1_list}
    pass2 = {(r["name"], r["acronym"]): r for r in pass2_list}

    merged: dict[tuple[str, str], dict] = {}

    for key, rec in pass1.items():
        merged[key] = dict(rec)

    upgraded = 0
    for key, rec in pass2.items():
        if key in merged:
            for field in ["cse_dept_email", "cse_dept_head_email"]:
                if rec.get(field) and not merged[key].get(field):
                    merged[key][field] = rec[field]
                    upgraded += 1
            if rec.get("confidence", "low") != "low":
                merged[key]["confidence"] = rec["confidence"]
        else:
            merged[key] = dict(rec)

    if upgraded:
        logger.info("Pass 2 upgraded %d email fields", upgraded)

    records = [_dict_to_record(r) for r in merged.values()]
    records.sort(key=lambda r: r.name)

    export_csv(records)


def _load_json_cache(path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_json_cache(path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _record_to_dict(rec: UniversityRecord) -> dict:
    return {
        "name": rec.name,
        "acronym": rec.acronym,
        "website": rec.website,
        "registrar_email": rec.registrar_email,
        "cse_dept_email": rec.cse_dept_email,
        "cse_dept_head_email": rec.cse_dept_head_email,
        "email_source": rec.email_source,
        "cse_dept_url": rec.cse_dept_url,
        "confidence": rec.confidence,
        "notes": rec.notes,
    }


def _dict_to_record(d: dict) -> UniversityRecord:
    return UniversityRecord(
        name=d.get("name", ""),
        acronym=d.get("acronym", ""),
        website=d.get("website"),
        registrar_email=d.get("registrar_email"),
        cse_dept_email=d.get("cse_dept_email"),
        cse_dept_head_email=d.get("cse_dept_head_email"),
        email_source=d.get("email_source", "not_found"),
        cse_dept_url=d.get("cse_dept_url"),
        confidence=d.get("confidence", "low"),
        notes=d.get("notes", ""),
    )
