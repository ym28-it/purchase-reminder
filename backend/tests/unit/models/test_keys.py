"""キーの組み立て・分解（``app/models/keys.py``）のテスト。"""

import pytest

from app.models.exceptions import InvalidKeyError
from app.models.keys import ItemKeySchema, KeyTemplate


class TestKeyTemplate:
    def test_値を埋めてキー文字列を作る(self):
        template = KeyTemplate("USER#{user_id}")

        assert template.build(user_id="u1") == "USER#u1"

    def test_複数の値を埋められる(self):
        template = KeyTemplate("USER#{user_id}#CATEGORY#{category}")

        assert template.build(user_id="u1", category="food") == "USER#u1#CATEGORY#food"

    def test_値は文字列に変換される(self):
        template = KeyTemplate("PURCHASE#{purchase_id}")

        assert template.build(purchase_id=42) == "PURCHASE#42"

    def test_必要な値が無ければエラー(self):
        template = KeyTemplate("USER#{user_id}")

        with pytest.raises(InvalidKeyError):
            template.build()

    def test_値がNoneならエラー(self):
        template = KeyTemplate("USER#{user_id}")

        with pytest.raises(InvalidKeyError):
            template.build(user_id=None)

    def test_値に区切り文字が含まれていればエラー(self):
        """区切り文字の混入を許すと``parse``で復元できないアイテムが生まれる。"""
        template = KeyTemplate("USER#{user_id}")

        with pytest.raises(InvalidKeyError):
            template.build(user_id="u#1")

    def test_必要な値の名前を宣言順で返す(self):
        template = KeyTemplate("USER#{user_id}#CATEGORY#{category}")

        assert template.field_names == ("user_id", "category")

    def test_キー文字列を元の値に分解する(self):
        template = KeyTemplate("USER#{user_id}#CATEGORY#{category}")

        assert template.parse("USER#u1#CATEGORY#food") == {"user_id": "u1", "category": "food"}

    def test_書式に一致しないキーはエラー(self):
        template = KeyTemplate("USER#{user_id}")

        with pytest.raises(InvalidKeyError):
            template.parse("PURCHASE#p1")

    def test_組み立てた結果は分解して元に戻る(self):
        template = KeyTemplate("USER#{user_id}#PURCHASE#{purchase_id}")

        key = template.build(user_id="u1", purchase_id="p1")

        assert template.parse(key) == {"user_id": "u1", "purchase_id": "p1"}

    def test_値を渡さない前方一致は最初の埋め込み直前まで(self):
        template = KeyTemplate("PURCHASE#{purchase_id}")

        assert template.prefix() == "PURCHASE#"

    def test_前方一致は埋められる値まで埋める(self):
        template = KeyTemplate("USER#{user_id}#CATEGORY#{category}")

        assert template.prefix(user_id="u1") == "USER#u1#CATEGORY#"


class TestItemKeySchema:
    def test_キー属性名をキーとした辞書を作る(self):
        schema = ItemKeySchema(
            partition_key=KeyTemplate("USER#{user_id}"),
            sort_key=KeyTemplate("PURCHASE#{purchase_id}"),
        )

        key = schema.build({"user_id": "u1", "purchase_id": "p1"})

        assert key == {"PK": "USER#u1", "SK": "PURCHASE#p1"}

    def test_ソートキーが無ければパーティションキーだけ(self):
        schema = ItemKeySchema(partition_key=KeyTemplate("USER#{user_id}"))

        assert schema.build({"user_id": "u1"}) == {"PK": "USER#u1"}
        assert schema.attribute_names == ("PK",)

    def test_属性名を差し替えてGSIのキーにできる(self):
        schema = ItemKeySchema(
            partition_key=KeyTemplate("USER#{user_id}"),
            sort_key=KeyTemplate("CATEGORY#{category}"),
            partition_attribute="GSI1PK",
            sort_attribute="GSI1SK",
        )

        key = schema.build({"user_id": "u1", "category": "food"})

        assert key == {"GSI1PK": "USER#u1", "GSI1SK": "CATEGORY#food"}

    def test_必要な値の名前は重複を除いて返す(self):
        schema = ItemKeySchema(
            partition_key=KeyTemplate("USER#{user_id}"),
            sort_key=KeyTemplate("USER#{user_id}#PURCHASE#{purchase_id}"),
        )

        assert schema.field_names == ("user_id", "purchase_id")

    def test_値が欠けているとtry_buildは空辞書を返す(self):
        """sparse index：キーを組み立てられないアイテムはインデックスに載せない。"""
        schema = ItemKeySchema(
            partition_key=KeyTemplate("USER#{user_id}"),
            sort_key=KeyTemplate("CATEGORY#{category}"),
            partition_attribute="GSI1PK",
            sort_attribute="GSI1SK",
        )

        assert schema.try_build({"user_id": "u1", "category": None}) == {}
