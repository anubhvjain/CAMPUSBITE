from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Restaurant, User, UserRole
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise unauthorized
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise unauthorized
    return user


def require_role(*roles: UserRole):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


require_customer = require_role(UserRole.CUSTOMER)
require_owner = require_role(UserRole.RESTAURANT_OWNER)
require_partner = require_role(UserRole.DELIVERY_PARTNER)


def get_owner_restaurant(
    user: User = Depends(require_owner), db: Session = Depends(get_db)
) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.owner_id == user.id).first()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="No restaurant linked to this owner")
    return restaurant
