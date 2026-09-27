"""Approved purchase-create TDD scenarios (PURC-TDD-001, 004–007)."""

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
