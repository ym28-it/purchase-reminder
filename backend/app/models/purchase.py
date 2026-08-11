"""購入物（purchase）のDynamoDB永続化層。

``domain.Purchase``（コアのビジネスエンティティ）とは別に、DynamoDBの
アイテム表現として``PurchaseItem``を持つ。両者を知っているのはこの層なので、
相互変換（``from_domain``/``to_domain``）もここに置く。
"""

from uuid import UUID

from botocore.exceptions import ClientError

from app.core.dynamodb import get_table
from app.domain.purchase import Purchase
from app.models.base import TimestampedItem
from app.models.exceptions import ItemAlreadyExistsError
from app.models.keys import ItemKeySchema, KeyTemplate


class PurchaseItem(TimestampedItem):
    """購入物1件分のDynamoDBアイテム。"""

    entity_type = "PURCHASE"
    primary_key = ItemKeySchema(
        partition_key=KeyTemplate("USER#{user_id}"),
        sort_key=KeyTemplate("PURCHASE#{id}"),
    )

    user_id: str
    id: UUID
    name: str
    category: str
    speed: float
    stock: float
    is_temporary: bool

    @classmethod
    def from_domain(cls, purchase: Purchase) -> PurchaseItem:
        """``Purchase``エンティティから、永続化用のアイテムを作る。"""
        return cls(
            user_id=purchase.user_id,
            id=purchase.id,
            name=purchase.name,
            category=purchase.category,
            speed=purchase.speed,
            stock=purchase.stock,
            is_temporary=purchase.is_temporary,
        )

    def to_domain(self) -> Purchase:
        """このアイテムを``Purchase``エンティティへ復元する。"""
        return Purchase(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            category=self.category,
            speed=self.speed,
            stock=self.stock,
            is_temporary=self.is_temporary,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


def create_purchase_item(item: PurchaseItem, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を新規作成する。

    同じキー（``user_id``+``id``）のアイテムが既にあれば``ItemAlreadyExistsError``。
    """
    table = get_table(table_name)
    try:
        table.put_item(
            Item=item.to_item(),
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ItemAlreadyExistsError(f"購入物 {item.id} は既に存在します") from error
        raise
    return item
