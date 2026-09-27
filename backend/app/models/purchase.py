"""購入物（purchase）のDynamoDB永続化層。

``domain.Purchase``（コアのビジネスエンティティ）とは別に、DynamoDBの
アイテム表現として``PurchaseItem``を持つ。両者を知っているのはこの層なので、
相互変換（``from_domain``/``to_domain``）もここに置く。
"""

import hashlib
import json
from uuid import UUID

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.dynamodb import get_table
from app.domain.purchase import Purchase
from app.models.base import TimestampedItem
from app.models.exceptions import ItemAlreadyExistsError, ItemNotFoundError
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


def _unique_key(item: PurchaseItem) -> dict[str, str]:
    """Keep a per-user exact name/category reservation beside the purchase."""
    pair = json.dumps([item.name, item.category], ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(pair.encode("utf-8")).hexdigest()
    return {"PK": f"USER#{item.user_id}", "SK": f"PURCHASE_UNIQUE#{digest}"}


def _duplicate_transaction(error: ClientError, reservation_index: int) -> bool:
    if error.response["Error"]["Code"] != "TransactionCanceledException":
        return False
    reasons = error.response.get("CancellationReasons", [])
    return (
        len(reasons) > reservation_index
        and reasons[reservation_index].get("Code") == "ConditionalCheckFailed"
    )


def create_purchase_item(item: PurchaseItem, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を新規作成する。

    同じキー（``user_id``+``id``）のアイテムが既にあれば``ItemAlreadyExistsError``。
    """
    table = get_table(table_name)
    # Pre-existing items may have been written before unique reservations existed.
    if any(
        existing.name == item.name and existing.category == item.category
        for existing in get_all_purchase_items(item.user_id, table_name=table_name, consistent=True)
    ):
        raise ItemAlreadyExistsError("同じ名前とカテゴリの購入物は既に存在します")
    try:
        table.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table.name,
                        "Item": item.to_item(),
                        "ConditionExpression": "attribute_not_exists(PK)",
                    }
                },
                {
                    "Put": {
                        "TableName": table.name,
                        "Item": {**_unique_key(item), "EntityType": "PURCHASE_UNIQUE"},
                        "ConditionExpression": "attribute_not_exists(PK)",
                    }
                },
            ]
        )
    except ClientError as error:
        if _duplicate_transaction(error, 1):
            raise ItemAlreadyExistsError("同じ名前とカテゴリの購入物は既に存在します") from error
        raise
    return item


def get_all_purchase_items(
    user_id: str, *, table_name: str | None = None, consistent: bool = False
) -> list[PurchaseItem]:
    """指定ユーザーの購入物を全件取得する。"""
    table = get_table(table_name)
    partition_key = PurchaseItem.primary_key
    response = table.query(
        KeyConditionExpression=Key(partition_key.partition_attribute).eq(
            partition_key.partition_key.build(user_id=user_id)
        ),
        ConsistentRead=consistent,
    )
    return [
        PurchaseItem.from_item(item)
        for item in response["Items"]
        if item.get("EntityType") == PurchaseItem.entity_type
    ]


def put_purchase_item(item: PurchaseItem, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を更新する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    """
    table = get_table(table_name)
    old_response = table.get_item(Key=item.key(), ConsistentRead=True)
    if "Item" not in old_response:
        raise ItemNotFoundError(f"購入物 {item.id}は存在しません。")
    old = PurchaseItem.from_item(old_response["Item"])
    changed = _unique_key(old) != _unique_key(item)
    if changed and any(
        existing.id != item.id and existing.name == item.name and existing.category == item.category
        for existing in get_all_purchase_items(item.user_id, table_name=table_name, consistent=True)
    ):
        raise ItemAlreadyExistsError("同じ名前とカテゴリの購入物は既に存在します")
    actions = [
        {
            "Put": {
                "TableName": table.name,
                "Item": item.to_item(),
                "ConditionExpression": "attribute_exists(PK)",
            }
        }
    ]
    if changed:
        actions.append({"Delete": {"TableName": table.name, "Key": _unique_key(old)}})
        actions.append(
            {
                "Put": {
                    "TableName": table.name,
                    "Item": {**_unique_key(item), "EntityType": "PURCHASE_UNIQUE"},
                    "ConditionExpression": "attribute_not_exists(PK)",
                }
            }
        )
    try:
        table.meta.client.transact_write_items(TransactItems=actions)
    except ClientError as error:
        if changed and _duplicate_transaction(error, 2):
            raise ItemAlreadyExistsError("同じ名前とカテゴリの購入物は既に存在します") from error
        if _duplicate_transaction(error, 0):
            raise ItemNotFoundError(f"購入物 {item.id}は存在しません。") from error
        raise
    return item


def delete_purchase_item(user_id: str, id: UUID, *, table_name: str | None = None) -> None:
    """購入物を削除する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    """
    table = get_table(table_name)
    key = PurchaseItem.build_key(user_id=user_id, id=id)
    old_response = table.get_item(Key=key, ConsistentRead=True)
    if "Item" not in old_response:
        raise ItemNotFoundError(f"購入物 {id}は存在しません。")
    old = PurchaseItem.from_item(old_response["Item"])
    try:
        table.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Delete": {
                        "TableName": table.name,
                        "Key": key,
                        "ConditionExpression": "attribute_exists(PK)",
                    }
                },
                {"Delete": {"TableName": table.name, "Key": _unique_key(old)}},
            ]
        )
    except ClientError as error:
        if _duplicate_transaction(error, 0):
            raise ItemNotFoundError(f"購入物 {id}は存在しません。") from error
        raise
