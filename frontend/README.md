# VIKMO Dealer Desk frontend

The existing React 19 / Vite / Tailwind 4 application uses Lucide icons and Recharts. No new runtime dependencies were added for the redesign.

Run the backend from the repository root after installing `requirements.txt`, configuring `.env` with a PostgreSQL `DATABASE_URL`, applying migrations, and optionally seeding the supplied catalogue:

```powershell
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Run the frontend in a separate terminal (Node 22.12+ or a supported newer Node release):

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` requests to http://127.0.0.1:8000. `VITE_API_BASE_URL` can point to another API deployment. Production hosting must route SPA paths to `index.html` and provide an API proxy or configure the API base URL. Django admin remains at http://127.0.0.1:8000/admin/ and requires an existing staff account.

The design system is in `src/index.css` and `src/App.css`. Pages use semantic tokens, `panel`, `form-control`, standardized buttons, shared status badges, loading skeletons, and an accessible `Modal`. `ThemeProvider` tracks Light / Dark / System and reduced motion. Theme and sidebar preferences persist locally. The HTML head applies theme preference before first paint. Django admin shares the theme preference via its existing template inheritance and additional static styles; authentication and form processing remain Django's responsibility.

Routes: overview, products/inventory, dealers, orders, assistant, and forecasting. Inventory adjustments remain inside products. The dashboard uses API counts and forecast reorder recommendations. Order values are shown as order values rather than revenue. Catalogue search/category/fitment and pagination use the existing server API. Dealer search explicitly filters the current page because the dealer API has no search endpoint. Product editing uses the existing PATCH contract. Route modules load on demand, so the forecasting chart is not in the initial application bundle.

Verification commands:

```powershell
# From frontend/
npm run lint
npm run build

# From the repository root; backend dependencies and PostgreSQL required
python manage.py check
python manage.py test --noinput

# Browser checks; Vite running, Python Playwright and Chromium installed
python frontend/tests/ui_smoke.py
python frontend/tests/admin_smoke.py
```

The browser scripts use isolated API responses derived from supplied CSV files and explicit test fixtures. They do not change production data and do not replace backend integration tests. `ui_smoke.py` covers all six routes at 1440, 768, and 375px in both themes, theme persistence/system changes, search/filter/pagination, product creation/editing, stock payload validation, dealer creation, draft creation, order transitions/cancellation, assistant messages, modal keyboard focus, and mobile dialogs/navigation. `admin_smoke.py` renders the actual Django login through Django's test client and checks both themes, password visibility, responsive layout, and the preserved CSRF form. Screenshots and JSON results are written to `artifacts/`.

Current verification: frontend lint and production build pass without warnings; Django system check passes. Browser route and workflow checks pass without JavaScript exceptions. A project-local PostgreSQL 18 server is now configured on port 5433: all migrations and seeding succeeded, and 28 core, supplier-sync, and forecasting tests pass. Live API reads return HTTP 200. See `../LOCAL_SETUP.md` for startup commands. Staff login/logout/password changes and authenticated admin pages still require an account and live verification. The environment lacks the optional assistant test SDK (`google-genai`); install the complete existing requirements before rerunning the full suite.

Existing product boundaries: the REST API is explicitly unauthenticated (`AllowAny`) and the React workspace has no dealer/admin account role model. The redesign preserves this behavior. Django admin retains staff authentication, permissions, logout, and password change. The API does not provide product/dealer deletion, dealer editing, inventory history, or revenue aggregates, so the UI does not simulate those capabilities. No API endpoints, database models, order lifecycle rules, or inventory rules were changed. The only Django setting change adds the project template directory for the visual admin override.
