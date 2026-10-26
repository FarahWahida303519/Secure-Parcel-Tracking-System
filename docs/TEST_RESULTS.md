# Recorded security test results

Run date: **26 October 2026**. Owner: **[Enter your name / matric number]**.
Environment: Python 3.14, Flask 3.1.3, SQLite; isolated temporary databases. Automated integration tests use Flask's request client against the real app routes and database, not mocked security functions. Initial implementation/test-environment issues were corrected before the final passing run.

Command: `python -m unittest discover -s tests -v`.

**Latest result after module separation: see the final validation entry below.** JavaScript syntax, UI startup/encoding checks and Python compilation also passed. Subtests exercise additional inputs within individual tests.

| Module | Input / scenario | Expected | Actual |
|---|---|---|---|
| M1 | Login email `' OR 1=1 --`; short registration password | 401 login; 400 registration | PASS |
| M1 | Seller opens admin; rider registers parcel; anonymous opens parcels | 403 / 403 / 401 | PASS |
| M1 | Seller self-registers with `role: admin` | Created account is seller | PASS |
| M1 | Logout then reuse client session | Protected endpoint returns 401 | PASS |
| M1 | Admin disables seller, seller tries login | 401, access revoked | PASS |
| M2 | Valid fictional recipient, phone +60123456789, weight 1.25 | 201, KC- plus 32 hex characters; public history only | PASS |
| M2 | Register two parcels | Different random tracking numbers | PASS |
| M2 | Search `' OR 1=1 --` | 200, empty result; no SQL execution | PASS |
| M2 | Seller B requests seller A's ID and proof, lists own parcels | 404 details/proof; empty own list | PASS |
| M2 | Phone abc / 123 / script / 17 digits | 400 each | PASS |
| M2 | Weight -1 / 0 / abc / NaN / Infinity / 51 / boolean / null | 400 each | PASS |
| M2 | 501-character address, short address, 81-character/empty name, 101-character search | 400 each | PASS |
| M2 | Address `<script>alert(1)</script>` | Stored as data; absent from HTML shell; restrictive CSP | PASS; actual UI encoding separately tested in Node |
| M2 | SQL/XSS/malformed/overlong/sequential/unissued tracking | Same generic 404 | PASS |
| M2 | 31 public lookups within one minute | 31st returns 429 | PASS |
| Shared | Missing CSRF / foreign Origin | 403 each | PASS |
| M3 | Register → assign → Out for Delivery → Delivered, real generated PNG | All transitions succeed; private proof retrievable by authorized rider; four public events; admin count 1 | PASS |
| M3 | Skip status; foreign rider changes status; rider assigns | 409 / 404 / 403 | PASS |
| M3 | shell.php.jpg / fake.jpg non-image / image over 2 MB | 400 each | PASS |
| P3 | Delivered event older than 365 days; retention command | Name/address anonymized; phone cleared | PASS |

## Verification boundaries

Browser preview was attempted but the in-app browser could not reach the local server (connection timeout). Automated API/integration tests and JavaScript syntax/runtime checks are available; full visual and interactive browser verification is still required on your machine. Tests do not constitute an independent security audit. Capture your own screenshots and run/test the module yourself before submission. No owner names, marks, personal authorship or Git commits have been fabricated.

Additional commands: `node --check static/js/module2.js`, `node tests/test_frontend.cjs`, `python -m py_compile app.py manage.py`.

## Final validation after module separation

26 October 2026: **24 tests passed in 5.970 seconds**, organized in separate module test files. Additional page tests verified public URLs, login redirects, seller/rider/admin HTML page restrictions, foreign parcel denial, actual HTML escaping of script input and per-module asset loading. Node tests exercised the Module 2 registration and tracking handlers and verified that dynamic values use DOM text rather than HTML insertion. All four JavaScript files passed syntax checks.
