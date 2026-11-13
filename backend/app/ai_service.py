import json
import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import get_settings
from app.models import Order

logger = logging.getLogger("campusbite.ai")
settings = get_settings()

SYSTEM_PROMPT = (
    "You are CampusBite's order insights assistant. You answer questions about ONE customer's "
    "food order history using only the JSON data provided. Amounts are in INR (₹). "
    "Be concise and friendly, use bullet points where helpful, and compute totals precisely. "
    "If the data does not contain the answer, say so. Never invent orders."
)
DEFAULT_QUESTION = "Give me a short summary of my order history and any useful insights."


class RateLimiter:
    """Sliding-window per-user limiter (in-memory, good enough for a single container)."""

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self.hits: dict[int, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: int) -> None:
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = int(self.window - (now - q[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many AI requests. Try again in {retry} seconds.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)


rate_limiter = RateLimiter(settings.ai_rate_limit_per_minute)


def build_order_context(orders: list[Order]) -> str:
    data = [
        {
            "order_id": o.id,
            "restaurant": o.restaurant.name if o.restaurant else None,
            "placed_at": o.created_at.isoformat(),
            "status": o.status.value,
            "payment_status": o.payment_status.value,
            "return_status": o.return_status.value,
            "total": float(o.total_amount),
            "items": [{"name": i.name, "qty": i.quantity, "unit_price": float(i.unit_price)} for i in o.items],
        }
        for o in orders
    ]
    return json.dumps(data, ensure_ascii=False)


def ask_openai(orders: list[Order], question: str | None, today_iso: str) -> str:
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="AI insights are not configured (missing OPENAI_API_KEY).")

    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key, timeout=30, max_retries=2)
    user_prompt = (
        f"Today's date (UTC): {today_iso}\n"
        f"My orders (newest first), JSON:\n{build_order_context(orders)}\n\n"
        f"Question: {question or DEFAULT_QUESTION}"
    )
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
    except openai.RateLimitError:
        logger.warning("OpenAI rate limit hit")
        raise HTTPException(status_code=429, detail="The AI service is busy right now. Please retry shortly.")
    except openai.AuthenticationError:
        logger.error("OpenAI authentication failed")
        raise HTTPException(status_code=503, detail="AI service authentication failed.")
    except openai.APIError as exc:
        logger.error("OpenAI API error: %s", exc)
        raise HTTPException(status_code=502, detail="The AI service returned an error. Please try again.")
    return (resp.choices[0].message.content or "").strip()
