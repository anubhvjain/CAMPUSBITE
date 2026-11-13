import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_customer
from app.models import (
    LedgerType,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentLedger,
    PaymentStatus,
    Restaurant,
    ReturnRequest,
    ReturnStatus,
    Review,
    User,
    UserRole,
    utcnow,
)
from app.order_rules import ensure_transition
from app.schemas import (
    OrderCreate,
    OrderDetailOut,
    OrderOut,
    Page,
    ReturnCreate,
    ReturnOut,
    ReviewCreate,
    ReviewOut,
)
from app.tasks import resolve_reminders
from app.utils import apply_order_filters, order_detail_out, order_out, paginate, review_out

router = APIRouter(prefix="/orders", tags=["Customer Orders"])


def _get_customer_order(db: Session, order_id: int, customer: User) -> Order:
    order = db.get(Order, order_id)
    # 404 (not 403) so customers can't probe which order ids exist
    if not order or order.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("", response_model=OrderDetailOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    restaurant = db.get(Restaurant, payload.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    ids = [i.menu_item_id for i in payload.items]
    menu = {
        m.id: m
        for m in db.query(MenuItem).filter(
            MenuItem.id.in_(ids), MenuItem.restaurant_id == restaurant.id, MenuItem.is_deleted.is_(False)
        )
    }
    missing = [i for i in ids if i not in menu]
    if missing:
        raise HTTPException(status_code=400, detail=f"Menu items not found in this restaurant: {missing}")
    unavailable = [menu[i].name for i in ids if not menu[i].is_available]
    if unavailable:
        raise HTTPException(status_code=400, detail=f"Currently unavailable: {', '.join(unavailable)}")

    order = Order(
        customer_id=user.id,
        restaurant_id=restaurant.id,
        delivery_address=payload.delivery_address.strip(),
        notes=payload.notes,
        total_amount=Decimal("0"),
        status=OrderStatus.PLACED,
        payment_status=PaymentStatus.PENDING,
    )
    total = Decimal("0")
    for line in payload.items:
        m = menu[line.menu_item_id]
        order.items.append(OrderItem(menu_item_id=m.id, name=m.name, unit_price=m.price, quantity=line.quantity))
        total += m.price * line.quantity
    order.total_amount = total
    db.add(order)
    db.flush()

    # Dummy payment: always succeeds, recorded in the ledger
    db.add(
        PaymentLedger(
            order_id=order.id,
            entry_type=LedgerType.PAYMENT,
            amount=total,
            status="success",
            reference=f"MOCK-{payload.payment_method.upper()}-{uuid.uuid4().hex[:10].upper()}",
        )
    )
    order.payment_status = PaymentStatus.MOCK_PAID
    db.commit()
    db.refresh(order)
    return order_detail_out(order)


@router.get("/my", response_model=Page[OrderOut])
def my_orders(
    status: OrderStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    q = db.query(Order).options(selectinload(Order.items)).filter(Order.customer_id == user.id)
    q = apply_order_filters(q, status, date_from, date_to).order_by(Order.created_at.desc(), Order.id.desc())
    return paginate(q, page, page_size, order_out)


@router.get("/{order_id}", response_model=OrderDetailOut)
def order_detail(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    allowed = order is not None and (
        (user.role == UserRole.CUSTOMER and order.customer_id == user.id)
        or (user.role == UserRole.RESTAURANT_OWNER and order.restaurant.owner_id == user.id)
        or (user.role == UserRole.DELIVERY_PARTNER and order.delivery_partner_id == user.id)
    )
    if not allowed:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_detail_out(order)


@router.post("/{order_id}/cancel", response_model=OrderDetailOut)
def cancel_order(order_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    order = _get_customer_order(db, order_id, user)
    if order.status != OrderStatus.PLACED:
        raise HTTPException(
            status_code=400, detail=f"Order can only be cancelled while PLACED (current: {order.status.value})"
        )
    ensure_transition(order.status, OrderStatus.CANCELLED, user.role)
    order.status = OrderStatus.CANCELLED
    order.updated_at = utcnow()
    # The mock payment is reversed automatically on cancellation
    if order.payment_status == PaymentStatus.MOCK_PAID:
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


@router.post("/{order_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def review_order(
    order_id: int, payload: ReviewCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)
):
    order = _get_customer_order(db, order_id, user)
    if order.status not in (OrderStatus.DELIVERED, OrderStatus.REFUNDED):
        raise HTTPException(status_code=400, detail="Only delivered orders can be reviewed")
    if order.review:
        raise HTTPException(status_code=409, detail="This order has already been reviewed")
    review = Review(
        order_id=order.id,
        customer_id=user.id,
        restaurant_id=order.restaurant_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review_out(review)


@router.post("/{order_id}/return", response_model=ReturnOut, status_code=status.HTTP_201_CREATED)
def request_return(
    order_id: int, payload: ReturnCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)
):
    order = _get_customer_order(db, order_id, user)
    if order.return_request or order.return_status != ReturnStatus.NONE:
        raise HTTPException(status_code=409, detail="A return request already exists for this order")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Returns can only be requested after delivery")
    req = ReturnRequest(
        order_id=order.id,
        customer_id=user.id,
        restaurant_id=order.restaurant_id,
        reason=payload.reason.strip(),
    )
    order.return_status = ReturnStatus.REQUESTED
    order.updated_at = utcnow()
    db.add(req)
    db.commit()
    db.refresh(req)
    return req
