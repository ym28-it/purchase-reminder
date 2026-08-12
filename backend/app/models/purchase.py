"""購入物（purchase）のDynamoDB永続化層。

``domain.Purchase``（コアのビジネスエンティティ）とは別に、DynamoDBの
アイテム表現として``PurchaseItem``を持つ。両者を知っているのはこの層なので、
相互変換（``from_domain``/``to_domain``）もここに置く。
"""

from uuid import UUID

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.dynamodb import get_table
from app.domain.purchase import Purchase
from app.models.base import TimestampedItem
from app.models.exceptions import DuplicatePurchaseError, ItemAlreadyExistsError, ItemNotFoundError
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
        """``Purchase``エンティティから、永続化用のアイテムを作る。

        ``created_at``/``updated_at``は``purchase``の値をそのまま使う
        （呼び出し側が「作成日時を保持したいか、現在時刻にしたいか」を決める）。
        """
        return cls(
            user_id=purchase.user_id,
            id=purchase.id,
            name=purchase.name,
            category=purchase.category,
            speed=purchase.speed,
            stock=purchase.stock,
            is_temporary=purchase.is_temporary,
            created_at=purchase.created_at,
            updated_at=purchase.updated_at,
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


def _ensure_no_duplicate_name_category(item: PurchaseItem, *, table_name: str | None) -> None:
    """同一ユーザー内に、同じname+categoryを持つ別アイテムがあれば``DuplicatePurchaseError``。

    自分自身（同じid）との一致は除外する（PUTでの自己一致を許すため）。
    """
    existing_items = get_all_purchase_items(item.user_id, table_name=table_name)
    for existing in existing_items:
        if existing.id == item.id:
            continue
        if existing.name == item.name and existing.category == item.category:
            raise DuplicatePurchaseError(
                f"name={item.name!r} category={item.category!r} の購入物は既に存在します"
            )


def create_purchase_item(item: PurchaseItem, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を新規作成する。

    同じキー（``user_id``+``id``）のアイテムが既にあれば``ItemAlreadyExistsError``。
    同一ユーザー内に同じname+categoryのアイテムが既にあれば``DuplicatePurchaseError``。
    """
    _ensure_no_duplicate_name_category(item, table_name=table_name)
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


def get_purchase_item(user_id: str, id: UUID, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を1件取得する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    """
    table = get_table(table_name)
    response = table.get_item(Key=PurchaseItem.build_key(user_id=user_id, id=id))
    item = response.get("Item")
    if item is None:
        raise ItemNotFoundError(f"購入物 {id}は存在しません。")
    return PurchaseItem.from_item(item)


def get_all_purchase_items(user_id: str, *, table_name: str | None = None) -> list[PurchaseItem]:
    """指定ユーザーの購入物を全件取得する。"""
    table = get_table(table_name)
    partition_key = PurchaseItem.primary_key
    response = table.query(
        KeyConditionExpression=Key(partition_key.partition_attribute).eq(
            partition_key.partition_key.build(user_id=user_id)
        ),
    )
    return [PurchaseItem.from_item(item) for item in response["Items"]]


def put_purchase_item(item: PurchaseItem, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を更新する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    同一ユーザー内の他のアイテムと同じname+categoryになる場合は``DuplicatePurchaseError``。
    """
    _ensure_no_duplicate_name_category(item, table_name=table_name)
    table = get_table(table_name)
    try:
        table.put_item(
            Item=item.to_item(),
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ItemNotFoundError(f"購入物 {item.id}は存在しません。") from error
        raise
    return item


def delete_purchase_item(user_id: str, id: UUID, *, table_name: str | None = None) -> None:
    """購入物を削除する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    """
    table = get_table(table_name)
    try:
        table.delete_item(
            Key=PurchaseItem.build_key(user_id=user_id, id=id),
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ItemNotFoundError(f"購入物 {id}は存在しません。") from error
        raise
