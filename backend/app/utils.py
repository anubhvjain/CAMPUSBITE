import math
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Query

from app.models import Order, Review
from app.schemas import OrderDetailOut, OrderOut, PersonOut, ReviewOut


def as_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo; treat naive datetimes as UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def paginate(query: Query, page: int, page_size: int, mapper=lambda x: x) -> dict:
    total = query.order_by(None).count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [mapper(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


def apply_order_filters(query: Query, status, date_from: date | None, date_to: date | None) -> Query:
    if status:
        query = query.filter(Order.status == status)
    if date_from:
        query = query.filter(Order.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.filter(Order.created_at < end)
    return query


def review_out(review: Review) -> ReviewOut:
    out = ReviewOut.model_validate(review)
    out.customer_name = review.customer.name if review.customer else None
    return out


def order_out(order: Order) -> OrderOut:
    out = OrderOut.model_validate(order)
    out.restaurant_name = order.restaurant.name if order.restaurant else None
    out.has_review = order.review is not None
    return out


def order_detail_out(order: Order) -> OrderDetailOut:
    out = OrderDetailOut.model_validate(order)
    out.restaurant_name = order.restaurant.name if order.restaurant else None
    out.customer = PersonOut.model_validate(order.customer) if order.customer else None
    out.delivery_partner = (
        PersonOut.model_validate(order.delivery_partner) if order.delivery_partner else None
    )
    out.review = review_out(order.review) if order.review else None
    out.has_review = order.review is not None
    return out
