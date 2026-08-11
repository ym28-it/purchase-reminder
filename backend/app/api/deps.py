"""FastAPIのDependsで使う横断的な依存関係。"""

#: 認証（Cognito）実装前の仮のユーザーID。
_DUMMY_USER_ID = "dev-user"


def get_current_user_id() -> str:
    """リクエストのユーザーIDを解決する。

    ``app/auth/``でのCognito JWT検証実装後、そちらを使う形に置き換える前提の仮実装。
    """
    return _DUMMY_USER_ID
