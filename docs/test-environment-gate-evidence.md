# テスト環境 Environment Gate 実行証跡

## 現在の状態

`ENVIRONMENT_REVALIDATION_REQUIRED`

PR #19でDynamoDB Localの取得経路をCloudFront配布アーカイブからMaven Centralへ変更し、
Maven Wrapper、POM、推移依存関係、proxy設定をテスト環境の一部へ追加した。これは環境コードの
変更であるため、以下の旧方式の証跡と人間承認を、現在のMaven方式のGate根拠へ流用しない。

Maven方式はWorkで連続2回のEnvironment Gateを通過したが、その後Claude Codeで古いuvが
Python 3.14.0rc2を選択し、GitHub経由の取得がネットワーク制約で失敗した。PR #23でツールチェーンを
mise管理へ移した後、mise自体が未導入のクリーン環境で停止したため、PR #24ではmise 2026.9.12を
固定した公式生成ラッパー`bin/mise`を追加する。ラッパーは`mise.jdx.dev`から配布物を取得して
埋め込みSHA-256を検証し、リポジトリ内の`.mise/`へ配置する。global mise、npm、GitHub Releasesを
bootstrap前提にしない。この環境コード変更後、WorkとClaude Codeの両方で同一コマンドを連続2回
実行し、新しい検証済みSHAを記録して人間の再承認を受ける。完了するまで機能TDDを開始しない。
mise管理のTemurin Javaがクラウド実行環境の追加CAを自動参照しないため、Maven実行時だけ一時
truststoreへ追加CAを取り込み、終了時に削除する。

## Maven方式のWork検証（uv・Python固定前の参考記録）

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23 |
| Work検証対象SHA | `0ad3e352362750218d5233bfd5798daffcfc8664` |
| 実行環境 | ChatGPT Work / Ubuntu 24.04.3 LTS / x86_64 |
| Python | 3.14.7 |
| Java | OpenJDK 17.0.20 |
| Maven Wrapper | 3.3.4 / `only-script` |
| Maven | 3.9.16 |
| Maven配布物SHA-256 | `5af3b743dd8b876b5c45da33b676251e5f1687712644abb4ee519ca56e1d89ce` |
| DynamoDB Local | `software.amazon.dynamodb:DynamoDBLocal:3.3.1` |
| Runtime POM SHA-256 | `75b35c4a96123215077d1e7bd97f567d96cbb5fbbfd0cb04e7bc3047a9faa2ec` |

`backend/`で次を実行した。

```bash
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not integration"
uv run python -m scripts.run_with_dynamodb_local \
  -- uv run pytest -m integration
```

| 検証 | 1回目 | 2回目 |
|---|---:|---:|
| Backend unit | 53 passed | 53 passed |
| Maven依存解決 | Pass（初回取得） | Pass（cache再利用） |
| 環境スモーク / fail-closed / Maven設定 | 15 passed | 15 passed |
| DynamoDB Local version | 3.3.1 | 3.3.1 |
| API ready check | Pass | Pass |
| DynamoDB Local停止 | Pass | Pass |
| セッションID | `2c7aaf35ec8d4f2c9ca26d6fc0c7c15c` | `2913fd0b77e74d1fbba38b38bda860fd` |

追加の負系確認:

| 検証 | 結果 |
|---|---|
| ランナーなしintegration | `ENVIRONMENT_FAILURE`、exit 70 |
| Maven Wrapper / Central失敗の自動テスト | `ENVIRONMENT_FAILURE`、exit 70 |
| 子コマンド失敗 | exit 23を保持 |
| 子コマンド失敗後のPID停止・8001番port解放 | Pass |
| POMの固定version読取 | DynamoDB Local 3.3.1 / dependency plugin 3.8.1 |

Workでは環境変数のHTTP proxyを一時Maven settingsへ変換し、Maven実行後に削除する経路を通過した。
proxy認証情報はリポジトリ、POM、marker、実行ログへ保存していない。

## 旧CloudFront方式の判定

`ENVIRONMENT_READY`

PR #16をマージした最新`main`だけを根拠として、クリーンなWork環境からテスト環境を再現し、
Environment Gateを2回連続で通過した。購入物登録の機能テスト、プロダクトコード、E2E、
integration・E2E用のGitHub Actions workflow、AWS stagingには着手していない。既存の
`.github/workflows/test.yml`では、PR #16でunit testをintegration testから分離済みである。
Environment Gateは人間に承認済みである。機能TDDは別の開始判断であり、人間による明示的な「TDD開始」指示までは開始しない。

| 項目 | 値 |
|---|---|
| 実行日 | 2026-09-23 |
| Environment Gate検証済みSHA | `2983f363565f09cf364dfd0d6ae20c7846c3cc01` |
| Environment Gate人間承認 | 承認済み（2026-09-23） |
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
PR #17は文書だけを変更したため、そのマージによってこの環境検証結果は無効にならず、
Environment Gateを再実行する必要もない。

購入物登録TDDを開始するAgentは、PR #17マージ後の最新`main`からブランチを作成し、
実際の分岐元を**TDD作業開始SHA**としてTDD実行記録へ別途記録する。
`docs/specs/purchase-create-tdd-plan.md`のGAP-002は旧CloudFront方式では解消済みだった。PR #19のマージ後は、Maven方式のWork・Claude Code再検証、新しい検証済みSHAの記録、人間によるEnvironment Gate再承認が必要である。その後も、機能TDDの開始には人間による明示的な「TDD開始」指示を別途必要とする。
