"""Logs in through the UI (credentials from .env) and exports the session token for Postman / Newman.

The website encrypts credentials with RSA in the browser before calling LoginClient, so the simplest
reliable way to obtain an API token is to reuse the session created by a real UI login.

Usage:  python scripts/get_api_token.py
Output: postman/CraftBet.env.local.json  (git-ignored - contains the token)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import settings  # noqa: E402
from pages.base_page import BasePage  # noqa: E402
from pages.components import Header  # noqa: E402
from utils.driver_factory import create_driver  # noqa: E402

READ_SESSION_JS = """
let token = localStorage.getItem('token'), user = null;
for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (/user/i.test(k)) { try { const v = JSON.parse(localStorage.getItem(k)); if (v && v.Token) user = v; } catch (e) {} }
}
return {token: (user && user.Token) || token, clientId: user && user.Id, currencyId: user && user.CurrencyId};
"""


def main() -> int:
    if not settings.HAS_CREDENTIALS:
        print("Set CRAFTBET_USERNAME and CRAFTBET_PASSWORD in .env first")
        return 1
    driver = create_driver()
    try:
        BasePage(driver).open("/home")
        header = Header(driver)
        header.open_login().fill(settings.USERNAME, settings.PASSWORD).submit()
        if not header.wait_until_logged_in():
            print("Login failed")
            return 2
        session = driver.execute_script(READ_SESSION_JS)
    finally:
        driver.quit()

    env_path = ROOT / "postman" / "CraftBet.postman_environment.json"
    env = json.loads(env_path.read_text(encoding="utf-8"))
    for var in env["values"]:
        if var["key"] in session and session[var["key"]]:
            var["value"] = str(session[var["key"]])
    out = ROOT / "postman" / "CraftBet.env.local.json"
    out.write_text(json.dumps(env, indent=2), encoding="utf-8")
    print(f"Session exported to {out.relative_to(ROOT)} (clientId={session.get('clientId')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
