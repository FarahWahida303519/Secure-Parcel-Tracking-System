# ParcelTrack · KirimCepat

A local, integrated STTCK3033 assignment application for **three members**. Python Flask + SQLite, server-side authorization, plain HTML, separate CSS and JavaScript. No cloud service or database server needed.

## Run on Windows

For the prepared workspace, double-click **START_PARCELTRACK.bat** in Windows Explorer. It starts the server on an available local port, opens the tracking page after it responds, and keeps the server console visible. Keep that window open while using the website. If the browser reports a connection timeout after a tool-started preview, use this launcher directly from Windows. For a fresh copy, install dependencies using the steps below first.

Python 3.11+ recommended. In this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py create-admin
python app.py
```

Open **http://127.0.0.1:5000**. In the current prepared workspace, dependencies are already in `.vendor`, so `python app.py` works directly. For a fresh copy use the virtual environment steps. Create an administrator using the interactive command; no default passwords are stored in source. Password entry is hidden. Seller accounts self-register. Admin creates riders in **User management**.

## Demonstrate the complete workflow

1. Create an admin from the terminal. Start the server.
2. Create two different seller accounts using **Create an account**.
3. Sign in as seller A. Register a parcel; copy its tracking number. Search and inspect it.
4. Sign out. Public tracking displays only status and timestamps, including without login.
5. Sign in as admin. Create a rider. Open **Deliveries**, view a Registered parcel and assign it.
6. Sign in as that rider. Open **Deliveries**. Change Assigned → Out for Delivery, then Delivered or Failed with a real JPG/PNG proof photo.
7. Recheck public tracking for the complete history. View admin counts and audit activity.
8. Sign in as seller B and show that seller A's parcel is inaccessible, including direct API requests.

No real personal data is seeded or required. Use fictional recipients and `.test` account emails for your demonstration. The application starts with an empty database.

## File organization

```text
app.py                           Application factory and blueprint integration
shared.py                        Shared DB, sessions, authorization and errors
pages.py                         Shared home page
manage.py                        Shared CLI entry point
database/schema.sql              Shared SQL schema
modules/
  module1/routes.py              Friend 1: authentication and account APIs
  module1/views.py               Friend 1: HTML page routes
  module2/routes.py              YOUR parcel registration/search/tracking APIs
  module2/views.py               YOUR HTML page routes and page ownership checks
  module3/routes.py              Friend 3: delivery and dashboard APIs
  module3/views.py               Friend 3: HTML page routes
templates/
  base.html                      Shared header/sidebar/footer
  index.html                     Shared home page
  module1/                       login.html, register.html, account.html, users.html
  module2/                       register_parcel.html, my_parcels.html,
                                 parcel_details.html, public_tracking.html
  module3/                       deliveries.html, delivery_details.html, dashboard.html
  shared/                        Reusable parcel table, details and timeline
static/css/                      shared.css, module1.css, module2.css, module3.css
static/js/                       shared.js, module1.js, module2.js, module3.js
tests/                           Separate module1/module2/module3/shared tests
docs/INTEGRATION.md               Group integration contract and ownership
instance/                        Private SQLite DB and proof photos (ignored)
```

Each screen has its own URL and real HTML template. No page is assembled inside a single JavaScript application. Each module loads only its own CSS and JavaScript plus shared utilities. Your friends can replace their module files without editing your Module 2 files.

## Module allocation

- **M1 / Member 1:** login/logout, seller registration, rider account creation, password changes, account disabling.
- **M2 / YOUR MODULE:** parcel registration, unique tracking generation, own-parcel search/details and public tracking. Search source for `M2 SECURITY` to find the specific controls.
- **M3 / Member 3:** admin assignment, assigned-rider access, delivery transitions, private proof upload, admin status counts and audit activity.

The case study and marking workbook are the three-member versions. The rubric PDF contains four-member wording and conflicting presentation timings. This app uses the three-member case study and workbook allocation; confirm presentation timing with your lecturer. The case study references security requirement IDs without including their full list; documentation maps the actual provided controls rather than inventing official SR numbers.

## Tests

```powershell
python -m unittest discover -s tests -v
node tests/test_frontend.cjs
```

Tests use a temporary, isolated SQLite database and generated test-only passwords. They do not alter your application database. See `docs/SECURITY.md` and the recorded results for demonstration evidence. Replace the owner placeholders with your real names and repeat the tests yourself; the generated work does not establish individual authorship or commit history.

## Data retention and operational setup

```powershell
python manage.py anonymize
```

Schedule this daily using Windows Task Scheduler: it removes recipient details and proof photos 365 days after delivery, preserving status history. This command is supplied but a recurring OS task is not installed automatically. Backups also need a retention policy. The local server binds only to localhost and uses HTTP cookies for local demonstration. For any real deployment use a production WSGI server, HTTPS, `PARCELTRACK_HTTPS=1`, restricted filesystem permissions, encrypted storage/backups and a reviewed reverse-proxy/rate-limit configuration. Do not expose Flask's development server publicly. No personal-data export feature is provided. SQLite data is not encrypted at rest by this app.

Report suspected compromise to your administrator within one hour, disable affected accounts in User management, preserve restricted audit records and investigate before re-enabling. No notification service is configured.
