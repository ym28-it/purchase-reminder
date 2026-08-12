"""購入物のリクエストスキーマ（``app/api/schemas/purchase.py``）のテスト。"""

import math

import pytest
from pydantic import ValidationError

from app.api.schemas.purchase import PurchaseCreateRequest, PurchasePutRequest

VALID_PAYLOAD = {
    "name": "牛乳",
    "category": "食品",
    "speed": 1.5,
    "stock": 2.0,
}


@pytest.mark.parametrize("schema_class", [PurchaseCreateRequest, PurchasePutRequest])
class TestValidPayload:
    def test_必須フィールドが揃っていれば作成できる(self, schema_class):
        request = schema_class(**VALID_PAYLOAD)

        assert request.name == "牛乳"
        assert request.category == "食品"
        assert request.speed == 1.5
        assert request.stock == 2.0

    def test_is_temporaryの既定値はFalse(self, schema_class):
        request = schema_class(**VALID_PAYLOAD)

        assert request.is_temporary is False

    def test_speedとstockの上限100は許可される(self, schema_class):
        request = schema_class(**(VALID_PAYLOAD | {"speed": 100, "stock": 100}))

        assert request.speed == 100
        assert request.stock == 100

    def test_stockは0を許可する(self, schema_class):
        request = schema_class(**(VALID_PAYLOAD | {"stock": 0}))

        assert request.stock == 0


@pytest.mark.parametrize("schema_class", [PurchaseCreateRequest, PurchasePutRequest])
class TestInvalidPayload:
    def test_nameが空文字だとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"name": ""}))

    def test_categoryが空文字だとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"category": ""}))

    def test_speedが0だとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"speed": 0}))

    def test_speedが負数だとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"speed": -1}))

    def test_stockが負数だとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"stock": -1}))

    def test_speedが上限100を超えるとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"speed": 100.1}))

    def test_stockが上限100を超えるとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"stock": 100.1}))

    def test_speedがInfinityだとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"speed": math.inf}))

    def test_stockがInfinityだとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"stock": math.inf}))

    def test_speedがNaNだとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"speed": math.nan}))

    def test_speedがNullだとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"speed": None}))

    def test_stockがNullだとエラー(self, schema_class):
        with pytest.raises(ValidationError):
            schema_class(**(VALID_PAYLOAD | {"stock": None}))

    def test_nameが無いとエラー(self, schema_class):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "name"}
        with pytest.raises(ValidationError):
            schema_class(**payload)
