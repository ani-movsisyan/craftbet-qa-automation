"""Scenario 2 - Website navigation: top menu, More menu, footer/info pages, logo."""
import pytest

from pages.components import Header
from pages.content_pages import ContentPage

TOP_MENU = [
    # (menu href, expected URL fragment, description)
    ("sport/prematch#/prematch", "sport/prematch", "Sport (pre-match)"),
    ("sport/live#/live", "sport/live", "Live betting"),
    ("group/7", "group/7", "Casino"),
    ("products/5", "products/5", "Live Casino"),
]

INFO_PAGES = [
    ("info/terms", "Terms and conditions"),
    ("info/privacy", "Privacy policy"),
    ("info/aml", "AML"),
    ("promotions", "Promotions"),
]


@pytest.mark.navigation
@pytest.mark.parametrize("href, fragment, title", TOP_MENU, ids=[m[2] for m in TOP_MENU])
def test_top_menu_navigation(driver, href, fragment, title):
    header = Header(driver)
    header.click_menu(href)
    url = header.wait_for_url_contains(fragment)
    page = ContentPage(driver)
    page.wait_for_content()
    assert not page.has_error_markers(), f"{title} page shows an error"
    assert header.is_login_button_visible(), "Header must stay rendered after navigation"
    page.screenshot(f"menu_{title}")
    header.log.info("'%s' opened: %s", title, url)


@pytest.mark.navigation
def test_more_menu_reveals_additional_sections(driver):
    header = Header(driver)
    items = header.open_more_menu()
    header.screenshot("more_menu_open")
    assert len(items) >= 2, f"'More' menu must list extra sections, got {items}"

    # Open a section from the drop-down and verify it loads.
    href = next((h for h in items if h.rstrip("/").endswith("promotions")), items[0])
    header.click_more_menu_item(href)
    header.wait_for_url_contains(href.split("#")[0].lstrip("/"))
    page = ContentPage(driver)
    page.wait_for_content()
    assert not page.has_error_markers()
    page.screenshot("more_menu_section")


@pytest.mark.navigation
@pytest.mark.parametrize("path, title", INFO_PAGES, ids=[p[1] for p in INFO_PAGES])
def test_info_pages_load(driver, path, title):
    page = ContentPage(driver).open(path)
    page.wait_for_url_contains(path)
    text = page.wait_for_content(min_chars=200)
    assert not page.has_error_markers(), f"{title} page shows an error"
    assert len(text) > 200, f"{title} page looks empty"
    page.screenshot(f"info_{title}")


@pytest.mark.navigation
def test_back_forward_and_logo_navigation(driver):
    header = Header(driver)
    header.click_menu("group/7")
    header.wait_for_url_contains("group/7")
    header.click_menu("products/5")
    header.wait_for_url_contains("products/5")

    driver.back()
    assert "group/7" in header.wait_for_url_contains("group/7"), "Browser Back must return to Casino"
    driver.forward()
    assert "products/5" in header.wait_for_url_contains("products/5"), "Browser Forward must return to Live Casino"

    header.click_logo()
    assert "/home" in header.wait_for_url_contains("/home"), "Logo must lead to the home page"
