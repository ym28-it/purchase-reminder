"""アイテム基底クラス（``app/models/base.py``）のテスト。"""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.models.base import ENTITY_TYPE_ATTRIBUTE, DynamoDBItem, TimestampedItem
from app.models.exceptions import InvalidKeyError
from app.models.keys import ItemKeySchema, KeyTemplate
from app.models.table import GSI1_PARTITION_ATTRIBUTE, GSI1_SORT_ATTRIBUTE

USER_ID = "u1"
ITEM_ID = UUID("00000000-0000-0000-0000-000000000001")


class _ExampleItem(DynamoDBItem):
    entity_type = "EXAMPLE"
    primary_key = ItemKeySchema(
        partition_key=KeyTemplate("USER#{user_id}"),
        sort_key=KeyTemplate("EXAMPLE#{id}"),
    )
    index_keys = (
        ItemKeySchema(
            partition_key=KeyTemplate("USER#{user_id}"),
            sort_key=KeyTemplate("CATEGORY#{category}"),
            partition_attribute=GSI1_PARTITION_ATTRIBUTE,
            sort_attribute=GSI1_SORT_ATTRIBUTE,
        ),
    )

    user_id: str
    id: UUID
    name: str
    speed: float
    category: str | None = None


def _example(**overrides) -> _ExampleItem:
    values = {"user_id": USER_ID, "id": ITEM_ID, "name": "milk", "speed": 1.5}
    return _ExampleItem(**(values | overrides))


class TestKey:
    def test_インスタンスからキーを組み立てる(self):
        key = _example().key()

        assert key == {"PK": f"USER#{USER_ID}", "SK": f"EXAMPLE#{ITEM_ID}"}

    def test_インスタンス無しでもキーを組み立てられる(self):
        key = _ExampleItem.build_key(user_id=USER_ID, id=ITEM_ID)

        assert key == {"PK": f"USER#{USER_ID}", "SK": f"EXAMPLE#{ITEM_ID}"}

    def test_キーの値が足りなければエラー(self):
        with pytest.raises(InvalidKeyError):
            _ExampleItem.build_key(user_id=USER_ID)


class TestToItem:
    def test_キー属性と種類が付与される(self):
        item = _example(category="food").to_item()

        assert item["PK"] == f"USER#{USER_ID}"
        assert item["SK"] == f"EXAMPLE#{ITEM_ID}"
        assert item[ENTITY_TYPE_ATTRIBUTE] == "EXAMPLE"

    def test_GSIのキーも書き出される(self):
        item = _example(category="food").to_item()

        assert item[GSI1_PARTITION_ATTRIBUTE] == f"USER#{USER_ID}"
        assert item[GSI1_SORT_ATTRIBUTE] == "CATEGORY#food"

    def test_GSIのキーを組み立てられないアイテムには属性を付けない(self):
        """sparse index：categoryを持たないアイテムはGSI1に載らない。"""
        item = _example(category=None).to_item()

        assert GSI1_PARTITION_ATTRIBUTE not in item
        assert GSI1_SORT_ATTRIBUTE not in item

    def test_キー属性はフィールドとして重複して持たない(self):
        """キーの元になる値とキー文字列が二重管理にならないことの確認。"""
        assert "PK" not in _ExampleItem.model_fields


class TestFromItem:
    def test_アイテムからモデルへ復元する(self):
        original = _example(category="food")

        restored = _ExampleItem.from_item(original.to_item())

        assert restored == original

    def test_復元した値の型が戻っている(self):
        restored = _ExampleItem.from_item(_example().to_item())

        assert isinstance(restored.id, UUID)
        assert restored.speed == 1.5

    def test_キー属性はフィールドに混入しない(self):
        restored = _ExampleItem.from_item(_example().to_item())

        assert not hasattr(restored, "PK")


class TestSubclassValidation:
    def test_未定義のフィールドを参照するキーは定義時にエラー(self):
        with pytest.raises(TypeError, match="unknown_field"):

            class _Broken(DynamoDBItem):
                entity_type = "BROKEN"
                primary_key = ItemKeySchema(partition_key=KeyTemplate("X#{unknown_field}"))

                name: str

    def test_キー定義が無ければ定義時にエラー(self):
        with pytest.raises(TypeError, match="primary_key"):

            class _NoKey(DynamoDBItem):
                entity_type = "NO_KEY"

                name: str

    def test_entity_typeを持たない中間クラスは検証しない(self):
        class _Intermediate(DynamoDBItem):
            name: str

        assert _Intermediate.entity_type == ""


class _TimestampedExample(TimestampedItem):
    entity_type = "TIMESTAMPED"
    primary_key = ItemKeySchema(partition_key=KeyTemplate("USER#{user_id}"))

    user_id: str


class TestTimestampedItem:
    def test_作成日時と更新日時が自動で入る(self):
        item = _TimestampedExample(user_id=USER_ID)

        assert item.created_at.tzinfo is not None
        assert item.updated_at.tzinfo is not None

    def test_touchで更新日時だけが進む(self):
        item = _TimestampedExample(
            user_id=USER_ID,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        item.touch()

        assert item.created_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert item.updated_at > item.created_at

    def test_日時は文字列として書き出され復元できる(self):
        item = _TimestampedExample(user_id=USER_ID)

        written = item.to_item()

        assert isinstance(written["created_at"], str)
        assert _TimestampedExample.from_item(written) == item
