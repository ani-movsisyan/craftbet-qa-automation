"""Game page: the provider game is rendered inside iframe#main-game-iframe."""
import time

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage

REGION_BLOCK_TEXTS = ("not available in your region", "restricted", "not allowed in your country")


class GamePage(BasePage):
    GAME_IFRAME = (By.CSS_SELECTOR, "iframe#main-game-iframe")
    CANVAS_OR_CONTENT = (By.CSS_SELECTOR, "canvas, video, iframe, #game, [id*='game' i], [class*='game' i]")
    MIN_WIDTH, MIN_HEIGHT = 600, 300

    def wait_for_game_container(self, timeout: int = 40):
        """Wait until the iframe exists, has a provider URL and is resized to a playable size."""
        iframe = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(self.GAME_IFRAME))
        WebDriverWait(self.driver, timeout).until(lambda d: (iframe.get_attribute("src") or "").startswith("http"))
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: iframe.size["width"] >= self.MIN_WIDTH and iframe.size["height"] >= self.MIN_HEIGHT
            )
        except TimeoutException:
            self.log.warning("Game container stayed small: %s", iframe.size)
        return iframe

    def iframe_src(self) -> str:
        return self.find(self.GAME_IFRAME).get_attribute("src") or ""

    def iframe_size(self) -> tuple[int, int]:
        size = self.find(self.GAME_IFRAME).size
        return size["width"], size["height"]

    def is_demo_mode(self) -> bool:
        src = self.iframe_src().lower()
        return "/demo/" in self.current_url and ("mode=fun" in src or "demo" in src or "fun" in src)

    def is_region_blocked(self) -> bool:
        text = self.page_text().lower()
        return any(t in text for t in REGION_BLOCK_TEXTS)

    def wait_game_rendered(self, timeout: int = 45, settle: int = 6) -> str:
        """Switch into the game iframe, wait for rendered content (canvas / video / DOM), then let the
        provider's loading screen finish. Returns the tag that was found."""
        self.driver.switch_to.frame(self.find(self.GAME_IFRAME))
        try:
            element = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(self.CANVAS_OR_CONTENT))
            tag = element.tag_name
        finally:
            self.driver.switch_to.default_content()
        time.sleep(settle)  # providers show their own loading bar after the canvas appears
        return tag

    def game_snapshot(self) -> bytes:
        return self.find(self.GAME_IFRAME).screenshot_as_png

    def _click_at(self, iframe, x_ratio: float, y_ratio: float, label: str, actions: list[str]):
        w, h = iframe.size["width"], iframe.size["height"]
        # move_to_element_with_offset is relative to the element centre in Selenium 4
        ActionChains(self.driver).move_to_element_with_offset(
            iframe, int(w * (x_ratio - 0.5)), int(h * (y_ratio - 0.5))
        ).click().perform()
        actions.append(label)
        time.sleep(1.5)

    def interact(self) -> list[str]:
        """Basic demo-mode interactions: dismiss intro screens (Play / Continue buttons are usually in the
        lower-middle part), then press SPACE - the standard 'spin' key, which spends only demo credits."""
        actions: list[str] = []
        iframe = self.find(self.GAME_IFRAME)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", iframe)
        time.sleep(1)
        self._click_at(iframe, 0.5, 0.5, "click centre (focus game)", actions)
        self._click_at(iframe, 0.5, 0.86, "click Play/Continue zone", actions)
        self._click_at(iframe, 0.5, 0.80, "click Play/Continue zone (alt.)", actions)
        for _ in range(2):
            ActionChains(self.driver).send_keys(Keys.SPACE).perform()
            actions.append("press SPACE (spin with demo credits)")
            time.sleep(3)
        self.log.info("Game interactions performed: %s", actions)
        return actions

    def iframe_still_alive(self) -> bool:
        try:
            self.driver.switch_to.frame(self.find(self.GAME_IFRAME))
            return self.driver.execute_script("return document.readyState") in ("interactive", "complete")
        except (TimeoutException, WebDriverException):
            return False
        finally:
            self.driver.switch_to.default_content()
