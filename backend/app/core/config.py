"""アプリケーション設定。

他の層が``os.environ``を直接触らずに済むよう、環境変数の読み取りをここに集約する。
値は起動時に一度だけ解決してキャッシュする（Lambda上ではコンテナが再利用される
ため、リクエストごとに読み直す意味がない）。

認証（Cognito）関連の設定は認証実装時にここへ追加する。
"""

import os
from dataclasses import dataclass
from functools import cache

DEFAULT_AWS_REGION = "ap-northeast-1"
DEFAULT_TABLE_NAME = "purchase-reminder"


@dataclass(frozen=True)
class Settings:
    """環境変数から解決した設定値。"""

    #: boto3クライアントのリージョン。
    aws_region: str
    #: メインテーブル（シングルテーブル設計）の名前。
    dynamodb_table_name: str
    #: DynamoDB Localを使うときの接続先。本番（実AWS）ではNone。
    dynamodb_endpoint_url: str | None


@cache
def get_settings() -> Settings:
    return Settings(
        aws_region=os.environ.get("AWS_DEFAULT_REGION") or DEFAULT_AWS_REGION,
        dynamodb_table_name=os.environ.get("DYNAMODB_TABLE_NAME") or DEFAULT_TABLE_NAME,
        dynamodb_endpoint_url=os.environ.get("DYNAMODB_ENDPOINT_URL") or None,
    )
