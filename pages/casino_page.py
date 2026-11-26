"""Casino lobby: category tabs, game search, game cards with Demo / Real buttons."""
from dataclasses import dataclass

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage
from pages.components import Header


@dataclass
class GameCard:
    name: str
    provider: str
    demo_href: str | None
    real_href: str | None

    @property
    def has_demo(self) -> bool:
        return bool(self.demo_href)


class CasinoPage(BasePage):
    PATH = "/group/7"
    CATEGORY_TABS = (By.CSS_SELECTOR, ".nav-bar.casino-menu-nav-bar li")
    SEARCH_INPUT = (By.CSS_SELECTOR, "input[placeholder='Search your game...']")
    GAME_CARD = (By.CSS_SELECTOR, ".casino-game")
    GAME_NAME = (By.CSS_SELECTOR, ".hidden-game-name")
    GAME_PROVIDER = (By.CSS_SELECTOR, ".title")
    DEMO_BUTTON = (By.CSS_SELECTOR, "a.game-btn_demo")
    REAL_BUTTON = (By.CSS_SELECTOR, "a.game-btn_real")
    FAVORITE_ICON = (By.CSS_SELECTOR, ".icon-star-info")

    def __init__(self, driver):
        super().__init__(driver)
        self.header = Header(driver)

    def open(self, path: str | None = None):
        super().open(path)
        self.wait_for_games()
        return self

    def wait_for_games(self, minimum: int = 1, timeout: int = 30) -> int:
        WebDriverWait(self.driver, timeout).until(
            lambda d: len([c for c in d.find_elements(*self.GAME_CARD) if self._displayed(c)]) >= minimum
        )
        return len(self.visible_cards())

    def visible_cards(self) -> list[WebElement]:
        return [c for c in self.driver.find_elements(*self.GAME_CARD) if self._displayed(c)]

    def read_cards(self) -> list[GameCard]:
        """Collect card data in one JS call - much faster and less flaky than per-element lookups."""
        raw = self.driver.execute_script("""
            return [...document.querySelectorAll('.casino-game')]
              .filter(c => c.getBoundingClientRect().width > 0)
              .map(c => ({
                 name: (c.querySelector('.hidden-game-name')?.textContent || '').trim(),
                 provider: (c.querySelector('.title')?.textContent || '').trim(),
                 demo: c.querySelector('a.game-btn_demo')?.getAttribute('href') || null,
                 real: c.querySelector('a.game-btn_real')?.getAttribute('href') || null }));""")
        return [GameCard(r["name"], r["provider"], r["demo"], r["real"]) for r in raw]

    # ---------- categories ----------
    def category_names(self) -> list[str]:
        return [t.text.strip() for t in self.find_all_visible(self.CATEGORY_TABS) if t.text.strip()]

    def select_category(self, name: str):
        self.log.info("Select casino category '%s'", name)
        tab = (By.XPATH, f"//*[contains(@class,'nav-bar') and contains(@class,'casino-menu-nav-bar')]"
                         f"//li[normalize-space()='{name}']")
        self.click(tab)
        WebDriverWait(self.driver, 10).until(lambda d: self.active_category() == name)
        self.wait_for_page_ready()

    BACK_LINK = (By.XPATH, "//*[self::a or self::div or self::span or self::button][normalize-space()='Back']")

    def go_back_to_lobby(self):
        back = [e for e in self.driver.find_elements(*self.BACK_LINK) if self._displayed(e)]
        assert back, "'Back' link is not displayed in the category view"
        self.click(back[-1])
        WebDriverWait(self.driver, 15).until(
            lambda d: any(self._displayed(t) for t in d.find_elements(*self.CATEGORY_TABS))
        )

    def active_category(self) -> str:
        # textContent instead of .text: the tab bar may be scrolled horizontally out of view.
        return self.driver.execute_script("""
            const a = document.querySelector('.nav-bar.casino-menu-nav-bar li.active');
            return a ? a.textContent.trim() : '';""")

    # ---------- search ----------
    def search(self, text: str) -> list[GameCard]:
        self.log.info("Search game '%s'", text)
        field = self.type(self.SEARCH_INPUT, text)
        field.send_keys(Keys.ENTER)
        self.wait_for_url_contains(f"pattern={text}")
        WebDriverWait(self.driver, 20).until(
            lambda d: self.read_cards() and all(text.lower() in c.name.lower() for c in self.read_cards()[:5])
        )
        return self.read_cards()

    # ---------- games ----------
    def demo_games(self, limit: int = 3) -> list[GameCard]:
        """Return cards that offer a free Demo mode. Real-money-only games are skipped."""
        cards = self.read_cards()
        demo = [c for c in cards if c.has_demo and c.name]
        skipped = len(cards) - len(demo)
        self.log.info("Found %s cards: %s with demo mode, %s real-money only (skipped)", len(cards), len(demo), skipped)
        return demo[:limit]

    def open_demo_by_name(self, name: str):
        card = self._card(name)
        self.hover(card)
        demo = card.find_element(*self.DEMO_BUTTON)
        self.click(demo)

    def _card(self, name: str) -> WebElement:
        return self.driver.find_element(
            By.XPATH, f"//*[contains(@class,'casino-game')][.//*[contains(@class,'hidden-game-name')][normalize-space()='{name}']]"
        )

    def is_favorite(self, name: str) -> bool:
        """Heart icon state: Font Awesome renders an outlined heart ('far') or a filled one ('fas')."""
        icon = self._card(name).find_element(*self.FAVORITE_ICON)
        svg = icon.find_elements(By.CSS_SELECTOR, "svg")
        prefix = svg[0].get_attribute("data-prefix") if svg else ""
        classes = icon.get_attribute("class") or ""
        return prefix == "fas" or "active" in classes or "selected" in classes

    def wait_favorite_state(self, name: str, expected: bool, timeout: int = 10):
        WebDriverWait(self.driver, timeout).until(lambda d: self.is_favorite(name) == expected)

    def wait_for_list_loaded(self, timeout: int = 20):
        """Wait until the game list has rendered: cards, or an empty-state message - not the loading gap."""
        self.wait_for_page_ready()
        WebDriverWait(self.driver, timeout).until(lambda d: self.read_cards() or d.execute_script("""
            const s = document.querySelector('.router_section');
            return !!s && /no (games|favorites|results)|empty|nothing/i.test(s.innerText || '');"""))

    def toggle_favorite(self, name: str) -> WebElement:
        card = self._card(name)
        self.hover(card)
        icon = card.find_element(*self.FAVORITE_ICON)
        self.driver.execute_script("arguments[0].click();", icon)
        return icon

    def is_game_in_list(self, name: str, timeout: int = 15) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(lambda d: any(c.name == name for c in self.read_cards()))
            return True
        except TimeoutException:
            return False
