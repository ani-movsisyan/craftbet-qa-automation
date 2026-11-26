# Test scenarios, validations and challenges

## Part 1 – Web UI automation (Selenium + Pytest)

### Approach

* **Page Object Model** – locators and actions live in `pages/`, tests only describe the scenario and assertions.
* **Explicit waits only** (`WebDriverWait`): `document.readyState`, disappearance of the SPA loader,
  URL changes, element visibility / clickability, iframe size, etc. No implicit waits, no blind sleeps
  except a short settle time inside games (canvas animations have no DOM signal).
* **Error handling** – click falls back to a JS click when an overlay (chat widget) intercepts it;
  stale elements are retried; `pytest-rerunfailures` re-runs a failed test once to absorb network flakiness;
  a screenshot is attached to the HTML report for every test (passed or failed).
* **Stable UI language** – the site opens in Armenian by default; the fixture sets English via the
  application's own `localStorage['lang']`, so captions used in locators are predictable.
* **Data-driven** – `pytest.mark.parametrize` for menu items, info pages, search queries, account tabs.

### Scenarios

| # | Test | Steps | Validation points |
|---|------|-------|-------------------|
| **1. Access & authentication** ||||
| 1.1 | `test_website_opens` | Open craftbet.com | title contains *CraftBet*, URL `/home`, Log In + Sign Up visible, `<html lang="en">` |
| 1.2 | `test_login_form_opens_and_validates_empty_fields` | Click **Log In** | username/password inputs visible, password is masked, submit inactive while form is empty |
| 1.3 | `test_login_with_invalid_credentials_is_rejected` *(negative)* | Submit unknown user | no session is created, Log In button stays |
| 1.4 | `test_successful_login` *(auth)* | Log in with the test account | Log In button disappears, session token stored by the app, balance widget shown |
| 1.5 | `test_session_persists_after_refresh_and_logout` *(auth)* | Refresh, then log out | session survives F5, Log In button returns after logout |
| **2. Navigation** ||||
| 2.1 | `test_top_menu_navigation[...]` | Click Sport, Live, Casino, Live Casino in the top menu | URL fragment, the routed page body (without header/footer) shows text, images or the embedded sportsbook iframe, no error markers, header still present |
| 2.2 | `test_more_menu_reveals_additional_sections` | Hover / click **More**, open *Skill Games* from the drop-down | drop-down lists ≥ 2 sections, target page body has content |
| 2.3 | `test_info_pages_load[...]` | Open Terms, Privacy, AML, Promotions | URL, ≥ 200 chars in the page body (header/footer excluded), no 404 / error. **Promotions is marked xfail: its body is empty for guests (found by this test)** |
| 2.4 | `test_back_forward_and_logo_navigation` | Casino → Live Casino → Back → Forward → Logo | browser history works in the SPA, logo leads to `/home` |
| **3. Game interaction (demo only)** ||||
| 3.1 | `test_open_several_demo_games` | Read lobby cards, keep only those with **Demo**, open 3 of them | URL `/demo/`, iframe `#main-game-iframe` loaded with fun-mode provider URL, container ≥ 600×300, **game draws on a canvas/video** inside the iframe (nested provider iframes searched too), **game redraws after interaction** (iframe snapshot before ≠ after), still in demo after interaction. Region-blocked games, games the platform could not launch and provider error screens (e.g. *Your stall disabled*) are logged and skipped |
| | | Interactions: focus click, click Play/Continue zone, SPACE ×2 (spin with demo credits) | iframe document still alive (game did not crash) |
| 3.2 | `test_open_demo_game_from_lobby_by_click` | Hover a card, click **Demo**, then browser Back | game opens in demo mode, lobby restored with games |
| **4. Additional functionality** ||||
| 4.1 | `test_language_switch` | Switch EN → Русский → EN with the language selector | `<html lang>` and `localStorage.lang` change, header captions translated (`Войти`) and back |
| 4.2 | `test_casino_category_tabs` | Open Slots, Table Games, Top; use **Back** after each | active tab highlighted, unique URL per category, games displayed |
| 4.3 | `test_game_search[book / roulette]` | Type a query in *Search your game…* | URL `?pattern=`, every result name contains the query |
| 4.4 | `test_scroll_lobby_loads_more_games` | Scroll a category | more games appear than before scrolling (lazy loading works) |
| 4.5 | `test_account_history_pages[...]` *(auth)* | Bets history, Transactions, Payments, Bonuses | page opens, data table or empty-state block present, session kept |
| 4.6 | `test_add_and_remove_favorite_game` *(auth)* | Heart a game → *Favorites* tab → un-heart → refresh | heart icon state changes both ways, game appears in Favorites, after reload (list fully rendered) it is gone |
| **5. End-to-end journey** ||||
| 5.1 | `test_complete_user_journey` *(auth)* | login → Sport → Live Casino → Casino/Slots → Back to lobby → search → demo game + interaction → bets history → logout | each step asserted; journey summary written to the log |

### Challenges and how they were solved

| Challenge | Solution |
|-----------|----------|
| Angular SPA – content is rendered after `readyState=complete` | waits on loader invisibility, URL and specific elements instead of page load |
| Site opens in Armenian, translations are partially missing (`Header.African Sport`) | language fixed to EN via the app's own `localStorage['lang']`; locators use `href` / classes where captions are unreliable |
| Duplicate hidden elements (two *More* menus – one in a hidden panel) | locate all and take the first **visible** one |
| Category view hides the tab bar and shows *Back* | test models the real flow: select → verify → Back |
| Games are cross-origin iframes rendered on `<canvas>` – no DOM to assert on | verify iframe URL (fun mode), size, content presence; validate interaction by comparing iframe snapshots before/after |
| Providers load at different speed; the iframe is resized after load (Pragmatic Play starts at 150 px) | wait until the container reaches a playable size + settle time for the provider's own loading bar |
| Some games are *real-money only* or *Not available in your region* | cards without a Demo button are filtered out and logged; region-blocked games are skipped and the next demo game is taken |
| Chat widget may overlay buttons | click falls back to a JS click on `ElementClickInterceptedException` |
| Test-account credentials must not be committed | `.env` (git-ignored) + `.env.example`; tests needing a session are skipped when it is absent |

---

## Part 2 – API testing (Postman)

### What was discovered

No public API documentation was provided, so the API was derived from the website itself
(network traffic + the Angular bundle):

* Base URL: `https://websitewebapi.craftbet.com/{partnerId}/api/Main/…`, `partnerId = 1`.
* It is an **RPC-style API**: most reads are `POST` requests; client data goes through
  `POST /ApiRequest` with `Controller` + `Method` + `Token` + `ClientId` + `RequestData` (JSON string).
  There is also a real `GET` endpoint (`getbets`) used by the *Wins* widget.
* HTTP status is always `200`; the business result is in `ResponseCode` (`0` = success,
  `28` = session not found, `138` = RestrictedDestination).
* Requests are accepted only with `Origin: https://craftbet.com` – the collection sends it on every request.
* Login (`LoginClient`) receives credentials **RSA-encrypted in the browser**, therefore the collection
  authenticates with a session token (obtained by `scripts/get_api_token.py` or copied from the browser).

### Requests

All requests are read-only (`Get*` methods). Common tests (collection level) run for every request:
HTTP 200, response time < 5 s, JSON body, `ResponseCode === 0`.

| # | Request | Category | Specific validations |
|---|---------|----------|----------------------|
| 00 | `GetClientByToken` | Authentication | client `Id > 0`, currency present; saves `clientId`, `currencyId` |
| 01 | `GetClientInfo` | Client information | profile `Id` = logged-in client, has `UserName`, currency matches, password not exposed |
| 02 | `GetClientBalance` | Account balance | currency matches, `AvailableBalance` ≥ 0, `Balances[]` typed |
| 03 | `Client/GetClientStates` | Account status | states object returned |
| 04 | `Client/GetClientAccounts` | Account status / wallets | non-empty `Accounts[]`, each has currency + numeric balance |
| 05 | `Document/GetPaymentRequests` `Type=2` | Deposit information | every item is a deposit of this client |
| 06 | `Document/GetPaymentRequests` `Type=1` | Withdrawal information | every item is a withdrawal |
| 07 | `Document/GetTransactionHistory` | Transaction history | page size ≤ 20, items have amount + date |
| 08 | `GetPartnerPaymentSystems` | Payment methods | list returned, each method has id + name |
| 09 | `Document/GetBonuses` | Bonus information | list returned, items have id |
| 10 | `Document/GetBetsHistory` | Betting history | `Bets[]` + `Count ≥ Bets.length`, each bet has amount, state, product |
| 11 | `GetGames` (search) | Game information | results not empty, ≤ page size, each name contains the pattern, id/provider/image present |
| 12 | `GetGameProviders` | Game information | non-empty, id/name/count, ids unique |
| 13 | `GET getbets?winnersonly=true` | Betting activity (public) | only winning bets, other users' names masked (`****1234`) |

Requests without a token are **skipped** by a pre-request script (`pm.execution.skipRequest()`),
so a run without credentials still reports green for the public part.
