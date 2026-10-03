"""購入物（purchase）のDynamoDB永続化層。

``domain.Purchase``（コアのビジネスエンティティ）とは別に、DynamoDBの
アイテム表現として``PurchaseItem``を持つ。両者を知っているのはこの層なので、
相互変換（``from_domain``/``to_domain``）もここに置く。
"""

import hashlib
import json
from typing import Any
from uuid import UUID

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.dynamodb import get_table
from app.domain.purchase import Purchase
from app.models.base import TimestampedItem
from app.models.exceptions import (
    ConditionalCheckFailedError,
    ItemAlreadyExistsError,
    ItemNotFoundError,
)
from app.models.keys import ItemKeySchema, KeyTemplate

#: 同じ利用者に名前・カテゴリが完全一致する購入物がある場合のメッセージ（APIの409応答）。
DUPLICATE_PURCHASE_MESSAGE = "同じ名前とカテゴリの購入物は既に存在します"


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

    同じユーザーに同じ名前・カテゴリの購入物が既にあれば``ItemAlreadyExistsError``。
    名前・カテゴリの予約を同じトランザクションで書き込み、同時登録でも重複を防ぐ。
    """
    table = get_table(table_name)
    # Pre-existing items may have been written before unique reservations existed.
    if any(
        existing.name == item.name and existing.category == item.category
        for existing in get_all_purchase_items(item.user_id, table_name=table_name, consistent=True)
    ):
        raise ItemAlreadyExistsError(DUPLICATE_PURCHASE_MESSAGE)
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
            raise ItemAlreadyExistsError(DUPLICATE_PURCHASE_MESSAGE) from error
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


#: 読み取りから書き込みまでの間に他の操作が名前・カテゴリを変えたときの再試行回数。
_MAX_WRITE_ATTEMPTS = 5


def _read_current(table: Any, key: dict[str, str], id: UUID) -> PurchaseItem:
    """現在の購入物を強い整合性で読む。存在しなければ``ItemNotFoundError``。"""
    response = table.get_item(Key=key, ConsistentRead=True)
    if "Item" not in response:
        raise ItemNotFoundError(f"購入物 {id}は存在しません。")
    return PurchaseItem.from_item(response["Item"])


def _unchanged_since_read(old: PurchaseItem) -> dict[str, Any]:
    """本体の書き込み条件: 読み取った名前・カテゴリのまま存在している。

    読み取り後に他の操作が名前・カテゴリを変えていれば条件が失敗し、
    古い組の予約を消して新しい組の予約を孤立させる書き込みを防ぐ。
    """
    return {
        "ConditionExpression": "attribute_exists(PK) AND #name = :name AND #category = :category",
        "ExpressionAttributeNames": {"#name": "name", "#category": "category"},
        "ExpressionAttributeValues": {":name": old.name, ":category": old.category},
    }


def put_purchase_item(item: PurchaseItem, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を更新する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    別の購入物と同じ名前・カテゴリへ変更しようとした場合は``ItemAlreadyExistsError``。
    読み取り後に他の操作が名前・カテゴリを変えていた場合は、読み直して再試行する。
    """
    table = get_table(table_name)
    for _ in range(_MAX_WRITE_ATTEMPTS):
        old = _read_current(table, item.key(), item.id)
        changed = _unique_key(old) != _unique_key(item)
        if changed and any(
            existing.id != item.id
            and existing.name == item.name
            and existing.category == item.category
            for existing in get_all_purchase_items(
                item.user_id, table_name=table_name, consistent=True
            )
        ):
            raise ItemAlreadyExistsError(DUPLICATE_PURCHASE_MESSAGE)
        actions: list[dict[str, Any]] = [
            {"Put": {"TableName": table.name, "Item": item.to_item(), **_unchanged_since_read(old)}}
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
            # 本体の条件失敗を先に判定する。同じ組への改名同士が競合した場合、後の要求は
            # 自分自身の予約とも衝突するが、別の購入物との重複ではないので読み直して判断する。
            if _duplicate_transaction(error, 0):
                continue  # 削除または名前・カテゴリの変更と競合した。読み直して判断する
            if changed and _duplicate_transaction(error, 2):
                raise ItemAlreadyExistsError(DUPLICATE_PURCHASE_MESSAGE) from error
            raise
        return item
    raise ConditionalCheckFailedError(f"購入物 {item.id}の更新が競合し続けました。")


def delete_purchase_item(user_id: str, id: UUID, *, table_name: str | None = None) -> None:
    """購入物を削除する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    読み取り後に他の操作が名前・カテゴリを変えていた場合は、読み直して再試行する。
    """
    table = get_table(table_name)
    key = PurchaseItem.build_key(user_id=user_id, id=id)
    for _ in range(_MAX_WRITE_ATTEMPTS):
        old = _read_current(table, key, id)
        try:
            table.meta.client.transact_write_items(
                TransactItems=[
                    {"Delete": {"TableName": table.name, "Key": key, **_unchanged_since_read(old)}},
                    {"Delete": {"TableName": table.name, "Key": _unique_key(old)}},
                ]
            )
        except ClientError as error:
            if _duplicate_transaction(error, 0):
                continue  # 削除または名前・カテゴリの変更と競合した。読み直して判断する
            raise
        return
    raise ConditionalCheckFailedError(f"購入物 {id}の削除が競合し続けました。")
