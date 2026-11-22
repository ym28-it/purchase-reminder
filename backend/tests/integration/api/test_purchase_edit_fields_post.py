"""Post-implementation API coverage for purchase-edit-fields (PEDT).

Expected results come from the approved logical test cases
(docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md) and the spec
only. The frozen TDD scenarios live in ``test_purchase_edit_fields.py`` and are not
duplicated here.
"""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.core.dynamodb import get_table
from app.models.purchase import PurchaseItem
from main import app

pytestmark = pytest.mark.integration

USER = "user-a"


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


def edit(client: TestClient, created: dict[str, Any], **overrides: object) -> Any:
    return client.put(f"/purchases/{created['id']}", json=valid_purchase(**overrides))


def error_locs(response_json: dict[str, Any]) -> list[list[object]]:
    detail = response_json["detail"]
    assert isinstance(detail, list) and detail
    return [list(error["loc"]) for error in detail]


def when(value: object) -> datetime:
    return datetime.fromisoformat(str(value))


def raw_item(purchase_id: str) -> dict[str, Any]:
    key = PurchaseItem.build_key(user_id=USER, id=UUID(purchase_id))
    return get_table().get_item(Key=key, ConsistentRead=True)["Item"]


# --- PEDT-001-TC2: the remaining fields (the frozen test covers unit/buffer_days/is_temporary) ---


@pytest.mark.parametrize("missing", ["name", "category", "days_per_unit", "stock"])
def test_pedt_001_tc2_missing_name_category_days_or_stock_is_rejected(
    client: TestClient, missing: str
) -> None:
    as_user(USER)
    created = create(client)
    body = valid_purchase()
    del body[missing]

    response = client.put(f"/purchases/{created['id']}", json=body)

    assert response.status_code == 422
    assert ["body", missing] in error_locs(response.json())
    assert purchases(client) == [created]


# --- PEDT-001-TC3: fields the server does not accept from the client ---


def test_pedt_001_tc3_server_owned_fields_and_legacy_speed_are_ignored(
    client: TestClient,
) -> None:
    as_user(USER)
    created = create(client)
    time.sleep(0.01)
    body = valid_purchase(
        name="豆乳",
        stock_counted_at="2000-01-01T00:00:00Z",
        created_at="2000-01-01T00:00:00Z",
        updated_at="2000-01-01T00:00:00Z",
        id=str(uuid4()),
        speed=99,
    )

    response = client.put(f"/purchases/{created['id']}", json=body)

    assert response.status_code == 200
    [listed] = purchases(client)
    for result in (response.json(), listed):
        assert result["id"] == created["id"]
        assert result["created_at"] == created["created_at"]
        # stock is unchanged, so only the stock comparison decides stock_counted_at (PEDT-006)
        assert result["stock_counted_at"] == created["stock_counted_at"]
        assert when(result["updated_at"]) > when(created["updated_at"])
        assert result["name"] == "豆乳"
        assert "speed" not in result
    assert "speed" not in raw_item(created["id"])
    assert len(purchases(client)) == 1


# --- PEDT-002-TC1 / TC2: edit and registration agree on every value ---

REJECTED = [
    ("name", "あ" * 51),
    ("name", ""),
    ("name", "  "),
    ("category", "あ" * 31),
    ("category", ""),
    ("category", " "),
    ("unit", "あ" * 11),
    ("unit", ""),
    ("unit", " "),
    ("days_per_unit", 366),
    ("days_per_unit", -1),
    ("days_per_unit", 1.5),
    ("days_per_unit", 1.0),
    ("days_per_unit", "3"),
    ("buffer_days", 31),
    ("buffer_days", -1),
    ("buffer_days", 1.5),
    ("buffer_days", 1.0),
    ("buffer_days", "1"),
    ("stock", 100001),
    ("stock", -1),
    ("stock", 1.5),
    ("stock", 2.0),
    ("stock", "2"),
    ("is_temporary", "true"),
    ("is_temporary", 1),
]


@pytest.mark.parametrize(("field", "value"), REJECTED)
def test_pedt_002_tc2_edit_and_registration_reject_the_same_values(
    client: TestClient, field: str, value: object
) -> None:
    as_user(USER)
    created = create(client)

    edited = edit(client, created, **{field: value})
    registered = client.post("/purchases", json=valid_purchase(**{"name": "別物", field: value}))

    assert edited.status_code == registered.status_code == 422
    assert ["body", field] in error_locs(edited.json())
    assert ["body", field] in error_locs(registered.json())
    assert purchases(client) == [created]


BOUNDARIES: list[dict[str, object]] = [
    {"name": "あ" * 50},
    {"category": "い" * 30},
    {"unit": "𠮷" * 10},
    {"days_per_unit": 0},
    {"days_per_unit": 365},
    {"buffer_days": 0},
    {"buffer_days": 30},
    {"stock": 0},
    {"stock": 100_000},
]


@pytest.mark.parametrize("overrides", BOUNDARIES, ids=lambda o: next(iter(o)) + "=" + repr(o))
def test_pedt_002_tc1_edit_and_registration_accept_the_same_boundaries(
    client: TestClient, overrides: dict[str, object]
) -> None:
    as_user(USER)
    created = create(client)
    registered = client.post("/purchases", json=valid_purchase(**{**overrides, "name": "別物"}))
    assert registered.status_code == 201

    edited = edit(client, created, **overrides)

    assert edited.status_code == 200
    assert {key: edited.json()[key] for key in overrides} == overrides
    stored = {item["id"]: item for item in purchases(client)}[created["id"]]
    assert {key: stored[key] for key in overrides} == overrides


# --- PEDT-002-TC3: a padded name is a different pair from the unpadded name ---


def test_pedt_002_tc3_padded_name_is_stored_as_is_and_is_a_distinct_pair(
    client: TestClient,
) -> None:
    as_user(USER)
    create(client)
    other = create(client, name="豆乳")

    response = edit(client, other, name=" 牛乳 ")

    assert response.status_code == 200
    assert response.json()["name"] == " 牛乳 "
    assert raw_item(other["id"])["name"] == " 牛乳 "
    assert sorted(item["name"] for item in purchases(client)) == [" 牛乳 ", "牛乳"]
    assert client.post("/purchases", json=valid_purchase(name=" 牛乳 ")).status_code == 409


# --- PEDT-006-TC4: changing everything except stock never recounts ---


def test_pedt_006_tc4_multi_field_edit_without_stock_change_keeps_stock_counted_at(
    client: TestClient,
) -> None:
    as_user(USER)
    created = create(client, stock=2)
    time.sleep(0.01)

    response = edit(
        client,
        created,
        name="豆乳",
        category="飲料",
        unit="本",
        days_per_unit=9,
        buffer_days=4,
        stock=2,
        is_temporary=True,
    )

    assert response.status_code == 200
    [listed] = purchases(client)
    for body in (response.json(), listed):
        assert body["stock_counted_at"] == created["stock_counted_at"]
        assert (body["name"], body["unit"], body["buffer_days"], body["is_temporary"]) == (
            "豆乳",
            "本",
            4,
            True,
        )
        assert when(body["updated_at"]) > when(created["updated_at"])


# --- PEDT-009-TC3: editing an unknown id ---


def test_pedt_009_tc3_edit_of_unknown_id_is_404_and_creates_nothing(client: TestClient) -> None:
    as_user(USER)

    response = client.put(f"/purchases/{uuid4()}", json=valid_purchase())

    assert response.status_code == 404
    assert purchases(client) == []


# --- Persistence / isolation checks for the frozen scenarios (post-implementation) ---


def test_pedt_009_tc2_unit_only_edit_is_persisted_in_storage(client: TestClient) -> None:
    """The frozen test asserts the response; this checks the stored item (PEDT-005/009-TC2)."""
    as_user(USER)
    created = create(client)

    response = edit(client, created, unit="本")

    assert response.status_code == 200
    assert raw_item(created["id"])["unit"] == "本"
    [listed] = purchases(client)
    assert listed["unit"] == "本"


def test_pedt_009_tc1_rejected_rename_leaves_the_other_purchase_unchanged(
    client: TestClient,
) -> None:
    """The frozen test checks the edited purchase B; this checks the existing purchase A."""
    as_user(USER)
    a = create(client)
    b = create(client, name="豆乳")

    response = edit(client, b, name="牛乳", unit="本")

    assert response.status_code == 409
    assert raw_item(a["id"])["name"] == "牛乳"
    by_id = {item["id"]: item for item in purchases(client)}
    assert by_id[a["id"]] == a
    assert by_id[b["id"]] == b
    assert raw_item(b["id"])["unit"] == "パック"


# --- PEDT-010-TC2: an edited purchase can be deleted and its pair registered again ---


def test_pedt_010_tc2_edited_purchase_can_be_deleted_and_pair_registered_again(
    client: TestClient,
) -> None:
    as_user(USER)
    created = create(client)
    assert edit(client, created, unit="本", buffer_days=3).status_code == 200

    assert client.delete(f"/purchases/{created['id']}").status_code == 204

    assert purchases(client) == []
    assert client.post("/purchases", json=valid_purchase()).status_code == 201


# --- PEDT-009-TC4: the pre-edit pair is free after an edit that also changes other fields ---


def test_pedt_009_tc4_pre_edit_pair_can_be_registered_after_multi_field_edit(
    client: TestClient,
) -> None:
    as_user(USER)
    created = create(client)
    assert edit(client, created, name="豆乳", unit="本", buffer_days=3).status_code == 200

    assert client.post("/purchases", json=valid_purchase()).status_code == 201
    assert sorted(item["name"] for item in purchases(client)) == ["牛乳", "豆乳"]
