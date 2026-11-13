from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import OrderStatus, PaymentStatus, ReturnStatus, UserRole

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


# ---------- Auth ----------
class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    role: UserRole = UserRole.CUSTOMER
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    # Only used when registering as a restaurant owner
    restaurant_name: str | None = Field(default=None, max_length=150)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    phone: str | None = None
    address: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Restaurants & menu ----------
class RestaurantOut(ORMModel):
    id: int
    name: str
    description: str | None = None
    cuisine: str | None = None
    address: str | None = None
    image_url: str | None = None
    avg_rating: float | None = None
    review_count: int = 0


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    cuisine: str | None = None
    address: str | None = None
    image_url: str | None = None


class MenuItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category: str | None = Field(default=None, max_length=80)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category: str | None = None
    image_url: str | None = None
    is_available: bool | None = None


class AvailabilityUpdate(BaseModel):
    is_available: bool


class MenuItemOut(ORMModel):
    id: int
    restaurant_id: int
    name: str
    description: str | None = None
    price: Decimal
    category: str | None = None
    image_url: str | None = None
    is_available: bool


# ---------- Orders ----------
class CartItem(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    restaurant_id: int
    items: list[CartItem] = Field(min_length=1)
    delivery_address: str = Field(min_length=3, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    payment_method: str = Field(default="dummy_card", max_length=32)

    @field_validator("items")
    @classmethod
    def unique_items(cls, v: list[CartItem]):
        ids = [i.menu_item_id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate menu items in cart; merge quantities instead")
        return v


class OrderItemOut(ORMModel):
    id: int
    menu_item_id: int | None
    name: str
    unit_price: Decimal
    quantity: int


class PaymentOut(ORMModel):
    id: int
    entry_type: str
    amount: Decimal
    status: str
    reference: str
    created_at: datetime


class ReviewOut(ORMModel):
    id: int
    order_id: int
    rating: int
    comment: str | None = None
    created_at: datetime
    customer_name: str | None = None


class ReturnOut(ORMModel):
    id: int
    order_id: int
    reason: str
    status: ReturnStatus
    resolution_note: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class PersonOut(ORMModel):
    id: int
    name: str
    phone: str | None = None
    address: str | None = None


class OrderOut(ORMModel):
    id: int
    customer_id: int
    restaurant_id: int
    restaurant_name: str | None = None
    delivery_partner_id: int | None = None
    status: OrderStatus
    payment_status: PaymentStatus
    return_status: ReturnStatus
    total_amount: Decimal
    delivery_address: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []
    has_review: bool = False


class OrderDetailOut(OrderOut):
    customer: PersonOut | None = None
    delivery_partner: PersonOut | None = None
    payments: list[PaymentOut] = []
    review: ReviewOut | None = None
    return_request: ReturnOut | None = None


class StatusUpdate(BaseModel):
    status: OrderStatus


class AssignPartner(BaseModel):
    delivery_partner_id: int


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReturnCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class ReturnDecision(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ReturnAdminOut(ReturnOut):
    customer_name: str | None = None
    order_total: Decimal | None = None


# ---------- Owner ----------
class ReminderOut(ORMModel):
    id: int
    order_id: int
    order_status: str
    message: str
    resolved: bool
    created_at: datetime


class TopDish(BaseModel):
    name: str
    quantity: int


class RestaurantStats(BaseModel):
    total_orders: int
    orders_today: int
    total_revenue: Decimal
    refunded_amount: Decimal
    avg_rating: float | None
    review_count: int
    status_counts: dict[str, int]
    top_dishes: list[TopDish]
    pending_returns: int
    open_reminders: int


# ---------- AI ----------
class InsightRequest(BaseModel):
    question: str | None = Field(default=None, max_length=500)


class InsightResponse(BaseModel):
    answer: str
    orders_considered: int
    model: str
