"""PythonオブジェクトとDynamoDBアイテムの間の型変換。

DynamoDBには浮動小数点数の型がなく、数値はすべて ``Decimal`` で受け渡しする
必要がある（boto3のresource APIは``float``を渡すと例外を送出し、読み出しでは
すべての数値を``Decimal``で返す）。この差分をモデルごとに手当てしていると
漏れるので、変換をここに集約する。

書き込み側はPydanticのJSON表現を経由することで、``datetime``/``UUID``/``Enum``
やネストしたモデルもまとめて素の型に落とす。
"""

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


def to_dynamodb(value: Any) -> Any:
    """Python値をDynamoDBに書き込める形へ変換する（``float``→``Decimal``）。

    モデルを経由しない値（更新式に渡す値など）のための入口。モデル全体の
    変換には``dump_model``を使う。

    ``Decimal(str(value))``としているのは、``Decimal(0.1)``のように
    浮動小数点の誤差をそのまま持ち込まないため。
    """
    if isinstance(value, bool):  # boolはintのサブクラスなので先に判定する
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, Mapping):
        return {key: to_dynamodb(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [to_dynamodb(item) for item in value]
    return value


def from_dynamodb(value: Any) -> Any:
    """DynamoDBから読み出した値をPythonの素の型へ戻す（``Decimal``→``int``/``float``）。

    整数として表せる``Decimal``は``int``にする。``Decimal``のままPydanticに
    渡しても多くの場合は検証を通るが、モデルを経由しない値も同じ扱いに
    揃えておきたいのでここで復元する。
    """
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, Mapping):
        return {key: from_dynamodb(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [from_dynamodb(item) for item in value]
    if isinstance(value, set):
        return {from_dynamodb(item) for item in value}
    return value


def dump_model(model: BaseModel, *, exclude_none: bool = True) -> dict[str, Any]:
    """Pydanticモデルを、そのままDynamoDBに書き込める辞書へ変換する。

    ``model_dump(mode="json")``ではなく``model_dump_json()``を経由するのは、
    ``json.loads(..., parse_float=Decimal)``によってネストした構造の中の
    浮動小数点数まで一括で``Decimal``にできるため。

    ``exclude_none=True``（既定）では値が``None``のフィールドは属性ごと
    書き込まない。これによりGSIのキーが欠けたアイテムはインデックスに
    載らない（sparse index）。読み出し時はモデル側の既定値``None``に戻る。
    """
    return json.loads(model.model_dump_json(exclude_none=exclude_none), parse_float=Decimal)


def load_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """DynamoDBアイテムを、Pydanticモデルに渡せる辞書へ変換する。"""
    return {key: from_dynamodb(value) for key, value in item.items()}
