from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from main import app


@pytest.fixture
def client(user_id: str) -> Iterator[TestClient]:
    """``user_id``フィクスチャの値を認証済みユーザーとして扱うTestClient。

    本物の認証実装前のため、``get_current_user_id``の依存関係を差し替えて
    テストごとに独立したユーザーとしてAPIを叩けるようにする。
    """
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
