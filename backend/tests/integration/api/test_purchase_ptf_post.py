"""Post-implementation API coverage for purchase-timing-fields (PTF).

Expected results come from the approved logical test cases
(docs/superpowers/specs/2026-11-12-purchase-timing-fields-test-cases.md) and the
plan Review Focus only. The frozen TDD scenarios live in ``test_purchase_ptf.py`` and
are not duplicated here.
"""

import re
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.core.dynamodb import get_table
from app.models.purchase import PurchaseItem
from app.services import purchase_service
from main import app

pytestmark = pytest.mark.integration

SURROGATE = "\U00020bb7"  # 𠮷: one character, two UTF-16 code units
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


def put_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": "牛乳",
        "category": "食品",
        "days_per_unit": 3,
        "stock": 2,
        "is_temporary": False,
    }
    body.update(overrides)
    return body


def purchases(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/purchases")
    assert response.status_code == 200
    return response.json()


def create(client: TestClient, **overrides: object) -> dict[str, Any]:
    response = client.post("/purchases", json=valid_purchase(**overrides))
    assert response.status_code == 201
    return response.json()


def error_fields(response_json: dict[str, Any]) -> set[str]:
    detail = response_json["detail"]
    assert isinstance(detail, list) and detail
    return {str(error["loc"][-1]) for error in detail}


def when(value: object) -> datetime:
    return datetime.fromisoformat(str(value))


def assert_rejected_on(client: TestClient, overrides: dict[str, object], field: str) -> None:
    response = client.post("/purchases", json=valid_purchase(**overrides))

    assert response.status_code == 422
    assert field in error_fields(response.json())
    assert purchases(client) == []


def raw_item(purchase_id: str) -> dict[str, Any]:
    key = PurchaseItem.build_key(user_id=USER, id=UUID(purchase_id))
    return get_table().get_item(Key=key, ConsistentRead=True)["Item"]


# --- PTF-001: field rename ---


def test_ptf_001_tc2_days_per_unit_matches_input_in_response_and_refetch(
    client: TestClient,
) -> None:
    as_user(USER)
    created = create(client, days_per_unit=7)

    [listed] = purchases(client)

    for body in (created, listed):
        assert body["days_per_unit"] == 7
        assert "speed" not in body


def test_ptf_001_tc4_legacy_speed_is_ignored_when_days_per_unit_is_given(
    client: TestClient,
) -> None:
    as_user(USER)

    response = client.post("/purchases", json=valid_purchase(speed=99))

    assert response.status_code == 201
    assert response.json()["days_per_unit"] == 3
    assert "speed" not in response.json()
    [listed] = purchases(client)
    assert listed["days_per_unit"] == 3
    assert "speed" not in listed


# --- PTF-002 / PTF-003 / PTF-005: ranges and types ---


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"days_per_unit": 0}, id="PTF-002-TC1-days-0"),
        pytest.param({"days_per_unit": 365}, id="PTF-002-TC1-days-365"),
        pytest.param({"days_per_unit": 0, "is_temporary": True}, id="PTF-002-TC3-temporary-true"),
        pytest.param({"days_per_unit": 0, "is_temporary": False}, id="PTF-002-TC3-temporary-false"),
        pytest.param({"buffer_days": 0}, id="PTF-003-TC2-buffer-0"),
        pytest.param({"buffer_days": 30}, id="PTF-003-TC2-buffer-30"),
        pytest.param({"stock": 0}, id="PTF-004-TC1-stock-0"),
        pytest.param({"stock": 100000}, id="PTF-004-TC1-stock-100000"),
        pytest.param({"unit": "あ" * 10}, id="PTF-014-TC3-unit-10"),
        pytest.param({"unit": SURROGATE * 10}, id="PTF-014-TC3-unit-10-surrogate"),
        pytest.param({"unit": " パック "}, id="PTF-014-TC5-unit-surrounding-spaces"),
    ],
)
def test_accepted_boundaries_are_stored_unchanged(
    client: TestClient, overrides: dict[str, object]
) -> None:
    as_user(USER)
    payload = valid_purchase(**overrides)

    response = client.post("/purchases", json=payload)

    assert response.status_code == 201
    [stored] = purchases(client)
    for key, value in payload.items():
        assert stored[key] == value


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        pytest.param({"days_per_unit": -1}, "days_per_unit", id="PTF-005-TC1-days-negative"),
        pytest.param({"days_per_unit": 1.5}, "days_per_unit", id="PTF-005-TC1-days-1.5"),
        pytest.param({"days_per_unit": 1.0}, "days_per_unit", id="PTF-005-TC1-days-1.0"),
        pytest.param({"days_per_unit": "3"}, "days_per_unit", id="PTF-005-TC2-days-string"),
        pytest.param({"days_per_unit": 366}, "days_per_unit", id="PTF-002-TC2-days-366"),
        pytest.param({"buffer_days": -1}, "buffer_days", id="PTF-005-TC3-buffer-negative"),
        pytest.param({"buffer_days": 1.5}, "buffer_days", id="PTF-005-TC3-buffer-1.5"),
        pytest.param({"buffer_days": 1.0}, "buffer_days", id="PTF-005-TC3-buffer-1.0"),
        pytest.param({"buffer_days": "1"}, "buffer_days", id="PTF-005-TC3-buffer-string"),
        pytest.param({"buffer_days": 31}, "buffer_days", id="PTF-003-TC3-buffer-31"),
        pytest.param({"stock": -1}, "stock", id="PTF-004-TC2-stock-negative"),
        pytest.param({"stock": 1.5}, "stock", id="PTF-004-TC2-stock-decimal"),
        pytest.param({"stock": 100001}, "stock", id="PTF-004-TC2-stock-over"),
        pytest.param({"unit": ""}, "unit", id="PTF-014-TC2-unit-empty"),
        pytest.param({"unit": "   "}, "unit", id="PTF-014-TC2-unit-spaces"),
        pytest.param({"unit": "　"}, "unit", id="PTF-014-TC2-unit-u3000"),
        pytest.param({"unit": "あ" * 11}, "unit", id="PTF-014-TC4-unit-11"),
        pytest.param({"unit": SURROGATE * 11}, "unit", id="PTF-014-TC4-unit-11-surrogate"),
    ],
)
def test_out_of_range_or_wrong_type_is_rejected_with_field_and_not_stored(
    client: TestClient, overrides: dict[str, object], field: str
) -> None:
    as_user(USER)
    assert_rejected_on(client, overrides, field)


# --- PTF-006: stock_counted_at at registration ---


def test_ptf_006_tc1_stock_counted_at_equals_created_at_in_response_and_refetch(
    client: TestClient,
) -> None:
    as_user(USER)
    created = create(client)

    [listed] = purchases(client)

    for body in (created, listed):
        assert body["stock_counted_at"] == body["created_at"]


# --- PTF-007 / PTF-013: editing ---


def test_ptf_013_tc2_same_stock_edit_keeps_stock_counted_at(client: TestClient) -> None:
    as_user(USER)
    created = create(client)
    time.sleep(0.01)

    response = client.put(f"/purchases/{created['id']}", json=put_body(name="豆乳"))

    assert response.status_code == 200
    assert response.json()["stock_counted_at"] == created["stock_counted_at"]
    assert when(response.json()["updated_at"]) > when(created["updated_at"])
    [listed] = purchases(client)
    assert listed["stock_counted_at"] == created["stock_counted_at"]


def test_review_focus_1_edit_keeps_created_at(client: TestClient) -> None:
    as_user(USER)
    created = create(client)
    raw_created_at = raw_item(created["id"])["created_at"]
    time.sleep(0.01)

    response = client.put(f"/purchases/{created['id']}", json=put_body(name="豆乳", stock=9))

    assert response.status_code == 200
    assert response.json()["created_at"] == created["created_at"]
    [listed] = purchases(client)
    assert listed["created_at"] == created["created_at"]
    assert raw_item(created["id"])["created_at"] == raw_created_at


@pytest.mark.parametrize("sent", [2, 2.0])
def test_review_focus_5_stock_2_and_2_0_do_not_update_stock_counted_at(
    client: TestClient, sent: float
) -> None:
    as_user(USER)
    created = create(client, stock=2)
    time.sleep(0.01)

    response = client.put(f"/purchases/{created['id']}", json=put_body(stock=sent))

    assert response.status_code == 200
    assert response.json()["stock_counted_at"] == created["stock_counted_at"]
    [listed] = purchases(client)
    assert listed["stock_counted_at"] == created["stock_counted_at"]


# --- Review Focus 4: UTC ISO 8601 format ---

ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


def test_review_focus_4_stock_counted_at_is_utc_iso_like_created_at(client: TestClient) -> None:
    as_user(USER)
    created = create(client)
    time.sleep(0.01)
    edited = client.put(f"/purchases/{created['id']}", json=put_body(stock=9)).json()

    for body in (created, edited, *purchases(client)):
        for key in ("stock_counted_at", "created_at"):
            assert ISO_UTC.match(body[key]), body[key]
            assert when(str(body[key]).replace("Z", "+00:00")).utcoffset() == timedelta(0)
        # same offset notation as created_at
        assert body["stock_counted_at"][-1] == body["created_at"][-1]

    stored = raw_item(created["id"])
    for key in ("stock_counted_at", "created_at"):
        assert isinstance(stored[key], str)
        assert ISO_UTC.match(stored[key]), stored[key]
    assert stored["stock_counted_at"][-1] == stored["created_at"][-1]


# --- PTF-016: unit is not part of the duplicate key ---


def test_ptf_016_tc1_different_unit_with_same_name_and_category_is_409(
    client: TestClient,
) -> None:
    as_user(USER)
    original = create(client, unit="パック")

    duplicate = client.post("/purchases", json=valid_purchase(unit="本"))

    assert duplicate.status_code == 409
    assert purchases(client) == [original]


# --- Review Focus 3: a retried edit compares stock with the latest stored value ---


def inject_concurrent_edit(
    monkeypatch: pytest.MonkeyPatch, purchase_id: str, concurrent: Callable[[], None]
) -> list[int]:
    """Run ``concurrent`` once, right after the edit's first read and before its write."""
    import app.models.purchase as models

    original = models._read_current
    reads: list[int] = []
    racing = False

    def read_then_race(table: Any, key: dict[str, str], id: UUID) -> PurchaseItem:
        nonlocal racing
        item = original(table, key, id)
        if racing:  # a read made by the concurrent edit itself is not an attempt of ours
            return item
        reads.append(1)
        if len(reads) == 1:
            racing = True
            try:
                concurrent()
            finally:
                racing = False
        return item

    monkeypatch.setattr(models, "_read_current", read_then_race)
    return reads


def concurrent_stock_edit(purchase_id: str, stock: float) -> Callable[[], None]:
    def run() -> None:
        purchase_service.put_purchase(
            USER,
            UUID(purchase_id),
            name="牛乳",
            category="食品",
            days_per_unit=3,
            stock=stock,
            is_temporary=False,
        )

    return run


def test_review_focus_3_retry_compares_with_latest_stock_equal_keeps_counted_at(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another edit already set stock 7; our retried edit of 7 must not re-count it."""
    as_user(USER)
    created = create(client, stock=2)
    time.sleep(0.01)
    holder: dict[str, Any] = {}

    def race() -> None:
        concurrent_stock_edit(created["id"], 7)()
        holder["concurrent"] = raw_item(created["id"])

    reads = inject_concurrent_edit(monkeypatch, created["id"], race)

    response = client.put(f"/purchases/{created['id']}", json=put_body(stock=7))

    assert response.status_code == 200
    assert len(reads) == 2  # the first attempt lost the race and was retried
    concurrent = holder["concurrent"]
    assert response.json()["stock"] == 7
    assert response.json()["stock_counted_at"] == concurrent["stock_counted_at"]
    assert when(response.json()["stock_counted_at"]) > when(created["stock_counted_at"])
    assert when(response.json()["updated_at"]) > when(concurrent["updated_at"])
    assert response.json()["created_at"] == created["created_at"]


def test_review_focus_3_retry_compares_with_latest_stock_different_recounts(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Our edit sends the stale stock 2, but stock is now 9: the retry is a real change."""
    as_user(USER)
    created = create(client, stock=2)
    time.sleep(0.01)
    reads = inject_concurrent_edit(
        monkeypatch, created["id"], concurrent_stock_edit(created["id"], 9)
    )

    response = client.put(f"/purchases/{created['id']}", json=put_body(stock=2))

    assert response.status_code == 200
    assert len(reads) == 2
    body = response.json()
    assert body["stock"] == 2
    assert body["stock_counted_at"] == body["updated_at"]
    assert when(body["stock_counted_at"]) > when(created["stock_counted_at"])
    assert body["created_at"] == created["created_at"]


def test_review_focus_3_unrelated_concurrent_write_does_not_recount_stock(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrent rename (stock unchanged) forces a retry that still keeps stock_counted_at."""
    as_user(USER)
    created = create(client, stock=2)
    time.sleep(0.01)

    def rename() -> None:
        purchase_service.put_purchase(
            USER,
            UUID(created["id"]),
            name="牛乳",
            category="食品",
            days_per_unit=8,
            stock=2,
            is_temporary=False,
        )

    reads = inject_concurrent_edit(monkeypatch, created["id"], rename)

    response = client.put(f"/purchases/{created['id']}", json=put_body(stock=2.0, days_per_unit=4))

    assert response.status_code == 200
    assert len(reads) == 2
    assert response.json()["stock_counted_at"] == created["stock_counted_at"]
    assert response.json()["days_per_unit"] == 4
