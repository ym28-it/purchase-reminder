"""Approved purchase-edit-fields TDD scenarios (PEDT-TDD-001〜010, PEDT-CORE-001〜006).

Expected results come from the approved logical test cases
(docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md) only.
"""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

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


def edit(client: TestClient, created: dict[str, Any], **overrides: object) -> Response:
    return client.put(f"/purchases/{created['id']}", json=valid_purchase(**overrides))


def assert_edit_rejected_on(
    client: TestClient, created: dict[str, Any], field: str, **overrides: object
) -> None:
    response = edit(client, created, **overrides)

    assert response.status_code == 422
    assert ["body", field] in error_locs(response.json())
    assert purchases(client) == [created]


def when(value: object) -> datetime:
    return datetime.fromisoformat(str(value))


def test_pedt_tdd_001_pedt_001_tc1_edit_changes_all_seven_fields(client: TestClient) -> None:
    """PEDT-001-TC1, PEDT-005-TC1, PEDT-005-TC2; PEDT-CORE-001/002."""
    as_user("user-a")
    created = create(client)
    time.sleep(0.01)
    sent = {
        "name": "豆乳",
        "category": "飲料",
        "unit": "本",
        "days_per_unit": 5,
        "buffer_days": 2,
        "stock": 7,
        "is_temporary": True,
    }

    response = edit(client, created, **sent)

    assert response.status_code == 200
    edited = response.json()
    [listed] = purchases(client)
    for body in (edited, listed):
        assert {key: body[key] for key in sent} == sent
        assert body["id"] == created["id"]
        assert body["created_at"] == created["created_at"]
        assert when(body["updated_at"]) > when(created["created_at"])
        assert "user_id" not in body
    assert edited == listed


@pytest.mark.parametrize("missing", ["unit", "buffer_days", "is_temporary"])
def test_pedt_tdd_002_pedt_001_tc2_missing_required_field_is_rejected(
    client: TestClient, missing: str
) -> None:
    """PEDT-001-TC2; PEDT-CORE-003."""
    as_user("user-a")
    created = create(client, is_temporary=True)
    body = valid_purchase(is_temporary=False)
    del body[missing]

    response = client.put(f"/purchases/{created['id']}", json=body)

    assert response.status_code == 422
    assert ["body", missing] in error_locs(response.json())
    assert purchases(client) == [created]


def test_pedt_tdd_003_pedt_004_tc1_multiple_violations_are_identified_per_field(
    client: TestClient,
) -> None:
    """PEDT-004-TC1; PEDT-CORE-003."""
    as_user("user-a")
    created = create(client)

    response = edit(client, created, days_per_unit=366, buffer_days=31)

    assert response.status_code == 422
    locs = error_locs(response.json())
    assert ["body", "days_per_unit"] in locs
    assert ["body", "buffer_days"] in locs
    assert purchases(client) == [created]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("days_per_unit", 366),
        ("days_per_unit", 1.5),
        ("days_per_unit", 1.0),
        ("days_per_unit", "3"),
        ("buffer_days", 31),
        ("buffer_days", 1.5),
        ("buffer_days", "1"),
        ("stock", 100001),
        ("stock", 1.5),
        ("stock", 2.0),
        ("stock", "2"),
        ("is_temporary", "true"),
        ("is_temporary", 1),
    ],
)
def test_pedt_tdd_004_pedt_002_tc2_out_of_range_or_wrong_numeric_type_is_rejected(
    client: TestClient, field: str, value: object
) -> None:
    """PEDT-002-TC2 (numeric fields); PEDT-CORE-003."""
    as_user("user-a")
    created = create(client)

    assert_edit_rejected_on(client, created, field, **{field: value})


@pytest.mark.parametrize(
    ("field", "value", "is_temporary"),
    [
        ("days_per_unit", 0, False),
        ("days_per_unit", 0, True),
        ("days_per_unit", 365, False),
        ("buffer_days", 0, False),
        ("buffer_days", 30, False),
        ("stock", 0, False),
        ("stock", 100000, False),
    ],
)
def test_pedt_tdd_005_pedt_002_tc1_pedt_003_tc1_numeric_boundaries_are_accepted(
    client: TestClient, field: str, value: int, is_temporary: bool
) -> None:
    """PEDT-002-TC1 (numeric fields), PEDT-003-TC1; PEDT-CORE-003."""
    as_user("user-a")
    created = create(client, days_per_unit=3, buffer_days=1, stock=2)

    response = edit(client, created, is_temporary=is_temporary, **{field: value})

    assert response.status_code == 200
    [listed] = purchases(client)
    assert response.json()[field] == value
    assert listed[field] == value
    assert listed["is_temporary"] is is_temporary


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "あ" * 51),
        ("name", "  "),
        ("category", "あ" * 31),
        ("category", " "),
        ("unit", "あ" * 11),
        ("unit", " "),
        ("unit", ""),
    ],
)
def test_pedt_tdd_006_pedt_002_tc2_text_limits_and_blank_are_rejected(
    client: TestClient, field: str, value: str
) -> None:
    """PEDT-002-TC2 (text fields); PEDT-CORE-003."""
    as_user("user-a")
    created = create(client)

    assert_edit_rejected_on(client, created, field, **{field: value})


def test_pedt_tdd_007_pedt_002_tc1_tc3_text_boundaries_and_padding_are_stored_as_is(
    client: TestClient,
) -> None:
    """PEDT-002-TC1 (text fields), PEDT-002-TC3; PEDT-CORE-003."""
    as_user("user-a")
    created = create(client)
    boundary = {"name": "あ" * 50, "category": "い" * 30, "unit": "𠮷" * 10}

    response = edit(client, created, **boundary)

    assert response.status_code == 200
    [listed] = purchases(client)
    for body in (response.json(), listed):
        assert {key: body[key] for key in boundary} == boundary

    padded = edit(client, created, **{**boundary, "unit": " パック "})

    assert padded.status_code == 200
    [listed] = purchases(client)
    assert padded.json()["unit"] == " パック "
    assert listed["unit"] == " パック "


@pytest.mark.parametrize(("field", "value"), [("unit", "本"), ("buffer_days", 5)])
def test_pedt_tdd_008_pedt_006_tc2_tc3_unit_or_buffer_only_edit_keeps_stock_counted_at(
    client: TestClient, field: str, value: object
) -> None:
    """PEDT-006-TC2, PEDT-006-TC3; PEDT-CORE-004."""
    as_user("user-a")
    created = create(client)
    time.sleep(0.01)

    response = edit(client, created, **{field: value})

    assert response.status_code == 200
    [listed] = purchases(client)
    for body in (response.json(), listed):
        assert body[field] == value
        assert body["stock_counted_at"] == created["stock_counted_at"]
        assert when(body["updated_at"]) > when(created["updated_at"])


def test_pedt_tdd_009_pedt_009_tc1_rename_into_pair_with_other_unit_is_409(
    client: TestClient,
) -> None:
    """PEDT-009-TC1; PEDT-CORE-005 (regression / characterization)."""
    as_user("user-a")
    create(client)
    other = create(client, name="豆乳")

    response = edit(client, other, name="牛乳", unit="本")

    assert response.status_code == 409
    by_id = {item["id"]: item for item in purchases(client)}
    assert by_id[other["id"]] == other


def test_pedt_tdd_010_pedt_009_tc2_unit_only_edit_is_not_a_self_duplicate(
    client: TestClient,
) -> None:
    """PEDT-009-TC2; PEDT-CORE-006."""
    as_user("user-a")
    created = create(client)

    response = edit(client, created, unit="本")

    assert response.status_code == 200
    assert response.json()["unit"] == "本"
