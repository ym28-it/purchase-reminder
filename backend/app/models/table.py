"""DynamoDBのテーブル定義。

シングルテーブル設計を採り、全エンティティを1つのテーブルに同居させる:

===========  =========================  ==============================
用途         PK                         SK
===========  =========================  ==============================
purchase     ``USER#<user_id>``         ``PURCHASE#<purchase_id>``
===========  =========================  ==============================

ユーザー単位でパーティションを分けることで、「あるユーザーの購入物一覧」を
1回のQueryで取得できる。GSI1はそれ以外の軸（カテゴリ順、補充期限順など）で
引くための予備の索引として用意しておく。

本番のテーブルはTerraformで作成する。ここでの定義は、DynamoDB Localや
統合テストでテーブルを用意するため、およびキー構成をコード側の
single source of truthとして明示するためのもの。
"""

from dataclasses import dataclass, field
from typing import Any, Literal

AttributeType = Literal["S", "N", "B"]

#: GSI1のキー属性名。アイテム側の``ItemKeySchema``と対応させる。
GSI1_NAME = "GSI1"
GSI1_PARTITION_ATTRIBUTE = "GSI1PK"
GSI1_SORT_ATTRIBUTE = "GSI1SK"


@dataclass(frozen=True)
class AttributeSchema:
    """キーに使う属性の定義。DynamoDBはキー属性の型だけを事前に宣言する。"""

    name: str
    type: AttributeType = "S"


@dataclass(frozen=True)
class GlobalSecondaryIndexSchema:
    """GSIの定義。"""

    name: str
    partition_key: AttributeSchema
    sort_key: AttributeSchema | None = None
    projection_type: Literal["ALL", "KEYS_ONLY", "INCLUDE"] = "ALL"

    @property
    def attributes(self) -> tuple[AttributeSchema, ...]:
        if self.sort_key is None:
            return (self.partition_key,)
        return (self.partition_key, self.sort_key)


@dataclass(frozen=True)
class TableSchema:
    """テーブルのキー構成。``create_table``に渡す引数を組み立てられる。"""

    partition_key: AttributeSchema
    sort_key: AttributeSchema | None = None
    global_secondary_indexes: tuple[GlobalSecondaryIndexSchema, ...] = field(default=())

    @property
    def attributes(self) -> tuple[AttributeSchema, ...]:
        """キーに使う全属性（重複除去）。``AttributeDefinitions``に対応する。"""
        collected: dict[str, AttributeSchema] = {self.partition_key.name: self.partition_key}
        if self.sort_key is not None:
            collected.setdefault(self.sort_key.name, self.sort_key)
        for index in self.global_secondary_indexes:
            for attribute in index.attributes:
                collected.setdefault(attribute.name, attribute)
        return tuple(collected.values())

    def to_create_table_kwargs(
        self,
        table_name: str,
        *,
        billing_mode: Literal["PAY_PER_REQUEST", "PROVISIONED"] = "PAY_PER_REQUEST",
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "TableName": table_name,
            "BillingMode": billing_mode,
            "KeySchema": _key_schema(self.partition_key, self.sort_key),
            "AttributeDefinitions": [
                {"AttributeName": attribute.name, "AttributeType": attribute.type}
                for attribute in self.attributes
            ],
        }
        if self.global_secondary_indexes:
            kwargs["GlobalSecondaryIndexes"] = [
                {
                    "IndexName": index.name,
                    "KeySchema": _key_schema(index.partition_key, index.sort_key),
                    "Projection": {"ProjectionType": index.projection_type},
                }
                for index in self.global_secondary_indexes
            ]
        return kwargs


def _key_schema(
    partition_key: AttributeSchema, sort_key: AttributeSchema | None
) -> list[dict[str, str]]:
    schema = [{"AttributeName": partition_key.name, "KeyType": "HASH"}]
    if sort_key is not None:
        schema.append({"AttributeName": sort_key.name, "KeyType": "RANGE"})
    return schema


#: 全エンティティを収めるメインテーブルの構成。
MAIN_TABLE_SCHEMA = TableSchema(
    partition_key=AttributeSchema("PK"),
    sort_key=AttributeSchema("SK"),
    global_secondary_indexes=(
        GlobalSecondaryIndexSchema(
            name=GSI1_NAME,
            partition_key=AttributeSchema(GSI1_PARTITION_ATTRIBUTE),
            sort_key=AttributeSchema(GSI1_SORT_ATTRIBUTE),
        ),
    ),
)


def create_table_if_not_exists(
    dynamodb: Any,
    table_name: str,
    schema: TableSchema = MAIN_TABLE_SCHEMA,
) -> Any:
    """テーブルが無ければ作る。DynamoDB Localと統合テストのセットアップ用。

    本番のテーブルはTerraformで管理するため、この関数はアプリの起動経路からは
    呼ばない（ローカル開発・テストのブートストラップ専用）。
    """
    client = dynamodb.meta.client
    try:
        table = dynamodb.create_table(**schema.to_create_table_kwargs(table_name))
    except client.exceptions.ResourceInUseException:
        return dynamodb.Table(table_name)
    table.wait_until_exists()
    return table
