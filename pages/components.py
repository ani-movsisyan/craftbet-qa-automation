"""Reusable UI components that appear on every page: header, top menu, language selector, login modal."""
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage


class Header(BasePage):
    LOGO = (By.CSS_SELECTOR, "a.general-menu_item.image-style2[href='/home']")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "button.global_login-btn")
    REGISTER_BUTTON = (By.CSS_SELECTOR, "button.global_register-btn")
    LANGUAGE_DROPDOWN = (By.CSS_SELECTOR, ".global-language .dropdown-style1-type-Dpd")
    LANGUAGE_ITEMS = (By.CSS_SELECTOR, ".global-language .custom_dropdown_list_item")
    MORE_MENU = (By.CSS_SELECTOR, "li.header-menu-more > a.general-menu_item_link")
    BALANCE = (By.CSS_SELECTOR, "[class*='balance' i]")
    # The top menu links are rendered from menu.json; the href is the most stable attribute.
    MENU_LINK = "a.header-menu-item-style1[href='{href}']"

    def menu_link(self, href: str):
        return By.CSS_SELECTOR, self.MENU_LINK.format(href=href)

    def click_menu(self, href: str):
        self.log.info("Click top menu item '%s'", href)
        self.click(self.menu_link(href))
        self.wait_for_page_ready()

    def click_logo(self):
        self.click(self.LOGO)
        self.wait_for_page_ready()

    def open_more_menu(self) -> list[str]:
        """Open the 'More' item (menu entries that do not fit the width) and return sub-menu hrefs."""
        more = self.find_all_visible(self.MORE_MENU)[0]  # the first 'More' in DOM belongs to a hidden panel
        submenu = (By.CSS_SELECTOR, "li.header-menu-more .general-menu-sub-menu a[href]")

        def visible_links(d):
            return [e for e in d.find_elements(*submenu) if e.is_displayed()]

        self.hover(more)
        try:
            WebDriverWait(self.driver, 3).until(visible_links)
        except TimeoutException:
            self.click(more)
            WebDriverWait(self.driver, 5).until(visible_links)
        return [e.get_dom_attribute("href") for e in visible_links(self.driver)]

    def click_more_menu_item(self, href: str):
        self.open_more_menu()
        self.click((By.CSS_SELECTOR, f"li.header-menu-more .general-menu-sub-menu a[href='{href}']"))
        self.wait_for_page_ready()

    # ---------- language ----------
    def switch_language(self, language_name: str, language_code: str):
        self.log.info("Switch language to '%s'", language_name)
        self.click(self.LANGUAGE_DROPDOWN)
        item = (By.XPATH, f"//*[contains(@class,'custom_dropdown_list_item')]"
                          f"[.//span[contains(@class,'lang_name')][normalize-space()='{language_name}']]")
        self.click(self.find_visible(item))
        # Changing the language reloads the application - wait for the new <html lang> and a ready page.
        WebDriverWait(self.driver, 30).until(lambda d: self.html_lang() == language_code)
        self.wait_for_page_ready()

    # ---------- auth state ----------
    def open_login(self) -> "LoginModal":
        self.click(self.LOGIN_BUTTON)
        modal = LoginModal(self.driver)
        modal.find_visible(LoginModal.USERNAME)
        return modal

    def is_balance_visible(self, timeout: int = 10) -> bool:
        """Any visible balance element - the first DOM match may be a hidden (mobile) duplicate."""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: any(self._displayed(e) for e in d.find_elements(*self.BALANCE))
            )
            return True
        except TimeoutException:
            return False

    def is_login_button_visible(self, timeout: int = 3) -> bool:
        return self.is_visible(self.LOGIN_BUTTON, timeout)

    def has_session_in_storage(self) -> bool:
        """The SPA stores the authenticated client (with its Token) in localStorage after login."""
        return bool(self.driver.execute_script("""
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i), v = localStorage.getItem(k) || '';
                if (k === 'token' && v && v !== 'null') return true;
                if (/user/i.test(k) && /"Token"\\s*:\\s*"[^"]+"/.test(v)) return true;
            }
            return false;"""))

    def wait_until_logged_in(self, timeout: int = 30) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.invisibility_of_element_located(self.LOGIN_BUTTON))
            WebDriverWait(self.driver, 10).until(lambda d: self.has_session_in_storage())
            return True
        except TimeoutException:
            return False


class LoginModal(BasePage):
    USERNAME = (By.CSS_SELECTOR, "input[name='ClientIdentifier']")
    PASSWORD = (By.CSS_SELECTOR, "input[name='Password']")
    SUBMIT = (By.CSS_SELECTOR, "button.login_btn")
    ERROR = (By.CSS_SELECTOR, "[class*='error' i]:not(:empty), [class*='invalid-feedback' i]:not(:empty)")

    def fill(self, username: str, password: str):
        self.type(self.USERNAME, username)
        self.type(self.PASSWORD, password)
        return self

    def submit(self):
        self.log.info("Submit login form")
        self.click(self.SUBMIT)

    def is_submit_enabled(self) -> bool:
        button = self.find_visible(self.SUBMIT)
        return button.is_enabled() and "not_active" not in (button.get_attribute("class") or "")

    def is_open(self, timeout: int = 3) -> bool:
        return self.is_visible(self.USERNAME, timeout)

    def visible_error_text(self) -> str:
        texts = [e.text.strip() for e in self.driver.find_elements(*self.ERROR) if self._displayed(e)]
        return " | ".join(t for t in texts if t)
