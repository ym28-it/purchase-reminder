# Work Environment Gate 実行証跡

## 判定

`ENVIRONMENT_READY`

購入物登録の機能テストおよびプロダクトコードには着手していない。機能TDDの開始には、
この環境整備PRのマージ後に人間による明示的な承認が必要である。

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23 |
| 基準 `main` | `b911bf2233051f8ddc48ef79c7e4a70a883dd00a` |
| 環境実装コミット | `49b0db8104950f7e1017ed4a5691ceef5a6e5b52` |
| レビュー対応コミット | `85f25f874ab4b0d560931c1ff75327f67680fb3a` |
| ブランチ | `test/dynamodb-local-environment` |
| Java | OpenJDK 17.0.20 |
| DynamoDB Local | 3.3.1 |
| 配布物SHA-256 | `f80bcec477f85f57e2c77f8d54aa6b672a8403fceff0c450560aee1cf6c21163` |

## Environment Gate（連続2回）

`backend/`で次のコマンドを2回連続で実行した。

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not integration"
uv run python -m scripts.run_with_dynamodb_local \
  -- uv run pytest -m integration
```

| 検証 | 1回目 | 2回目 |
|---|---:|---:|
| Ruff lint | Pass | Pass |
| Ruff format | Pass（42 files） | Pass（42 files） |
| 既存Backend unit | 53 passed | 53 passed |
| 環境スモーク / fail-closed / OS失敗 | 14 passed | 14 passed |
| API ready check | Pass | Pass |
| 子コマンド終了コード | 0 | 0 |
| DynamoDB Local停止 | Pass | Pass |
| セッションID | `f9bbd6e1163940cabfc939700a4fa2e6` | `329d65c1659e4b05bcb266fa9725d39c` |

異なるセッションIDとテーブル名が生成され、各テスト前のテーブル削除・再作成、空状態、
汎用的な1件のput/get、`DescribeTable`、設定キャッシュのクリアを確認した。両実行後に
DynamoDB Localプロセスと8001番ポートは残っていない。

## 負系Gate

| 検証 | 実行方法 | 結果 |
|---|---|---|
| ランナーなし | `uv run pytest -m integration` | SDK呼び出し前に`ENVIRONMENT_FAILURE`、exit 70 |
| endpoint未設定 | 環境スモーク内 | SDK呼び出しなしでFail |
| 非loopback endpoint | 環境スモーク内 | SDK呼び出しなしでFail |
| endpointとportの不一致 | 環境スモーク内 | SDK呼び出しなしでFail |
| 非dummy credential | 環境スモーク内 | SDK呼び出しなしでFail |
| AWS profile / session token | 環境スモーク内 | SDK呼び出しなしでFail |
| checksum不一致 | 環境スモーク内 | 展開・JAR実行前にFail |
| Javaプロセス起動の`OSError` | 環境スモーク内 | `ENVIRONMENT_FAILURE`、exit 70 |
| その他のOSレベル失敗 | ランナーの共通例外境界 | ログ作成・checksum読み取り等を`ENVIRONMENT_FAILURE`、exit 70として処理 |
| 8001番ポート使用中 | 一時HTTP serverを所有者として起動後にランナーを実行 | `ENVIRONMENT_FAILURE`、exit 70、既存プロセスを維持 |
| 子コマンド失敗 | `python -c 'raise SystemExit(23)'` | exit 23を保持し、起動したPIDだけを停止、port解放 |

ランナーなしと子コマンド失敗の負系Gateも2回連続で実行し、各回でexit 70 / exit 23、
PID cleanup、8001番port解放を確認した。

## 実装範囲と差分

- 固定バージョン・取得元・SHA-256のロックファイル
- Java確認、download、checksum、展開、version確認、API ready check、子プロセス実行、cleanupを行う共通ランナー
- Java起動、ログ作成、checksum読み取り等のOS例外をexit 70へ変換する共通境界
- loopback endpoint、テスト用table prefix、dummy credential、port、実AWS向け環境変数のfail-closed検査
- pytestの`integration` marker、セッション単位の接続、テスト単位の空テーブル再作成、冪等cleanup
- DynamoDB Localに依存しない既存unitを分離するActionsコマンド
- 環境スモークと安全性テストのみ。購入物機能テスト、プロダクトコード、E2E、AWS stagingは変更なし

`docs/todo/test-environment-rollout.md`はStep 1〜3を実装・技術検証済みとして更新した。
Environment Gateの人間承認、PR #16のマージ、最新`main`での再検証は未完了である。
承認済み計画からの逸脱はない。
