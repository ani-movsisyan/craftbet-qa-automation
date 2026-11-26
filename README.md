# CraftBet QA Automation

Test assignment for the Automation QA Engineer position.

1. UI tests for https://craftbet.com — Python, Selenium, Pytest (Page Object pattern)
2. API tests — Postman collection

More details about test cases and problems I faced are in [docs/TEST_SCENARIOS.md](docs/TEST_SCENARIOS.md).
Results of my test runs (reports, log, screenshots) are in [docs/results](docs/results).

## Project structure

- `config/` – settings (URL, browser, timeouts), values are read from `.env`
- `pages/` – page objects (header, login, casino lobby, game page, account)
- `tests/` – tests:
  - `test_01_authentication.py` – login / logout
  - `test_02_navigation.py` – menu, pages, back / forward
  - `test_03_games.py` – demo games
  - `test_04_additional_features.py` – language, categories, search, favorites, account pages
  - `test_05_user_journey.py` – full user flow from login to logout
- `utils/` – driver setup and logger
- `postman/` – Postman collection and environment
- `scripts/get_api_token.py` – logs in and saves the token for Postman

## How to install

You need Python 3.10+ and Google Chrome. The chromedriver is downloaded automatically by Selenium.

```bash
python -m venv .venv
.venv\Scripts\activate          # on Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Login and password are not in the repository. Copy `.env.example` to `.env` and write the test account there:

```
CRAFTBET_USERNAME=...
CRAFTBET_PASSWORD=...
```

If `.env` is empty, tests that need login are skipped, other tests still run.

## How to run

```bash
pytest                                   # all tests
pytest -m smoke                          # only smoke tests
pytest tests/test_03_games.py            # one file
```

Markers: `smoke`, `auth`, `negative`, `navigation`, `games`, `functional`, `e2e`.

After the run:
- `reports/report.html` – HTML report, every test has a screenshot
- `reports/screenshots/` – screenshots of the steps
- `reports/logs/` – log file

## Postman

Import `postman/CraftBet_API.postman_collection.json` and `postman/CraftBet.postman_environment.json`.

Public requests work without login. For client data you need a token:
- run `python scripts/get_api_token.py` – it logs in with the account from `.env` and creates `postman/CraftBet.env.local.json`, or
- log in on the site, copy `token` from Local Storage (DevTools → Application) to the `token` variable and run request `00. Validate session` first.

Run from command line with Newman:

```bash
npm install -g newman newman-reporter-htmlextra
newman run postman/CraftBet_API.postman_collection.json -e postman/CraftBet.env.local.json -r cli,htmlextra
```

## Notes

- Only demo games are opened. Games that can be played only for real money are skipped.
- No deposits, withdrawals or real bets. All API requests only read data.
- `.env` and files with tokens are in `.gitignore`.
