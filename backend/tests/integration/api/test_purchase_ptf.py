"""Approved purchase-timing-fields TDD scenarios (PTF-TDD-001〜012, PTF-CORE-001〜007).

Expected results come from the approved logical test cases
(docs/superpowers/specs/2026-11-12-purchase-timing-fields-test-cases.md) only.
"""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

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
        "unit": "パック",
        "days_per_unit": 3,
        "buffer_days": 0,
        "stock": 2,
        "is_temporary": False,
    }
    payload.update(overrides)
    return payload


def purchases(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/purchases")
    assert response.status_code == 200
    return response.json()


def create(client: TestClient, **overrides: object) -> dict[str, Any]:
    response = client.post("/purchases", json=valid_purchase(**overrides))
    assert response.status_code == 201
    return response.json()


def error_locs(response_json: dict[str, Any]) -> list[list[object]]:
    detail = response_json["detail"]
    assert isinstance(detail, list) and detail
    return [list(error["loc"]) for error in detail]


def assert_rejected_on(client: TestClient, payload: dict[str, object], field: str) -> None:
    response = client.post("/purchases", json=payload)

    assert response.status_code == 422
    assert ["body", field] in error_locs(response.json())
    assert purchases(client) == []


def when(value: object) -> datetime:
    return datetime.fromisoformat(str(value))


def test_ptf_tdd_001_ptf_008_tc1_create_returns_new_fields(client: TestClient) -> None:
    """PTF-008-TC1; PTF-CORE-001/002."""
    as_user("user-a")
    response = client.post("/purchases", json=valid_purchase())

    assert response.status_code == 201
    body = response.json()
    assert body["unit"] == "パック"
    assert body["days_per_unit"] == 3
    assert body["buffer_days"] == 0
    assert body["stock_counted_at"] == body["created_at"]
    assert "speed" not in body


def test_ptf_tdd_002_ptf_011_tc1_list_reads_back_new_fields(client: TestClient) -> None:
    """PTF-011-TC1; PTF-CORE-001/002."""
    as_user("user-a")
    created = create(client, buffer_days=2)

    [listed] = purchases(client)

    for key in ("unit", "days_per_unit", "buffer_days", "stock_counted_at"):
        assert key in created
        assert listed[key] == created[key]


def test_ptf_tdd_003_ptf_006_tc2_client_stock_counted_at_is_ignored(client: TestClient) -> None:
    """PTF-006-TC2; PTF-CORE-003."""
    as_user("user-a")
    response = client.post(
        "/purchases", json=valid_purchase(stock_counted_at="2000-01-01T00:00:00Z")
    )

    assert response.status_code == 201
    body = response.json()
    assert body["stock_counted_at"] == body["created_at"]
    assert body["stock_counted_at"] != "2000-01-01T00:00:00Z"


def test_ptf_tdd_004_ptf_002_tc2_days_per_unit_366_is_rejected(client: TestClient) -> None:
    """PTF-002-TC2; PTF-CORE-004."""
    as_user("user-a")
    assert_rejected_on(client, valid_purchase(days_per_unit=366), "days_per_unit")


def test_ptf_tdd_005_ptf_001_tc3_legacy_speed_only_is_rejected(client: TestClient) -> None:
    """PTF-001-TC3; PTF-CORE-001."""
    as_user("user-a")
    payload = valid_purchase(speed=3)
    del payload["days_per_unit"]

    assert_rejected_on(client, payload, "days_per_unit")


def test_ptf_tdd_006_ptf_003_tc4_missing_buffer_days_is_rejected(client: TestClient) -> None:
    """PTF-003-TC4; PTF-CORE-004."""
    as_user("user-a")
    payload = valid_purchase()
    del payload["buffer_days"]

    assert_rejected_on(client, payload, "buffer_days")


def test_ptf_tdd_007_ptf_003_tc3_buffer_days_31_is_rejected(client: TestClient) -> None:
    """PTF-003-TC3; PTF-CORE-004."""
    as_user("user-a")
    assert_rejected_on(client, valid_purchase(buffer_days=31), "buffer_days")


def test_ptf_tdd_008_ptf_014_tc1_missing_unit_is_rejected(client: TestClient) -> None:
    """PTF-014-TC1; PTF-CORE-005."""
    as_user("user-a")
    payload = valid_purchase()
    del payload["unit"]

    assert_rejected_on(client, payload, "unit")


def test_ptf_tdd_009_ptf_014_tc4_unit_of_11_chars_is_rejected(client: TestClient) -> None:
    """PTF-014-TC4; PTF-CORE-005."""
    as_user("user-a")
    assert_rejected_on(client, valid_purchase(unit="あ" * 11), "unit")


def test_ptf_tdd_010_ptf_013_tc1_stock_edit_recounts_at_updated_at(client: TestClient) -> None:
    """PTF-013-TC1; PTF-CORE-006."""
    as_user("user-a")
    created = create(client)
    time.sleep(0.01)

    response = client.put(
        f"/purchases/{created['id']}",
        json={
            "name": "牛乳",
            "category": "食品",
            "days_per_unit": 3,
            "stock": 5,
            "is_temporary": False,
        },
    )

    assert response.status_code == 200
    edited = response.json()
    assert edited["stock_counted_at"] == edited["updated_at"]
    assert when(edited["stock_counted_at"]) > when(created["stock_counted_at"])
    [listed] = purchases(client)
    assert listed["stock_counted_at"] == edited["stock_counted_at"]


def test_ptf_tdd_011_ptf_007_tc1_rename_keeps_stock_counted_at(client: TestClient) -> None:
    """PTF-007-TC1; PTF-CORE-006."""
    as_user("user-a")
    created = create(client)
    time.sleep(0.01)

    response = client.put(
        f"/purchases/{created['id']}",
        json={
            "name": "豆乳",
            "category": "飲料",
            "days_per_unit": 3,
            "stock": 2,
            "is_temporary": False,
        },
    )

    assert response.status_code == 200
    edited = response.json()
    assert when(edited["updated_at"]) > when(created["created_at"])
    assert edited["stock_counted_at"] == created["stock_counted_at"]


def test_ptf_tdd_012_ptf_012_tc1_edit_keeps_unit_and_buffer_days(client: TestClient) -> None:
    """PTF-012-TC1; PTF-CORE-007."""
    as_user("user-a")
    created = create(client, buffer_days=2)

    response = client.put(
        f"/purchases/{created['id']}",
        json={
            "name": "牛乳",
            "category": "食品",
            "days_per_unit": 5,
            "stock": 2,
            "is_temporary": False,
        },
    )

    assert response.status_code == 200
    [listed] = purchases(client)
    for body in (response.json(), listed):
        assert (body["days_per_unit"], body["unit"], body["buffer_days"]) == (5, "パック", 2)
