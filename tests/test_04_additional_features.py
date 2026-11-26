"""Scenario 4 - Additional functionality available without deposits."""
import pytest
from selenium.webdriver.support.ui import WebDriverWait

from pages.casino_page import CasinoPage
from pages.components import Header
from pages.content_pages import AccountPage


@pytest.mark.functional
def test_language_switch(driver):
    header = Header(driver)
    header.switch_language("Русский", "ru")
    assert header.local_storage("lang") == "ru", "Selected language must be persisted"
    WebDriverWait(driver, 15).until(lambda d: header.find_visible(Header.LOGIN_BUTTON).text not in ("", "Log In"))
    login_caption = header.find_visible(Header.LOGIN_BUTTON).text
    assert login_caption == "Войти", f"Header captions must be translated, got '{login_caption}'"
    header.screenshot("language_russian")

    header.switch_language("English", "en")
    assert header.local_storage("lang") == "en"
    WebDriverWait(driver, 15).until(lambda d: header.find_visible(Header.LOGIN_BUTTON).text == "Log In")


@pytest.mark.functional
def test_casino_category_tabs(driver):
    casino = CasinoPage(driver).open()
    categories = casino.category_names()
    assert {"Top", "Slots", "Table Games"} <= set(categories), f"Unexpected categories: {categories}"

    lobby_url = casino.current_url
    visited = set()
    for name in ("Slots", "Table Games", "Top"):
        casino.select_category(name)
        assert casino.active_category() == name, f"'{name}' tab is not highlighted"
        assert casino.current_url != lobby_url, f"URL did not change for '{name}'"
        assert casino.wait_for_games() > 0, f"No games displayed in '{name}'"
        visited.add(casino.current_url)
        casino.screenshot(f"casino_category_{name}")
        casino.go_back_to_lobby()  # category view hides the tab bar and shows a 'Back' link
    assert len(visited) == 3, f"Each category must have its own URL, got {visited}"


@pytest.mark.functional
@pytest.mark.parametrize("query", ["book", "roulette"])
def test_game_search(driver, query):
    casino = CasinoPage(driver).open()
    results = casino.search(query)
    assert results, f"No results for '{query}'"
    mismatches = [c.name for c in results if query not in c.name.lower()]
    assert not mismatches, f"Results not matching '{query}': {mismatches[:5]}"
    casino.screenshot(f"search_{query}")


@pytest.mark.functional
def test_scroll_lobby_loads_more_games(driver):
    casino = CasinoPage(driver).open("group/7/1")
    before = casino.wait_for_games()
    for _ in range(4):
        casino.scroll_by(2500)
        casino.wait_for_page_ready()
    after = casino.wait_for_games(minimum=before + 1)  # times out if lazy loading adds nothing
    assert after > before, f"Scrolling must load more games (before={before}, after={after})"
    casino.screenshot("lobby_scrolled")


@pytest.mark.auth
@pytest.mark.functional
@pytest.mark.parametrize("tab", list(AccountPage.TABS))
def test_account_history_pages(logged_in_driver, tab):
    account = AccountPage(logged_in_driver).open_tab(tab)
    assert account.has_data_area(), f"'{tab}' page has neither data nor an empty-state block"
    assert not Header(logged_in_driver).is_login_button_visible(timeout=2), "Session lost on account page"
    account.screenshot(f"account_{tab}")


@pytest.mark.auth
@pytest.mark.functional
def test_add_and_remove_favorite_game(logged_in_driver):
    casino = CasinoPage(logged_in_driver).open()
    game = casino.demo_games(limit=1)[0]

    assert not casino.is_favorite(game.name), f"'{game.name}' is already a favorite - pick a clean account state"
    casino.toggle_favorite(game.name)
    casino.wait_favorite_state(game.name, True)
    casino.select_category("Favorites")
    assert casino.is_game_in_list(game.name), f"'{game.name}' was not added to Favorites"
    casino.screenshot("favorites_added")

    casino.toggle_favorite(game.name)
    casino.wait_favorite_state(game.name, False)  # heart icon switched back
    logged_in_driver.refresh()
    casino.wait_for_list_loaded()  # cards or empty-state rendered, not the loading gap
    assert not casino.is_game_in_list(game.name, timeout=5), f"'{game.name}' was not removed from Favorites"
