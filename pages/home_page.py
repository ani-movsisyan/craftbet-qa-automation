from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from pages.components import Header


class HomePage(BasePage):
    PATH = "/home"
    BANNER = (By.CSS_SELECTOR, "a.image-bar-item, [class*='banner' i] img, [class*='slider' i] img")
    GAME_LINKS = (By.CSS_SELECTOR, "a.game-btn")

    def __init__(self, driver):
        super().__init__(driver)
        self.header = Header(driver)

    def has_banners(self) -> bool:
        return len(self.driver.find_elements(*self.BANNER)) > 0

    def game_links_count(self) -> int:
        return len(self.driver.find_elements(*self.GAME_LINKS))
