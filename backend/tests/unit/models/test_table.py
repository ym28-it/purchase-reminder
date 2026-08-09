"""テーブル定義（``app/models/table.py``）のテスト。"""

from app.models.table import (
    GSI1_NAME,
    MAIN_TABLE_SCHEMA,
    AttributeSchema,
    GlobalSecondaryIndexSchema,
    TableSchema,
)


class TestToCreateTableKwargs:
    def test_パーティションキーとソートキーがHASHとRANGEになる(self):
        kwargs = MAIN_TABLE_SCHEMA.to_create_table_kwargs("test-table")

        assert kwargs["TableName"] == "test-table"
        assert kwargs["KeySchema"] == [
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ]

    def test_キーに使う属性だけが定義される(self):
        """DynamoDBはキー以外の属性を事前に宣言しない（スキーマレス）。"""
        kwargs = MAIN_TABLE_SCHEMA.to_create_table_kwargs("test-table")

        names = [attribute["AttributeName"] for attribute in kwargs["AttributeDefinitions"]]
        assert names == ["PK", "SK", "GSI1PK", "GSI1SK"]

    def test_GSIが定義される(self):
        kwargs = MAIN_TABLE_SCHEMA.to_create_table_kwargs("test-table")

        index = kwargs["GlobalSecondaryIndexes"][0]
        assert index["IndexName"] == GSI1_NAME
        assert index["Projection"] == {"ProjectionType": "ALL"}

    def test_既定は従量課金(self):
        kwargs = MAIN_TABLE_SCHEMA.to_create_table_kwargs("test-table")

        assert kwargs["BillingMode"] == "PAY_PER_REQUEST"

    def test_GSIが無ければ引数に含めない(self):
        schema = TableSchema(partition_key=AttributeSchema("PK"))

        kwargs = schema.to_create_table_kwargs("test-table")

        assert "GlobalSecondaryIndexes" not in kwargs
        assert kwargs["KeySchema"] == [{"AttributeName": "PK", "KeyType": "HASH"}]

    def test_テーブルとGSIで同じ属性を使っても重複しない(self):
        schema = TableSchema(
            partition_key=AttributeSchema("PK"),
            sort_key=AttributeSchema("SK"),
            global_secondary_indexes=(
                GlobalSecondaryIndexSchema(
                    name="GSI1",
                    partition_key=AttributeSchema("SK"),
                    sort_key=AttributeSchema("PK"),
                ),
            ),
        )

        kwargs = schema.to_create_table_kwargs("test-table")

        names = [attribute["AttributeName"] for attribute in kwargs["AttributeDefinitions"]]
        assert names == ["PK", "SK"]
