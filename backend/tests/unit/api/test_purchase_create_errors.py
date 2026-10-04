"""PURC-017-TC2 (API side): server failures must not expose internal details."""

from collections.abc import Iterator

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from main import app

SECRET = "arn:aws:dynamodb:ap-northeast-1:123456789012:table/secret-internal-table"


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_current_user_id] = lambda: "user-a"
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _raise_internal_error(*_args: object, **_kwargs: object) -> None:
    raise ClientError(
        {
            "Error": {"Code": "InternalServerError", "Message": f"boom at {SECRET}"},
            "CancellationReasons": [{"Code": "None"}],
        },
        "TransactWriteItems",
    )


def test_persistence_failure_returns_500_without_internal_details(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PURC-017-TC2."""
    monkeypatch.setattr("app.services.purchase_service.create_purchase_item", _raise_internal_error)

    response = client.post(
        "/purchases",
        json={"name": "牛乳", "category": "食品", "speed": 1, "stock": 2, "is_temporary": False},
    )

    assert response.status_code == 500
    body = response.text
    for leaked in (SECRET, "secret-internal-table", "Traceback", "ClientError", "TransactWrite"):
        assert leaked not in body
