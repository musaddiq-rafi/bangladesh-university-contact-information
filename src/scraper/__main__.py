"""CLI entry point - python -m scraper."""

import argparse
import logging
import sys
import time

from scraper.config import LOG_DIR, LOG_FILE



class _ConsoleFormatter(logging.Formatter):
    """Clean formatter for console output - no logger names, just the message."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[1;31m",
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        msg = record.getMessage()
        if record.levelno == logging.WARNING:
            return f"  {color}[!]{reset} {msg}"
        if record.levelno == logging.ERROR:
            return f"  {color}[x]{reset} {msg}"
        return f"  {color}[~]{reset} {msg}"


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(file_fmt))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_ConsoleFormatter())

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler],
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

    print(f"  BD University Scraper")
    print(f"  Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {'Resume from cache' if args.resume else 'Fresh run (ignoring cache)'}")
    if args.step:
        print(f"  Running: Phase {args.step} only")
    else:
        print(f"  Running: Full pipeline (Phases 1-5)")
    print()

    start = time.time()

    from scraper.pipeline.orchestrator import run
    run(step=args.step, resume=args.resume, api_key=args.api_key)

    elapsed = time.time() - start
    minutes, seconds = divmod(int(elapsed), 60)
    print(f"\n  Finished in {minutes}m {seconds}s")


if __name__ == "__main__":
    main()
