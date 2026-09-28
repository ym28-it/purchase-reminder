"""Approved purchase-create TDD scenarios plus post-implementation coverage."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from main import app

pytestmark = pytest.mark.integration


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


def test_purc_tdd_001_create_zero_speed_and_reload_from_storage(client: TestClient) -> None:
    """PURC-005-TC1, 008-TC1/2/3, 009-TC1, 004-TC12; CORE-001/002."""
    as_user("user-a")
    response = client.post("/purchases", json=valid_purchase(speed=0))

    assert response.status_code == 201
    created = response.json()
    UUID(created["id"])
    assert {"name", "category", "speed", "stock", "is_temporary"} <= created.keys()
    assert (created["name"], created["category"], created["speed"], created["stock"]) == (
        "牛乳",
        "食品",
        0,
        2,
    )
    assert created["is_temporary"] is False
    assert created["created_at"] and created["updated_at"]
    assert "user_id" not in created
    assert purchases(client) == [created]


def test_purc_tdd_004_whitespace_name_is_rejected_without_storage(client: TestClient) -> None:
    """PURC-003-TC2; CORE-002."""
    as_user("user-a")
    response = client.post("/purchases", json=valid_purchase(name="   "))

    assert response.status_code == 422
    assert "name" in str(response.json()).lower()
    assert purchases(client) == []


def test_purc_tdd_005_client_user_id_cannot_change_owner(client: TestClient) -> None:
    """PURC-007-TC1, 019-TC2; CORE-003 (approved Red exception)."""
    as_user("user-a")
    response = client.post("/purchases", json=valid_purchase(user_id="user-b"))
    assert response.status_code == 201
    created = response.json()
    assert "user_id" not in created
    assert purchases(client) == [created]

    as_user("user-b")
    assert purchases(client) == []


def test_purc_tdd_006_concurrent_identical_creates_leave_one_item(client: TestClient) -> None:
    """PURC-014-TC8; CORE-004."""
    as_user("user-a")
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(lambda _: client.post("/purchases", json=valid_purchase()), range(4))
        )

    assert sorted(response.status_code for response in responses) == [201, 409, 409, 409]
    saved = purchases(client)
    assert len(saved) == 1
    assert saved[0]["id"] == next(r.json()["id"] for r in responses if r.status_code == 201)


def test_purc_tdd_007_identical_names_are_allowed_for_different_users(
    client: TestClient,
) -> None:
    """PURC-014-TC7; CORE-004 (approved Red exception)."""
    as_user("user-a")
    first = client.post("/purchases", json=valid_purchase())
    assert first.status_code == 201
    as_user("user-b")
    second = client.post("/purchases", json=valid_purchase())
    assert second.status_code == 201
    assert [purchase["id"] for purchase in purchases(client)] == [second.json()["id"]]
    as_user("user-a")
    assert [purchase["id"] for purchase in purchases(client)] == [first.json()["id"]]


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"category": "   "}, "category"),
        ({"name": "x" * 51}, "name"),
        ({"category": "x" * 31}, "category"),
        ({"speed": -1}, "speed"),
        ({"speed": 1.5}, "speed"),
        ({"speed": 100001}, "speed"),
        ({"stock": -1}, "stock"),
        ({"stock": 1.5}, "stock"),
        ({"stock": 100001}, "stock"),
    ],
)
def test_post_invalid_inputs_are_rejected_without_storage(
    client: TestClient, overrides: dict[str, object], field: str
) -> None:
    """PURC-003-TC2, PURC-004-TC2/4/6/8/10."""
    as_user("user-a")
    response = client.post("/purchases", json=valid_purchase(**overrides))
    assert response.status_code == 422
    assert field in str(response.json()).lower()
    assert purchases(client) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "x" * 50},
        {"category": "x" * 30},
        {"speed": 100000},
        {"stock": 0},
        {"stock": 100000},
        {"speed": 0, "is_temporary": True},
    ],
)
def test_post_boundary_inputs_are_accepted(
    client: TestClient, overrides: dict[str, object]
) -> None:
    """PURC-004-TC3/5/7/9/11."""
    as_user("user-a")
    response = client.post("/purchases", json=valid_purchase(**overrides))
    assert response.status_code == 201
    assert len(purchases(client)) == 1


def test_post_missing_required_field_is_rejected(client: TestClient) -> None:
    """PURC-003-TC3."""
    as_user("user-a")
    payload = valid_purchase()
    del payload["name"]
    response = client.post("/purchases", json=payload)
    assert response.status_code == 422
    assert "name" in str(response.json()).lower()
    assert purchases(client) == []


def test_post_two_creates_get_distinct_system_ids(client: TestClient) -> None:
    """PURC-006-TC2."""
    as_user("user-a")
    first = client.post("/purchases", json=valid_purchase())
    second = client.post("/purchases", json=valid_purchase(name="卵"))
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_post_duplicate_ignores_non_key_fields(client: TestClient) -> None:
    """PURC-014-TC1/2."""
    as_user("user-a")
    assert client.post("/purchases", json=valid_purchase()).status_code == 201
    duplicate = client.post(
        "/purchases",
        json=valid_purchase(speed=9, stock=99, is_temporary=True),
    )
    assert duplicate.status_code == 409
    assert len(purchases(client)) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"category": "飲料"},
        {"name": "低脂肪乳"},
        {"name": " 牛乳 "},
        {"name": "milk"},
        {"name": "Ｍｉｌｋ"},
    ],
)
def test_post_exact_match_rules_allow_distinct_values(
    client: TestClient, overrides: dict[str, object]
) -> None:
    """PURC-014-TC3/4/5/6."""
    as_user("user-a")
    original_name = "Milk" if overrides.get("name") in {"milk", "Ｍｉｌｋ"} else "牛乳"
    original = valid_purchase(name=original_name)
    assert client.post("/purchases", json=original).status_code == 201
    assert client.post("/purchases", json=valid_purchase(**overrides)).status_code == 201
    assert len(purchases(client)) == 2


def test_post_update_releases_old_unique_reservation(client: TestClient) -> None:
    """IMPL-RISK-001: updating a purchase must not permanently block its old exact pair."""
    as_user("user-a")
    created = client.post("/purchases", json=valid_purchase()).json()
    updated = client.put(
        f"/purchases/{created['id']}",
        json=valid_purchase(name="低脂肪乳"),
    )
    assert updated.status_code == 200
    recreated = client.post("/purchases", json=valid_purchase())
    assert recreated.status_code == 201


def test_post_update_cannot_take_an_existing_unique_pair(client: TestClient) -> None:
    """IMPL-RISK-002: update must preserve the same uniqueness invariant as create."""
    as_user("user-a")
    first = client.post("/purchases", json=valid_purchase()).json()
    second = client.post("/purchases", json=valid_purchase(name="卵")).json()
    conflict = client.put(
        f"/purchases/{second['id']}",
        json=valid_purchase(name=first["name"], category=first["category"]),
    )
    assert conflict.status_code == 409
    assert len(purchases(client)) == 2


def test_post_delete_releases_unique_reservation(client: TestClient) -> None:
    """IMPL-RISK-003: deleting a purchase must allow the exact pair to be created again."""
    as_user("user-a")
    created = client.post("/purchases", json=valid_purchase()).json()
    deleted = client.delete(f"/purchases/{created['id']}")
    assert deleted.status_code == 204
    recreated = client.post("/purchases", json=valid_purchase())
    assert recreated.status_code == 201
