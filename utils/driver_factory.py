"""Creates a configured WebDriver. Selenium Manager downloads the matching driver automatically."""
from selenium import webdriver

from config import settings
from utils.logger import get_logger

log = get_logger("driver")


def create_driver() -> webdriver.Remote:
    width, height = settings.WINDOW_SIZE
    if settings.BROWSER == "edge":
        options = webdriver.EdgeOptions()
    else:
        options = webdriver.ChromeOptions()

    if settings.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--disable-notifications")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument(f"--lang={settings.UI_LANGUAGE}")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.page_load_strategy = "normal"

    driver = webdriver.Edge(options=options) if settings.BROWSER == "edge" else webdriver.Chrome(options=options)
    driver.set_page_load_timeout(settings.PAGE_LOAD_TIMEOUT)
    driver.set_window_size(width, height)
    log.info("Started %s (headless=%s)", settings.BROWSER, settings.HEADLESS)
    return driver
