# Execution results

## UI tests (Selenium) – guest run, 26.11.2026

`pytest -m "not negative"` without test-account credentials:

**18 passed, 1 xfailed, 8 skipped**, duration 5 min 9 s.

* skipped = tests marked `auth`, they need the test account from `.env`
* xfailed = known issue found by the suite: `/promotions` renders an empty page body for guest users

* [ui_report_guest.html](ui_report_guest.html) – pytest-html report, a screenshot attached to every test (download and open in a browser)
* [ui_run_guest.log](ui_run_guest.log) – step log
* [screenshots/](screenshots/) – key steps: demo games loaded / after interaction, language switch, categories, search, menus

## API tests (Postman / Newman) – public part

`newman run` without a session token: **3 requests, 23 assertions, 0 failures**; 11 client-data requests skipped
(they need `token`, see main README).

* [postman_report_public.html](postman_report_public.html) – Newman htmlextra report
