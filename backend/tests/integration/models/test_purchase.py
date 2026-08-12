"""購入物の永続化層（``app/models/purchase.py``）の統合テスト。DynamoDB Localを使用。"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.exceptions import DuplicatePurchaseError, ItemAlreadyExistsError, ItemNotFoundError
from app.models.purchase import (
    PurchaseItem,
    create_purchase_item,
    delete_purchase_item,
    get_all_purchase_items,
    get_purchase_item,
    put_purchase_item,
)


def _item(user_id: str, **overrides) -> PurchaseItem:
    now = datetime.now(UTC)
    values = {
        "user_id": user_id,
        "id": uuid4(),
        "name": "牛乳",
        "category": "食品",
        "speed": 1.0,
        "stock": 1.0,
        "is_temporary": False,
        "created_at": now,
        "updated_at": now,
    }
    return PurchaseItem(**(values | overrides))


class TestCreatePurchaseItem:
    def test_作成したアイテムを取得できる(self, user_id):
        item = _item(user_id)

        create_purchase_item(item)

        fetched = get_purchase_item(user_id, item.id)
        assert fetched.name == "牛乳"
        assert fetched.category == "食品"
        assert fetched.speed == 1.0
        assert fetched.stock == 1.0
        assert fetched.is_temporary is False

    def test_同じidで再作成しようとするとエラー(self, user_id):
        item = _item(user_id)
        create_purchase_item(item)

        with pytest.raises(ItemAlreadyExistsError):
            create_purchase_item(_item(user_id, id=item.id, name="別の名前", category="別カテゴリ"))


class TestGetPurchaseItem:
    def test_存在しなければエラー(self, user_id):
        with pytest.raises(ItemNotFoundError):
            get_purchase_item(user_id, uuid4())

    def test_他ユーザーのアイテムは取得できない(self, user_id):
        other_user_id = f"other-{user_id}"
        item = create_purchase_item(_item(user_id))

        with pytest.raises(ItemNotFoundError):
            get_purchase_item(other_user_id, item.id)


class TestGetAllPurchaseItems:
    def test_登録が無ければ空リスト(self, user_id):
        assert get_all_purchase_items(user_id) == []

    def test_同一ユーザーの全件を取得する(self, user_id):
        create_purchase_item(_item(user_id, name="牛乳", category="食品"))
        create_purchase_item(_item(user_id, name="卵", category="食品"))

        items = get_all_purchase_items(user_id)

        assert {item.name for item in items} == {"牛乳", "卵"}

    def test_他ユーザーのアイテムは含まれない(self, user_id):
        other_user_id = f"other-{user_id}"
        create_purchase_item(_item(user_id, name="牛乳", category="食品"))
        create_purchase_item(_item(other_user_id, name="卵", category="食品"))

        items = get_all_purchase_items(user_id)

        assert [item.name for item in items] == ["牛乳"]


class TestPutPurchaseItem:
    def test_既存の値を上書きする(self, user_id):
        original = create_purchase_item(_item(user_id, stock=1.0))

        put_purchase_item(
            _item(
                user_id,
                id=original.id,
                name=original.name,
                category=original.category,
                stock=5.0,
                created_at=original.created_at,
            )
        )

        assert get_purchase_item(user_id, original.id).stock == 5.0

    def test_存在しなければエラー(self, user_id):
        with pytest.raises(ItemNotFoundError):
            put_purchase_item(_item(user_id))


class TestDeletePurchaseItem:
    def test_削除後は取得できなくなる(self, user_id):
        item = create_purchase_item(_item(user_id))

        delete_purchase_item(user_id, item.id)

        with pytest.raises(ItemNotFoundError):
            get_purchase_item(user_id, item.id)

    def test_存在しなければエラー(self, user_id):
        with pytest.raises(ItemNotFoundError):
            delete_purchase_item(user_id, uuid4())


class TestDuplicateNameCategory:
    """name+categoryの組み合わせは同一ユーザー内で一意（docs/purchase-spec.md 6.4）。"""

    def test_同じuser内で同じname_categoryは作成できない(self, user_id):
        create_purchase_item(_item(user_id, name="牛乳", category="食品"))

        with pytest.raises(DuplicatePurchaseError):
            create_purchase_item(_item(user_id, name="牛乳", category="食品"))

    def test_nameが同じでもcategoryが違えば作成できる(self, user_id):
        create_purchase_item(_item(user_id, name="牛乳", category="食品"))

        created = create_purchase_item(_item(user_id, name="牛乳", category="日用品"))

        assert created.category == "日用品"

    def test_categoryが同じでもnameが違えば作成できる(self, user_id):
        create_purchase_item(_item(user_id, name="牛乳", category="食品"))

        created = create_purchase_item(_item(user_id, name="卵", category="食品"))

        assert created.name == "卵"

    def test_別ユーザーなら同じname_categoryでも作成できる(self, user_id):
        other_user_id = f"other-{user_id}"
        create_purchase_item(_item(user_id, name="牛乳", category="食品"))

        created = create_purchase_item(_item(other_user_id, name="牛乳", category="食品"))

        assert created.user_id == other_user_id

    def test_putで他のアイテムとname_categoryが重複するとエラー(self, user_id):
        create_purchase_item(_item(user_id, name="牛乳", category="食品"))
        egg = create_purchase_item(_item(user_id, name="卵", category="食品"))

        with pytest.raises(DuplicatePurchaseError):
            put_purchase_item(
                _item(
                    user_id,
                    id=egg.id,
                    name="牛乳",
                    category="食品",
                    created_at=egg.created_at,
                )
            )

    def test_putで自分自身のname_categoryはそのまま維持できる(self, user_id):
        milk = create_purchase_item(_item(user_id, name="牛乳", category="食品"))

        updated = put_purchase_item(
            _item(
                user_id,
                id=milk.id,
                name="牛乳",
                category="食品",
                stock=5.0,
                created_at=milk.created_at,
            )
        )

        assert updated.stock == 5.0
