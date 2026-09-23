# テスト実行環境構築計画（Work / Pull Request / main）

## 1. 文書の目的

この文書は、DynamoDBを本番の永続化方式として維持しながら、AIのリモート実行環境であるChatGPT Work、GitHub Actions、AWS stagingの各段階にテスト環境を構築する手順とゲートを定義する。

最初の目的は、承認済みの購入物登録TDDテストを作成する前に、Work上でDynamoDB Localを安全かつ再現可能に起動し、環境障害とValid Redを区別できる状態にすることである。

この文書はテスト環境の契約と実装順序を定める。個別機能の期待動作は定義せず、機能仕様、論理テストケース、TDD計画をsource of truthとする。

| 項目 | 値 |
|---|---|
| 更新日 | 2026-09-23 |
| Environment Gate検証済みSHA | `2983f363565f09cf364dfd0d6ae20c7846c3cc01` |
| 環境整備PR | PR #16（マージ済み） |
| 対象 | ChatGPT Work、Pull Request Actions、`main`マージ後のAWS staging |
| 採用DB | DynamoDB Local / AWS DynamoDB |
| 状態 | Step 1〜3実装・最新`main`再検証済み / Environment Gate人間承認待ち |

## 2. 基本方針

SQLiteやPostgreSQLで代替せず、WorkとPRではAWS公式のDynamoDB Localを使用する。

| 実行場所 | DB | 起動方法 | 主な検証 |
|---|---|---|---|
| ChatGPT Work | DynamoDB Local | Java 17以上でJARを直接起動 | TDD、models/API integration、実装中検証 |
| Pull Request | DynamoDB Local | Workと同じJAR実行ラッパー | unit、component、integration、主要E2E |
| `main`マージ後 | AWS staging DynamoDB | Terraformで管理 | IAM、デプロイ、smoke、AWS固有挙動、重要E2E |
| production | AWS DynamoDB | Terraformで管理 | デプロイ前後の最小確認 |

原則:

- PRから実AWSへ接続しない。
- WorkとPRはdummy credentialだけを使用する。
- TDDのRedは、環境起動やfixtureの失敗ではなく、承認済み契約の不成立を理由にする。
- Workで検証した起動・初期化処理をGitHub Actionsでも再利用し、二重実装を避ける。
- 自動テストはin-memoryモードを標準とする。
- E2Eを含む実装後テストはTDD Green後に追加する。
- AWS stagingはWork・PRのテスト基盤が安定してから構築する。
- productionへのデプロイはstagingと別の承認ゲートを持つ。

## 3. 現在地

### 3.1 アプリケーション

| 領域 | 現状 |
|---|---|
| Backend | FastAPI、boto3、Python 3.14、uv |
| Frontend | React、TypeScript、Vite、bun |
| 永続化 | PK/SKとGSIを使うDynamoDBシングルテーブル |
| 接続切替 | `DYNAMODB_ENDPOINT_URL`の有無 |
| テーブル作成 | `backend/scripts/bootstrap_local_table.py` |
| ローカル開発 | Docker Compose上のDynamoDB Local |
| Work | Dockerなし、OpenJDK 17あり |

### 3.2 Baseline

- Backend tests: 53 passed
- Backend lint / format: Pass
- Frontend lint / format: Pass
- Frontend tests: 既存テスト0件
- Frontend build: `src/routeTree.gen`不足による既存失敗
- Backend integration: 環境スモーク・fail-closedテスト14件
- E2E: READMEのみ
- WorkからAWS公式のDynamoDB Local配布URLとchecksum URLへ到達可能

### 3.3 承認済みTDD計画との関係

購入物登録の最小TDDセットには、APIからDynamoDBまでを接続する統合テストと同時重複登録テストが含まれる。

したがって、DynamoDB Local実行基盤はTDDテスト作成後ではなく、その前にEnvironment Gateを通過させる。

## 4. Work環境仕様

### 4.1 DynamoDB Local

- DynamoDB Local `3.3.1`を使用する。
- 公式配布URLは`https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.tar.gz`とする。
- 配布アーカイブの期待SHA-256は`f80bcec477f85f57e2c77f8d54aa6b672a8403fceff0c450560aee1cf6c21163`とする。
- 実行前にアーカイブのSHA-256とJARの`-version`出力（`3.3.1`）を検証する。
- `latest` URL側のchecksumを実行時の信頼元にせず、レビュー済みの期待SHA-256と照合する。
- バージョン更新はロックファイルを変更する専用PRで行う。
- JAR、native library、DBファイル、PID、ログはGit管理しない。

ロックファイル:

```text
backend/dynamodb-local.lock.json
```

キャッシュ:

```text
.cache/dynamodb-local/3.3.1/
```

### 4.2 起動モード

自動テスト:

```bash
java \
  -Djava.library.path=<cache>/DynamoDBLocal_lib \
  -jar <cache>/DynamoDBLocal.jar \
  -inMemory \
  -sharedDb \
  -port <port> \
  -disableTelemetry
```

自動テストでは、ラッパーがpytestセッションの開始前にDynamoDB Localを1回だけ起動し、子コマンド終了後に停止する。pytest fixtureはプロセスを起動・停止せず、ラッパーが用意した接続先を使用する。ラッパーを介さずintegration testを実行した場合は`ENVIRONMENT_FAILURE`として停止する。

手動デバッグで状態保持が必要な場合だけ、`-inMemory`を外して専用の`-dbPath`を指定する。

### 4.3 ポート

- 既定値は現在のDocker Composeと合わせて`8001`とする。
- `DYNAMODB_LOCAL_PORT`で上書き可能にする。
- 起動前に使用中か検査し、既存プロセスを無条件に終了しない。
- ラッパーが起動したPIDだけを記録し、終了時にそのPIDだけを停止する。

### 4.4 接続設定

```text
DYNAMODB_ENDPOINT_URL=http://127.0.0.1:<port>
DYNAMODB_TABLE_NAME=purchase-reminder-test-<session-id>
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
AWS_DEFAULT_REGION=ap-northeast-1
AWS_EC2_METADATA_DISABLED=true
```

`AWS_PROFILE`、`AWS_SESSION_TOKEN`などの実AWS向け設定をテストプロセスへ引き継がない。

## 5. 安全性契約

### 5.1 Fail closed

テーブル作成、削除、テスト実行より前に、次を機械的に検査する。

- `DYNAMODB_ENDPOINT_URL`が設定されている
- schemeが`http`である
- hostが`127.0.0.1`または`localhost`である
- portが期待値と一致する
- table名がテスト専用prefixを持つ
- credentialがdummy値である
- 実AWS profileやsession tokenが渡されていない

1つでも満たさない場合はSDK呼び出し前に停止する。endpoint未設定時にAWS SDKの既定接続先へフォールバックしてはならない。

### 5.2 設定キャッシュ

現在のBackendは次を`@cache`している。

- `get_settings()`
- `get_dynamodb_resource()`
- `get_table()`

fixtureは環境変数設定後かつ最初のDynamoDBアクセス前に、これらのキャッシュを明示的にクリアする。teardownでも再度クリアし、別テストや別endpointへ状態を漏らさない。

### 5.3 テストセッションとデータ分離

- DynamoDB Localプロセスはpytestセッション単位で1回起動する。
- テーブル名は`purchase-reminder-test-<session-id>`とし、セッションごとに一意、同一セッション内では固定とする。
- 各テストの開始前にテスト専用テーブルを削除し、既存の`MAIN_TABLE_SCHEMA`から再作成する。
- 再作成したテーブルは空の状態とし、共通の初期データを投入しない。
- 各テストが必要なデータをArrange段階で作成する。
- 初期実装では並列実行を対象外とする。
- 作成、削除、`DescribeTable`の失敗は機能テスト失敗ではなく`ENVIRONMENT_FAILURE`として扱う。

### 5.4 Ready check

portが開いていることだけをready判定にしない。

1. DynamoDB Localプロセスが生存している
2. dummy credentialとlocal endpointで`ListTables`が成功する
3. テストテーブルを作成できる
4. `DescribeTable`で対象テーブルを確認できる

上記をtimeout付きで確認する。失敗時はJavaプロセスの標準出力・標準エラーと判定理由を残す。

## 6. TDD開始前の構築ステップ

### Step 0: 文書と基準コミットを固定する

- [x] PR #14のTDD計画をマージする
- [x] PR #15を最新の`main`へ追従させる
- [x] DynamoDB LocalをWork・PRの共通DBとする方針を人間が承認する
- [x] DynamoDB Local 3.3.1とSHA-256を固定する
- [x] port、キャッシュ場所、テスト用table prefixを固定する
- [x] pytestセッション、テーブル再作成、空の初期状態を固定する
- [x] Environment Gateの判定項目を承認する

完了条件: 環境仕様と基準コミットが固定されている。

### Step 1: Work用ランタイムラッパーを実装する（実装・検証済み）

成果物:

```text
backend/dynamodb-local.lock.json
backend/scripts/run_with_dynamodb_local.py
.gitignore
```

ラッパーは次を1コマンドで行う。すべて実装済みである。

1. [x] Java 17以上を確認
2. [x] ロックファイルを読む
3. [x] キャッシュ済み配布物のchecksumを確認
4. [x] 未取得なら公式配布元からダウンロード
5. [x] 期待SHA-256を照合
6. [x] 安全なキャッシュ先へ展開
7. [x] 未使用portを確認
8. [x] in-memoryモードで起動
9. [x] APIレベルのready check
10. [x] 子コマンドをサニタイズした環境変数で実行
11. [x] 終了コードを保持
12. [x] 自分が起動したDynamoDB Localだけを停止
13. [x] ログと終了理由を出力

想定コマンド:

```bash
cd backend
uv run python -m scripts.run_with_dynamodb_local \
  -- uv run pytest -m integration
```

ダウンロード、checksum、Java、起動、ready checkの失敗は`ENVIRONMENT_FAILURE`として扱い、Valid Redへ数えない。

完了条件: **達成済み。** 空のWork環境から単一コマンドでDynamoDB Localを起動・停止できる。

### Step 2: pytest統合テスト基盤を実装する（実装・検証済み）

成果物:

```text
backend/tests/integration/conftest.py
backend/tests/integration/test_environment.py
backend/pyproject.toml
```

- [x] `integration` markerを登録する
- [x] DB不要のテストとDB統合テストを別コマンドで実行できるようにする
- [x] DynamoDB Localプロセスはセッション開始前にラッパーが1回だけ起動する
- [x] セッションごとに一意なテーブル名を作り、同一セッション内では固定する
- [x] 各テスト前にテスト専用テーブルを削除・再作成し、空の状態から開始する
- [x] テストデータは各テストのArrange段階で作成する
- [x] 安全性契約をSDK呼び出し前に検査する
- [x] 設定・resource・tableのキャッシュを開始前後にクリアする
- [x] 既存のテーブルschema生成処理を再利用する
- [x] テーブル作成後に`DescribeTable`で確認する
- [x] 各テストを他テストのデータと分離する
- [x] teardownを冪等にする
- [x] 実AWS endpointでは必ず失敗する安全性テストを追加する

`test_environment.py`は環境だけを検証し、購入物登録などの未実装契約を先回りしてテストしない。

環境スモークで確認する範囲:

- DynamoDB Localへの接続
- テストテーブルの作成・参照・削除
- 1件の汎用的なput/get
- fixture終了後のキャッシュとテストデータの分離

完了条件: **達成済み。** 環境スモークが成功し、機能テストを追加していない状態を維持している。

### Step 3: Work Environment Gateを検証する（技術検証済み / 人間承認待ち）

最低限、次を記録する。

| 検証 | 期待結果 |
|---|---|
| Java version | 17以上 |
| 配布物checksum | ロックファイルと一致 |
| DynamoDB Local version | 3.3.1 |
| API ready check | Pass |
| テーブル作成・DescribeTable | Pass |
| 環境スモーク | Pass |
| 既存Backend unit | 53件以上、既存分がPass |
| 連続2回実行 | 前回データ・プロセス・portを引き継がずPass |
| endpoint未設定 | SDK呼び出し前にFail |
| 非loopback endpoint | SDK呼び出し前にFail |
| checksum不一致 | JAR実行前にFail |
| Javaプロセス起動失敗 | `ENVIRONMENT_FAILURE`、exit 70 |
| ログ作成・checksum読み取り等のOS失敗 | `ENVIRONMENT_FAILURE`、exit 70 |
| 子コマンド失敗 | 終了コードを保持し、DynamoDB Localを停止 |

Environment Gate:

- [x] 取得元、バージョン、SHA-256が固定されている
- [x] 単一コマンドで起動、ready check、子コマンド、停止が行われる
- [x] 実AWSへ接続しないfail-closed検査がある
- [x] 設定キャッシュがテスト間で分離される
- [x] 環境スモークが連続して成功する
- [x] 既存unit testが回帰していない
- [x] 環境・安全性・OSレベルの失敗を`ENVIRONMENT_FAILURE`として判別できる
- [ ] 人間がTDDテスト作成開始を承認した

技術判定は`ENVIRONMENT_READY`である。完了条件のうち人間承認だけが未完了であり、
承認されるまで機能TDDを開始しない。

### Step 4: TDD計画へ環境証跡を反映する

- [x] 環境整備専用コミットSHAを記録する
- [x] 実行コマンドと結果を記録する
- [x] PR #14で記録したGAP-002の解消状況を更新する
- [x] 環境整備とTDDテストのコミットを分離する（機能TDDテストは未作成）
- [x] 環境整備PRをマージする
- [x] 最新`main`でBaselineを再実行する
- [x] Environment Gate検証済みSHAを固定する

Environment Gate検証済みSHAは、環境コードまたはテスト基盤を変更した場合に再検証して更新する。
文書だけの変更では更新しない。TDDを開始するAgentは、その時点の最新`main`からブランチを作成し、
実際の分岐元をTDD作業開始SHAとしてTDD実行記録へ記録する。

ここまで完了するまで、承認済みの購入物登録TDDテストコードを作成しない。

## 7. TDD開始後

Environment Gate通過後、人間の「TDD開始」を起点として3エージェント運用を開始する。

1. 新しいテストエージェントが承認済み7項目をテストコードへ変換する
2. 環境スモークを先に実行する
3. 環境スモークがGreenであることを確認する
4. TDD対象テストを実行する
5. Redと承認済みRed例外を記録する
6. オーケストレーターがAutomated Red Gateを判定する
7. 実装エージェントが凍結済みテストを変更せず実装する

環境スモークが失敗した場合は`ENVIRONMENT_FAILURE`で停止する。機能テストの失敗と混在させない。

## 8. Pull Request Actionsへの展開

WorkでEnvironment Gateを通過した後、同じラッパーをActionsへ移植する。

### 8.1 Workflow

| Workflow | 内容 |
|---|---|
| `lint.yml` | Backend/Frontend lint・format |
| `test.yml` | Backend unit、Frontend component |
| `integration.yml` | DynamoDB Local環境スモーク、API/models integration |
| `e2e.yml` | DynamoDB Local、FastAPI、Vite、Playwright |

- unitとintegrationを別checkとして表示する。
- 最初のFrontendテスト追加後に`--passWithNoTests`を削除する。
- integrationはAWS credentialを持たない。
- 失敗時にDynamoDB Local・APIログをartifactとして残す。
- 必須checkをbranch protectionへ登録する。
- Actions固有の起動処理を増やさず、Workと同じラッパーを呼ぶ。

### 8.2 E2E

E2EはTDD Green後の実装後テストとして追加する。

- Playwright、FastAPI、Vite、DynamoDB Localを接続する
- 最初は購入物登録の代表正常系1件に限定する
- API統合テストの境界値を重複させない
- 認証未実装中はテスト用の認証境界を明示する
- trace、screenshot、server logをartifact化する

## 9. AWS stagingへの展開

AWS stagingは既存CRUD、Work統合基盤、PR CI、主要E2Eが安定してから別計画として実施する。

- Terraformでstaging専用DynamoDB、IAM、Lambda/API Gateway等を管理する
- GitHub Actions OIDCによる短期credentialだけを使用する
- productionとtable、IAM role、SSM Parameter、Cognitoを分離する
- Localで保証できないIAM、throttling、PITR、tagging、非同期挙動を検証する
- staging deployとproduction deployを別の承認ゲートにする
- 同じstagingへのdeployには`concurrency`を設定する

別workflowでstaging deployを行う場合、単に同じ`main push`をtriggerにしてCIと並列実行しない。次のいずれかで成功依存を明示する。

- 同一workflow内の`needs`
- reusable workflowを使う統合pipeline
- 成功したCIの`workflow_run`と対象commit SHAの照合

## 10. DynamoDB Localで保証しない範囲

DynamoDB LocalとAWS DynamoDBは完全には一致しない。次はLocalのGreenだけで保証済みにしない。

- IAMによる認証・認可
- AWSアカウントとリージョンの分離
- provisioned throughput、throttling、capacity
- PITR、backup、tagging
- table/index作成・削除の実時間
- `TransactionConflictException`
- Streams、TTL、非同期処理の時間的挙動
- CloudWatch Logs、metrics、alarms
- LambdaからDynamoDBへのIAM統合

必要な失敗経路はStubber等で注入するか、AWS stagingへ明示的に割り当てる。

## 11. エージェントとコミット境界

### 環境整備

- テスト基盤を担当するエージェントが実装する
- プロダクトコードと機能TDDテストを変更しない
- 環境ランタイム、fixture、環境スモーク、テスト設定だけを変更する
- 契約オーナーが安全性と再現性をレビューする
- 人間がEnvironment Gateを最終承認する

### TDD

- 環境整備をマージした後、新しいテストエージェント実行を開始する
- 承認済みTDD計画だけを機能テストへ変換する
- 環境整備コミットとTDDテストコミットを分離する

推奨コミット:

```text
test: add remote DynamoDB Local test runtime
test: add approved purchase creation TDD tests
feat: implement purchase creation vertical slice
test: complete purchase creation post-implementation verification
```

## 12. PR分割

### TDD開始前

1. PR #15: 環境構築計画
2. Work用DynamoDB Localランタイム、fail-closed検査、pytest integration fixture、marker、環境スモークを1つの環境整備PRとして実装

ランタイムラッパーとfixtureは一体でEnvironment Gateを成立させるため、別PRには分割しない。

### TDD開始後

3. 承認済み購入物登録TDDテストとValid Red
4. 購入物登録の垂直スライス実装とTDD Green
5. 実装後テストと代表E2E
6. GitHub Actions integration / E2E

### 後続

7. AWS stagingのTerraformとOIDC
8. Backend/Frontendのstaging deploy
9. staging smoke・重要E2E

## 13. TDD開始前の最終チェックリスト

- [x] PR #14がマージ済み
- [x] PR #15がマージ済み
- [x] Work用環境整備PR（PR #16）がマージ済み
- [x] DynamoDB Local 3.3.1とSHA-256がロックファイルに固定済み
- [x] fail-closed検査が自動テスト済み
- [x] APIレベルready checkが成功
- [x] pytest integration fixtureが実AWSへ接続しない
- [x] 設定キャッシュを開始前後にクリア
- [x] 環境スモークが連続2回成功
- [x] 既存unit testが成功
- [x] TDD計画のGAP-002を解消済み
- [x] Environment Gate検証済みSHAを記録
- [ ] 人間がEnvironment Gateを承認
- [ ] 人間が「TDD開始」を指示

すべて満たすまで、購入物登録のTDDテスト作成へ進まない。
