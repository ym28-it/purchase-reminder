"""DynamoDBの複合キーを組み立て・分解するための汎用部品。

シングルテーブル設計では ``USER#<user_id>`` のように、区切り文字で意味を繋いだ
文字列をパーティションキー／ソートキーに使う。この文字列操作を各モデルに
散らかさないよう、テンプレートとして宣言的に扱えるようにする。

    >>> template = KeyTemplate("PURCHASE#{purchase_id}")
    >>> template.build(purchase_id="0f8f...")
    'PURCHASE#0f8f...'
    >>> template.parse("PURCHASE#0f8f...")
    {'purchase_id': '0f8f...'}
    >>> template.prefix()
    'PURCHASE#'

ここにはドメイン固有のキー（``USER#``など具体的な接頭辞）は定義しない。
どんなキーを持つかは各モデル（``app/models/purchase.py``など）が宣言する。
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from string import Formatter
from typing import Any

from app.models.exceptions import InvalidKeyError

#: キー内で意味の区切りに使う文字。この文字は値そのものには含められない。
KEY_SEPARATOR = "#"

#: 既定のキー属性名（シングルテーブル設計のメインテーブル）。
DEFAULT_PARTITION_ATTRIBUTE = "PK"
DEFAULT_SORT_ATTRIBUTE = "SK"


@cache
def _parse_pattern(template: str) -> re.Pattern[str]:
    """テンプレートから、キー文字列を分解するための正規表現を作る。

    ``{name}`` を名前付きグループに、それ以外をリテラルとして扱う。
    値には区切り文字を含められないため、各グループは ``[^#]+`` にマッチさせる。
    """
    pattern = ""
    for literal, name, _format_spec, _conversion in Formatter().parse(template):
        pattern += re.escape(literal)
        if name:
            pattern += f"(?P<{name}>[^{re.escape(KEY_SEPARATOR)}]+)"
    return re.compile(f"^{pattern}$")


@dataclass(frozen=True)
class KeyTemplate:
    """キー文字列の書式。``"USER#{user_id}"`` のように ``{}`` で値を埋める。"""

    template: str

    @property
    def field_names(self) -> tuple[str, ...]:
        """テンプレートが必要とする値の名前。宣言順で返す。"""
        return tuple(name for _, name, _, _ in Formatter().parse(self.template) if name)

    def build(self, **values: Any) -> str:
        """値を埋めてキー文字列を作る。

        値が足りない場合や、値に区切り文字が含まれる場合は ``InvalidKeyError``。
        後者を弾いておかないと ``parse`` で正しく復元できないアイテムが生まれる。
        """
        resolved: dict[str, str] = {}
        for name in self.field_names:
            if name not in values or values[name] is None:
                raise InvalidKeyError(f"キー'{self.template}'の値'{name}'が指定されていません")
            text = str(values[name])
            if KEY_SEPARATOR in text:
                raise InvalidKeyError(
                    f"キーの値'{name}'に区切り文字'{KEY_SEPARATOR}'は使えません: {text!r}"
                )
            resolved[name] = text
        return self.template.format(**resolved)

    def prefix(self, **values: Any) -> str:
        """先頭から埋められるところまでを埋めた前方一致用の文字列を返す。

        ``begins_with`` を使ったクエリの検索条件に使う。値を渡さなければ
        最初のプレースホルダ直前まで（``"PURCHASE#"``）が返る。
        """
        result = ""
        for literal, name, _format_spec, _conversion in Formatter().parse(self.template):
            result += literal
            if not name:
                continue
            if name not in values or values[name] is None:
                break
            text = str(values[name])
            if KEY_SEPARATOR in text:
                raise InvalidKeyError(
                    f"キーの値'{name}'に区切り文字'{KEY_SEPARATOR}'は使えません: {text!r}"
                )
            result += text
        return result

    def parse(self, key: str) -> dict[str, str]:
        """キー文字列を元の値に分解する。書式に合わなければ ``InvalidKeyError``。"""
        matched = _parse_pattern(self.template).match(key)
        if matched is None:
            raise InvalidKeyError(f"キー{key!r}は書式'{self.template}'に一致しません")
        return matched.groupdict()


@dataclass(frozen=True)
class ItemKeySchema:
    """1つのキー（メインテーブルのキー、またはGSIのキー）の定義。

    「どの属性名に」「どんな書式の値を入れるか」の組み合わせを表す。
    メインテーブルとGSIを同じ型で扱えるようにしておくことで、
    アイテム側は「持っているキーを全部書き出す」だけで済む。
    """

    partition_key: KeyTemplate
    sort_key: KeyTemplate | None = None
    partition_attribute: str = DEFAULT_PARTITION_ATTRIBUTE
    sort_attribute: str = DEFAULT_SORT_ATTRIBUTE

    @property
    def attribute_names(self) -> tuple[str, ...]:
        if self.sort_key is None:
            return (self.partition_attribute,)
        return (self.partition_attribute, self.sort_attribute)

    @property
    def field_names(self) -> tuple[str, ...]:
        """このキーの組み立てに必要な値の名前（重複は除く）。"""
        names = dict.fromkeys(self.partition_key.field_names)
        if self.sort_key is not None:
            names.update(dict.fromkeys(self.sort_key.field_names))
        return tuple(names)

    def build(self, values: Mapping[str, Any]) -> dict[str, str]:
        """キー属性名をキーとした辞書を作る。``get_item``の``Key``にそのまま渡せる。"""
        key = {self.partition_attribute: self.partition_key.build(**values)}
        if self.sort_key is not None:
            key[self.sort_attribute] = self.sort_key.build(**values)
        return key

    def try_build(self, values: Mapping[str, Any]) -> dict[str, str]:
        """組み立てられなければ空辞書を返す``build``。

        値が ``None`` の場合にGSIのキー属性を書き込まないことで、
        「その属性を持つアイテムだけがインデックスに載る」sparse indexになる。
        """
        try:
            return self.build(values)
        except InvalidKeyError:
            return {}
