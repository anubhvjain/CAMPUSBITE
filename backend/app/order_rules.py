from fastapi import HTTPException

from app.models import OrderStatus as S
from app.models import UserRole as R

# (from_status, to_status) -> roles allowed to perform the transition
TRANSITIONS: dict[tuple[S, S], set[R]] = {
    (S.PLACED, S.ACCEPTED): {R.RESTAURANT_OWNER},
    (S.PLACED, S.CANCELLED): {R.CUSTOMER, R.RESTAURANT_OWNER},
    (S.ACCEPTED, S.PREPARING): {R.RESTAURANT_OWNER},
    (S.PREPARING, S.READY): {R.RESTAURANT_OWNER},
    (S.READY, S.ASSIGNED): {R.RESTAURANT_OWNER},
    (S.ASSIGNED, S.OUT_FOR_DELIVERY): {R.DELIVERY_PARTNER},
    (S.OUT_FOR_DELIVERY, S.DELIVERED): {R.DELIVERY_PARTNER},
}

# Transitions the owner may trigger through the generic status endpoint
OWNER_STATUS_TARGETS = {S.ACCEPTED, S.PREPARING, S.READY, S.CANCELLED}
PARTNER_STATUS_TARGETS = {S.OUT_FOR_DELIVERY, S.DELIVERED}

ACTIVE_STATUSES = {S.PLACED, S.ACCEPTED, S.PREPARING, S.READY, S.ASSIGNED, S.OUT_FOR_DELIVERY}


def next_statuses(current: S, role: R) -> list[S]:
    return [to for (frm, to), roles in TRANSITIONS.items() if frm == current and role in roles]


def ensure_transition(current: S, target: S, role: R) -> None:
    roles = TRANSITIONS.get((current, target))
    if roles is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from {current.value} to {target.value}",
        )
    if role not in roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role {role.value} cannot move an order from {current.value} to {target.value}",
        )
