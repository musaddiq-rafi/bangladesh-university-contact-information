"""Central configuration — all tuneable constants in one place."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openrouter/auto"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

DDG_SEARCH_DELAY = 2.5
DDG_BATCH_SIZE = 5
DDG_BATCH_PAUSE = 8.0

FETCH_TIMEOUT = 15
FETCH_WORKERS = 5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

LLM_WORKERS = 3
LLM_RATE_LIMIT = 1.0
LLM_MAX_TEXT_CHARS = 8000
LLM_RETRIES = 2

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
HTML_CACHE_DIR = OUTPUT_DIR / "html_cache"
LOG_DIR = BASE_DIR / "logs"

INPUT_CSV = DATA_DIR / "university_of_bangladesh.csv"
WEBSITES_CACHE = OUTPUT_DIR / "websites_cache.csv"
PASS1_CACHE = OUTPUT_DIR / "llm_results_pass1.json"
PASS2_CACHE = OUTPUT_DIR / "llm_results_pass2.json"
FINAL_OUTPUT = OUTPUT_DIR / "universities_contact.csv"

LOG_FILE = LOG_DIR / "scraper.log"
