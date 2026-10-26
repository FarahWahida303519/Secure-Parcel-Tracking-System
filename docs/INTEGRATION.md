# Group ownership and integration contract

This is a multi-page Flask application. Each module is a separate Blueprint with its own backend API file, HTML view file, templates, CSS, JS and security tests. The original single-file application has been replaced.

| Owner | Backend | HTML templates | Frontend assets | Tests |
|---|---|---|---|---|
| Friend / Member 1 | modules/module1/routes.py and views.py | templates/module1/ | static/css/module1.css; static/js/module1.js | tests/test_module1.py |
| **You / Member 2** | **modules/module2/routes.py and views.py** | **templates/module2/** | **static/css/module2.css; static/js/module2.js** | **tests/test_module2.py** |
| Friend / Member 3 | modules/module3/routes.py and views.py | templates/module3/ | static/css/module3.css; static/js/module3.js | tests/test_module3.py |
| Group shared | app.py, shared.py, pages.py, database/schema.sql | templates/base.html, index.html, error.html, shared/ | static/css/shared.css; static/js/shared.js | tests/fixtures.py, test_pages.py, test_shared.py |

## Your Module 2 pages

| URL | HTML template | Purpose |
|---|---|---|
| /parcels/new | module2/register_parcel.html | Seller registers parcel |
| /parcels | module2/my_parcels.html | Own parcels, GET search via q parameter |
| /parcels/ID | module2/parcel_details.html | Owner-authorized private details |
| /track | module2/public_tracking.html | Anonymous status/timestamp lookup |

Each page is directly navigable, bookmarkable and refreshable. Server-side checks protect private HTML routes as well as JSON endpoints. A shared layout removes repeated headers and navigation without combining module pages.

## API contract

- M1 owns `/api/me`, `/api/register`, `/api/login`, `/api/logout`, `/api/password`, `/api/users`, `/api/users/ID/toggle`. It establishes a server-side session cookie and makes `g.user` available to the rest of the application.
- M2 owns GET/POST `/api/parcels`, GET `/api/parcels/ID`, and GET `/api/track?number=...`. The list/detail API serves all authenticated roles for integration, with seller/rider ownership predicates enforced. Public tracking returns only `history: [{status, created}]`.
- M3 owns `/api/admin`, `/api/parcels/ID/assign`, `/api/parcels/ID/status`, `/api/parcels/ID/proof`.
- All modules use the same database connection through `shared.db()` and the same schema. Do not create a second user/parcel table in a friend's module.
- Shared helpers `role`, `accessible`, `limited`, `audit` enforce consistent controls. `g.user` exposes id, role, active status and csrf; clients submit that csrf value through `X-CSRF-Token` on authenticated mutations.
- Only `app.py` registers the blueprints. A friend can replace a module implementation while preserving its Blueprint export and API contract. Keep public endpoints unchanged or agree on a contract change together.

## Develop your module

Your module needs M1 authentication and the shared database contract for protected functions. Use the included M1/M3 implementations as integration scaffolding until your friends replace them. Public tracking needs no login. Do not bypass seller checks to make a standalone demo.

Run only your security tests with `python -m unittest discover -s tests -p test_module2.py -v`. Run the full integration suite before sharing the combined project. Do not share `.vendor`, `instance`, session/database files or personal recipient data in Git.
