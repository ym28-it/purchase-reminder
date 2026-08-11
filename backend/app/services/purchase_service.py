from dataclasses import field
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.purchase import Purchase
from app.models.purchase import PurchaseItem, create_purchase_item, get_all_purchase_items


def get_all_purchases(
    user_id: str,
) -> list[Purchase]:
    purchase_items = get_all_purchase_items(user_id)
    return [item.to_domain() for item in purchase_items]


def create_purchase(
    user_id: str,
    name: str,
    category: str,
    speed: float,
    stock: float,
    is_temporary: bool,
) -> Purchase:
    purchase = Purchase(
        id=uuid4(),
        user_id=user_id,
        name=name,
        category=category,
        speed=speed,
        stock=stock,
        is_temporary=is_temporary,
        created_at=field(default_factory=lambda: datetime.now(UTC)),
        updated_at=field(default_factory=lambda: datetime.now(UTC)),
    )
    purchase_item = PurchaseItem.from_domain(purchase=purchase)
    created_item = create_purchase_item(item=purchase_item)
    return created_item.to_domain()
