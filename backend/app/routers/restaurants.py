from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MenuItem, Restaurant, Review
from app.schemas import MenuItemOut, Page, RestaurantOut, ReviewOut
from app.utils import paginate, review_out

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


def _rating_map(db: Session, ids: list[int]) -> dict[int, tuple[float, int]]:
    if not ids:
        return {}
    rows = (
        db.query(Review.restaurant_id, func.avg(Review.rating), func.count(Review.id))
        .filter(Review.restaurant_id.in_(ids))
        .group_by(Review.restaurant_id)
        .all()
    )
    return {rid: (round(float(avg), 2), cnt) for rid, avg, cnt in rows}


def _restaurant_out(r: Restaurant, ratings: dict) -> RestaurantOut:
    out = RestaurantOut.model_validate(r)
    if r.id in ratings:
        out.avg_rating, out.review_count = ratings[r.id]
    return out


@router.get("", response_model=Page[RestaurantOut])
def list_restaurants(
    search: str | None = None,
    cuisine: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Restaurant)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(Restaurant.name.ilike(like), Restaurant.cuisine.ilike(like)))
    if cuisine:
        q = q.filter(Restaurant.cuisine.ilike(cuisine))
    q = q.order_by(Restaurant.name)
    result = paginate(q, page, page_size)
    ratings = _rating_map(db, [r.id for r in result["items"]])
    result["items"] = [_restaurant_out(r, ratings) for r in result["items"]]
    return result


@router.get("/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    r = db.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return _restaurant_out(r, _rating_map(db, [r.id]))


@router.get("/{restaurant_id}/menu", response_model=Page[MenuItemOut])
def get_menu(
    restaurant_id: int,
    search: str | None = None,
    category: str | None = None,
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    available_only: bool = False,
    sort: str = Query("name", pattern="^(name|price_asc|price_desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if not db.get(Restaurant, restaurant_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price cannot exceed max_price")
    q = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id, MenuItem.is_deleted.is_(False))
    if search:
        q = q.filter(MenuItem.name.ilike(f"%{search.strip()}%"))
    if category:
        q = q.filter(MenuItem.category.ilike(category))
    if min_price is not None:
        q = q.filter(MenuItem.price >= min_price)
    if max_price is not None:
        q = q.filter(MenuItem.price <= max_price)
    if available_only:
        q = q.filter(MenuItem.is_available.is_(True))
    order = {"name": MenuItem.name, "price_asc": MenuItem.price.asc(), "price_desc": MenuItem.price.desc()}[sort]
    return paginate(q.order_by(order), page, page_size)


@router.get("/{restaurant_id}/reviews", response_model=Page[ReviewOut])
def get_reviews(
    restaurant_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(Review).filter(Review.restaurant_id == restaurant_id).order_by(Review.created_at.desc())
    return paginate(q, page, page_size, review_out)
