"""Pre-implementation TDD tests for purchase-create rev2 (PURC-TDD-008 to PURC-TDD-011).

Approved inputs: docs/specs/purchase-create.md (rev2), docs/specs/purchase-create-test-cases.md
(section 9a, PURC-004-TC14) and docs/specs/purchase-create-tdd-plan.md (第2版の追加).
Expected results come from the logical test cases only.

PURC-TDD-008/009 reproduce the edit/delete race deterministically through the HTTP API:
after a rename has been committed, the next read of the purchase inside the product
returns the pre-rename snapshot exactly once (fault injection), as if the competing
operation had read the purchase before the rename was committed.
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
PAIR_Z = ("アーモンドミルク", "食品")


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    with TestClient(app) as test_client:
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


def register(client: TestClient, pair: tuple[str, str]) -> Any:
    return client.post("/purchases", json=payload(pair))


def purchases(client: TestClient) -> list[dict[str, object]]:
    response = client.get("/purchases")
    assert response.status_code == 200
    return response.json()


def listed_pairs(client: TestClient) -> set[tuple[object, object]]:
    return {(item["name"], item["category"]) for item in purchases(client)}


def stored_item(purchase_id: str) -> dict[str, Any]:
    key = PurchaseItem.build_key(user_id=USER_ID, id=UUID(purchase_id))
    response = get_table().get_item(Key=key, ConsistentRead=True)
    return copy.deepcopy(response["Item"])


class StaleFirstReadTable:
    """Real table whose first ``get_item`` of one key returns a stale snapshot."""

    def __init__(self, real: Any, stale_item: dict[str, Any]) -> None:
        self._real = real
        self._stale_item = stale_item
        self._stale_key = {"PK": stale_item["PK"], "SK": stale_item["SK"]}
        self.stale_reads = 0

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        if self.stale_reads == 0 and kwargs.get("Key") == self._stale_key:
            self.stale_reads += 1
            return {"Item": copy.deepcopy(self._stale_item)}
        return self._real.get_item(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def inject_stale_read(monkeypatch: pytest.MonkeyPatch, stale_item: dict[str, Any]) -> None:
    proxy = StaleFirstReadTable(get_table(), stale_item)
    monkeypatch.setattr("app.models.purchase.get_table", lambda table_name=None: proxy)


def create_and_rename(client: TestClient) -> tuple[str, dict[str, Any]]:
    """Create purchase P with pair X, snapshot it, then rename P to pair Y."""
    created = register(client, PAIR_X)
    assert created.status_code == 201
    purchase_id = created.json()["id"]
    snapshot = stored_item(purchase_id)
    renamed = client.put(f"/purchases/{purchase_id}", json=payload(PAIR_Y))
    assert renamed.status_code == 200
    return purchase_id, snapshot


# --- PURC-TDD-008 / PURC-024-TC2: delete and rename race ---


def test_purc_tdd_008_purc_024_tc2_delete_racing_rename_leaves_unlisted_pairs_registrable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    purchase_id, snapshot = create_and_rename(client)

    inject_stale_read(monkeypatch, snapshot)
    deleted = client.delete(f"/purchases/{purchase_id}")
    monkeypatch.undo()

    assert deleted.status_code == 204
    unlisted = [pair for pair in (PAIR_X, PAIR_Y) if pair not in listed_pairs(client)]
    assert unlisted == [PAIR_X, PAIR_Y]
    results = {pair: register(client, pair).status_code for pair in unlisted}
    assert results == {PAIR_X: 201, PAIR_Y: 201}


# --- PURC-TDD-009 / PURC-024-TC1: rename and rename race ---


def test_purc_tdd_009_purc_024_tc1_rename_racing_rename_keeps_listed_pair_unique(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    purchase_id, snapshot = create_and_rename(client)

    inject_stale_read(monkeypatch, snapshot)
    renamed_again = client.put(f"/purchases/{purchase_id}", json=payload(PAIR_Z))
    monkeypatch.undo()

    assert renamed_again.status_code == 200
    listed = listed_pairs(client)
    assert listed == {PAIR_Z}
    results = {pair: register(client, pair).status_code for pair in (PAIR_Z, PAIR_X, PAIR_Y)}
    assert results == {PAIR_Z: 409, PAIR_X: 201, PAIR_Y: 201}


# --- PURC-TDD-010: representative regression (approved Red exception) ---


def test_purc_tdd_010_purc_022_tc1_deleted_pair_can_be_registered_again(
    client: TestClient,
) -> None:
    created = register(client, PAIR_X)
    assert created.status_code == 201
    assert client.delete(f"/purchases/{created.json()['id']}").status_code == 204

    assert register(client, PAIR_X).status_code == 201


def test_purc_tdd_010_purc_023_tc1_pre_rename_pair_can_be_registered(
    client: TestClient,
) -> None:
    created = register(client, PAIR_X)
    assert created.status_code == 201
    renamed = client.put(f"/purchases/{created.json()['id']}", json=payload(PAIR_Y))
    assert renamed.status_code == 200

    assert register(client, PAIR_X).status_code == 201


def test_purc_tdd_010_purc_023_tc2_rename_to_other_purchase_pair_is_409_and_not_persisted(
    client: TestClient,
) -> None:
    created_a = register(client, PAIR_X)
    created_b = register(client, PAIR_Y)
    assert created_a.status_code == 201
    assert created_b.status_code == 201
    a_before = created_a.json()

    edited = client.put(
        f"/purchases/{a_before['id']}",
        json=payload(PAIR_Y, speed=7, stock=9, is_temporary=True),
    )

    assert edited.status_code == 409
    listed_a = [item for item in purchases(client) if item["id"] == a_before["id"]]
    assert len(listed_a) == 1
    fields = ("name", "category", "speed", "stock", "is_temporary")
    assert {f: listed_a[0][f] for f in fields} == {f: a_before[f] for f in fields}


# --- PURC-TDD-011 / PURC-004-TC14: is_temporary must be a JSON boolean ---


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("true", id="string-true"),
        pytest.param(1, id="integer-1"),
    ],
)
def test_purc_tdd_011_purc_004_tc14_non_boolean_is_temporary_is_rejected_and_not_stored(
    client: TestClient, value: object
) -> None:
    response = client.post("/purchases", json=payload(PAIR_X, is_temporary=value))

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert "is_temporary" in {str(error["loc"][-1]) for error in detail}
    assert purchases(client) == []
