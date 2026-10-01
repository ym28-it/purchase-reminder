"""Post-implementation API coverage for purchase-create (docs/specs/purchase-create*.md).

Expected results come from the approved logical test cases only. The frozen TDD
scenarios live in ``test_purchase_create.py`` and are not duplicated here.
"""

from collections.abc import Iterator
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.core.dynamodb import get_table
from app.models.purchase import PurchaseItem
from main import app

pytestmark = pytest.mark.integration

SURROGATE = "\U00020bb7"  # 𠮷: one character, two UTF-16 code units
IDEOGRAPHIC_SPACE = "　"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def as_user(user_id: str) -> None:
    app.dependency_overrides[get_current_user_id] = lambda: user_id


def valid_purchase(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "牛乳",
        "category": "食品",
        "speed": 1,
        "stock": 2,
        "is_temporary": False,
    }
    payload.update(overrides)
    return payload


def purchases(client: TestClient) -> list[dict[str, object]]:
    response = client.get("/purchases")
    assert response.status_code == 200
    return response.json()


def error_fields(response_json: dict[str, object]) -> set[str]:
    """Field names that a 422 body identifies (FastAPI ``loc`` of each error)."""
    detail = response_json["detail"]
    assert isinstance(detail, list) and detail
    return {str(error["loc"][-1]) for error in detail}


def stored_fields(item: dict[str, object]) -> tuple[object, ...]:
    return (item["name"], item["category"], item["speed"], item["stock"], item["is_temporary"])


# --- PURC-003-TC2 / PURC-004: invalid input is rejected with 422 and not stored ---


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        pytest.param({"name": ""}, "name", id="PURC-004-TC1-name-empty"),
        pytest.param({"name": IDEOGRAPHIC_SPACE}, "name", id="PURC-004-TC1-name-u3000"),
        pytest.param({"name": f" \t{IDEOGRAPHIC_SPACE}\n"}, "name", id="PURC-004-TC1-name-mixed"),
        pytest.param({"category": ""}, "category", id="PURC-004-TC2-category-empty"),
        pytest.param({"category": "   "}, "category", id="PURC-004-TC2-category-spaces"),
        pytest.param(
            {"category": IDEOGRAPHIC_SPACE * 2}, "category", id="PURC-004-TC2-category-u3000"
        ),
        pytest.param({"name": "x" * 51}, "name", id="PURC-004-TC4-name-51-ascii"),
        pytest.param({"name": SURROGATE * 51}, "name", id="PURC-004-TC4-name-51-surrogate"),
        pytest.param({"category": "x" * 31}, "category", id="PURC-004-TC6-category-31-ascii"),
        pytest.param(
            {"category": SURROGATE * 31}, "category", id="PURC-004-TC6-category-31-surrogate"
        ),
        pytest.param({"speed": -1}, "speed", id="PURC-004-TC8-speed-negative"),
        pytest.param({"speed": 1.5}, "speed", id="PURC-004-TC8-speed-decimal"),
        pytest.param({"speed": 100001}, "speed", id="PURC-004-TC8-speed-over"),
        pytest.param({"stock": -1}, "stock", id="PURC-004-TC10-stock-negative"),
        pytest.param({"stock": 1.5}, "stock", id="PURC-004-TC10-stock-decimal"),
        pytest.param({"stock": 100001}, "stock", id="PURC-004-TC10-stock-over"),
        pytest.param({"speed": None}, "speed", id="PURC-003-TC2-speed-null"),
        pytest.param({"stock": None}, "stock", id="PURC-003-TC2-stock-null"),
    ],
)
def test_invalid_input_is_rejected_with_field_and_not_stored(
    client: TestClient, overrides: dict[str, object], field: str
) -> None:
    """PURC-003-TC2, PURC-004-TC1/2/4/6/8/10, PURC-016-TC2 (API side)."""
    as_user("user-a")
    response = client.post("/purchases", json=valid_purchase(**overrides))

    assert response.status_code == 422
    assert field in error_fields(response.json())
    assert purchases(client) == []


# --- PURC-003-TC3: missing required field ---


@pytest.mark.parametrize("field", ["name", "category", "speed", "stock"])
def test_missing_required_field_is_rejected_with_field_and_not_stored(
    client: TestClient, field: str
) -> None:
    """PURC-003-TC3."""
    as_user("user-a")
    payload = valid_purchase()
    del payload[field]

    response = client.post("/purchases", json=payload)

    assert response.status_code == 422
    assert field in error_fields(response.json())
    assert purchases(client) == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEFECT-001: spec §3 marks 一時的な購入 as 必須 and PURC-003-TC3 requires 422 for any "
        "missing required item, but the API defaults a missing is_temporary to false (201)."
    ),
)
def test_missing_is_temporary_is_rejected_with_field_and_not_stored(client: TestClient) -> None:
    """PURC-003-TC3 (is_temporary)."""
    as_user("user-a")
    payload = valid_purchase()
    del payload["is_temporary"]

    response = client.post("/purchases", json=payload)

    assert response.status_code == 422
    assert "is_temporary" in error_fields(response.json())
    assert purchases(client) == []


# --- PURC-004: accepted boundaries are stored exactly as sent ---


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"name": "x" * 50}, id="PURC-004-TC3-name-50-ascii"),
        pytest.param({"name": SURROGATE * 50}, id="PURC-004-TC3-name-50-surrogate"),
        pytest.param({"category": "x" * 30}, id="PURC-004-TC5-category-30-ascii"),
        pytest.param({"category": SURROGATE * 30}, id="PURC-004-TC5-category-30-surrogate"),
        pytest.param({"speed": 0}, id="PURC-004-TC7-speed-0"),
        pytest.param({"speed": 100000}, id="PURC-004-TC7-speed-100000"),
        pytest.param({"stock": 0}, id="PURC-004-TC9-stock-0"),
        pytest.param({"stock": 100000}, id="PURC-004-TC9-stock-100000"),
        pytest.param({"speed": 0, "is_temporary": True}, id="PURC-004-TC11-temporary-speed-0"),
    ],
)
def test_boundary_input_is_created_and_stored_unchanged(
    client: TestClient, overrides: dict[str, object]
) -> None:
    """PURC-004-TC3/5/7/9/11."""
    as_user("user-a")
    payload = valid_purchase(**overrides)

    response = client.post("/purchases", json=payload)

    assert response.status_code == 201
    [stored] = purchases(client)
    assert stored["id"] == response.json()["id"]
    assert stored_fields(stored) == stored_fields(payload)


# --- PURC-006: system generated values ---


def test_each_create_gets_distinct_id_and_server_timestamps(client: TestClient) -> None:
    """PURC-006-TC1, PURC-006-TC2."""
    as_user("user-a")
    client_values = {
        "id": str(uuid4()),
        "created_at": "2000-01-01T00:00:00Z",
        "updated_at": "2000-01-01T00:00:00Z",
    }
    first = client.post("/purchases", json=valid_purchase(**client_values))
    second = client.post("/purchases", json=valid_purchase(name="卵", **client_values))

    assert first.status_code == second.status_code == 201
    ids = {UUID(str(first.json()["id"])), UUID(str(second.json()["id"]))}
    assert len(ids) == 2
    assert UUID(client_values["id"]) not in ids
    for body in (first.json(), second.json()):
        for key in ("created_at", "updated_at"):
            assert datetime.fromisoformat(str(body[key])).year != 2000
    assert {item["id"] for item in purchases(client)} == {str(i) for i in ids}


# --- PURC-014: duplicate rules ---


def test_exact_duplicate_is_rejected_with_409_and_original_kept(client: TestClient) -> None:
    """PURC-014-TC1, PURC-016-TC1 (API: duplicate is identifiable)."""
    as_user("user-a")
    original = client.post("/purchases", json=valid_purchase())
    assert original.status_code == 201

    duplicate = client.post("/purchases", json=valid_purchase())

    assert duplicate.status_code == 409
    detail = str(duplicate.json()["detail"])
    assert "既に存在" in detail or "重複" in detail
    assert purchases(client) == [original.json()]


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"speed": 9}, id="speed"),
        pytest.param({"stock": 99}, id="stock"),
        pytest.param({"is_temporary": True}, id="is_temporary"),
        pytest.param({"speed": 0, "stock": 0, "is_temporary": True}, id="all"),
    ],
)
def test_duplicate_ignores_non_key_fields(client: TestClient, overrides: dict[str, object]) -> None:
    """PURC-014-TC2."""
    as_user("user-a")
    original = client.post("/purchases", json=valid_purchase())
    assert original.status_code == 201

    duplicate = client.post("/purchases", json=valid_purchase(**overrides))

    assert duplicate.status_code == 409
    assert purchases(client) == [original.json()]


@pytest.mark.parametrize(
    ("existing", "candidate"),
    [
        pytest.param({}, {"category": "飲料"}, id="PURC-014-TC3-category-differs"),
        pytest.param({}, {"name": "低脂肪乳"}, id="PURC-014-TC4-name-differs"),
        pytest.param({}, {"name": " 牛乳 "}, id="PURC-014-TC5-surrounding-spaces"),
        pytest.param({"name": "Milk"}, {"name": "milk"}, id="PURC-014-TC6-case"),
        pytest.param({"name": "Milk"}, {"name": "Ｍｉｌｋ"}, id="PURC-014-TC6-width"),
    ],
)
def test_non_identical_pairs_are_distinct_and_not_normalized(
    client: TestClient, existing: dict[str, object], candidate: dict[str, object]
) -> None:
    """PURC-014-TC3/4/5/6 and spec §3 (strings are stored without normalization)."""
    as_user("user-a")
    first_payload = valid_purchase(**existing)
    second_payload = valid_purchase(**{**existing, **candidate})
    assert client.post("/purchases", json=first_payload).status_code == 201

    response = client.post("/purchases", json=second_payload)

    assert response.status_code == 201
    assert (response.json()["name"], response.json()["category"]) == (
        second_payload["name"],
        second_payload["category"],
    )
    stored = sorted(stored_fields(item) for item in purchases(client))
    assert stored == sorted([stored_fields(first_payload), stored_fields(second_payload)])


def test_duplicate_of_item_without_reservation_is_rejected(client: TestClient) -> None:
    """PURC-014-TC1 against a purchase already persisted by the earlier CRUD (IMPL-RISK-004)."""
    as_user("user-a")
    legacy = PurchaseItem(
        user_id="user-a",
        id=uuid4(),
        name="牛乳",
        category="食品",
        speed=1,
        stock=2,
        is_temporary=False,
    )
    get_table().put_item(Item=legacy.to_item())
    assert len(purchases(client)) == 1

    duplicate = client.post("/purchases", json=valid_purchase())

    assert duplicate.status_code == 409
    assert [item["id"] for item in purchases(client)] == [str(legacy.id)]


def test_delete_then_recreate_same_pair_succeeds(client: TestClient) -> None:
    """IMPL-RISK-003: existing delete behavior must keep the pair available again."""
    as_user("user-a")
    created = client.post("/purchases", json=valid_purchase()).json()
    assert client.delete(f"/purchases/{created['id']}").status_code == 204
    assert purchases(client) == []

    recreated = client.post("/purchases", json=valid_purchase())

    assert recreated.status_code == 201
    assert recreated.json()["id"] != created["id"]
    assert [item["id"] for item in purchases(client)] == [recreated.json()["id"]]


# --- PURC-019: user separation ---


def test_list_contains_only_current_users_purchases(client: TestClient) -> None:
    """PURC-019-TC1."""
    as_user("user-a")
    a_item = client.post("/purchases", json=valid_purchase(name="牛乳")).json()
    as_user("user-b")
    b_item = client.post("/purchases", json=valid_purchase(name="洗剤", category="日用品")).json()

    as_user("user-a")
    assert purchases(client) == [a_item]
    as_user("user-b")
    assert purchases(client) == [b_item]


def test_reservation_rejects_duplicate_when_both_requests_pass_the_precheck(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PURC-014-TC8 / IMPL-RISK-005: force the race window deterministically.

    The implementation first reads existing purchases and then writes with a
    reservation. Concurrent requests can both pass the read; simulating that by
    hiding existing purchases from the pre-check must still yield one 201, one
    409, and a single stored purchase.
    """
    monkeypatch.setattr("app.models.purchase.get_all_purchase_items", lambda *_a, **_k: [])
    as_user("user-a")

    first = client.post("/purchases", json=valid_purchase())
    second = client.post("/purchases", json=valid_purchase(stock=5))

    assert (first.status_code, second.status_code) == (201, 409)
    assert purchases(client) == [first.json()]
