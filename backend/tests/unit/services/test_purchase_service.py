"""ユースケースのオーケストレーション（``app/services/purchase_service.py``）のテスト。

domain/servicesは本来ユーザー実装担当だが、created_at保持・
``dataclasses.field()``誤用の修正は本人からの明示的な依頼により今回のみ
エージェントが実装した。永続化層（``app/models/purchase``）はモックし、
services層が正しい値を組み立てて渡しているかだけを見る。
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.services import purchase_service

USER_ID = "u1"
PURCHASE_ID = UUID("00000000-0000-0000-0000-000000000001")
FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
ORIGINAL_CREATED_AT = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)


class TestCreatePurchase:
    @patch("app.services.purchase_service.create_purchase_item")
    @patch("app.services.purchase_service.datetime")
    def test_新しいUUIDで購入物を作成する(self, mock_datetime, mock_create_item):
        mock_datetime.now.return_value = FIXED_NOW
        mock_create_item.side_effect = lambda item: item
        domain_purchase = purchase_service.create_purchase(
            user_id=USER_ID,
            name="牛乳",
            category="食品",
            speed=1.5,
            stock=2.0,
            is_temporary=False,
        )

        created_item = mock_create_item.call_args.kwargs["item"]
        assert isinstance(created_item.id, UUID)
        assert created_item.user_id == USER_ID
        assert created_item.name == "牛乳"
        assert domain_purchase.id == created_item.id

    @patch("app.services.purchase_service.create_purchase_item")
    @patch("app.services.purchase_service.datetime")
    def test_created_atとupdated_atは現在時刻で揃う(self, mock_datetime, mock_create_item):
        mock_datetime.now.return_value = FIXED_NOW
        mock_create_item.side_effect = lambda item: item

        purchase_service.create_purchase(
            user_id=USER_ID,
            name="牛乳",
            category="食品",
            speed=1.5,
            stock=2.0,
            is_temporary=False,
        )

        created_item = mock_create_item.call_args.kwargs["item"]
        assert created_item.created_at == FIXED_NOW
        assert created_item.updated_at == FIXED_NOW

    @patch("app.services.purchase_service.create_purchase_item")
    def test_作成結果をドメインへ変換して返す(self, mock_create_item):
        expected_domain = object()
        mock_item = MagicMock()
        mock_item.to_domain.return_value = expected_domain
        mock_create_item.return_value = mock_item

        result = purchase_service.create_purchase(
            user_id=USER_ID,
            name="牛乳",
            category="食品",
            speed=1.5,
            stock=2.0,
            is_temporary=False,
        )

        assert result is expected_domain


class TestPutPurchase:
    @patch("app.services.purchase_service.put_purchase_item")
    @patch("app.services.purchase_service.get_purchase_item")
    @patch("app.services.purchase_service.datetime")
    def test_created_atは既存アイテムの値を引き継ぐ(
        self, mock_datetime, mock_get_item, mock_put_item
    ):
        mock_datetime.now.return_value = FIXED_NOW
        mock_get_item.return_value = MagicMock(created_at=ORIGINAL_CREATED_AT)
        mock_put_item.side_effect = lambda item: item

        purchase_service.put_purchase(
            user_id=USER_ID,
            id=PURCHASE_ID,
            name="牛乳",
            category="食品",
            speed=1.5,
            stock=2.0,
            is_temporary=False,
        )

        put_item = mock_put_item.call_args.kwargs["item"]
        assert put_item.created_at == ORIGINAL_CREATED_AT
        mock_get_item.assert_called_once_with(USER_ID, PURCHASE_ID)

    @patch("app.services.purchase_service.put_purchase_item")
    @patch("app.services.purchase_service.get_purchase_item")
    @patch("app.services.purchase_service.datetime")
    def test_updated_atは現在時刻に更新される(self, mock_datetime, mock_get_item, mock_put_item):
        mock_datetime.now.return_value = FIXED_NOW
        mock_get_item.return_value = MagicMock(created_at=ORIGINAL_CREATED_AT)
        mock_put_item.side_effect = lambda item: item

        purchase_service.put_purchase(
            user_id=USER_ID,
            id=PURCHASE_ID,
            name="牛乳",
            category="食品",
            speed=1.5,
            stock=2.0,
            is_temporary=False,
        )

        put_item = mock_put_item.call_args.kwargs["item"]
        assert put_item.updated_at == FIXED_NOW
        assert put_item.updated_at != put_item.created_at

    @patch("app.services.purchase_service.put_purchase_item")
    @patch("app.services.purchase_service.get_purchase_item")
    def test_指定したidをそのまま使う(self, mock_get_item, mock_put_item):
        mock_get_item.return_value = MagicMock(created_at=ORIGINAL_CREATED_AT)
        mock_put_item.side_effect = lambda item: item

        purchase_service.put_purchase(
            user_id=USER_ID,
            id=PURCHASE_ID,
            name="牛乳",
            category="食品",
            speed=1.5,
            stock=2.0,
            is_temporary=False,
        )

        put_item = mock_put_item.call_args.kwargs["item"]
        assert put_item.id == PURCHASE_ID

    @patch("app.services.purchase_service.put_purchase_item")
    @patch("app.services.purchase_service.get_purchase_item")
    def test_更新結果をドメインへ変換して返す(self, mock_get_item, mock_put_item):
        mock_get_item.return_value = MagicMock(created_at=ORIGINAL_CREATED_AT)
        expected_domain = object()
        mock_item = MagicMock()
        mock_item.to_domain.return_value = expected_domain
        mock_put_item.return_value = mock_item

        result = purchase_service.put_purchase(
            user_id=USER_ID,
            id=PURCHASE_ID,
            name="牛乳",
            category="食品",
            speed=1.5,
            stock=2.0,
            is_temporary=False,
        )

        assert result is expected_domain


class TestDeletePurchase:
    @patch("app.services.purchase_service.delete_purchase_item")
    def test_永続化層のdeleteへ委譲する(self, mock_delete_item):
        purchase_service.delete_purchase(USER_ID, PURCHASE_ID)

        mock_delete_item.assert_called_once_with(USER_ID, PURCHASE_ID)


class TestGetAllPurchases:
    @patch("app.services.purchase_service.get_all_purchase_items")
    def test_取得したアイテムをすべてドメインへ変換する(self, mock_get_all_items):
        item1, item2 = MagicMock(), MagicMock()
        domain1, domain2 = object(), object()
        item1.to_domain.return_value = domain1
        item2.to_domain.return_value = domain2
        mock_get_all_items.return_value = [item1, item2]

        result = purchase_service.get_all_purchases(USER_ID)

        assert result == [domain1, domain2]

    @patch("app.services.purchase_service.get_all_purchase_items")
    def test_0件なら空リスト(self, mock_get_all_items):
        mock_get_all_items.return_value = []

        result = purchase_service.get_all_purchases(USER_ID)

        assert result == []
