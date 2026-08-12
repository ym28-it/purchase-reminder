"""purchasesエンドポイント（``app/api/purchase.py``）の統合テスト。

FastAPIの``TestClient``経由でAPI層〜永続化層（DynamoDB Local）まで通しで検証する。
"""

from app.api.deps import get_current_user_id
from main import app

VALID_PAYLOAD = {
    "name": "牛乳",
    "category": "食品",
    "speed": 1.5,
    "stock": 2.0,
    "is_temporary": False,
}


def _create(client, **overrides) -> dict:
    response = client.post("/purchases", json=VALID_PAYLOAD | overrides)
    assert response.status_code == 201
    return response.json()


class TestGetAllPurchases:
    def test_登録が無ければ空リスト(self, client):
        response = client.get("/purchases")

        assert response.status_code == 200
        assert response.json() == []

    def test_作成した購入物が一覧に含まれる(self, client):
        created = _create(client)

        response = client.get("/purchases")

        assert response.status_code == 200
        [purchase] = response.json()
        assert purchase["id"] == created["id"]
        assert purchase["name"] == "牛乳"

    def test_他ユーザーの購入物は見えない(self, client, user_id):
        _create(client)

        app.dependency_overrides[get_current_user_id] = lambda: f"other-{user_id}"
        try:
            response = client.get("/purchases")
        finally:
            app.dependency_overrides[get_current_user_id] = lambda: user_id

        assert response.json() == []


class TestCreatePurchase:
    def test_登録できる(self, client):
        response = client.post("/purchases", json=VALID_PAYLOAD)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "牛乳"
        assert body["category"] == "食品"
        assert body["speed"] == 1.5
        assert body["stock"] == 2.0
        assert body["is_temporary"] is False
        assert body["created_at"] == body["updated_at"]

    def test_is_temporaryの既定値はFalse(self, client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "is_temporary"}

        response = client.post("/purchases", json=payload)

        assert response.status_code == 201
        assert response.json()["is_temporary"] is False

    def test_同一ユーザー内でname_categoryが重複すると409(self, client):
        _create(client)

        response = client.post("/purchases", json=VALID_PAYLOAD)

        assert response.status_code == 409

    def test_categoryが違えば重複にならない(self, client):
        _create(client)

        response = client.post("/purchases", json=VALID_PAYLOAD | {"category": "日用品"})

        assert response.status_code == 201

    class TestValidation:
        def test_nameが空文字だと422(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"name": ""})

            assert response.status_code == 422

        def test_speedが0だと422(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"speed": 0})

            assert response.status_code == 422

        def test_speedが負数だと422(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"speed": -1})

            assert response.status_code == 422

        def test_stockが負数だと422(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"stock": -1})

            assert response.status_code == 422

        def test_speedが上限100を超えると422(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"speed": 100.1})

            assert response.status_code == 422

        def test_speedが100ちょうどなら登録できる(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"speed": 100})

            assert response.status_code == 201

        def test_stockが上限100を超えると422(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"stock": 100.1})

            assert response.status_code == 422

        def test_speedがnullだと422(self, client):
            response = client.post("/purchases", json=VALID_PAYLOAD | {"speed": None})

            assert response.status_code == 422

        def test_必須フィールドが無いと422(self, client):
            payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "name"}

            response = client.post("/purchases", json=payload)

            assert response.status_code == 422


class TestPutPurchase:
    def test_更新できる(self, client):
        created = _create(client)

        response = client.put(
            f"/purchases/{created['id']}",
            json=VALID_PAYLOAD | {"stock": 9.0},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == created["id"]
        assert body["stock"] == 9.0

    def test_created_atは変わらずupdated_atは進む(self, client):
        created = _create(client)

        response = client.put(f"/purchases/{created['id']}", json=VALID_PAYLOAD | {"stock": 9.0})

        body = response.json()
        assert body["created_at"] == created["created_at"]
        assert body["updated_at"] >= created["updated_at"]

    def test_存在しなければ404(self, client):
        response = client.put("/purchases/00000000-0000-0000-0000-000000000001", json=VALID_PAYLOAD)

        assert response.status_code == 404

    def test_他の購入物とname_categoryが重複すると409(self, client):
        _create(client, name="牛乳", category="食品")
        egg = _create(client, name="卵", category="食品")

        response = client.put(
            f"/purchases/{egg['id']}", json=VALID_PAYLOAD | {"name": "牛乳", "category": "食品"}
        )

        assert response.status_code == 409

    def test_自分自身のname_categoryのまま更新できる(self, client):
        created = _create(client)

        response = client.put(f"/purchases/{created['id']}", json=VALID_PAYLOAD | {"stock": 3.0})

        assert response.status_code == 200

    def test_speedが上限を超えると422(self, client):
        created = _create(client)

        response = client.put(f"/purchases/{created['id']}", json=VALID_PAYLOAD | {"speed": 100.1})

        assert response.status_code == 422


class TestDeletePurchase:
    def test_削除できる(self, client):
        created = _create(client)

        response = client.delete(f"/purchases/{created['id']}")

        assert response.status_code == 204
        assert client.get("/purchases").json() == []

    def test_存在しなければ404(self, client):
        response = client.delete("/purchases/00000000-0000-0000-0000-000000000001")

        assert response.status_code == 404

    def test_削除後に再作成できる(self, client):
        """name+category重複制約が、削除済みアイテムを誤って検出しないことの確認。"""
        created = _create(client)
        client.delete(f"/purchases/{created['id']}")

        response = client.post("/purchases", json=VALID_PAYLOAD)

        assert response.status_code == 201
