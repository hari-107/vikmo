# VIKMO DealerDesk — Candidate Technical Interview Notes

These notes are designed to prepare you for defending and explaining your implementation during the live technical interview.

---

### 1. Request Flow in Django
- **Entry Point**: A request hits Django via WSGI (`dealerdesk/wsgi.py`) or the dev server.
- **Routing**: `dealerdesk/urls.py` directs `/api/` traffic to `core/urls.py`.
- **View Execution**:
  - `core/urls.py` maps URL patterns directly to class-based views in `core/views.py`, `core/assistant/views.py`, `core/ml_views.py`, and `core/supplier_views.py`.
  - Django REST Framework (DRF) processes request parsing, query parameters, and serializes responses.
- **Error Handling**:
  - DRF's default exception handler is replaced by `custom_exception_handler` in `core/exceptions.py`.
  - Every error is formatted into `{"error": {"code": ..., "message": ..., "details": [...]}}` with correct HTTP status codes (400, 404, 409, 502).

---

### 2. Models, Serializers, and Money Formatting
- **Models** (`core/models.py`):
  - `Product`: Stores catalogue items.
  - `Dealer`: Stores authorized distributors.
  - `Order`: Stores orders (`order_number` formatted as `ORD-YYYYMMDD-NNNN`).
  - `OrderItem`: Stores order lines snapshotting prices and taxes.
  - `IdempotencyRecord`: Protects duplicate order submissions.
  - `AssistantConversation`: Stores chat history by `session_id`.
- **Money Handling**:
  - `MoneyField` in `core/serializers.py` serializes financial fields as strings with exactly 2 decimal places (`f"{d:.2f}"`).
  - Money calculations inside `core/services.py` use Python's `Decimal` type with `ROUND_HALF_UP`. Floating-point binary arithmetic is avoided to prevent paise rounding errors.

---

### 3. Product Search Logic
- **Endpoint**: `GET /api/products/` in `core/views.py` (`ProductListCreateView`).
- **Filters**:
  - `search`: Filtered using `Q(sku__icontains=search) | Q(name__icontains=search) | Q(brand__icontains=search)`.
  - `category`: Exact match filter.
  - `vehicle`: Case-insensitive match on `vehicle_fitment__icontains`.
- **Pagination**: Uses `StandardResultsSetPagination` (`core/pagination.py`) with default page size 20, max 100.

---

### 4. AI Assistant Multi-Provider Architecture & Reliability Overhaul
- **Endpoint**: `POST /api/assistant/chat/` (`core/assistant/views.py`).
- **Orchestration Layer**: `MultiProviderOrchestrator` (`core/assistant/providers.py`) driving `AssistantEngine` (`core/assistant/agent.py`).
- **Three-Tier Failover Policy**:
  1. **Primary Provider — Google Gemini**:
     - Configured via `GEMINI_API_KEY`, `GEMINI_MODEL` (default: `gemini-3.5-flash-lite`), and `GEMINI_MODEL_PREFERENCES` (`gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3.8-flash,gemini-3.1-flash-lite`).
     - Supports multi-turn function calling (`search_parts`, `check_stock`, `create_draft_order`) with automatic function calling disabled.
     - Quota tracking: Detects HTTP 429 `RESOURCE_EXHAUSTED` and immediately stops retrying models that share the same exhausted daily project quota, cleanly failing over to Groq.
     - Model availability rotation: Rotates across verified models on transient 404 or 503 spikes.
  2. **Secondary Provider — Groq**:
     - Configured via `GROQ_API_KEY`, `GROQ_MODEL` (`llama-3.3-70b-versatile`), and `GROQ_ENABLED=true`.
     - Official `groq` SDK integration with OpenAI-compatible tool calling definitions.
     - Automatically selected when Gemini is unavailable, unconfigured, or rate-limited.
  3. **Tertiary Provider — Deterministic Fallback Engine**:
     - Intent-aware, database-grounded engine active when both LLMs are unavailable or disabled.
     - Routes across 9 intents: Greetings, Stock queries, Price lookups, Typo-tolerant Product Searches, Draft Orders, 4-Week Demand Forecasting (`ml/forecast.csv`), Reorder Recommendations (`lead_times.csv` + stock), Off-topic defense, and Clarification questions.
- **Root Cause of Original Failure ("did you have scliencer")**:
  1. In the legacy `agent.py`, `search_triggers` contained `"do you have"` but lacked `"did you have"`, and had zero typo tolerance for misspelled tokens like `"scliencer"`.
  2. The legacy default model `gemini-flash-latest` aliased to `gemini-3.8-flash`, which had hit the free-tier quota limit (HTTP 429 `RESOURCE_EXHAUSTED`).
  3. When Gemini threw an exception after issuing 2 tool calls, the tool calls remained in `tool_calls`, while execution fell back to `_run_deterministic`.
  4. Because `"did you have scliencer"` matched none of the rigid regex triggers, it fell through to the last line returning the generic greeting (`"Hello! I am your VIKMO DealerDesk Assistant..."`).
  5. The UI displayed "Executed 2 Tool Calls" alongside the fallback greeting, confusing the user.
- **Resolution & Protections**:
  - **Typo Tolerance**: Standard library `difflib.get_close_matches` against domain vocabulary normalizes `"scliencer"` $\rightarrow$ `"silencer"`. Searches catalogue, confirms silencers are not in catalogue, and truthfully explains available categories.
  - **State Preservation & No Duplicate Orders**: If a provider executes `create_draft_order` and crashes before generating final text, `tool_registry._created_orders_cache` and recorded actions preserve the created order. The deterministic engine formulates the order confirmation directly without creating a second order in PostgreSQL.
  - **Truthful UI Badges**: Frontend displays `Gemini Live`, `Groq Live`, or `Deterministic Fallback` based on backend `res.provider`. Tool call counts accurately reflect executed tools.

---

### 5. Draft Order Creation Business Logic
- **Service**: `create_draft_order` in `core/services.py`.
- **Validation Rules**:
  1. `dealer_id` must exist.
  2. Order must contain at least one item.
  3. Every quantity must be an integer $\ge 1$.
  4. Duplicate SKUs within the same order are rejected.
  5. Every SKU must exist in the database catalogue.
- **Pricing & Stock**:
  - Draft creation uses the current catalogue price (`product.price`).
  - Draft creation **never** deducts stock. Stock is only deducted when an order is transitioned to `CONFIRMED`.
  - Order numbers are generated in the `Asia/Kolkata` timezone with a sequence starting at 0001 each day (`ORD-YYYYMMDD-NNNN`).

---

### 6. Demand Forecasting: Training, Validation & Leakage Prevention
- **Pipeline Scripts**:
  - `forecasting/evaluate.py`: Evaluates models on historical cutoffs.
  - `forecasting/predict.py`: Generates the final `ml/forecast.csv`.
  - `forecasting/train.py`: Orchestrates training and prediction.
- **Why Time-Based Validation Matters**:
  - Randomly splitting time-series data leaks future data into the past (lookahead bias).
  - Expanding-window validation trains strictly on dates prior to the cutoff date and tests on future 4-week horizons.
- **Empirical Results**:
  - Selected Model: **MAE 7.61, WAPE 0.222, RMSE 12.04** on recent temporal fold.
  - Outperformed Naive (WAPE 0.300), Moving Average (WAPE 0.247), and Seasonal Naive (WAPE 0.334).
- **Special Cases Handled**:
  - **Promotions**: $2.02\times$ empirical sales multiplier incorporated using `data/promo_calendar.csv`.
  - **Diwali Shift**: Calculated relative to shifting Diwali dates (`weeks_to_diwali`) from `data/festival_calendar.csv`.
  - **Intermittent Demand**: Low-volume SKUs (>40% zero sales) use moving average baselines with promo scaling suppressed.
  - **New SKUs**: Newly launched SKUs with only 6 weeks of history fall back to short-window non-promo averages.

---

### 7. Reorder Calculation Formula
- **Endpoint**: `GET /api/reorder-suggestions/` (`core/ml_views.py`).
- **Formulas**:
  - $L = \text{lead\_time\_weeks}$ (from `data/lead_times.csv`).
  - $\text{lead\_time\_demand} = \sum_{w=1}^L \text{forecast\_units}_w$ for the first $L$ forecast weeks.
  - $\sigma = \text{sample standard deviation with } (n - 1) \text{ denominator of sales over the most recent 12 weeks}$.
  - $\text{safety\_stock} = \lceil 1.65 \times \sigma \times \sqrt{L} \rceil$.
  - $\text{reorder\_point} = \text{lead\_time\_demand} + \text{safety\_stock}$.
  - $\text{reorder\_qty} = \max(0, \lceil \text{reorder\_point} - \text{current\_stock} \rceil)$.
  - `current_stock` is fetched **live** from `Product.objects.get(sku=sku).stock` at the time of the request.

---

### 8. Running the Application & Tests
- **Database**: PostgreSQL on `localhost:5432/dealerdesk`.
- **Environment**: Configured via `.env` with `DATABASE_URL`.
- **Commands**:
  ```bash
  pip install -r requirements.txt
  python manage.py migrate --noinput
  python manage.py seed_data
  python manage.py runserver 0.0.0.0:8000 --noreload
  ```
- **Tests**:
  ```bash
  # Django automated test suite (27 tests)
  python manage.py test core

  # AI/ML track smoke test
  python smoke_test.py --base-url http://localhost:8000 --track aiml

  # Full smoke test across all tracks (including optional order engine and supplier sync)
  python smoke_test.py --base-url http://localhost:8000 --all
  ```
