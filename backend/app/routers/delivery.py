from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_partner
from app.models import Order, OrderStatus, User, UserRole, utcnow
from app.order_rules import PARTNER_STATUS_TARGETS, ensure_transition
from app.schemas import OrderDetailOut, Page, StatusUpdate
from app.utils import order_detail_out, paginate

router = APIRouter(prefix="/delivery", tags=["Delivery Partner"])

ACTIVE = (OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY)
DONE = (OrderStatus.DELIVERED, OrderStatus.REFUNDED)


def _base(db: Session, user: User):
    return (
        db.query(Order)
        .options(selectinload(Order.items), selectinload(Order.customer), selectinload(Order.restaurant))
        .filter(Order.delivery_partner_id == user.id)
    )


@router.get("/orders", response_model=Page[OrderDetailOut])
def assigned_orders(
    status: OrderStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(require_partner),
    db: Session = Depends(get_db),
):
    q = _base(db, user)
    q = q.filter(Order.status == status) if status else q.filter(Order.status.in_(ACTIVE))
    return paginate(q.order_by(Order.updated_at.desc()), page, page_size, order_detail_out)


@router.get("/history", response_model=Page[OrderDetailOut])
def delivery_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(require_partner),
    db: Session = Depends(get_db),
):
    q = _base(db, user).filter(Order.status.in_(DONE)).order_by(Order.updated_at.desc())
    return paginate(q, page, page_size, order_detail_out)


@router.patch("/orders/{order_id}/status", response_model=OrderDetailOut)
def update_delivery_status(
    order_id: int, payload: StatusUpdate, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    order = db.get(Order, order_id)
    if not order or order.delivery_partner_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if payload.status not in PARTNER_STATUS_TARGETS:
        raise HTTPException(status_code=400, detail=f"Delivery partners cannot set status {payload.status.value}")
    ensure_transition(order.status, payload.status, UserRole.DELIVERY_PARTNER)
    order.status = payload.status
    order.updated_at = utcnow()
    db.commit()
    db.refresh(order)
    return order_detail_out(order)
