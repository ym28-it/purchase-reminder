"""永続化層（models）が送出する例外。

botocoreの ``ClientError`` やDynamoDB固有のエラーを上位層（services/api）に
そのまま漏らさないため、この層の言葉に翻訳した例外をここに定義する。
ドメイン例外（``app/domain/exception.py``）とは別系統で、
「DBに対する操作が失敗した」という永続化上の事実だけを表す。
"""


class PersistenceError(Exception):
    """永続化層で発生したエラーの基底クラス。"""


class InvalidKeyError(PersistenceError, ValueError):
    """キーの組み立て・分解に失敗した（値の不足や区切り文字の混入など）。"""


class ItemNotFoundError(PersistenceError):
    """指定されたキーのアイテムが存在しない。"""


class ItemAlreadyExistsError(PersistenceError):
    """すでに同じキーのアイテムが存在するため作成できない。"""


class ConditionalCheckFailedError(PersistenceError):
    """条件付き書き込みの条件が満たされなかった（競合更新など）。"""
