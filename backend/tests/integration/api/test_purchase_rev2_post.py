"""Post-implementation API coverage for purchase-create rev2 (docs/specs/purchase-create*.md).

Expected results come from the approved spec rev2 and logical test cases rev2 only.
The frozen rev2 TDD scenarios live in ``test_purchase_uniqueness_rev2.py`` and are not
duplicated here; the stale-read fault injection below is the same technique.

Edit/delete statuses are not part of this slice (spec §8), so racing edits are judged
only by what PURC-024 makes observable: afterwards a pair that is not listed can be
registered (201) and a listed pair is a duplicate (409).
"""

import copy
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.core.dynamodb import get_table
from app.models.purchase import PurchaseItem
from main import app

pytestmark = pytest.mark.integration

USER_ID = "user-a"
PAIR_X = ("牛乳", "食品")
PAIR_Y = ("豆乳", "食品")


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    # Edit/delete conflicts may surface as server errors; inspect them as responses.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def payload(pair: tuple[str, str], **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": pair[0],
        "category": pair[1],
        "speed": 1,
        "stock": 2,
        "is_temporary": False,
    }
    body.update(overrides)
    return body


def purchases(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/purchases")
    assert response.status_code == 200
    return response.json()


def listed_pairs(client: TestClient) -> set[tuple[object, object]]:
    return {(item["name"], item["category"]) for item in purchases(client)}


def expect_pairs_follow_the_list(client: TestClient, pairs: tuple[tuple[str, str], ...]) -> None:
    """PURC-024: unlisted pairs are registrable, listed pairs are duplicates."""
    listed = listed_pairs(client)
    expected = {pair: 409 if pair in listed else 201 for pair in pairs}
    results = {pair: client.post("/purchases", json=payload(pair)).status_code for pair in pairs}
    assert results == expected


def stored_item(purchase_id: str) -> dict[str, Any]:
    key = PurchaseItem.build_key(user_id=USER_ID, id=UUID(purchase_id))
    response = get_table().get_item(Key=key, ConsistentRead=True)
    return copy.deepcopy(response["Item"])


class StaleReadTable:
    """Real table whose ``get_item`` of one key returns a stale snapshot ``times`` times."""

    def __init__(self, real: Any, stale_item: dict[str, Any], times: int) -> None:
        self._real = real
        self._stale_item = stale_item
        self._stale_key = {"PK": stale_item["PK"], "SK": stale_item["SK"]}
        self._remaining = times
        self.stale_reads = 0

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        if self._remaining > 0 and kwargs.get("Key") == self._stale_key:
            self._remaining -= 1
            self.stale_reads += 1
            return {"Item": copy.deepcopy(self._stale_item)}
        return self._real.get_item(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def inject_stale_reads(
    monkeypatch: pytest.MonkeyPatch, stale_item: dict[str, Any], times: int
) -> StaleReadTable:
    proxy = StaleReadTable(get_table(), stale_item, times)
    monkeypatch.setattr("app.models.purchase.get_table", lambda table_name=None: proxy)
    return proxy


def create_snapshot_and_rename(client: TestClient) -> tuple[str, dict[str, Any]]:
    """Register P with pair X, snapshot it, then commit a rename of P to pair Y."""
    created = client.post("/purchases", json=payload(PAIR_X))
    assert created.status_code == 201
    purchase_id = created.json()["id"]
    snapshot = stored_item(purchase_id)
    renamed = client.put(f"/purchases/{purchase_id}", json=payload(PAIR_Y))
    assert renamed.status_code == 200
    return purchase_id, snapshot


# --- PURC-004-TC13: numbers must be JSON integers ---


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("speed", 1.0, id="speed-1.0"),
        pytest.param("speed", "1", id="speed-string-1"),
        pytest.param("stock", 1.0, id="stock-1.0"),
        pytest.param("stock", "1", id="stock-string-1"),
    ],
)
def test_purc_004_tc13_integer_valued_non_integer_json_is_rejected_and_not_stored(
    client: TestClient, field: str, value: object
) -> None:
    response = client.post("/purchases", json=payload(PAIR_X, **{field: value}))

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert field in {str(error["loc"][-1]) for error in detail}
    assert purchases(client) == []


# --- PURC-023-TC3: editing only other fields keeps the pair reserved ---


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"speed": 7}, id="speed"),
        pytest.param({"stock": 9}, id="stock"),
        pytest.param({"is_temporary": True}, id="is_temporary"),
        pytest.param({"speed": 3, "stock": 0, "is_temporary": True}, id="all-other-fields"),
        pytest.param({}, id="identical"),
    ],
)
def test_purc_023_tc3_edit_without_pair_change_keeps_duplicate_rejected(
    client: TestClient, overrides: dict[str, object]
) -> None:
    created = client.post("/purchases", json=payload(PAIR_X))
    assert created.status_code == 201
    edited = client.put(f"/purchases/{created.json()['id']}", json=payload(PAIR_X, **overrides))
    assert edited.status_code == 200
    before = purchases(client)

    duplicate = client.post("/purchases", json=payload(PAIR_X))

    assert duplicate.status_code == 409
    assert purchases(client) == before


# --- PURC-024: an edit that keeps the pair races a rename ---


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"stock": 9}, id="stock-only"),
        pytest.param({"is_temporary": True}, id="is_temporary-only"),
    ],
)
def test_purc_024_same_pair_edit_racing_rename_leaves_no_orphaned_pair(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, overrides: dict[str, object]
) -> None:
    """The edit read P as pair X before the rename to Y was committed and keeps pair X."""
    purchase_id, snapshot = create_snapshot_and_rename(client)

    proxy = inject_stale_reads(monkeypatch, snapshot, times=1)
    client.put(f"/purchases/{purchase_id}", json=payload(PAIR_X, **overrides))
    monkeypatch.undo()

    assert proxy.stale_reads == 1  # the race window was actually exercised
    assert [item["id"] for item in purchases(client)] == [purchase_id]
    expect_pairs_follow_the_list(client, (PAIR_X, PAIR_Y))


# --- Bounded retries exhausted: the uniqueness invariant still holds ---


def test_purc_024_edit_whose_retries_are_exhausted_leaves_no_orphaned_pair(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every read of P is stale, so the edit can never commit (retries exhausted).

    The status of a failed edit is not specified (spec §8); spec §6 forbids internal
    details in user-facing errors, and PURC-024 must still hold afterwards.
    """
    purchase_id, snapshot = create_snapshot_and_rename(client)

    inject_stale_reads(monkeypatch, snapshot, times=1_000)
    edited = client.put(f"/purchases/{purchase_id}", json=payload(PAIR_X, stock=9))
    monkeypatch.undo()

    for leaked in ("Traceback", "ConditionalCheck", "TransactWrite", "PURCHASE_UNIQUE"):
        assert leaked not in edited.text
    assert [item["id"] for item in purchases(client)] == [purchase_id]
    expect_pairs_follow_the_list(client, (PAIR_X, PAIR_Y))


def test_purc_024_delete_whose_retries_are_exhausted_leaves_no_orphaned_pair(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    purchase_id, snapshot = create_snapshot_and_rename(client)

    inject_stale_reads(monkeypatch, snapshot, times=1_000)
    deleted = client.delete(f"/purchases/{purchase_id}")
    monkeypatch.undo()

    for leaked in ("Traceback", "ConditionalCheck", "TransactWrite", "PURCHASE_UNIQUE"):
        assert leaked not in deleted.text
    assert [item["id"] for item in purchases(client)] == [purchase_id]
    expect_pairs_follow_the_list(client, (PAIR_X, PAIR_Y))


# --- PURC-023-TC2: the reservation still rejects a rename that passed the pre-check ---


def test_purc_023_tc2_rename_into_existing_pair_is_409_even_when_precheck_misses_it(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrent create can land between the edit's pre-check and its write.

    Hiding existing purchases from the edit's pre-check forces that window
    deterministically; the rename must still be rejected with 409 and not persisted.
    """
    created_a = client.post("/purchases", json=payload(PAIR_X))
    created_b = client.post("/purchases", json=payload(PAIR_Y))
    assert created_a.status_code == created_b.status_code == 201
    before = purchases(client)

    monkeypatch.setattr("app.models.purchase.get_all_purchase_items", lambda *_a, **_k: [])
    edited = client.put(f"/purchases/{created_a.json()['id']}", json=payload(PAIR_Y, stock=9))
    monkeypatch.undo()

    assert edited.status_code == 409
    assert sorted(purchases(client), key=lambda item: item["id"]) == sorted(
        before, key=lambda item: item["id"]
    )
    expect_pairs_follow_the_list(client, (PAIR_X, PAIR_Y))
