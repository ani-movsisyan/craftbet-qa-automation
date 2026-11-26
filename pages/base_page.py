"""Common helpers shared by every page object: explicit waits, safe clicks, screenshots."""
import re
import time
from datetime import datetime

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from utils.logger import get_logger

Locator = tuple[str, str]


class BasePage:
    PATH = "/"
    LOADER = (By.CSS_SELECTOR, ".loader")

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.log = get_logger(self.__class__.__name__)
        self.wait = WebDriverWait(
            driver,
            settings.EXPLICIT_TIMEOUT,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    # ---------- navigation ----------
    def open(self, path: str | None = None):
        url = f"{settings.BASE_URL}/{(path if path is not None else self.PATH).lstrip('/')}"
        self.log.info("Open %s", url)
        self.driver.get(url)
        self.wait_for_page_ready()
        return self

    def wait_for_page_ready(self, timeout: int | None = None):
        """Wait for document.readyState == complete and for the SPA loader to disappear."""
        wait = WebDriverWait(self.driver, timeout or settings.EXPLICIT_TIMEOUT)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        try:
            wait.until(EC.invisibility_of_element_located(self.LOADER))
        except TimeoutException:
            self.log.warning("Loader is still visible after %ss", timeout or settings.EXPLICIT_TIMEOUT)
        return self

    def wait_for_url_contains(self, fragment: str, timeout: int | None = None) -> str:
        WebDriverWait(self.driver, timeout or settings.EXPLICIT_TIMEOUT).until(EC.url_contains(fragment))
        return self.driver.current_url

    def wait_for_url_matches(self, pattern: str, timeout: int | None = None) -> str:
        WebDriverWait(self.driver, timeout or settings.EXPLICIT_TIMEOUT).until(
            lambda d: re.search(pattern, d.current_url)
        )
        return self.driver.current_url

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    # ---------- element helpers ----------
    def find(self, locator: Locator) -> WebElement:
        return self.wait.until(EC.presence_of_element_located(locator))

    def find_visible(self, locator: Locator, timeout: int | None = None) -> WebElement:
        wait = WebDriverWait(self.driver, timeout) if timeout else self.wait
        return wait.until(EC.visibility_of_element_located(locator))

    def find_all_visible(self, locator: Locator) -> list[WebElement]:
        self.wait.until(EC.visibility_of_any_elements_located(locator))
        return [e for e in self.driver.find_elements(*locator) if self._displayed(e)]

    def is_visible(self, locator: Locator, timeout: int = 3) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def wait_invisible(self, locator: Locator, timeout: int | None = None) -> bool:
        return WebDriverWait(self.driver, timeout or settings.EXPLICIT_TIMEOUT).until(
            EC.invisibility_of_element_located(locator)
        )

    def click(self, target: Locator | WebElement, retries: int = 3):
        """Click with explicit wait; falls back to a JS click if an overlay intercepts it."""
        for attempt in range(1, retries + 1):
            try:
                element = target if isinstance(target, WebElement) else self.wait.until(
                    EC.element_to_be_clickable(target)
                )
                self.scroll_into_view(element)
                element.click()
                return element
            except ElementClickInterceptedException:
                self.log.info("Click intercepted (attempt %s) - using JS click", attempt)
                element = target if isinstance(target, WebElement) else self.find(target)
                self.driver.execute_script("arguments[0].click();", element)
                return element
            except StaleElementReferenceException:
                if attempt == retries or isinstance(target, WebElement):
                    raise
                time.sleep(0.5)

    def type(self, locator: Locator, text: str, clear: bool = True):
        element = self.find_visible(locator)
        if clear:
            element.clear()
        element.send_keys(text)
        return element

    def hover(self, element: WebElement):
        self.scroll_into_view(element)
        ActionChains(self.driver).move_to_element(element).perform()

    def scroll_into_view(self, element: WebElement):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

    def scroll_by(self, pixels: int):
        self.driver.execute_script("window.scrollBy(0, arguments[0]);", pixels)

    def page_text(self) -> str:
        return self.driver.find_element(By.TAG_NAME, "body").text

    def local_storage(self, key: str):
        return self.driver.execute_script("return window.localStorage.getItem(arguments[0]);", key)

    def html_lang(self) -> str:
        return self.driver.execute_script("return document.documentElement.lang;")

    # ---------- evidence ----------
    def screenshot(self, name: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:80]
        path = settings.SCREENSHOTS_DIR / f"{datetime.now():%H%M%S}_{safe}.png"
        self.driver.save_screenshot(str(path))
        self.log.info("Screenshot saved: %s", path.name)
        return str(path)

    @staticmethod
    def _displayed(element: WebElement) -> bool:
        try:
            return element.is_displayed()
        except StaleElementReferenceException:
            return False
