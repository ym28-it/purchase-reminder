"""ローカル開発用: DynamoDB Localにメインテーブルがなければ作る。

本番のテーブルはTerraformで管理するため、この処理はdocker-composeのdev環境
（``Dockerfile``の``dev``ステージ）からのみ呼ぶ。詳細は``app/models/table.py``。
"""

from app.core.config import get_settings
from app.core.dynamodb import get_dynamodb_resource
from app.models.table import create_table_if_not_exists


def main() -> None:
    settings = get_settings()
    create_table_if_not_exists(get_dynamodb_resource(), settings.dynamodb_table_name)


if __name__ == "__main__":
    main()
