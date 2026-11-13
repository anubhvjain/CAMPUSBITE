from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session, selectinload

from app.ai_service import ask_openai, rate_limiter
from app.config import get_settings
from app.database import get_db
from app.deps import require_customer
from app.models import Order, User
from app.schemas import InsightRequest, InsightResponse

router = APIRouter(prefix="/ai", tags=["AI Insights"])
settings = get_settings()

MAX_ORDERS_IN_CONTEXT = 50


@router.post("/insights", response_model=InsightResponse)
async def order_insights(
    payload: InsightRequest, user: User = Depends(require_customer), db: Session = Depends(get_db)
):
    rate_limiter.check(user.id)
    # Context is strictly the authenticated customer's own orders
    orders = (
        db.query(Order)
        .options(selectinload(Order.items), selectinload(Order.restaurant))
        .filter(Order.customer_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(MAX_ORDERS_IN_CONTEXT)
        .all()
    )
    if not orders:
        return InsightResponse(
            answer="You haven't placed any orders yet, so there's nothing to analyse. Place an order and come back!",
            orders_considered=0,
            model=settings.openai_model,
        )
    today = datetime.now(timezone.utc).date().isoformat()
    answer = await run_in_threadpool(ask_openai, orders, payload.question, today)
    return InsightResponse(answer=answer, orders_considered=len(orders), model=settings.openai_model)
