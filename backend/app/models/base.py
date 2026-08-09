"""DynamoDBに保存するアイテムの基底クラス。

シングルテーブル設計では1つのテーブルに複数種類のアイテムが同居するため、
各アイテムは「自分がどんなキーを持つか」「自分が何者か（entity_type）」を
自分で宣言する。その宣言の置き場所と、アイテム⇄モデルの変換をここに用意する。

サブクラスの定義例（実際のエンティティは``app/models/purchase.py``などに置く）::

    class ExampleItem(TimestampedItem):
        entity_type = "EXAMPLE"
        primary_key = ItemKeySchema(
            partition_key=KeyTemplate("USER#{user_id}"),
            sort_key=KeyTemplate("EXAMPLE#{id}"),
        )

        user_id: str
        id: UUID

この層はドメイン（``app/domain/``）を一切importしない。ドメインエンティティと
アイテムの相互変換は、両者を知っている具体的なモデルの側で行う。
"""

from datetime import UTC, datetime
from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field

from app.models.keys import ItemKeySchema
from app.models.serialization import dump_model, load_item

#: アイテムの種類を保持する属性名。シングルテーブル上で種類を見分けるために使う。
ENTITY_TYPE_ATTRIBUTE = "EntityType"


class DynamoDBItem(BaseModel):
    """DynamoDBの1アイテムを表すPydanticモデルの基底クラス。

    キー属性（``PK``/``SK``/GSIのキー）はフィールドとして持たず、
    ``to_item``のたびに他のフィールドから組み立てる。キーの元になる値と
    キー文字列が二重管理になって食い違うのを防ぐため。
    """

    model_config = ConfigDict(extra="ignore")

    #: アイテムの種類。空文字のままのクラスは中間の基底クラスとして扱う。
    entity_type: ClassVar[str] = ""
    #: メインテーブルのキー定義。
    primary_key: ClassVar[ItemKeySchema]
    #: GSIのキー定義。必要なアイテムだけが宣言する。
    index_keys: ClassVar[tuple[ItemKeySchema, ...]] = ()

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """宣言されたキーがフィールドと対応しているかをクラス定義時に検証する。

        キーの綴り間違いは、実行してみるまで気づけないと痛いので早期に落とす。
        """
        super().__pydantic_init_subclass__(**kwargs)
        if not cls.entity_type:
            return  # 中間の基底クラス（TimestampedItemなど）は検証しない

        if getattr(cls, "primary_key", None) is None:
            raise TypeError(f"{cls.__name__}に primary_key が定義されていません")

        for schema in (cls.primary_key, *cls.index_keys):
            unknown = [name for name in schema.field_names if name not in cls.model_fields]
            if unknown:
                raise TypeError(
                    f"{cls.__name__}のキーが未定義のフィールドを参照しています: {unknown}"
                )

    @classmethod
    def reserved_attributes(cls) -> frozenset[str]:
        """アイテム上の予約属性（キーと種類）。フィールドとしては復元しない。"""
        names = {ENTITY_TYPE_ATTRIBUTE}
        for schema in (cls.primary_key, *cls.index_keys):
            names.update(schema.attribute_names)
        return frozenset(names)

    @classmethod
    def build_key(cls, **values: Any) -> dict[str, str]:
        """インスタンスを作らずにキーを組み立てる（``get_item``/``delete_item``用）。"""
        return cls.primary_key.build(values)

    def key(self) -> dict[str, str]:
        """このアイテム自身のキー。"""
        return self.primary_key.build(self._key_values(self.primary_key))

    def to_item(self) -> dict[str, Any]:
        """DynamoDBに``put_item``できる辞書へ変換する。"""
        item = dump_model(self)
        item.update(self.key())
        for schema in self.index_keys:
            item.update(schema.try_build(self._key_values(schema)))
        item[ENTITY_TYPE_ATTRIBUTE] = self.entity_type
        return item

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> Self:
        """DynamoDBから読み出したアイテムをモデルへ復元する。"""
        reserved = cls.reserved_attributes()
        payload = {key: value for key, value in item.items() if key not in reserved}
        return cls.model_validate(load_item(payload))

    def _key_values(self, schema: ItemKeySchema) -> dict[str, Any]:
        return {name: getattr(self, name, None) for name in schema.field_names}


class TimestampedItem(DynamoDBItem):
    """作成日時・更新日時を持つアイテム。

    ISO 8601形式の文字列として保存されるため、ソートキーやGSIのキーに
    そのまま使っても時系列順に並ぶ。
    """

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """更新日時を現在時刻にする。書き込み直前に呼ぶ。"""
        self.updated_at = datetime.now(UTC)
