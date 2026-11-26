"""Scenario 1 - Website access & authentication."""
import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from pages.components import Header
from pages.content_pages import AccountPage
from pages.home_page import HomePage


@pytest.mark.smoke
def test_website_opens(driver):
    home = HomePage(driver)
    # The Angular app sets <title> after bootstrap, so wait for it instead of reading it immediately.
    try:
        WebDriverWait(driver, 20).until(lambda d: "craftbet" in d.title.lower())
    except TimeoutException:
        pass
    assert "craftbet" in driver.title.lower(), f"Unexpected title: {driver.title}"
    assert "/home" in home.current_url
    assert home.header.is_login_button_visible(), "Guest user must see the Log In button"
    assert home.is_visible(Header.REGISTER_BUTTON), "Sign Up button is not visible"
    assert home.html_lang() == "en"
    home.screenshot("home_page_guest")


@pytest.mark.smoke
def test_login_form_opens_and_validates_empty_fields(driver):
    header = Header(driver)
    modal = header.open_login()
    assert modal.is_visible(modal.USERNAME) and modal.is_visible(modal.PASSWORD)
    assert modal.find(modal.PASSWORD).get_attribute("type") == "password", "Password must be masked"
    assert not modal.is_submit_enabled(), "Submit must be inactive while the form is empty"
    modal.screenshot("login_form_empty")


@pytest.mark.negative
def test_login_with_invalid_credentials_is_rejected(driver):
    header = Header(driver)
    modal = header.open_login()
    modal.fill("qa_nonexistent_user_000", "Invalid_Pass_123").submit()
    assert not header.wait_until_logged_in(timeout=10), "Invalid credentials must not create a session"
    assert header.is_login_button_visible(), "User must stay a guest"
    modal.screenshot("login_invalid_credentials")


@pytest.mark.auth
def test_successful_login(logged_in_driver):
    header = Header(logged_in_driver)
    assert not header.is_login_button_visible(timeout=2), "Log In button must disappear after login"
    assert header.has_session_in_storage(), "Session token must be stored by the application"
    assert header.is_balance_visible(timeout=10), "Balance widget must be shown for a logged-in client"
    header.screenshot("logged_in_home")


@pytest.mark.auth
def test_session_persists_after_refresh_and_logout(logged_in_driver):
    header = Header(logged_in_driver)
    logged_in_driver.refresh()
    header.wait_for_page_ready()
    assert not header.is_login_button_visible(timeout=5), "Session must survive a page refresh"

    AccountPage(logged_in_driver).logout()
    assert header.is_login_button_visible(timeout=15), "Log In button must return after logout"
    header.screenshot("after_logout")
