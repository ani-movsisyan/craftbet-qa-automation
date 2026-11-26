"""Central place for all run-time settings. Values come from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "y"}


BASE_URL = os.getenv("BASE_URL", "https://craftbet.com").rstrip("/")
BROWSER = os.getenv("BROWSER", "chrome").lower()
HEADLESS = _bool("HEADLESS", False)
UI_LANGUAGE = os.getenv("UI_LANGUAGE", "en")
EXPLICIT_TIMEOUT = int(os.getenv("EXPLICIT_TIMEOUT", "25"))
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
WINDOW_SIZE = (1440, 900)

USERNAME = os.getenv("CRAFTBET_USERNAME", "")
PASSWORD = os.getenv("CRAFTBET_PASSWORD", "")
HAS_CREDENTIALS = bool(USERNAME and PASSWORD)

REPORTS_DIR = ROOT_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
LOGS_DIR = REPORTS_DIR / "logs"
for _d in (SCREENSHOTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
