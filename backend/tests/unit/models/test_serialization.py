"""型変換（``app/models/serialization.py``）のテスト。"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from app.models.serialization import dump_model, from_dynamodb, load_item, to_dynamodb


class TestToDynamoDB:
    def test_floatはDecimalになる(self):
        assert to_dynamodb(1.5) == Decimal("1.5")

    def test_floatの誤差を持ち込まない(self):
        """``Decimal(0.1)``は``0.1000000000000000055511151231257827``になってしまう。"""
        assert to_dynamodb(0.1) == Decimal("0.1")

    def test_boolはそのまま(self):
        """boolはintのサブクラスなので数値として扱われないことを確かめる。"""
        assert to_dynamodb(True) is True

    def test_intはそのまま(self):
        assert to_dynamodb(3) == 3

    def test_ネストした構造の中のfloatも変換される(self):
        converted = to_dynamodb({"items": [{"speed": 1.5}], "name": "milk"})

        assert converted == {"items": [{"speed": Decimal("1.5")}], "name": "milk"}


class TestFromDynamoDB:
    def test_整数のDecimalはintになる(self):
        value = from_dynamodb(Decimal("3"))

        assert value == 3
        assert isinstance(value, int)

    def test_小数のDecimalはfloatになる(self):
        value = from_dynamodb(Decimal("1.5"))

        assert value == 1.5
        assert isinstance(value, float)

    def test_ネストした構造の中のDecimalも変換される(self):
        restored = from_dynamodb({"items": [{"speed": Decimal("1.5")}], "count": Decimal("2")})

        assert restored == {"items": [{"speed": 1.5}], "count": 2}

    def test_文字列は分解されない(self):
        assert from_dynamodb("milk") == "milk"


class Category(StrEnum):
    FOOD = "food"


class _Sample(BaseModel):
    id: UUID
    name: str
    speed: float
    category: Category
    created_at: datetime
    memo: str | None = None


class TestDumpModel:
    def _sample(self, **overrides) -> _Sample:
        values = {
            "id": UUID("00000000-0000-0000-0000-000000000001"),
            "name": "milk",
            "speed": 1.5,
            "category": Category.FOOD,
            "created_at": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        }
        return _Sample(**(values | overrides))

    def test_floatはDecimalとして書き出される(self):
        item = dump_model(self._sample())

        assert item["speed"] == Decimal("1.5")

    def test_UUIDとEnumと日時は文字列になる(self):
        item = dump_model(self._sample())

        assert item["id"] == "00000000-0000-0000-0000-000000000001"
        assert item["category"] == "food"
        assert item["created_at"] == "2026-01-02T03:04:05Z"

    def test_Noneのフィールドは書き出さない(self):
        item = dump_model(self._sample())

        assert "memo" not in item

    def test_exclude_noneを外せばNoneも書き出す(self):
        item = dump_model(self._sample(), exclude_none=False)

        assert item["memo"] is None

    def test_書き出したアイテムはモデルに復元できる(self):
        model = self._sample()

        restored = _Sample.model_validate(load_item(dump_model(model)))

        assert restored == model
