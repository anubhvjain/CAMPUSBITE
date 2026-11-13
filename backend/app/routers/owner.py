import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_owner_restaurant, require_owner
from app.models import (
    LedgerType,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentLedger,
    PaymentStatus,
    ReminderLog,
    Restaurant,
    ReturnRequest,
    ReturnStatus,
    Review,
    User,
    UserRole,
    utcnow,
)
from app.order_rules import OWNER_STATUS_TARGETS, ensure_transition
from app.schemas import (
    AssignPartner,
    AvailabilityUpdate,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    OrderDetailOut,
    OrderOut,
    Page,
    PersonOut,
    ReminderOut,
    RestaurantOut,
    RestaurantStats,
    RestaurantUpdate,
    ReturnAdminOut,
    ReturnDecision,
    StatusUpdate,
    TopDish,
)
from app.tasks import generate_reminders, resolve_reminders
from app.utils import apply_order_filters, order_detail_out, order_out, paginate

router = APIRouter(prefix="/owner", tags=["Restaurant Owner"], dependencies=[Depends(require_owner)])


def _menu_item(db: Session, item_id: int, restaurant: Restaurant) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if not item or item.restaurant_id != restaurant.id or item.is_deleted:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


def _order(db: Session, order_id: int, restaurant: Restaurant) -> Order:
    order = db.get(Order, order_id)
    if not order or order.restaurant_id != restaurant.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ---------- Restaurant profile ----------
@router.get("/restaurant", response_model=RestaurantOut)
def my_restaurant(restaurant: Restaurant = Depends(get_owner_restaurant)):
    return restaurant


@router.put("/restaurant", response_model=RestaurantOut)
def update_restaurant(
    payload: RestaurantUpdate, restaurant: Restaurant = Depends(get_owner_restaurant), db: Session = Depends(get_db)
):
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(restaurant, k, v)
    db.commit()
    db.refresh(restaurant)
    return restaurant


# ---------- Menu ----------
@router.get("/menu", response_model=Page[MenuItemOut])
def list_menu(
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    q = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id, MenuItem.is_deleted.is_(False))
    if search:
        q = q.filter(MenuItem.name.ilike(f"%{search.strip()}%"))
    return paginate(q.order_by(MenuItem.category, MenuItem.name), page, page_size)


@router.post("/menu", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    payload: MenuItemCreate, restaurant: Restaurant = Depends(get_owner_restaurant), db: Session = Depends(get_db)
):
    item = MenuItem(restaurant_id=restaurant.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/menu/{item_id}", response_model=MenuItemOut)
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    item = _menu_item(db, item_id, restaurant)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/menu/{item_id}/availability", response_model=MenuItemOut)
def set_availability(
    item_id: int,
    payload: AvailabilityUpdate,
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    item = _menu_item(db, item_id, restaurant)
    item.is_available = payload.is_available
    db.commit()
    db.refresh(item)
    return item


@router.delete("/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: int, restaurant: Restaurant = Depends(get_owner_restaurant), db: Session = Depends(get_db)
):
    item = _menu_item(db, item_id, restaurant)
    # Soft delete keeps historical order items intact
    item.is_deleted = True
    item.is_available = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Orders ----------
@router.get("/orders", response_model=Page[OrderOut])
def list_orders(
    status: OrderStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    q = db.query(Order).options(selectinload(Order.items)).filter(Order.restaurant_id == restaurant.id)
    q = apply_order_filters(q, status, date_from, date_to).order_by(Order.created_at.desc(), Order.id.desc())
    return paginate(q, page, page_size, order_out)


@router.get("/orders/{order_id}", response_model=OrderDetailOut)
def get_order(order_id: int, restaurant: Restaurant = Depends(get_owner_restaurant), db: Session = Depends(get_db)):
    return order_detail_out(_order(db, order_id, restaurant))


@router.patch("/orders/{order_id}/status", response_model=OrderDetailOut)
def update_order_status(
    order_id: int,
    payload: StatusUpdate,
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    order = _order(db, order_id, restaurant)
    if payload.status not in OWNER_STATUS_TARGETS:
        raise HTTPException(
            status_code=400,
            detail=f"Owners cannot set status {payload.status.value} here"
            + (" (use the assign endpoint)" if payload.status == OrderStatus.ASSIGNED else ""),
        )
    ensure_transition(order.status, payload.status, UserRole.RESTAURANT_OWNER)
    order.status = payload.status
    order.updated_at = utcnow()
    if payload.status == OrderStatus.CANCELLED and order.payment_status == PaymentStatus.MOCK_PAID:
        db.add(
            PaymentLedger(
                order_id=order.id,
                entry_type=LedgerType.REFUND,
                amount=order.total_amount,
                status="success",
                reference=f"MOCK-CANCEL-{uuid.uuid4().hex[:10].upper()}",
            )
        )
        order.payment_status = PaymentStatus.REFUNDED
    resolve_reminders(db, order.id)
    db.commit()
    db.refresh(order)
    return order_detail_out(order)


@router.get("/delivery-partners", response_model=list[PersonOut])
def delivery_partners(db: Session = Depends(get_db)):
    return db.query(User).filter(User.role == UserRole.DELIVERY_PARTNER).order_by(User.name).all()


@router.post("/orders/{order_id}/assign", response_model=OrderDetailOut)
def assign_partner(
    order_id: int,
    payload: AssignPartner,
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    order = _order(db, order_id, restaurant)
    partner = db.get(User, payload.delivery_partner_id)
    if not partner or partner.role != UserRole.DELIVERY_PARTNER:
        raise HTTPException(status_code=400, detail="Selected user is not a delivery partner")
    if order.status != OrderStatus.READY:
        raise HTTPException(
            status_code=400, detail=f"Delivery partners can only be assigned to READY orders (current: {order.status.value})"
        )
    ensure_transition(order.status, OrderStatus.ASSIGNED, UserRole.RESTAURANT_OWNER)
    order.delivery_partner_id = partner.id
    order.status = OrderStatus.ASSIGNED
    order.updated_at = utcnow()
    db.commit()
    db.refresh(order)
    return order_detail_out(order)


# ---------- Stats ----------
@router.get("/stats", response_model=RestaurantStats)
def stats(restaurant: Restaurant = Depends(get_owner_restaurant), db: Session = Depends(get_db)):
    rid = restaurant.id
    status_counts = {s.value: 0 for s in OrderStatus}
    for st, cnt in db.query(Order.status, func.count(Order.id)).filter(Order.restaurant_id == rid).group_by(Order.status):
        status_counts[st.value] = cnt
    total_orders = sum(status_counts.values())

    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    orders_today = db.query(func.count(Order.id)).filter(Order.restaurant_id == rid, Order.created_at >= today_start).scalar()

    revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.restaurant_id == rid, Order.payment_status == PaymentStatus.MOCK_PAID)
        .scalar()
    )
    refunded = (
        db.query(func.coalesce(func.sum(PaymentLedger.amount), 0))
        .join(Order, Order.id == PaymentLedger.order_id)
        .filter(Order.restaurant_id == rid, PaymentLedger.entry_type == LedgerType.REFUND)
        .scalar()
    )
    avg_rating, review_count = (
        db.query(func.avg(Review.rating), func.count(Review.id)).filter(Review.restaurant_id == rid).one()
    )
    top = (
        db.query(OrderItem.name, func.sum(OrderItem.quantity).label("qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.restaurant_id == rid, Order.status != OrderStatus.CANCELLED)
        .group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    pending_returns = (
        db.query(func.count(ReturnRequest.id))
        .filter(ReturnRequest.restaurant_id == rid, ReturnRequest.status == ReturnStatus.REQUESTED)
        .scalar()
    )
    open_reminders = (
        db.query(func.count(ReminderLog.id))
        .filter(ReminderLog.restaurant_id == rid, ReminderLog.resolved.is_(False))
        .scalar()
    )
    return RestaurantStats(
        total_orders=total_orders,
        orders_today=orders_today or 0,
        total_revenue=Decimal(revenue or 0),
        refunded_amount=Decimal(refunded or 0),
        avg_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        review_count=review_count,
        status_counts=status_counts,
        top_dishes=[TopDish(name=n, quantity=int(q)) for n, q in top],
        pending_returns=pending_returns or 0,
        open_reminders=open_reminders or 0,
    )


# ---------- Returns ----------
def _return_out(r: ReturnRequest) -> ReturnAdminOut:
    out = ReturnAdminOut.model_validate(r)
    out.customer_name = r.order.customer.name if r.order and r.order.customer else None
    out.order_total = r.order.total_amount if r.order else None
    return out


@router.get("/returns", response_model=Page[ReturnAdminOut])
def list_returns(
    status: ReturnStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    q = db.query(ReturnRequest).filter(ReturnRequest.restaurant_id == restaurant.id)
    if status:
        q = q.filter(ReturnRequest.status == status)
    return paginate(q.order_by(ReturnRequest.created_at.desc()), page, page_size, _return_out)


def _pending_return(db: Session, return_id: int, restaurant: Restaurant) -> ReturnRequest:
    req = db.get(ReturnRequest, return_id)
    if not req or req.restaurant_id != restaurant.id:
        raise HTTPException(status_code=404, detail="Return request not found")
    if req.status != ReturnStatus.REQUESTED:
        raise HTTPException(status_code=409, detail=f"Return request already {req.status.value}")
    return req


@router.post("/returns/{return_id}/approve", response_model=ReturnAdminOut)
def approve_return(
    return_id: int,
    payload: ReturnDecision | None = None,
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    req = _pending_return(db, return_id, restaurant)
    order = req.order
    req.status = ReturnStatus.APPROVED
    req.resolution_note = payload.note if payload else None
    req.resolved_at = utcnow()
    order.return_status = ReturnStatus.APPROVED
    order.payment_status = PaymentStatus.REFUNDED
    order.status = OrderStatus.REFUNDED
    order.updated_at = utcnow()
    db.add(
        PaymentLedger(
            order_id=order.id,
            entry_type=LedgerType.REFUND,
            amount=order.total_amount,
            status="success",
            reference=f"MOCK-REFUND-{uuid.uuid4().hex[:10].upper()}",
        )
    )
    db.commit()
    db.refresh(req)
    return _return_out(req)


@router.post("/returns/{return_id}/reject", response_model=ReturnAdminOut)
def reject_return(
    return_id: int,
    payload: ReturnDecision | None = None,
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    req = _pending_return(db, return_id, restaurant)
    req.status = ReturnStatus.REJECTED
    req.resolution_note = payload.note if payload else None
    req.resolved_at = utcnow()
    req.order.return_status = ReturnStatus.REJECTED
    req.order.updated_at = utcnow()
    db.commit()
    db.refresh(req)
    return _return_out(req)


# ---------- Reminders ----------
@router.get("/reminders", response_model=Page[ReminderOut])
def list_reminders(
    include_resolved: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    restaurant: Restaurant = Depends(get_owner_restaurant),
    db: Session = Depends(get_db),
):
    q = db.query(ReminderLog).filter(ReminderLog.restaurant_id == restaurant.id)
    if not include_resolved:
        q = q.filter(ReminderLog.resolved.is_(False))
    return paginate(q.order_by(ReminderLog.created_at.desc()), page, page_size)


@router.post("/reminders/refresh", response_model=dict)
def refresh_reminders(db: Session = Depends(get_db)):
    """Manually trigger the stale-order scan (the background loop also runs it periodically)."""
    return {"created": generate_reminders(db)}


@router.post("/reminders/{reminder_id}/dismiss", response_model=ReminderOut)
def dismiss_reminder(
    reminder_id: int, restaurant: Restaurant = Depends(get_owner_restaurant), db: Session = Depends(get_db)
):
    rem = db.get(ReminderLog, reminder_id)
    if not rem or rem.restaurant_id != restaurant.id:
        raise HTTPException(status_code=404, detail="Reminder not found")
    rem.resolved = True
    db.commit()
    db.refresh(rem)
    return rem
