# Security implementation and Module 2 demonstration

Owner: **[Your name and matric number]**. M1/M3 owners: **[Team members]**.

## Requirements and design

The provided three-member case study §4.2 and marking workbook Modules sheet define M2 as **Parcel Registration and Public Tracking**. The four-member rubric PDF is supplementary. Syllabus connections: least privilege and privacy (Topic 2), policy decomposition and abuse cases (Topic 4), trust boundaries (Topic 5), secure coding (Topic 6), security tests (Topic 7), retention and delivery (Topic 8).

Browser input is untrusted. Flask validates and authorizes each request before SQLite queries or private image access. Public visitors cross a different trust boundary and receive an explicit status/timestamp-only response. UI visibility is not an authorization mechanism.

| Module / threat | Implemented control | Source location / evidence |
|---|---|---|
| M2 SQL injection in search or tracking | SQLite placeholders; escaped LIKE wildcards; tracking format check | `parcels`, `track` in modules/module2/routes.py |
| M2 stored XSS in recipient/address | HTML entity encoding at all UI interpolation points, no inline scripts, restrictive CSP | Jinja autoescaping in templates/shared/parcel_table.html and parcel_summary.html; DOM textContent in static/js/module2.js; headers in shared.py |
| M2 IDOR and role escalation | Seller ID from authenticated session; owner predicate on every detail/proof request; only sellers create | `accessible`, `role`, `create_parcel` |
| M2 sequential tracking enumeration | 128-bit cryptographic token, UNIQUE SQL constraint, 30 lookups/IP/minute | `create_parcel`, `track`, `limited` |
| M2 invalid data | Bounded name/address, 9–15 digit phone with optional +, finite weight >0 and <=50, 35-character tracking format | `create_parcel`, `track` |
| M2 recipient privacy | Public SELECT allowlists only status/created; no exports; no personal details in audit events | `track`, `audit` |
| Shared CSRF | Server-stored per-session CSRF token and Origin check on mutations | `authenticate` |
| M1 account takeover | Argon2 passwords, 10-character minimum, login limiter, server-side expiring session, regenerated login token, logout deletion | login/register/password routes |
| M1 role abuse | Seller self-registration cannot choose role; only admin creates riders; account disabling invalidates sessions | register/add_rider/toggle |
| M3 access misuse | Admin-only assignment and counts; rider assignment predicates; atomic status progression | assign/update_status/admin |
| M3 upload execution | JPG/PNG only; 2 MB limit; real image decoding, pixel cap, re-encoding strips metadata; random private filename; authorized image retrieval | update_status/proof |
| P3 retention | CLI anonymizes delivered records and removes photos after 365 days | anonymize (must schedule daily) |
| Safe failures | Validation, missing/foreign parcel, unauthenticated, wrong role, missing CSRF, duplicate account, limiter, invalid upload, stale status, oversized request, DB failure | API error messages; generic exception handler |

Recipient input containing `<script>` is stored as data, then encoded on output. This is deliberate: blocking particular strings is not reliable XSS prevention. API JSON may contain those characters; the renderer must never treat them as HTML.

Rate limiting is per connection IP, database-persisted and process-safe for this local app. Shared networks share a quota. A deployed proxy requires explicit trusted-proxy configuration; the app does not trust arbitrary forwarded IP headers. Sessions expire after one hour; the interface asks users to sign in again when needed.

Implementation ownership: M1 APIs/pages are in `modules/module1/`, M2 in `modules/module2/`, and M3 in `modules/module3/`. Session authorization and SQLite connection helpers are shared in `shared.py`. M2 templates and static files are isolated under their own module names.

## M2 live demo outline

1. Register a fictional parcel, copy its tracking number and explain the four input validations.
2. Search with `' OR 1=1 --` and show no extra records. Explain SQL parameters.
3. Save `<script>alert(1)</script>` in an address, open details and show it as literal text. Explain encoding and CSP.
4. Switch sellers and request the first seller's numeric parcel ID: 404 with no details. Explain the owner predicate.
5. Sign out and track a valid number. Inspect response: only `history`, `status`, `created`. No recipient, actor or photo.
6. Try malformed/sequential tracking and repeated lookups: generic not-found and then 429. Explain random entropy and the limiter.
7. Run the automated tests and discuss the input/expected/actual evidence. Fill in your owner name and capture your own screenshots/results for submission.

## Practical limits

This is an educational local app, not an audited production system. Automated HTTP/API tests do not replace an independent browser or penetration test. Retention scheduling, encrypted disk/backups, HTTPS infrastructure and operational incident response require deployment configuration. Failed-delivery retention is not defined by the supplied 12-month-after-delivery policy and should be agreed before real use. Members must understand, adapt, test and commit their own work; do not represent generated code/history as evidence of personal authorship.
