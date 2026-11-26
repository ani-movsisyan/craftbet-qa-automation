"""Scenario 3 - Casino games in DEMO mode only. Games without a Demo button (real money) are skipped."""
import pytest

from pages.casino_page import CasinoPage
from pages.game_page import GamePage

GAMES_TO_OPEN = 3


@pytest.mark.games
def test_open_several_demo_games(driver):
    casino = CasinoPage(driver).open()
    candidates = CasinoPage(driver).demo_games(limit=GAMES_TO_OPEN + 3)  # spare ones in case of region blocks
    assert candidates, "No demo games available in the lobby"

    opened = []
    for card in candidates:
        if len(opened) == GAMES_TO_OPEN:
            break
        casino.log.info("Opening demo game '%s' (%s)", card.name, card.provider)
        game = GamePage(driver).open(card.demo_href)
        game.wait_for_url_contains("/demo/")
        if game.is_region_blocked():
            game.log.warning("'%s' is not available in this region - skipped", card.name)
            continue

        game.wait_for_game_container()
        assert game.is_demo_mode(), f"'{card.name}' did not start in demo (fun) mode: {game.iframe_src()}"
        width, height = game.iframe_size()
        assert width >= game.MIN_WIDTH and height >= game.MIN_HEIGHT, f"Game container is too small: {width}x{height}"
        rendered = game.wait_game_rendered()
        game.screenshot(f"game_loaded_{card.name}")
        before = game.game_snapshot()

        actions = game.interact()
        assert game.iframe_still_alive(), f"'{card.name}' crashed after interaction"
        assert game.game_snapshot() != before, f"'{card.name}' did not react / redraw after interaction"
        assert "/demo/" in game.current_url, "Interaction must not switch the game to real mode"
        game.screenshot(f"game_after_interaction_{card.name}")
        opened.append((card.name, rendered, len(actions)))

    casino.log.info("Demo games verified: %s", opened)
    assert len(opened) >= 2, f"Expected at least 2 demo games to open, opened: {opened}"


@pytest.mark.games
def test_open_demo_game_from_lobby_by_click(driver):
    casino = CasinoPage(driver).open()
    card = casino.demo_games(limit=1)[0]
    casino.open_demo_by_name(card.name)
    game = GamePage(driver)
    game.wait_for_url_contains("/demo/")
    game.wait_for_game_container()
    assert game.is_demo_mode()
    game.screenshot(f"game_opened_by_click_{card.name}")

    driver.back()
    casino.wait_for_url_contains("group/7")
    assert casino.wait_for_games() > 0, "Lobby must be restored after leaving the game"
