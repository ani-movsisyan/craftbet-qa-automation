"""Generic content pages (info, promotions, sport) and the logged-in account area."""
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage

ERROR_MARKERS = ("404", "page not found", "something went wrong", "server error")


class ContentPage(BasePage):
    """Any page whose correctness we validate by URL, rendered content and absence of error markers."""
    IFRAME = (By.TAG_NAME, "iframe")

    def wait_for_content(self, min_chars: int = 50, timeout: int = 30) -> str:
        WebDriverWait(self.driver, timeout).until(lambda d: len(self.page_text().strip()) >= min_chars)
        return self.page_text()

    def has_error_markers(self) -> bool:
        main_text = self.page_text().lower()
        return any(m in main_text.split("\n")[:40] for m in ERROR_MARKERS) or "404" in self.driver.title

    def has_visible_iframe(self, timeout: int = 20) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: any(f.is_displayed() and f.size["height"] > 200 for f in d.find_elements(*self.IFRAME))
            )
            return True
        except TimeoutException:
            return False


class AccountPage(BasePage):
    """Logged-in client area: /user/1/<tab>."""
    TABS = {
        "bets history": "user/1/history",
        "transactions": "user/1/transactions",
        "payments": "user/1/payments",
        "bonuses": "user/1/bonuses",
    }
    LOGOUT = (By.XPATH, "//*[self::a or self::button or self::div or self::span]"
                        "[translate(normalize-space(), 'LOGUT ', 'logut')='logout']")
    TABLE_OR_EMPTY = (By.CSS_SELECTOR, "table, [class*='history' i], [class*='no-data' i], [class*='empty' i], [class*='list' i]")

    def open_tab(self, tab: str):
        self.open(self.TABS[tab])
        self.wait_for_url_contains(self.TABS[tab].split("/")[-1])
        return self

    def has_data_area(self) -> bool:
        return self.is_visible(self.TABLE_OR_EMPTY, timeout=15)

    def logout(self):
        self.log.info("Logout")
        buttons = [e for e in self.driver.find_elements(*self.LOGOUT) if self._displayed(e)]
        if not buttons:
            self.open(self.TABS["bets history"])
            buttons = [e for e in self.driver.find_elements(*self.LOGOUT) if self._displayed(e)]
        assert buttons, "Logout control was not found"
        self.click(buttons[-1])
        # Some skins ask for confirmation.
        confirm = (By.XPATH, "//button[normalize-space()='Yes' or normalize-space()='OK' or normalize-space()='Confirm']")
        if self.is_visible(confirm, timeout=3):
            self.click(confirm)
        self.wait_for_page_ready()
