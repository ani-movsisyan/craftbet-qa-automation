"""Complete end-to-end user journey executed as one automated sequence:
login -> navigate sections -> search -> play demo game -> account history -> logout."""
import pytest

from pages.casino_page import CasinoPage
from pages.components import Header
from pages.content_pages import AccountPage, ContentPage
from pages.game_page import GamePage


@pytest.mark.e2e
@pytest.mark.auth
def test_complete_user_journey(logged_in_driver):
    driver = logged_in_driver
    header = Header(driver)
    steps = []

    # 1. Logged in (fixture) - verify state
    assert header.has_session_in_storage()
    steps.append("login")

    # 2. Navigate several sections
    for href, fragment in (("sport/prematch#/prematch", "sport/prematch"), ("products/5", "products/5")):
        header.click_menu(href)
        header.wait_for_url_contains(fragment)
        ContentPage(driver).wait_for_content()
        steps.append(f"open {fragment}")

    # 3. Casino: category + search
    casino = CasinoPage(driver).open()
    casino.select_category("Slots")
    steps.append("select Slots")
    casino.go_back_to_lobby()  # the category view hides the tab bar and the search field
    results = casino.search("book")
    assert results
    steps.append(f"search 'book' -> {len(results)} games")

    # 4. Open a demo game and interact
    demo = next(c for c in results if c.has_demo)
    game = GamePage(driver).open(demo.demo_href)
    game.wait_for_game_container()
    assert game.is_demo_mode()
    game.interact()
    game.screenshot("journey_game")
    steps.append(f"play demo '{demo.name}'")

    # 5. Account area
    account = AccountPage(driver).open_tab("bets history")
    assert account.has_data_area()
    steps.append("open bets history")

    # 6. Logout
    account.logout()
    assert header.is_login_button_visible(timeout=15)
    steps.append("logout")

    header.log.info("Journey completed: %s", " -> ".join(steps))
