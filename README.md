# CraftBet QA Automation

Practical assignment for the **Automation QA Engineer** position.

| Part | Tooling | Location |
|------|---------|----------|
| 1. Web UI automation of [craftbet.com](https://craftbet.com) | Python 3.11, Selenium 4, Pytest, Page Object Model | `pages/`, `tests/` |
| 2. API testing | Postman collection (14 requests) + Newman | `postman/` |

Detailed scenario descriptions, validations and challenges: [docs/TEST_SCENARIOS.md](docs/TEST_SCENARIOS.md).
Execution results (HTML reports, logs, screenshots): [docs/results/](docs/results/).

---

## 1. Project structure

```
craftbet-qa-automation/
├── config/settings.py          # all settings, read from environment / .env
├── pages/                      # Page Object Model
│   ├── base_page.py            # explicit waits, safe click, screenshots, helpers
│   ├── components.py           # Header (menu, language, auth state) + LoginModal
│   ├── home_page.py
│   ├── casino_page.py          # lobby: categories, search, game cards (demo / real)
│   ├── game_page.py            # game iframe: load checks + demo interactions
│   └── content_pages.py        # info / promo pages, account area (history, logout)
├── tests/
│   ├── conftest.py             # driver & logged-in fixtures, screenshot-on-result hook
│   ├── test_01_authentication.py
│   ├── test_02_navigation.py
│   ├── test_03_games.py
│   ├── test_04_additional_features.py
│   └── test_05_user_journey.py # complete end-to-end journey
├── utils/                      # driver factory, logger
├── scripts/get_api_token.py    # UI login -> exports a session token for Postman
├── postman/                    # collection, environment, generator
├── docs/                       # scenarios, challenges, execution results
├── .env.example                # template for credentials (real .env is git-ignored)
├── pytest.ini
└── requirements.txt
```

## 2. Installation

Requirements: **Python 3.10+**, **Google Chrome** (or Edge). The browser driver is resolved automatically by Selenium Manager.

```bash
git clone <this repository>
cd craftbet-qa-automation
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

Credentials of the test account are **not** stored in the repository:

```bash
cp .env.example .env        # Windows: copy .env.example .env
# then fill CRAFTBET_USERNAME and CRAFTBET_PASSWORD in .env
```

Without credentials, tests that need a session (marker `auth`) are skipped automatically and all guest scenarios still run.

## 3. Running the UI tests

```bash
pytest                                  # everything
pytest -m smoke                         # quick smoke
pytest -m "navigation or games"         # by area
pytest tests/test_05_user_journey.py    # full journey (needs credentials)
HEADLESS=true pytest                    # headless (PowerShell: $env:HEADLESS="true"; pytest)
```

Markers: `smoke`, `auth`, `negative`, `navigation`, `games`, `functional`, `e2e`.

Results of every run:

* `reports/report.html` – self-contained HTML report with a screenshot attached to every test
* `reports/screenshots/` – step screenshots (game loaded, after interaction, pages, etc.)
* `reports/logs/run_<timestamp>.log` – detailed step log

## 4. Running the Postman collection

Import into Postman:

* `postman/CraftBet_API.postman_collection.json`
* `postman/CraftBet.postman_environment.json`

The public folder works immediately. Client-data requests need a session **token**:

* **Option A (automated):** `python scripts/get_api_token.py` – logs in through the UI with the `.env`
  credentials and writes `postman/CraftBet.env.local.json` (git-ignored) with `token`, `clientId`, `currencyId`.
* **Option B (manual):** log in on craftbet.com, open DevTools → Application → Local Storage →
  `https://craftbet.com`, copy the `Token` value (key `token`, or the `Token` field of the `…user` entry),
  paste it into the `token` environment variable and run **00. Validate session** – it fills `clientId` and `currencyId`.

Command-line run with Newman (Node.js required):

```bash
npm install -g newman newman-reporter-htmlextra
newman run postman/CraftBet_API.postman_collection.json \
       -e postman/CraftBet.env.local.json \
       --reporters cli,htmlextra --reporter-htmlextra-export postman/newman/report.html
```

If the token is empty, client-data requests are skipped (not failed) by a pre-request script.
The collection is generated from `postman/build_collection.py` (`python postman/build_collection.py`).

## 5. Safety rules followed

* Only **Demo** (fun-mode) games are opened; cards that offer only *Real* play are skipped and logged.
* No deposits, withdrawals, bets with real money or any data-changing API calls – the Postman
  collection uses only `Get*` methods.
* Credentials and tokens are kept in `.env` / `*.local.json`, both git-ignored.
