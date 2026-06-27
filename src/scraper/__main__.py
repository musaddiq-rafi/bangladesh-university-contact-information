"""CLI entry point — python -m scraper."""

import argparse
import logging
import sys

from scraper.config import LOG_DIR, LOG_FILE


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="scraper",
        description="BD University Contact Info Scraper",
    )
    parser.add_argument(
        "--step", type=int, choices=[1, 2, 3, 4, 5], default=None,
        help="Run only a specific phase (1-5)",
    )
    parser.add_argument(
        "--resume", action="store_true", default=True,
        help="Resume from cached results (default: True)",
    )
    parser.add_argument(
        "--no-resume", action="store_false", dest="resume",
        help="Ignore caches and start fresh",
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="OpenRouter API key (overrides .env)",
    )

    args = parser.parse_args()
    _setup_logging()

    logger = logging.getLogger("scraper.main")
    logger.info("BD University Scraper starting")

    from scraper.pipeline.orchestrator import run
    run(step=args.step, resume=args.resume, api_key=args.api_key)


if __name__ == "__main__":
    main()
