# 🍔 CampusBite — Restaurant Ordering & Delivery Platform

CampusBite is a full-stack food ordering and delivery app for a campus. It has three roles:

- **Customers** browse restaurants, order food, track deliveries, leave reviews, request refunds and get AI-generated insights about their orders.
- **Restaurant owners** manage their menu, move orders through preparation, assign delivery partners, handle refund requests and see stats and reminders.
- **Delivery partners** see the orders assigned to them, update delivery status and view their history.

The frontend is **React**, the backend is **FastAPI** with **SQLAlchemy** on **PostgreSQL**, and the backend runs in **Docker Compose**.

---

## Tech stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, JavaScript (ES6+), React Hooks (`useState`, `useEffect`, `useContext`, custom hooks), React Router DOM 6, Axios, Vite, plain responsive CSS |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 ORM, JWT (`python-jose`), `bcrypt` |
| Database | PostgreSQL 16 (Docker). SQLite fallback for local dev and tests |
| AI | OpenAI API (Chat Completions, default model `gpt-4o-mini`) |
| DevOps | Docker, Docker Compose, Git/GitHub |
| Testing | pytest + FastAPI TestClient |

---

## Features

### Authentication & authorization
- Register and log in for all three roles. Registering as an owner also creates their restaurant.
- Passwords are hashed with **bcrypt**. Login returns a **JWT** (HS256) carrying the user id and role.
- The frontend keeps the token in `localStorage`. An Axios interceptor adds `Authorization: Bearer <token>` to every request and logs the user out on a 401.
- **The backend enforces RBAC.** Every protected route uses a `require_role(...)` dependency, and there are ownership checks on top of that:
  - customers can only see and change their own orders (other people's orders return 404),
  - owners can only manage their own restaurant's menu, orders, returns and reminders,
  - delivery partners can only see and update orders assigned to them.
- On the frontend, protected routes and role-based navigation redirect users who don't have the right role.

### Customer
- Browse restaurants (search, pagination, average rating).
- Restaurant menu: search dishes by name, filter by min/max price and availability, sort by name or price.
- Cart managed with React Context and saved to localStorage. A cart holds items from one restaurant at a time. You can change quantities or remove items.
- Checkout with a **dummy payment**: the order is created, a `payment` ledger entry is written and `payment_status` becomes `mock_paid`.
- Dashboard: order history with status and date filters, pagination, and payment and return status badges.
- Order tracking page with a visual status tracker and the payment ledger.
- Cancel an order (only while it is `PLACED`). The mock payment is reversed automatically.
- Rate and review an order after delivery (one review per order).
- Request a return/refund after delivery. A reason is required and only one request is allowed per order.
- **AI order insights**: get a summary or ask free-text questions about your own orders.

### Restaurant owner
- Dashboard with stats: total orders, orders today, revenue, refunded amount, average rating, orders by status and top dishes.
- **Reminders** panel for orders stuck in `PLACED`/`ACCEPTED` for more than 15 minutes. These come from a background task. You can dismiss them or trigger a check manually.
- Menu management: add, edit and delete dishes (deleting is a soft delete so past orders stay intact) and toggle availability.
- Order management: filter by status and date, accept, start preparing, mark ready, reject, and assign a delivery partner once an order is `READY`.
- Return/refund requests: approve (writes a `refund` ledger entry, sets `payment_status=refunded` and order status `REFUNDED`) or reject (`return_status=rejected`), with an optional note.

### Delivery partner
- List of assigned deliveries with a status filter, showing the customer's name, phone and address and the order items.
- Move an order from `ASSIGNED` to `OUT_FOR_DELIVERY` to `DELIVERED`.
- Paginated delivery history.

### Order lifecycle

```
PLACED → ACCEPTED → PREPARING → READY → ASSIGNED → OUT_FOR_DELIVERY → DELIVERED
   └→ CANCELLED                                                   └→ REFUNDED (return approved)
```

| Transition | Who |
|---|---|
| PLACED → ACCEPTED | Owner |
| PLACED → CANCELLED | Customer or owner (cancelling is only possible from PLACED) |
| ACCEPTED → PREPARING → READY | Owner |
| READY → ASSIGNED | Owner, through the assign endpoint (target user must be a delivery partner) |
| ASSIGNED → OUT_FOR_DELIVERY → DELIVERED | The assigned delivery partner only |
| DELIVERED → REFUNDED | Happens automatically when the owner approves a return |

The backend rejects any other transition with **400**, and a transition attempted by the wrong role with **403**. The rules live in [`backend/app/order_rules.py`](backend/app/order_rules.py).

### AI order insights
- `POST /api/ai/insights` with an optional `question`. With no question, it returns a summary.
- The backend loads **only the authenticated customer's** orders (the 50 most recent: items, totals, statuses, dates), sends them as JSON context to OpenAI and returns the answer.
- The API key is read from the `OPENAI_API_KEY` environment variable and never reaches the frontend.
- Error handling: missing or invalid key → 503, OpenAI rate limit → 429, other OpenAI errors → 502.
- There is also a per-user in-memory rate limit (`AI_RATE_LIMIT_PER_MINUTE`, default 5/min). It returns 429 with a `Retry-After` header.
- Example questions: *"Summarize my last five orders"*, *"Which of my orders are still not delivered?"*, *"How much did I spend this week?"*, *"Which food items have I ordered most frequently?"*

### Middleware & background tasks
- `RequestLoggingMiddleware` logs the method, path, status and response time of every request, and adds `X-Process-Time` and `X-Request-ID` response headers.
- CORS middleware is configured through `CORS_ORIGINS`.
- A background **reminder loop** starts in FastAPI's lifespan and runs every `REMINDER_INTERVAL_SECONDS`. It finds `PLACED`/`ACCEPTED` orders whose `updated_at` is older than `REMINDER_THRESHOLD_MINUTES` (15) and writes rows to `admin_reminder_logs`, at most one per order and status. Reminders are resolved automatically when the order moves on.

---

## Project structure

```
campusbite/
├── docker-compose.yml        # postgres + backend
├── .env.example              # variables used by docker-compose
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example          # for running without Docker
│   ├── app/
│   │   ├── main.py           # app, lifespan, middleware, routers
│   │   ├── config.py         # pydantic-settings
│   │   ├── database.py       # engine / session / Base
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── security.py       # bcrypt + JWT
│   │   ├── deps.py           # auth & RBAC dependencies
│   │   ├── order_rules.py    # status transition rules
│   │   ├── middleware.py     # request logging / timing
│   │   ├── tasks.py          # reminder background task
│   │   ├── ai_service.py     # OpenAI integration + rate limiter
│   │   ├── seed.py           # demo data
│   │   └── routers/          # auth, restaurants, orders, owner, delivery, ai
│   └── tests/                # pytest suite
└── frontend/
    ├── .env.example
    └── src/
        ├── api/              # axios client + endpoint wrappers
        ├── context/          # AuthContext, CartContext
        ├── components/       # Navbar, ProtectedRoute, Pagination, Modal, StatusTracker, …
        └── pages/            # Login, Register, Restaurants, RestaurantMenu, Cart,
                              # customer/*, owner/*, delivery/*
```

---

## Database

Tables (SQLAlchemy models in [`backend/app/models.py`](backend/app/models.py)):

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | All users, with a `role` column | 1→N orders (as customer), 1→N orders (as delivery partner), 1→N restaurants |
| `restaurants` | Restaurant profile | `owner_id → users`; 1→N menu items and orders |
| `menu_items` | Dishes (`is_available`, soft `is_deleted`) | `restaurant_id → restaurants` |
| `orders` | Order header: status, payment status, return status, total | `customer_id`, `delivery_partner_id → users`, `restaurant_id → restaurants` |
| `order_items` | Line items with a snapshot of name and price | `order_id → orders` |
| `reviews` | Rating 1–5 and comment | `order_id` **unique** (one review per order) |
| `payment_ledger` | `payment` / `refund` entries | `order_id → orders` (many per order) |
| `return_requests` | Reason, status, resolution note | `order_id` **unique** (one request per order) |
| `admin_reminder_logs` | Reminders for stale orders | `order_id → orders`, `restaurant_id → restaurants` |

**Setup:** tables are created automatically when the app starts (`Base.metadata.create_all`). The Docker container runs `python -m app.seed` before starting, which fills an empty database with demo data and does nothing if users already exist. To start over with a fresh database, run `docker compose down -v`.

### Demo accounts
All demo accounts use the password **`password123`**.

| Role | Email |
|---|---|
| Customer | `customer@campusbite.com`, `customer2@campusbite.com` |
| Restaurant owner | `owner@campusbite.com` (Spice Route), `owner2@` (Slice of Napoli), `owner3@` (Wok & Roll), `owner4@` (Green Bowl) |
| Delivery partner | `partner@campusbite.com`, `partner2@campusbite.com` |

The seed data includes an order history for the first customer, an active order at every stage, and one stale `PLACED` order, so the reminders panel has something to show straight away.

---

## Running locally

### Prerequisites
- Docker + Docker Compose
- Node.js 18+ and npm

### 1. Backend (Docker Compose)

```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD and JWT_SECRET, and optionally OPENAI_API_KEY
docker compose up --build
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

Stop it with `docker compose down`. Add `-v` to also delete the database volume.

### 2. Frontend

```bash
cd frontend
cp .env.example .env      # VITE_API_URL=http://localhost:8000/api
npm install
npm run dev
```

Open http://localhost:5173. The login page has one-click buttons for the demo accounts.

For a production build: `npm run build`. The output goes to `frontend/dist/`.

### Running the backend without Docker (optional)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # defaults to SQLite
python -m app.seed
uvicorn app.main:app --reload
```

### Tests

```bash
cd backend
pytest -q
```

The tests cover auth, RBAC, data isolation between users, the full order lifecycle, rejection of invalid transitions, cancellation rules, the review and return/refund flows (including duplicate requests), filters and pagination, stats, the reminder task, and the AI endpoint (OpenAI is mocked, and the tests check that only the caller's orders are sent).

---

## Environment variables

### Root `.env` (Docker Compose)

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | Database user | `campusbite` |
| `POSTGRES_PASSWORD` | Database password (**secret**) | — |
| `POSTGRES_DB` | Database name | `campusbite` |
| `JWT_SECRET` | Key used to sign JWTs (**secret**, long and random) | — |
| `JWT_EXPIRE_MINUTES` | How long a token is valid | `1440` |
| `OPENAI_API_KEY` | OpenAI key (**secret**). AI endpoint returns 503 if empty | — |
| `OPENAI_MODEL` | Model name | `gpt-4o-mini` |
| `AI_RATE_LIMIT_PER_MINUTE` | AI requests allowed per user per minute | `5` |
| `CORS_ORIGINS` | Allowed frontend origins, comma-separated | `http://localhost:5173` |
| `REMINDER_THRESHOLD_MINUTES` | Minutes before an order counts as stale | `15` |
| `REMINDER_INTERVAL_SECONDS` | How often the reminder task runs | `60` |

Docker Compose builds `DATABASE_URL` from the `POSTGRES_*` values. When running without Docker, set `DATABASE_URL` yourself in `backend/.env`.

### `frontend/.env`

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL, e.g. `http://localhost:8000/api` |

`.env` files are git-ignored and secrets are never baked into the Docker image (`.dockerignore` excludes `.env`). Only the `.env.example` files are committed.

---

## API documentation

FastAPI generates interactive docs at **`/docs`** (Swagger) and **`/redoc`**. All routes are under `/api`. Protected routes need `Authorization: Bearer <token>`.

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/auth/register` | public | Register (returns a token) |
| POST | `/auth/login` | public | Log in (returns a token) |
| GET | `/auth/me` | any | Current user |
| GET | `/restaurants` | public | List restaurants (`search`, `page`, `page_size`) |
| GET | `/restaurants/{id}` | public | Restaurant details and rating |
| GET | `/restaurants/{id}/menu` | public | Menu (`search`, `min_price`, `max_price`, `available_only`, `sort`, pagination) |
| GET | `/restaurants/{id}/reviews` | public | Reviews |
| POST | `/orders` | customer | Place an order (dummy payment → `mock_paid`) |
| GET | `/orders/my` | customer | Order history (`status`, `date_from`, `date_to`, pagination) |
| GET | `/orders/{id}` | owner of the order | Order details, including ledger, review and return |
| POST | `/orders/{id}/cancel` | customer | Cancel (PLACED only) |
| POST | `/orders/{id}/review` | customer | Review a delivered order |
| POST | `/orders/{id}/return` | customer | Request a return/refund |
| GET/PUT | `/owner/restaurant` | owner | View or update restaurant profile |
| GET/POST | `/owner/menu` | owner | List or add dishes |
| PUT/DELETE | `/owner/menu/{id}` | owner | Update or delete a dish |
| PATCH | `/owner/menu/{id}/availability` | owner | Toggle availability |
| GET | `/owner/orders` | owner | Restaurant orders (`status`, `date_from`, `date_to`, pagination) |
| PATCH | `/owner/orders/{id}/status` | owner | Set ACCEPTED / PREPARING / READY / CANCELLED |
| GET | `/owner/delivery-partners` | owner | List delivery partners |
| POST | `/owner/orders/{id}/assign` | owner | Assign a partner (READY → ASSIGNED) |
| GET | `/owner/stats` | owner | Restaurant statistics |
| GET | `/owner/returns` | owner | Return requests (`status`, pagination) |
| POST | `/owner/returns/{id}/approve` | owner | Approve and refund |
| POST | `/owner/returns/{id}/reject` | owner | Reject |
| GET | `/owner/reminders` | owner | Stale-order reminders |
| POST | `/owner/reminders/refresh` | owner | Run the reminder scan now |
| POST | `/owner/reminders/{id}/dismiss` | owner | Dismiss a reminder |
| GET | `/delivery/orders` | partner | Assigned orders (active by default, `status` filter) |
| PATCH | `/delivery/orders/{id}/status` | partner | Set OUT_FOR_DELIVERY / DELIVERED |
| GET | `/delivery/history` | partner | Completed deliveries |
| POST | `/ai/insights` | customer | AI summary or answer about your own orders |

Status codes used: `200/201/204` success, `400` invalid transition or business rule, `401` not authenticated, `403` wrong role, `404` not found or not yours, `409` duplicate (email, review, return), `422` validation error, `429` rate limited, `502/503` AI service problems.

---

## Deployment notes
- The backend image is self-contained. Supply environment variables from your hosting platform (Render, Railway, Fly.io, ECS, …) and point `DATABASE_URL` at a managed PostgreSQL database.
- The frontend is a static build (`npm run build`). Deploy `frontend/dist` to Netlify or Vercel, set `VITE_API_URL` when building, and add the frontend's URL to `CORS_ORIGINS`.
