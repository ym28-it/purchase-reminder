"""DynamoDB Localを使った統合テストの共通フィクスチャ。

``docker-compose up``で立ち上がるDynamoDB Local（localhost:8001）に接続する。
開発中のテーブル（``purchase-reminder``）とは別名のテーブルを使い、テスト実行が
開発データに影響しないようにする。
"""

import os
import uuid

import pytest

os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://localhost:8001")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "purchase-reminder-test")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "dummy")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "dummy")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")

from app.core.config import get_settings  # noqa: E402
from app.core.dynamodb import get_dynamodb_resource  # noqa: E402
from app.models.table import create_table_if_not_exists  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _ensure_table() -> None:
    settings = get_settings()
    create_table_if_not_exists(get_dynamodb_resource(), settings.dynamodb_table_name)


@pytest.fixture
def user_id() -> str:
    """テストごとに独立したパーティションを持つユーザーID。

    テスト間でDynamoDB Local上のデータが衝突しないよう、テストのたびに
    新しいuser_idを払い出す（明示的なクリーンアップは行わない。
    ``-inMemory``のDynamoDB Localなのでコンテナ再起動で消える想定）。
    """
    return f"test-user-{uuid.uuid4()}"
