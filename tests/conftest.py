import base64
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from pages.base_page import BasePage  # noqa: E402
from pages.components import Header  # noqa: E402
from utils.driver_factory import create_driver  # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("conftest")


@pytest.fixture
def driver(request):
    drv = create_driver()
    try:
        # Open the site once and fix the UI language, so locators based on English captions are stable.
        page = BasePage(drv).open("/home")
        drv.execute_script("window.localStorage.setItem('lang', arguments[0]);", settings.UI_LANGUAGE)
        drv.refresh()
        page.wait_for_page_ready()
    except Exception:
        drv.quit()  # do not leave the browser running when setup fails
        raise
    log.info("===== START %s =====", request.node.name)
    yield drv
    log.info("===== END %s =====", request.node.name)
    drv.quit()


@pytest.fixture
def logged_in_driver(driver):
    """Driver with an authenticated session (test account from .env)."""
    if not settings.HAS_CREDENTIALS:
        pytest.skip("Test account credentials are not set (CRAFTBET_USERNAME / CRAFTBET_PASSWORD in .env)")
    header = Header(driver)
    modal = header.open_login()
    modal.fill(settings.USERNAME, settings.PASSWORD).submit()
    assert header.wait_until_logged_in(), f"Login failed. Visible message: '{modal.visible_error_text()}'"
    log.info("Logged in as test user")
    return driver


def pytest_collection_modifyitems(config, items):
    skip_auth = pytest.mark.skip(reason="Credentials not provided in .env")
    for item in items:
        if "auth" in item.keywords and not settings.HAS_CREDENTIALS:
            item.add_marker(skip_auth)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach a screenshot to the HTML report for every failed test (and save it to reports/screenshots)."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    drv = item.funcargs.get("logged_in_driver") or item.funcargs.get("driver")
    if drv is None:
        return
    status = "FAILED" if report.failed else "PASSED"
    try:
        path = BasePage(drv).screenshot(f"{status}_{item.name}")
    except Exception as exc:  # browser may already be gone
        log.warning("Could not take screenshot: %s", exc)
        return
    extras = getattr(report, "extras", [])
    try:
        from pytest_html import extras as html_extras
        encoded = base64.b64encode(Path(path).read_bytes()).decode()
        extras.append(html_extras.png(encoded, name=f"{status} - {item.name}"))
    except ImportError:
        pass
    report.extras = extras
