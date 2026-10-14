# VIKMO DealerDesk — 5-Minute Video Walkthrough Script

**Track:** AI / ML Track  
**Duration:** Exactly 5:00  
**Target Audience:** VIKMO Evaluation Team & Technical Hiring Managers

---

### Segment 1: Executive Overview & Architecture (0:00 – 0:45)
- **Visual:** Open browser to `http://localhost:5173/` (Dashboard) showing KPI cards, real-time backend health, and urgent reorder suggestions.
- **Talking Points:**
  - *"Welcome to the VIKMO DealerDesk demonstration for the AI/ML Intern track. I’m presenting a complete, production-grade commerce and inventory intelligence platform built with Django REST Framework, PostgreSQL, and React."*
  - *"Our system powers two-wheeler spare-parts distributors across India, managing 600 catalogue SKUs, 25 authorized dealers, automated 4-week demand forecasting, and an intelligent GenAI assistant."*
  - *"Key technical highlights: strict PostgreSQL referential integrity with Decimal money arithmetic, genuine multi-turn Gemini tool calling with grounded inventory checks, and a time-series forecasting model that outperforms all moving average and seasonal baselines without lookahead leakage."*

---

### Segment 2: AI Dealer Assistant & Live Tool Calling (0:45 – 2:00)
- **Visual:** Navigate to `/assistant`. Select Dealer `DLR-001 — ABC Motors`.
- **Action 1: Parts Search & Stock Grounding**
  - Prompt: *"Do you have brake pads for a Pulsar 150 and what is the stock?"*
  - Point out in UI:
    - The assistant executes `search_parts(query='brake pads', vehicle='Bajaj Pulsar 150')` and `check_stock(sku='BRK-1044')`.
    - Expand the **"Executed 2 Tool Call(s)"** dropdown showing the exact JSON arguments and function names.
    - Clickable **"BRK-1044"** cited SKU badge.
    - The engine header badge shows grounded execution.
- **Action 2: Draft Order Creation & Guardrails**
  - Prompt: *"Order 2 units of BRK-1044"*
  - Point out in UI:
    - Assistant executes `create_draft_order(items=[{'sku': 'BRK-1044', 'quantity': 2}])`.
    - Creates genuine `DRAFT` order `ORD-YYYYMMDD-NNNN` in PostgreSQL with 18% GST calculated via `ROUND_HALF_UP`.
    - Stock is **NOT** deducted (draft orders never deduct inventory).
    - Assistant is restricted from confirming orders (server-side safety guardrail).
    - Click **"Inspect Order"** link on the green action card to transition directly to the Orders desk.

---

### Segment 3: Machine Learning Demand Forecasting (2:00 – 3:15)
- **Visual:** Navigate to `/forecasting`.
- **Talking Points:**
  - *"Next, our Machine Learning demand forecasting pipeline."*
  - Select an active SKU (e.g., `BRK-1044` or `FIL-1016`). Point out the 4-week demand forecast curve rendered by Recharts (`2026-09-28` to `2026-10-19`).
  - Explain the modeling methodology:
    - *"The model is trained on 104 weeks of historical sales across 40 focus SKUs, incorporating dynamic promotional calendar lifts (median 2.02× uplift) and festival shifts aligned to Diwali."*
    - *"Crucially, to prevent future-data leakage, we rejected random cross-validation in favor of temporal expanding-window validation on historical cutoffs."*
    - *"Our model achieved a WAPE of 0.222 (MAE 7.61, RMSE 12.04), outperforming the 4-week moving average (WAPE 0.247) and seasonal naive lag-52 (WAPE 0.334) by over 10% to 25%."*
    - The official output is committed at `ml/forecast.csv` with exactly 160 rows.

---

### Segment 4: Automated Reorder Suggestions Formula (3:15 – 4:00)
- **Visual:** Scroll down to the Reorder Recommendations Table on `/forecasting`.
- **Talking Points:**
  - *"The forecast directly drives dynamic inventory replenishment via `GET /api/reorder-suggestions/`."*
  - Walk through one concrete row (e.g. `FIL-1016`):
    - Lead time $L = 3$ weeks.
    - Lead time demand = sum of forecast units for the first $L$ weeks.
    - $\sigma = \text{sample standard deviation with } (n-1) \text{ denominator over the last 12 historical sales weeks}$.
    - $\text{Safety Stock} = \lceil 1.65 \times \sigma \times \sqrt{L} \rceil$.
    - $\text{Reorder Point} = \text{Lead Time Demand} + \text{Safety Stock}$.
    - $\text{Suggested Reorder Qty} = \max(0, \lceil \text{Reorder Point} - \text{Current Stock} \rceil)$.
  - *"All figures reflect live warehouse inventory; as stock changes, replenishment advice updates automatically."*

---

### Segment 5: Bonus Features & Test Suite (4:00 – 5:00)
- **Visual 1 (Bonus Features):**
  - Click **"Sync Supplier Feed"** in the sidebar. Show the live cursor-paginated synchronization completing with created and updated counts.
  - Briefly show `/orders` with order status lifecycle chips (`CONFIRMED`, `DISPATCHED`, `DELIVERED`).
- **Visual 2 (Terminal Testing):**
  - Switch to terminal:
    - Run `python manage.py test core`: point out `Ran 36 tests ... OK`.
    - Run `python smoke_test.py --base-url http://localhost:8000 --all`: point out `12/12 checks passed`.
  - *"All 36 unit tests and 12/12 official contract smoke checks pass with zero failures."*
  - *"Thank you for watching the VIKMO DealerDesk delivery walkthrough."*
