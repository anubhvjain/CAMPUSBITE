import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Order, OrderStatus, ReminderLog

logger = logging.getLogger("campusbite.tasks")
settings = get_settings()

STALE_STATUSES = (OrderStatus.PLACED, OrderStatus.ACCEPTED)


def generate_reminders(db: Session, threshold_minutes: int | None = None) -> int:
    """Create a reminder for every PLACED/ACCEPTED order not updated within the threshold.

    At most one reminder per order+status, so the loop doesn't spam duplicates
    and dismissed reminders stay dismissed.
    """
    threshold = threshold_minutes if threshold_minutes is not None else settings.reminder_threshold_minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold)
    stale = (
        db.query(Order)
        .filter(Order.status.in_(STALE_STATUSES), Order.updated_at < cutoff)
        .all()
    )
    created = 0
    for order in stale:
        exists = (
            db.query(ReminderLog.id)
            .filter(
                ReminderLog.order_id == order.id,
                ReminderLog.order_status == order.status.value,
            )
            .first()
        )
        if exists:
            continue
        db.add(
            ReminderLog(
                order_id=order.id,
                restaurant_id=order.restaurant_id,
                order_status=order.status.value,
                message=(
                    f"Order #{order.id} has been {order.status.value} for more than "
                    f"{threshold} minutes without an update."
                ),
            )
        )
        created += 1
    db.commit()
    return created


def resolve_reminders(db: Session, order_id: int) -> None:
    db.query(ReminderLog).filter(
        ReminderLog.order_id == order_id, ReminderLog.resolved.is_(False)
    ).update({ReminderLog.resolved: True}, synchronize_session=False)


async def reminder_loop(stop_event: asyncio.Event) -> None:
    logger.info("Reminder loop started (every %ss)", settings.reminder_interval_seconds)
    while not stop_event.is_set():
        try:
            db = SessionLocal()
            try:
                created = await asyncio.to_thread(generate_reminders, db)
                if created:
                    logger.info("Generated %d order reminder(s)", created)
            finally:
                db.close()
        except Exception:  # keep the loop alive no matter what
            logger.exception("Reminder generation failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.reminder_interval_seconds)
        except asyncio.TimeoutError:
            pass
