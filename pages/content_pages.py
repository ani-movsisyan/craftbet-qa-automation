"""Generic content pages (info, promotions, sport) and the logged-in account area."""
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage

ERROR_MARKERS = ("404", "page not found", "something went wrong", "server error")


class ContentPage(BasePage):
    """Any page whose correctness we validate by URL, rendered content and absence of error markers."""
    IFRAME = (By.TAG_NAME, "iframe")
    # The routed page component (everything except the header and footer).
    MAIN_CONTENT_JS = """
        const comps = [...document.querySelectorAll('.router_section > :not(router-outlet)')];
        const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        return {
            text: comps.map(c => (c.innerText || '').trim()).join('\\n'),
            height: Math.max(0, ...comps.map(c => c.getBoundingClientRect().height)),
            images: comps.reduce((n, c) => n + [...c.querySelectorAll('img')].filter(vis).length, 0),
            iframes: comps.reduce((n, c) => n + [...c.querySelectorAll('iframe')]
                                 .filter(f => f.getBoundingClientRect().height > 200).length, 0),
        };"""

    def main_content(self) -> dict:
        return self.driver.execute_script(self.MAIN_CONTENT_JS)

    def wait_for_content(self, min_chars: int = 50, timeout: int = 30) -> str:
        """Wait until the routed page component (not header/footer) shows real content:
        enough text, or visible images (e.g. Live Casino lobby) or an embedded app iframe (e.g. Sport)."""
        def ready(_):
            c = self.main_content()
            return c["height"] >= 150 and (len(c["text"]) >= min_chars or c["images"] > 0 or c["iframes"] > 0)

        WebDriverWait(self.driver, timeout).until(ready)
        return self.main_content()["text"]

    def has_error_markers(self) -> bool:
        lines = self.page_text().lower().split("\n")[:40]
        return any(m in line for line in lines for m in ERROR_MARKERS) or "404" in self.driver.title

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
