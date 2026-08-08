"""boto3のDynamoDBクライアントの初期化。

resource API（``Table``オブジェクト）を使う。低レベルのclient APIと違い、
属性値を``{"S": "..."}``のような型付き表現で書かなくてよいため、
アイテムを素の辞書として扱える（数値が``Decimal``になる点は
``app/models/serialization.py``で吸収している）。

接続先は環境変数で切り替わる。``DYNAMODB_ENDPOINT_URL``が設定されていれば
DynamoDB Local、なければ実際のAWSに接続する。
"""

from functools import cache
from typing import Any

import boto3

from app.core.config import get_settings


@cache
def get_dynamodb_resource() -> Any:
    """DynamoDBのresourceを返す（プロセス内で使い回す）。"""
    settings = get_settings()
    return boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.dynamodb_endpoint_url,
    )


@cache
def get_table(table_name: str | None = None) -> Any:
    """テーブルオブジェクトを返す。名前を省略すると設定のメインテーブル。"""
    name = table_name or get_settings().dynamodb_table_name
    return get_dynamodb_resource().Table(name)
