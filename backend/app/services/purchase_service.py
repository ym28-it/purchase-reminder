from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.purchase import Purchase
from app.models.purchase import (
    PurchaseItem,
    create_purchase_item,
    delete_purchase_item,
    get_all_purchase_items,
    get_purchase_item,
    put_purchase_item,
)


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
    now = datetime.now(UTC)
    purchase = Purchase(
        id=uuid4(),
        user_id=user_id,
        name=name,
        category=category,
        speed=speed,
        stock=stock,
        is_temporary=is_temporary,
        created_at=now,
        updated_at=now,
    )
    purchase_item = PurchaseItem.from_domain(purchase=purchase)
    created_item = create_purchase_item(item=purchase_item)
    return created_item.to_domain()


def put_purchase(
    user_id: str,
    id: UUID,
    name: str,
    category: str,
    speed: float,
    stock: float,
    is_temporary: bool,
) -> Purchase:
    existing_item = get_purchase_item(user_id, id)
    purchase = Purchase(
        id=id,
        user_id=user_id,
        name=name,
        category=category,
        speed=speed,
        stock=stock,
        is_temporary=is_temporary,
        created_at=existing_item.created_at,
        updated_at=datetime.now(UTC),
    )
    purchase_item = PurchaseItem.from_domain(purchase=purchase)
    put_item = put_purchase_item(item=purchase_item)
    return put_item.to_domain()


def delete_purchase(
    user_id: str,
    id: UUID,
) -> None:
    delete_purchase_item(user_id, id)
