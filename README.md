# VIKMO Dealer Desk

VIKMO Dealer Desk is a web-based automotive distribution workspace for managing catalogue inventory, dealers, orders, supplier feed sync, AI-assisted operations, and demand forecasting.

## Features

- **Dashboard** — operational overview and inventory insights.
- **Products & inventory** — browse the catalogue, search/filter products, edit product details, and manage stock through the existing API.
- **Dealers** — browse and create dealer records.
- **Orders** — create and manage order workflows supported by the backend.
- **AI assistant** — ask operational questions through a configured LLM provider.
- **Demand forecasting** — view weekly SKU demand predictions and reorder recommendations, including lead-time demand and safety-stock buffers.
- **Supplier sync** — trigger supplier-feed synchronization and see success/error feedback.
- **Light, dark, and system themes** — responsive workspace layout with reduced-motion support.

## Tech stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS 4, React Router, Lucide React, Recharts |
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Forecasting | pandas, NumPy, scikit-learn, hybrid demand forecasting |
| AI providers | Gemini, Groq, OpenAI-compatible configuration, Anthropic (configured via environment variables) |

## Repository layout

```text
vikmo/
├── core/                 # API views, business logic, supplier sync and forecasting
├── dealerdesk/           # Django project configuration and URL routing
├── data/                 # Seed/catalogue, sales, promotion and lead-time data
├── forecasting/          # Forecast model, prediction and validation scripts
├── frontend/             # React + Vite application
├── ml/                   # Generated forecast output
├── tests/                # Backend and forecast tests
├── manage.py
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.10+ (use a version supported by your installed dependencies)
- Node.js 22.12+ or a newer Vite-supported version
- PostgreSQL
- API key for whichever AI provider you want to use (optional for non-AI workflows)

## 1. Configure the backend

Create and activate a virtual environment from the repository root.

**Windows PowerShell**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file in the repository root. Do not commit secrets.

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=1
DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/vikmo
# Configure at least one provider if using the AI assistant:
GROQ_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
# Optional supplier feed configuration:
SUPPLIER_API_URL=http://127.0.0.1:8099
SUPPLIER_API_KEY=
```

Create the PostgreSQL database named in `DATABASE_URL`, then run migrations and optional seed data:

```bash
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

The backend runs at `http://127.0.0.1:8000`. Django admin is at `http://127.0.0.1:8000/admin/`; an existing staff account is required.

## 2. Configure the frontend

Open a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite development server proxies `/api` requests to the local Django backend by default.

To use a different API origin, copy `frontend/.env.example` to `frontend/.env.local` and set:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Restart Vite after changing environment variables.

## 3. Forecasting

Generate the rolling four-week forecast file:

```bash
python -m forecasting.predict
```

The generated file is `ml/forecast.csv`, with columns:

```csv
sku,week_start,forecast_units
```

The forecast generator selects the next upcoming weekly periods and preserves the CSV/API schema used by the dashboard and reorder logic. Keep `data/sales_history.csv` updated with actual sales before regenerating forecasts. If the history is stale, the model estimates intermediate weeks before producing the upcoming horizon, so those results should be treated as estimates until current sales data is supplied.

For temporal model evaluation and forecast generation, run:

```bash
python forecasting/train.py
```

## 4. Quality checks

Run frontend checks from `frontend/`:

```bash
npm run lint
npm run build
```

Run backend checks from the repository root (PostgreSQL and backend dependencies must be configured):

```bash
python manage.py check
python manage.py test --noinput
```

Optional browser smoke checks, when Playwright and Chromium are installed:

```bash
python frontend/tests/ui_smoke.py
python frontend/tests/admin_smoke.py
```

## UI motion and accessibility

The frontend includes route-entry transitions, interactive hover/press states, animated navigation and modal transitions, loading feedback, and theme transitions. Animations respect the operating system's `prefers-reduced-motion` setting. Light, dark, and system theme options are available in the workspace header.

## Security and deployment notes

- Never commit `.env`, API keys, database credentials, or production secrets.
- Set `DJANGO_DEBUG=0` and a strong `DJANGO_SECRET_KEY` for production; configure allowed hosts, HTTPS, database access, and deployment-specific CORS/proxy settings before exposing the service.
- The current API permission configuration is permissive for this assignment. Add authentication and authorization before deploying to a public production environment.
- For production frontend hosting, configure SPA route fallback to `index.html` and route API calls to the backend.
- This README documents the repository setup; actual deployment status depends on your environment.

## Contributing

1. Create a feature branch.
2. Keep API response shapes and business rules compatible with existing frontend flows.
3. Run the frontend lint/build and backend checks relevant to your changes.
4. Open a pull request with a concise summary and verification results.
