import logging
from datetime import datetime

from config import settings

_LOG_FILE = settings.LOGS_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"
_configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes both to the console (via pytest) and to reports/logs/."""
    global _configured
    if not _configured:
        handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        root = logging.getLogger("craftbet")
        root.setLevel(logging.INFO)
        root.addHandler(handler)
        _configured = True
    return logging.getLogger(f"craftbet.{name}")
