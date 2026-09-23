# Work Environment Gate 実行証跡

## 判定

`ENVIRONMENT_READY`

PR #16をマージした最新`main`だけを根拠として、クリーンなWork環境からテスト環境を再現し、
Environment Gateを2回連続で通過した。購入物登録の機能テスト、プロダクトコード、E2E、
integration・E2E用のGitHub Actions workflow、AWS stagingには着手していない。既存の
`.github/workflows/test.yml`では、PR #16でunit testをintegration testから分離済みである。
機能TDDの開始には人間による明示的な承認が必要である。

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23 |
| Environment Gate検証済みSHA | `2983f363565f09cf364dfd0d6ae20c7846c3cc01` |
| PR #16マージコミット | `2983f363565f09cf364dfd0d6ae20c7846c3cc01` |
| ブランチ | `main` |
| OS | Ubuntu 24.04.3 LTS |
| アーキテクチャ | `x86_64` |
| Java | OpenJDK 17.0.20 |
| DynamoDB Local | 3.3.1 |
| 配布物SHA-256 | `f80bcec477f85f57e2c77f8d54aa6b672a8403fceff0c450560aee1cf6c21163` |

## 実行コマンド

`backend/`で次のコマンドを2回連続で実行した。

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not integration"
uv run python -m scripts.run_with_dynamodb_local \
  -- uv run pytest -m integration
```

各回の後に、ランナーなしのfail-closedと子コマンド終了コード保持を確認した。

```bash
uv run pytest -m integration
uv run python -m scripts.run_with_dynamodb_local \
  -- python -c 'raise SystemExit(23)'
```

## Environment Gate（連続2回）

| 検証 | 1回目 | 2回目 |
|---|---:|---:|
| Ruff lint | Pass | Pass |
| Ruff format | Pass（42 files） | Pass（42 files） |
| 既存Backend unit | 53 passed | 53 passed |
| 環境スモーク / fail-closed / OS失敗 | 14 passed | 14 passed |
| API ready check | Pass | Pass |
| 子コマンド終了コード | 0 | 0 |
| DynamoDB Local停止 | Pass | Pass |
| 8001番ポート解放 | Pass | Pass |
| 永続DBファイル | なし | なし |
| セッションID | `5eb403ca45784f41a3b0e26cfba75ea9` | `f3b52c7af8974d349add0ff1b2a7deaf` |

異なるセッションIDとテーブル名が生成された。DynamoDB Localは`-inMemory`で起動し、
各テスト前にテスト専用テーブルを削除・再作成している。1回目のプロセス停止後に
8001番ポートと永続DBファイルが残らないことを確認してから2回目を開始したため、
1回目のテーブルおよびセッションデータは2回目へ継承されていない。

## 負系Gate

| 検証 | 1回目 | 2回目 |
|---|---|---|
| ランナーなし | `ENVIRONMENT_FAILURE`、exit 70 | `ENVIRONMENT_FAILURE`、exit 70 |
| endpoint未設定 | SDK呼び出し前にFail | SDK呼び出し前にFail |
| 非loopback endpoint | SDK呼び出し前にFail | SDK呼び出し前にFail |
| endpointとportの不一致 | SDK呼び出し前にFail | SDK呼び出し前にFail |
| 非dummy credential | SDK呼び出し前にFail | SDK呼び出し前にFail |
| AWS profile / session token | SDK呼び出し前にFail | SDK呼び出し前にFail |
| checksum不一致 | JAR実行前にFail | JAR実行前にFail |
| Javaプロセス起動の`OSError` | `ENVIRONMENT_FAILURE`、exit 70 | `ENVIRONMENT_FAILURE`、exit 70 |
| 子コマンド失敗 | exit 23を保持 | exit 23を保持 |
| 子コマンド失敗時のセッションID | `f72b721954864d8b9b4feb93b51fed9b` | `f9c24a9d1536489c9930f0e06f629d29` |
| 子コマンド失敗後のPID cleanup | Pass | Pass |
| 子コマンド失敗後の8001番ポート解放 | Pass | Pass |

ログ作成・checksum読み取りを含むOSレベルの失敗は、ランナーの共通例外境界と自動テストで
`ENVIRONMENT_FAILURE`、exit 70へ変換される。ランナーなしと子コマンド失敗の負系Gateは
両方とも2回実行した。

## PR #16証跡との差異

| 項目 | PR #16上の証跡 | 最新`main`再検証 |
|---|---|---|
| 基準 | `b911bf2233051f8ddc48ef79c7e4a70a883dd00a` + PRブランチ | `2983f363565f09cf364dfd0d6ae20c7846c3cc01` |
| ブランチ | `test/dynamodb-local-environment` | `main` |
| Unit | 53 passed × 2 | 53 passed × 2 |
| Environment | 14 passed × 2 | 14 passed × 2 |
| Java | OpenJDK 17.0.20 | OpenJDK 17.0.20 |
| DynamoDB Local / SHA-256 | 3.3.1 / 一致 | 3.3.1 / 一致 |
| Cleanup | Pass × 2 | Pass × 2 |

テスト件数、固定バージョン、checksum、安全性、cleanup結果に差異はない。差異は、
PRブランチ上の証跡からPR #16マージ後の最新`main`上の証跡へ基準が更新されたことと、
実行ごとに一意であるセッションIDだけである。

## 検証済み環境コード基準とTDD作業開始SHA

`2983f363565f09cf364dfd0d6ae20c7846c3cc01`は、Environment Gateを実際に通過した
**検証済み環境コードSHA**として固定する。これは移動する「最新main」のSHAではない。
PR #17は文書だけを変更するため、そのマージによってこの環境検証結果は無効にならず、
Environment Gateを再実行する必要もない。

購入物登録TDDを開始するAgentは、PR #17マージ後の最新`main`からブランチを作成し、
実際の分岐元を**TDD作業開始SHA**としてTDD実行記録へ別途記録する。
`docs/specs/purchase-create-tdd-plan.md`のGAP-002は解消済みである。残る開始条件は、
Environment Gateの人間承認と、人間による明示的な「TDD開始」指示である。
