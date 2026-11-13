# 🍔 CampusBite

CampusBite is a food ordering and delivery app I built for a campus setting. You can browse the restaurants around campus, order something, and watch it go from the kitchen to your door.

It has three kinds of users:

- **Customers** order food, track it, leave reviews, ask for refunds, and can ask an AI assistant questions about their own orders.
- **Restaurant owners** run their menu, push orders through the kitchen, hand them off to a delivery partner, deal with refund requests, and get nudged when an order has been sitting around too long.
- **Delivery partners** pick up the orders they're assigned and mark them delivered.

The frontend is React (with Vite). The backend is FastAPI with SQLAlchemy on PostgreSQL, and the whole backend runs in Docker Compose.

---

## Tech stack

- **Frontend:**
  - React 18 with hooks, plus a couple of custom ones
  - React Router 6
  - Axios
  - Vite
  - Plain responsive CSS (no UI framework)
- **Backend:**
  - Python 3.12, FastAPI, Pydantic v2
  - SQLAlchemy 2.0
  - JWT auth via `python-jose`
  - Password hashing with `bcrypt`
- **Database:** PostgreSQL 16 in Docker. Local dev and the tests fall back to SQLite.
- **AI:** the OpenAI Chat Completions API, using `gpt-4o-mini` by default.
- **Testing:** pytest with FastAPI's TestClient.

---

## Features

### Logging in and permissions

All three roles can register and log in. If you register as an owner, your restaurant is created at the same time.

Passwords are hashed with bcrypt. Logging in gives you a JWT (HS256) that carries your user id and role. The frontend keeps it in `localStorage`, and an Axios interceptor attaches it to every request. If the backend ever answers with a 401, you're logged out.

The frontend hides pages you aren't allowed to see, but the real checks happen on the backend. Every protected route goes through a `require_role(...)` dependency, and there are ownership checks on top of that:

- **Customers** only ever see their own orders. Ask for someone else's and you get a 404, as if it doesn't exist.
- **Owners** can only touch their own restaurant: its menu, orders, refunds and reminders.
- **Delivery partners** only see orders assigned to them.

### As a customer

**Finding food**
- Browse restaurants with search, pagination and an average rating for each.
- Inside a restaurant, search dishes by name, filter by price and availability, and sort by name or price.

**Ordering**
- Your cart lives in React Context and is saved to localStorage, so it survives a refresh. It holds items from one restaurant at a time.
- Checkout uses a **dummy payment**. No real money is involved. The order is created, a `payment` entry goes into the ledger, and the order is marked `mock_paid`.

**After you've ordered**
- Your dashboard lists past orders. You can filter it by status and date, and it's paginated.
- Each order has a tracking page with a visual progress tracker and its payment history.
- You can cancel while the order is still `PLACED`. The payment is reversed automatically.
- Once it's delivered, you can leave one review and one return/refund request per order. A refund request needs a reason.

**AI assistant**
- Ask questions about your past orders, or just ask for a summary.

### As a restaurant owner

**Dashboard**
- Total orders, orders today, revenue, refunded amount, average rating, a count of orders in each status, and your best-selling dishes.

**Reminders**
- A background task flags any order stuck in `PLACED` or `ACCEPTED` for more than 15 minutes.
- You can dismiss reminders, or run the check yourself instead of waiting for the next one.

**Menu**
- Add, edit and delete dishes, and switch them on or off.
- Deleting is a soft delete, so old orders still show what was ordered.

**Orders**
- Filter by status and date.
- Accept an order, start preparing it, mark it ready, or reject it.
- Once it's ready, assign a delivery partner.

**Refunds**
- **Approve:** a `refund` entry goes into the ledger, the payment status becomes `refunded`, and the order becomes `REFUNDED`.
- **Reject:** the return status becomes `rejected`.
- Either way you can leave a note.

### As a delivery partner

- You get a list of your assigned orders with the customer's name, phone number, address and what they ordered. It can be filtered by status.
- Move each one from `ASSIGNED` to `OUT_FOR_DELIVERY` to `DELIVERED`.
- There's a paginated history of everything you've delivered.

### How an order moves

```
PLACED → ACCEPTED → PREPARING → READY → ASSIGNED → OUT_FOR_DELIVERY → DELIVERED
   └→ CANCELLED                                                   └→ REFUNDED (return approved)
```

| Step | Who does it |
|---|---|
| PLACED → ACCEPTED, PREPARING, READY | The owner |
| READY → ASSIGNED | The owner, by assigning a delivery partner (it has to be an actual delivery partner) |
| ASSIGNED → OUT_FOR_DELIVERY → DELIVERED | Only the delivery partner it was assigned to |
| PLACED → CANCELLED | The customer or the owner, and only from `PLACED` |
| DELIVERED → REFUNDED | Happens automatically when the owner approves a refund |

Anything that skips a step gets a **400**. A step taken by the wrong role gets a **403**. All of these rules are in one place: [`backend/app/order_rules.py`](backend/app/order_rules.py).

### The AI assistant

The endpoint is `POST /api/ai/insights`, with an optional `question` field. Leave the question out and you get a summary of your orders.

When a request comes in, the backend:
1. Pulls the 50 most recent orders belonging to **the logged-in customer and nobody else**: items, totals, statuses and dates.
2. Sends them to OpenAI as JSON context.
3. Returns the answer.

The OpenAI key comes from the `OPENAI_API_KEY` environment variable and never reaches the browser.

| When this happens | You get |
|---|---|
| The key is missing or wrong | 503 |
| OpenAI rate-limits us | 429 |
| OpenAI fails in some other way | 502 |
| One user sends more than `AI_RATE_LIMIT_PER_MINUTE` requests a minute (default 5) | 429 with a `Retry-After` header |

The per-user limit is a small in-memory limiter.

Some questions to try:
- *"Summarize my last five orders"*
- *"Which of my orders haven't been delivered yet?"*
- *"How much did I spend this week?"*
- *"What do I order the most?"*

### Behind the scenes

- **Request logging:** `RequestLoggingMiddleware` logs the method, path, status and response time of every request. It also adds `X-Process-Time` and `X-Request-ID` headers to each response.
- **CORS:** configured through `CORS_ORIGINS`.
- **Reminder loop:**
  - Starts with the app and runs every `REMINDER_INTERVAL_SECONDS`.
  - Looks for `PLACED` or `ACCEPTED` orders that haven't changed in `REMINDER_THRESHOLD_MINUTES` (15 by default).
  - Writes a reminder to `admin_reminder_logs`, at most one per order and status.
  - A reminder clears itself once its order moves on.

---

## Project structure

```
campusbite/
├── docker-compose.yml        # postgres + backend
├── .env.example              # variables docker-compose uses
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example          # for running without Docker
│   ├── app/
│   │   ├── main.py           # app setup, lifespan, middleware, routers
│   │   ├── config.py         # settings (pydantic-settings)
│   │   ├── database.py       # engine, session, Base
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── security.py       # bcrypt + JWT
│   │   ├── deps.py           # auth and role checks
│   │   ├── order_rules.py    # which status changes are allowed
│   │   ├── middleware.py     # request logging and timing
│   │   ├── tasks.py          # the reminder loop
│   │   ├── ai_service.py     # OpenAI call + rate limiter
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

The models are in [`backend/app/models.py`](backend/app/models.py).

| Table | What's in it |
|---|---|
| `users` | Everyone, with a `role` column. A user can have orders as a customer, deliveries as a partner, or a restaurant as an owner. |
| `restaurants` | One per owner (`owner_id`), along with its menu items and orders |
| `menu_items` | Dishes, with an availability flag and a soft-delete flag |
| `orders` | The main order record: status, payment status, return status, total, plus links to the customer, the restaurant and the delivery partner |
| `order_items` | The lines of an order. The dish name and price are copied in, so later menu edits don't change old orders. |
| `reviews` | A 1–5 rating and a comment, with at most one per order |
| `payment_ledger` | `payment` and `refund` entries (an order can have several) |
| `return_requests` | Reason, status and the owner's note, with at most one per order |
| `admin_reminder_logs` | Reminders about orders that have been sitting too long |

**Setup:**
- You don't need to run migrations. The tables are created when the app starts.
- The Docker container runs `python -m app.seed` before starting. It fills an empty database with demo data and leaves it alone if there are already users.
- To start fresh, run `docker compose down -v`.

### Demo accounts

Every demo account uses the password **`password123`**.

| Role | Email |
|---|---|
| Customer | `customer@campusbite.com`, `customer2@campusbite.com` |
| Restaurant owner | `owner@campusbite.com` (Spice Route), `owner2@` (Slice of Napoli), `owner3@` (Wok & Roll), `owner4@` (Green Bowl) |
| Delivery partner | `partner@campusbite.com`, `partner2@campusbite.com` |

The first customer already has a few past orders. There's also an active order at most stages of the flow, plus one order that's been stuck in `PLACED` for a while, so the reminders panel has something in it the first time you log in.

---

## Running it locally

You'll need Docker (with Compose), and Node.js 18+ with npm.

### 1. Start the backend

```bash
cp .env.example .env
# open .env and set POSTGRES_PASSWORD and JWT_SECRET (OPENAI_API_KEY is optional)
docker compose up --build
```

Once it's up:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

`docker compose down` stops it. Add `-v` if you also want to delete the database.

### 2. Start the frontend

```bash
cd frontend
cp .env.example .env      # VITE_API_URL=http://localhost:8000/api
npm install
npm run dev
```

Go to http://localhost:5173. The login page has buttons that log you in as each demo account, so you don't have to type anything.

For a production build, run `npm run build`. The output goes to `frontend/dist/`.

### No Docker? That's fine too

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # uses SQLite by default
python -m app.seed
uvicorn app.main:app --reload
```

### Tests

```bash
cd backend
pytest -q
```

The tests cover:
- signing up and logging in
- role checks, and making sure users can't see each other's data
- the full order flow, including rejecting invalid steps
- the cancellation rules
- reviews and refunds, including duplicate requests
- filters and pagination
- the stats
- the reminder task
- the AI endpoint (OpenAI is mocked, and the test checks that only the caller's own orders are sent)

---

## Environment variables

### Root `.env` (for Docker Compose)

| Variable | What it does | Example |
|---|---|---|
| `POSTGRES_USER` | Database user | `campusbite` |
| `POSTGRES_PASSWORD` | Database password (keep it secret) | — |
| `POSTGRES_DB` | Database name | `campusbite` |
| `JWT_SECRET` | Key used to sign login tokens. Make it long and random, and keep it secret. | — |
| `JWT_EXPIRE_MINUTES` | How long a login lasts | `1440` |
| `OPENAI_API_KEY` | Your OpenAI key (keep it secret). Without it the AI endpoint returns 503. | — |
| `OPENAI_MODEL` | Which model to use | `gpt-4o-mini` |
| `AI_RATE_LIMIT_PER_MINUTE` | AI requests each user can make per minute | `5` |
| `CORS_ORIGINS` | Frontend URLs allowed to call the API, comma-separated | `http://localhost:5173` |
| `REMINDER_THRESHOLD_MINUTES` | Minutes before an order counts as stuck | `15` |
| `REMINDER_INTERVAL_SECONDS` | How often the reminder check runs | `60` |

Docker Compose builds `DATABASE_URL` from the `POSTGRES_*` values for you. If you run the backend without Docker, set `DATABASE_URL` yourself in `backend/.env`.

### `frontend/.env`

The frontend only needs `VITE_API_URL`, which points at the backend, for example `http://localhost:8000/api`.

`.env` files are git-ignored, and `.dockerignore` keeps them out of the Docker image, so secrets don't end up in either. Only the `.env.example` files are committed.

---

## API

FastAPI generates interactive docs at **`/docs`** (Swagger) and **`/redoc`**. Every route below is under `/api`. Protected routes need an `Authorization: Bearer <token>` header.

| Method | Endpoint | Who can call it | What it does |
|---|---|---|---|
| POST | `/auth/register` | anyone | Sign up and get a token |
| POST | `/auth/login` | anyone | Log in and get a token |
| GET | `/auth/me` | any logged-in user | Who am I? |
| GET | `/restaurants` | anyone | List restaurants (`search`, `page`, `page_size`) |
| GET | `/restaurants/{id}` | anyone | One restaurant, with its rating |
| GET | `/restaurants/{id}/menu` | anyone | Its menu (`search`, `min_price`, `max_price`, `available_only`, `sort`, pagination) |
| GET | `/restaurants/{id}/reviews` | anyone | Its reviews |
| POST | `/orders` | customer | Place an order (dummy payment, ends up `mock_paid`) |
| GET | `/orders/my` | customer | Your orders (`status`, `date_from`, `date_to`, pagination) |
| GET | `/orders/{id}` | the customer who placed it | Full details: payments, review and refund request |
| POST | `/orders/{id}/cancel` | customer | Cancel (only while `PLACED`) |
| POST | `/orders/{id}/review` | customer | Review a delivered order |
| POST | `/orders/{id}/return` | customer | Ask for a refund |
| GET/PUT | `/owner/restaurant` | owner | View or edit your restaurant |
| GET/POST | `/owner/menu` | owner | List or add dishes |
| PUT/DELETE | `/owner/menu/{id}` | owner | Edit or delete a dish |
| PATCH | `/owner/menu/{id}/availability` | owner | Switch a dish on or off |
| GET | `/owner/orders` | owner | Your restaurant's orders (`status`, `date_from`, `date_to`, pagination) |
| PATCH | `/owner/orders/{id}/status` | owner | Move to ACCEPTED, PREPARING, READY or CANCELLED |
| GET | `/owner/delivery-partners` | owner | List delivery partners |
| POST | `/owner/orders/{id}/assign` | owner | Assign a partner (READY → ASSIGNED) |
| GET | `/owner/stats` | owner | Dashboard numbers |
| GET | `/owner/returns` | owner | Refund requests (`status`, pagination) |
| POST | `/owner/returns/{id}/approve` | owner | Approve and refund |
| POST | `/owner/returns/{id}/reject` | owner | Reject |
| GET | `/owner/reminders` | owner | Reminders about stuck orders |
| POST | `/owner/reminders/refresh` | owner | Run the reminder check now |
| POST | `/owner/reminders/{id}/dismiss` | owner | Dismiss a reminder |
| GET | `/delivery/orders` | delivery partner | Your assigned orders (active by default, `status` filter) |
| PATCH | `/delivery/orders/{id}/status` | delivery partner | Move to OUT_FOR_DELIVERY or DELIVERED |
| GET | `/delivery/history` | delivery partner | Your completed deliveries |
| POST | `/ai/insights` | customer | Ask the AI about your orders |

| Status code | Meaning |
|---|---|
| 200 / 201 / 204 | It worked |
| 400 | You broke a rule, like skipping a step |
| 401 | You're not logged in |
| 403 | Your role isn't allowed to do that |
| 404 | It doesn't exist, or it isn't yours |
| 409 | Duplicate: an email that's already taken, a second review, or a second refund request |
| 422 | Bad input |
| 429 | Slow down |
| 502 / 503 | The AI service is having trouble |

---

## Deploying

**Backend**
- The Docker image has everything it needs.
- Set the environment variables on whatever host you use (Render, Railway, Fly.io, ECS…).
- Point `DATABASE_URL` at a managed PostgreSQL database.

**Frontend**
- It's a static build.
- Run `npm run build` with `VITE_API_URL` set to your deployed API.
- Upload `frontend/dist` to Netlify or Vercel.
- Add the frontend's URL to `CORS_ORIGINS` on the backend.
