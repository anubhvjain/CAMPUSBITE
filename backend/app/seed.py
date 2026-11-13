"""Seed demo data. Idempotent: skips if users already exist.

Run with:  python -m app.seed
"""
import uuid
from datetime import timedelta
from decimal import Decimal

from app.database import Base, SessionLocal, engine
from app.models import (
    LedgerType,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentLedger,
    PaymentStatus,
    Restaurant,
    Review,
    User,
    UserRole,
    utcnow,
)
from app.security import hash_password

DEMO_PASSWORD = "password123"

RESTAURANTS = [
    {
        "owner": ("Priya Sharma", "owner@campusbite.com"),
        "name": "Spice Route",
        "cuisine": "North Indian",
        "description": "Rich curries, tandoor breads and biryanis.",
        "address": "Block A, Campus Food Court",
        "image_url": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800",
        "menu": [
            ("Butter Chicken", "Creamy tomato gravy with tender chicken", "260", "Mains"),
            ("Paneer Tikka Masala", "Grilled cottage cheese in spiced gravy", "220", "Mains"),
            ("Chicken Biryani", "Fragrant basmati rice layered with chicken", "240", "Rice"),
            ("Dal Makhani", "Slow-cooked black lentils", "160", "Mains"),
            ("Garlic Naan", "Tandoor bread with garlic butter", "50", "Breads"),
            ("Gulab Jamun", "Two warm milk dumplings in syrup", "70", "Desserts"),
        ],
    },
    {
        "owner": ("Marco Rossi", "owner2@campusbite.com"),
        "name": "Slice of Napoli",
        "cuisine": "Italian",
        "description": "Wood-fired pizzas and fresh pasta.",
        "address": "Library Road, Shop 4",
        "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800",
        "menu": [
            ("Margherita Pizza", "Tomato, mozzarella, basil", "299", "Pizza"),
            ("Farmhouse Pizza", "Peppers, onion, mushroom, olives", "349", "Pizza"),
            ("Penne Arrabbiata", "Spicy tomato sauce", "249", "Pasta"),
            ("Alfredo Fettuccine", "Creamy parmesan sauce", "279", "Pasta"),
            ("Garlic Bread", "With cheese dip", "129", "Sides"),
            ("Tiramisu", "Classic coffee dessert", "189", "Desserts"),
        ],
    },
    {
        "owner": ("Kenji Tanaka", "owner3@campusbite.com"),
        "name": "Wok & Roll",
        "cuisine": "Asian",
        "description": "Noodles, dim sum and stir-fries.",
        "address": "Hostel Lane, Unit 2",
        "image_url": "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=800",
        "menu": [
            ("Hakka Noodles", "Wok-tossed noodles with veggies", "180", "Noodles"),
            ("Chilli Chicken", "Indo-Chinese classic", "230", "Starters"),
            ("Veg Momos", "Steamed dumplings (8 pcs)", "120", "Dim Sum"),
            ("Chicken Fried Rice", "Egg, chicken and spring onion", "200", "Rice"),
            ("Spring Rolls", "Crispy rolls (4 pcs)", "140", "Starters"),
        ],
    },
    {
        "owner": ("Aisha Khan", "owner4@campusbite.com"),
        "name": "Green Bowl",
        "cuisine": "Healthy",
        "description": "Salads, smoothie bowls and wraps.",
        "address": "Sports Complex Gate",
        "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800",
        "menu": [
            ("Quinoa Salad", "Quinoa, chickpeas, cucumber, feta", "210", "Salads"),
            ("Chicken Caesar Wrap", "Grilled chicken, romaine, caesar", "190", "Wraps"),
            ("Acai Bowl", "Acai, banana, granola, berries", "250", "Bowls"),
            ("Falafel Wrap", "Hummus, pickles, falafel", "170", "Wraps"),
            ("Cold-Pressed Juice", "Seasonal fruits", "120", "Drinks"),
        ],
    },
]

PARTNERS = [("Ravi Kumar", "partner@campusbite.com"), ("Sara Lee", "partner2@campusbite.com")]
CUSTOMERS = [("Aarav Mehta", "customer@campusbite.com"), ("Neha Gupta", "customer2@campusbite.com")]


def _ledger(order: Order, entry_type: LedgerType, prefix: str) -> PaymentLedger:
    return PaymentLedger(
        order_id=order.id,
        entry_type=entry_type,
        amount=order.total_amount,
        status="success",
        reference=f"MOCK-{prefix}-{uuid.uuid4().hex[:10].upper()}",
    )


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Seed skipped: data already present.")
            return
        pw = hash_password(DEMO_PASSWORD)

        customers = [
            User(name=n, email=e, hashed_password=pw, role=UserRole.CUSTOMER, phone="+91 98000 0000" + str(i),
                 address=f"Hostel {i + 1}, Room 10{i}")
            for i, (n, e) in enumerate(CUSTOMERS)
        ]
        partners = [
            User(name=n, email=e, hashed_password=pw, role=UserRole.DELIVERY_PARTNER, phone="+91 97000 0000" + str(i))
            for i, (n, e) in enumerate(PARTNERS)
        ]
        db.add_all(customers + partners)

        restaurants = []
        for spec in RESTAURANTS:
            owner = User(name=spec["owner"][0], email=spec["owner"][1], hashed_password=pw,
                         role=UserRole.RESTAURANT_OWNER, phone="+91 96000 00000")
            db.add(owner)
            db.flush()
            r = Restaurant(owner_id=owner.id, name=spec["name"], cuisine=spec["cuisine"],
                           description=spec["description"], address=spec["address"], image_url=spec["image_url"])
            r.menu_items = [
                MenuItem(name=n, description=d, price=Decimal(p), category=c) for n, d, p, c in spec["menu"]
            ]
            db.add(r)
            restaurants.append(r)
        db.flush()

        # Order history for the main demo customer so dashboards / AI insights have data
        now = utcnow()
        cust, partner = customers[0], partners[0]
        history = [
            # (restaurant idx, [(item idx, qty)], status, days_ago, minutes_ago_updated, review)
            (0, [(0, 1), (4, 2)], OrderStatus.DELIVERED, 12, None, (5, "Amazing butter chicken!")),
            (1, [(0, 1), (4, 1)], OrderStatus.DELIVERED, 9, None, (4, "Good pizza, a bit late.")),
            (0, [(2, 2)], OrderStatus.DELIVERED, 5, None, None),
            (2, [(0, 1), (2, 1)], OrderStatus.DELIVERED, 3, None, None),
            (3, [(2, 1)], OrderStatus.CANCELLED, 2, None, None),
            (0, [(1, 1), (4, 2), (5, 1)], OrderStatus.OUT_FOR_DELIVERY, 0, 10, None),
            (0, [(3, 1), (4, 1)], OrderStatus.READY, 0, 5, None),
            (0, [(0, 2)], OrderStatus.PLACED, 0, 25, None),  # stale -> triggers a reminder
            (1, [(2, 1)], OrderStatus.ACCEPTED, 0, 3, None),
        ]
        for r_idx, lines, status, days_ago, upd_min, review in history:
            r = restaurants[r_idx]
            created = now - timedelta(days=days_ago, minutes=(upd_min or 0) + 5)
            order = Order(customer_id=cust.id, restaurant_id=r.id, status=status, total_amount=Decimal("0"),
                          delivery_address=cust.address, created_at=created,
                          updated_at=now - timedelta(minutes=upd_min) if upd_min is not None else created + timedelta(minutes=40))
            total = Decimal("0")
            for m_idx, qty in lines:
                m = r.menu_items[m_idx]
                order.items.append(OrderItem(menu_item_id=m.id, name=m.name, unit_price=m.price, quantity=qty))
                total += m.price * qty
            order.total_amount = total
            if status in (OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED):
                order.delivery_partner_id = partner.id
            db.add(order)
            db.flush()
            db.add(_ledger(order, LedgerType.PAYMENT, "DUMMY_CARD"))
            order.payment_status = PaymentStatus.MOCK_PAID
            if status == OrderStatus.CANCELLED:
                db.add(_ledger(order, LedgerType.REFUND, "CANCEL"))
                order.payment_status = PaymentStatus.REFUNDED
            if review:
                db.add(Review(order_id=order.id, customer_id=cust.id, restaurant_id=r.id,
                              rating=review[0], comment=review[1]))
        db.commit()
        print("Seed complete. Demo password for all accounts:", DEMO_PASSWORD)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
