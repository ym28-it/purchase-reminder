# テスト環境構築 TODO（Work / Pull Request / main）

## 1. 文書の位置づけ

この文書は、DynamoDBを本番の永続化方式として維持し、次の3段階でテスト環境を構築するためのTODOである。

1. ChatGPT Work: DynamoDB LocalをJARで直接起動してTDD・統合テスト
2. Pull Request: GitHub Actions上のDynamoDB Localで統合テスト・E2E
3. `main`マージ後: AWS stagingへデプロイし、実DynamoDBでスモークテスト・重要E2E

この文書は実装順序と完了条件を整理するものであり、個別機能の期待動作を新たに定義しない。
機能のテスト実装時は、承認済み仕様、論理テストケース、TDD計画をsource of truthとする。

| 項目 | 値 |
|---|---|
| 更新日 | 2026-09-18 |
| 調査対象コミット | `69a00dc` |
| 対象ブランチ | `main` |
| 採用方針 | DynamoDBを全環境で維持 |
| 状態 | Draft / 実装前TODO |

## 2. 結論

SQLiteやPostgreSQLへ置き換えず、WorkとPRではAWS公式のDynamoDB Localを使用する。

DynamoDB Localはローカルで自己完結して動作し、アプリケーションからはboto3とDynamoDB APIで接続できる。
これにより、現在の次の設計を維持したままテスト環境を構築できる。

- boto3によるDynamoDBアクセス
- `DYNAMODB_ENDPOINT_URL`によるローカル・AWS接続先の切り替え
- PK/SKを使ったシングルテーブル設計
- GSI
- DynamoDBの条件付き書き込み
- Lambda + DynamoDBの本番構成

Work環境にはDockerがないが、OpenJDK 17がある。DynamoDB LocalのJARとnative libraryを準備すれば、
Dockerを使わずにDynamoDB Localを直接起動できる。

## 3. 目標構成

| 実行場所 | DB | 起動方式 | 主なテスト | 目的 |
|---|---|---|---|---|
| ChatGPT Work | DynamoDB Local | Java 17でJARを直接起動 | unit、models/API integration、限定的E2E | 高速なTDDと実装中検証 |
| PR Actions | DynamoDB Local | コンテナまたはJAR | 全unit、integration、主要E2E | DynamoDB APIを含む回帰検出 |
| `main` Actions | AWS staging DynamoDB | Terraformで管理 | 初期化、smoke、重要E2E | IAM・IaC・実AWS接続を含む確認 |
| production | AWS DynamoDB | Terraformで管理 | デプロイ前後の最小確認 | 利用者向け環境 |

原則:

- PRからAWSへ接続しない。PR検証はGitHub Actions内で自己完結させる。
- `main`マージ後のAWSはproductionではなく、分離したstaging環境を使う。
- TDDのRedは環境起動失敗ではなく、対象契約が未実装であることを理由に失敗させる。
- DynamoDB Localの状態はテスト単位またはテストセッション単位で初期化する。
- DynamoDB Localで再現できないAWS固有の挙動だけをstagingで検証する。
- AWSの長期アクセスキーをGitHub Secretsへ保存せず、GitHub Actions OIDCで短期認証する。
- productionデプロイは、このTODOとは別の承認ゲートを持つ。

## 4. 現在の構成

### 4.1 アプリケーションとDB

| 領域 | 現状 | 根拠 |
|---|---|---|
| Backend | FastAPI + boto3 | `backend/pyproject.toml`, `backend/app/` |
| Frontend | React + TypeScript + Vite + bun | `frontend/package.json` |
| 本番DB設計 | DynamoDB | `README.md` |
| ローカルDB | Docker Compose上のDynamoDB Local | `docker-compose.yml` |
| DB接続切替 | `DYNAMODB_ENDPOINT_URL`の有無 | `backend/app/core/config.py` |
| 永続化実装 | DynamoDBのPK/SK/GSIを使う独自models層 | `backend/app/models/` |
| テーブル初期化 | ローカル用bootstrap scriptあり | `backend/scripts/bootstrap_local_table.py` |
| 本番Backend | ECRのコンテナイメージをLambdaで実行 | `README.md`, `backend/Dockerfile` |
| AWS IaC | Terraform予定、未実装 | `README.md` |

### 4.2 テスト

| 領域 | 現状 | 差分 |
|---|---|---|
| Backend unit | 53件成功 | models基盤中心。CRUD/APIの保証は不足 |
| Backend integration | ディレクトリのみ | DynamoDB Localを使うテスト未実装 |
| Frontend test | 0件 | CIでは`--passWithNoTests`で成功扱い |
| E2E | READMEのみ | Playwright依存、設定、spec、実行スクリプトが未実装 |
| 認証E2E | 方針のみ | Cognito自体が未実装 |
| Lint/format | Backendは成功 | Work環境にはbunがなくFrontendは今回未実行 |

Backendの調査時Baseline:

```text
pytest: 53 passed
ruff check: passed
ruff format --check: passed
```

### 4.3 CI/CD

| ファイル | 現状 |
|---|---|
| `.github/workflows/lint.yml` | PRと`main` pushでBackend/FrontendのLint・format check |
| `.github/workflows/test.yml` | PRと`main` pushでBackend pytest、Frontend Vitest |
| DBサービス | なし |
| DynamoDB Local integration | なし |
| API統合テスト | なし |
| Playwright E2E | なし |
| AWS認証 | なし |
| Terraform plan/apply | なし |
| AWSデプロイ後テスト | なし |

## 5. DynamoDB Localの使用方針

### 5.1 自動テスト: in-memoryモード

TDD、API統合テスト、PR CIでは、原則として状態を残さないin-memoryモードを使用する。

```bash
java \
  -Djava.library.path=./DynamoDBLocal_lib \
  -jar DynamoDBLocal.jar \
  -inMemory \
  -sharedDb \
  -port 8001 \
  -disableTelemetry
```

用途:

- 実行ごとに空の状態から開始する
- 前回のテストデータを持ち越さない
- テスト終了時にプロセスごと破棄する
- CIとWorkの挙動を揃える

### 5.2 手動確認・デバッグ: ファイルモード

Work上で複数回の操作にまたがって状態を残したい場合だけ、ファイルモードを使用する。

```bash
java \
  -Djava.library.path=./DynamoDBLocal_lib \
  -jar DynamoDBLocal.jar \
  -sharedDb \
  -dbPath ./data \
  -port 8001 \
  -disableTelemetry
```

`-sharedDb`を指定すると、`shared-local-instance.db`へ保存される。DBファイルはテスト成果物ではないため、
Git管理せず、Workの一時領域または`.cache/`配下に置く。

### 5.3 接続設定

WorkとPRでは、現在の設定方式をそのまま使用する。

```text
DYNAMODB_ENDPOINT_URL=http://127.0.0.1:8001
DYNAMODB_TABLE_NAME=purchase-reminder-test
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
AWS_DEFAULT_REGION=ap-northeast-1
```

AWS stagingでは`DYNAMODB_ENDPOINT_URL`を設定せず、AWS SDKの標準接続先とIAM roleを使用する。

## 6. DynamoDB Localで保証できない範囲

DynamoDB Localは開発・テスト用であり、AWSのDynamoDBと完全には一致しない。
以下はLocalでGreenでも実AWSで別途確認が必要である。

- IAMによる認証・認可
- AWSアカウントとリージョンの分離
- provisioned throughput、throttling、capacity関連の挙動
- PITR、backup、tagging
- 実サービス上のtable/index作成・削除時間
- transaction conflictの一部
- Streams、TTL、非同期処理の時間的挙動
- CloudWatch Logs、metrics、alarms
- LambdaからDynamoDBへのIAM統合

Localで再現できない失敗を、通常のTDD Redとして扱わない。必要なケースはmockによるエラー注入、
または`main`マージ後のAWS stagingテストへ明示的に割り当てる。

## 7. 現状との差分

### 7.1 Work

- [ ] DynamoDB Localの配布物を取得するセットアップスクリプトを追加する
- [ ] DynamoDB Localのバージョンとchecksumを固定する
- [ ] JARとnative libraryをGit管理外のキャッシュディレクトリへ展開する
- [ ] in-memoryモードの起動スクリプトを追加する
- [ ] ファイルモードの起動を必要な場合だけ選べるようにする
- [ ] HTTP endpointのready checkを追加する
- [ ] テスト終了時にDynamoDB Localプロセスを確実に停止する
- [ ] `bootstrap_local_table.py`をテスト用テーブル名で実行できるようにする
- [ ] `make test-integration`または同等の単一コマンドを用意する
- [ ] ダウンロード不可の場合、環境問題として明示し、TDDのValid Redに数えない

### 7.2 Backend integration test

- [ ] DynamoDB Local endpointを向くpytest fixtureを追加する
- [ ] テストセッション用の一意なテーブル名を生成する
- [ ] テーブルschemaを既存bootstrap処理で作成する
- [ ] 各テストの前後でitemを削除するか、テーブル自体を再作成する
- [ ] 実AWS credentialを使用しないことをfixtureで保証する
- [ ] models層の保存、取得、更新、削除を検証する
- [ ] APIからDynamoDB Localまでを通る統合テストを追加する
- [ ] `user_id`によるデータ分離を検証する
- [ ] 条件付き書き込みによる重複防止を検証する
- [ ] PK/SK/GSIの期待構造を必要な範囲で検証する
- [ ] Localで再現できない例外はbotocore Stubber等で補う

### 7.3 Pull Request Actions

- [ ] DynamoDB LocalをコンテナまたはJARで起動する
- [ ] health check完了後にテーブルを作成する
- [ ] Backend unitとDynamoDB integrationを分けて結果を表示する
- [ ] Frontend Vitestの`--passWithNoTests`を最初のテスト追加後に削除する
- [ ] Playwrightのpackage、config、browser installを追加する
- [ ] FastAPIとViteをバックグラウンド起動し、ready check後にE2Eを開始する
- [ ] E2E用テーブルをrunごとに初期化する
- [ ] 失敗時にPlaywright trace、screenshot、DynamoDB/API logをartifactとして保存する
- [ ] 必須checkをbranch protectionへ登録する
- [ ] Actionsと`mise.toml`でPython/bun等のバージョンを一致させる

### 7.4 `main`マージ後のAWS staging

- [ ] `infra/`または`terraform/`の配置とmodule構成を決める
- [ ] staging専用AWSアカウント、または少なくとも専用IAM role・リソース名を使う
- [ ] GitHub Actions OIDC providerとstaging deploy roleをTerraformで管理する
- [ ] staging専用DynamoDBテーブルをTerraformで定義する
- [ ] productionとは異なるテーブル名、IAM role、SSM Parameterを使用する
- [ ] point-in-time recovery、暗号化、billing mode、tagを定義する
- [ ] GSIを含むテーブルschemaをTerraformとアプリ側schemaで照合する
- [ ] Backend imageをECRへpushし、staging Lambdaを更新する
- [ ] FrontendをS3へ配置し、CloudFrontを更新する
- [ ] デプロイ完了後にAPI smoke testを実行する
- [ ] Cognito実装後はstaging専用User Poolとテストユーザーを使う
- [ ] Localで再現できない重要ケースと主要Playwright E2Eをstaging URLへ実行する
- [ ] 失敗時にproductionへ進めず、stagingのログとartifactを残す
- [ ] stagingのテストデータ初期化・保持期間を決める

## 8. 実装順序

既存の開発順序を維持する。Work・PR用のテスト基盤はPhase 1の既存CRUD整備に含め、
AWS/Terraformは当初の計画どおりPhase 5まで後ろに置く。

### Step 0: テスト環境仕様を確定する

- [ ] DynamoDB LocalをWork・PRの共通DBとする方針を承認する
- [ ] Localのバージョン、port、キャッシュ場所を決める
- [ ] in-memoryを自動テストの標準とする
- [ ] ファイルモードを手動確認専用とする
- [ ] Localで保証しない項目とAWS stagingで保証する項目を分ける

完了条件: Work、PR、AWSそれぞれの責務と非対象が明記されている。

### Step 1: 現行CRUDの契約をテストで保護する

- [ ] 承認済み`purchase-create`仕様・論理テストケースを基準にTDD計画を確定する
- [ ] 最小TDDセットを実装してGreenにする
- [ ] CRUD/APIの未保護経路を実装後テストで補う
- [ ] DynamoDB Localが不要なdomain/serviceテストはmock/fakeで高速に保つ

完了条件: DBを起動しない高速テストと、DynamoDB APIを通す統合テストの責務が分離されている。

### Step 2: Work用DynamoDB Local実行基盤を追加する

- [ ] 配布物の取得、checksum検証、展開を自動化する
- [ ] 起動、ready check、table作成、pytest、停止を単一コマンドにまとめる
- [ ] WorkでDynamoDB Local integration testを実行する
- [ ] プロセス・DBファイル・ログをGit管理対象外にする
- [ ] 失敗時に環境起因かテスト起因かを判別できるログを残す

完了条件: DockerなしのWork環境で、DynamoDB Localを使った統合テストが再現可能に成功する。

### Step 3: PR用DynamoDB Local integrationを追加する

- [ ] ActionsでDynamoDB Localを起動する
- [ ] table作成後にintegration testを実行する
- [ ] Localプロセスのhealth checkとtimeoutを設定する
- [ ] unitとintegrationを別checkとして表示する
- [ ] PRの必須checkとして設定する

完了条件: PRはAWS認証情報なしでDynamoDB APIを使う統合テストを完了できる。

### Step 4: PR用フルスタックE2Eを追加する

- [ ] `e2e/package.json`とPlaywright設定を追加する
- [ ] DynamoDB Local、FastAPI、Viteを一括起動する
- [ ] 最初は購入物登録の代表正常系1件をE2Eにする
- [ ] API統合テストと重複する境界値をE2Eへ大量追加しない
- [ ] 認証未実装中は、テスト専用の認証境界を明示的に使う
- [ ] trace、screenshot、server logをartifact化する

完了条件: PR上で画面操作からDynamoDB Localへの永続化・再取得までを1件以上検証できる。

### Step 5: TerraformでAWS stagingを構築する

このStepは、承認済みロードマップのPhase 5（AWS/Terraform/CI/CD）で実施する。

- [ ] Terraform state backendとlock方式を決める
- [ ] stagingのDynamoDB、Lambda/API Gateway、ECR、S3/CloudFrontを段階的に作る
- [ ] OIDCによるGitHub Actions deploy roleを作る
- [ ] `terraform plan`と`terraform apply`の責務・承認条件を分ける
- [ ] staging deploy workflowを`main` pushだけで起動する
- [ ] deploy、table確認、smoke、重要E2Eの順に実行する
- [ ] production deployは自動的に連鎖させない

完了条件: `main`マージ後だけstagingが更新され、実DynamoDBを含むデプロイ後検証の結果を確認できる。

### Step 6: 運用を安定化する

- [ ] flaky E2Eの検出と隔離ルールを決める
- [ ] テスト時間を計測し、unit/integration/E2Eの責務重複を削る
- [ ] stagingデータの定期初期化方法を決める
- [ ] AWS予算アラートを設定する
- [ ] DynamoDB Localバージョン更新手順を作る
- [ ] CI/CDとstaging障害時の切り分け手順を作る

## 9. Workflowの分割案

| Workflow | Trigger | 内容 |
|---|---|---|
| `lint.yml` | PR, `main` push | Backend/Frontend lint・format |
| `test.yml` | PR, `main` push | unit、Frontend component test |
| `integration.yml` | PR, `main` push | DynamoDB Local、table作成、API integration |
| `e2e.yml` | PR, `main` push | DynamoDB Localを含むローカルフルスタックE2E |
| `deploy-staging.yml` | `main` push, manual | AWS認証、Terraform/deploy、smoke、staging E2E |

`main` pushではPRと同じCIが再実行されるが、AWS deployはすべての必須テスト成功後に開始する。
同じstagingへ複数のdeployが重ならないよう、Actionsの`concurrency`を設定する。

## 10. テストデータと分離ルール

- 自動テストではDynamoDB Localをin-memoryで起動する。
- テストセッションごとに一意なテーブル名を使う。
- テストごとにitemを削除するか、tableを再作成する。
- E2EのユーザーID・購入物IDはrun IDなどから一意にする。
- テストは他のテストが作成したデータや実行順に依存しない。
- 時刻、UUID、認証主体はテストから制御可能にする。
- staging E2Eは専用テストユーザーと専用データだけを使用する。
- productionテーブルやproductionデータをテストから参照しない。
- 失敗後も再実行できるよう、fixture作成を冪等にする。

## 11. セキュリティと権限

- WorkとPRのDynamoDB Localにはdummy credentialだけを設定する。
- PR workflowにはAWS権限を付与しない。
- fork由来PRへsecretを公開しない。
- AWSアクセスはGitHub Actions OIDCによる短期credentialを使う。
- staging deploy roleにはstagingリソースだけを操作できる権限を付与する。
- Cognitoテストユーザー情報をリポジトリへ保存しない。
- Playwright traceやserver logへtoken、password、個人情報を残さない。
- Terraform plan artifactにsecret値を含めない。

## 12. 完了判定

すべてを満たした時点で、このTODOを完了とする。

- [ ] WorkでDynamoDB LocalをJARから起動できる
- [ ] WorkでDynamoDB Local integrationを単一コマンドで再現できる
- [ ] DynamoDB Localの配布物とDBファイルがGit管理されていない
- [ ] PRでDynamoDB Local integrationが自動実行される
- [ ] PRで主要なフルスタックE2Eが成功する
- [ ] 失敗時のログ・trace・screenshotを確認できる
- [ ] Localで保証しないケースがAWS stagingへ明示的に割り当てられている
- [ ] `main`マージ後だけAWS stagingが更新される
- [ ] stagingで実DynamoDBを使うsmoke・主要E2Eが成功する
- [ ] AWS認証に長期アクセスキーを使用していない
- [ ] production deployがstaging deployから明示的に分離されている
- [ ] TDD計画・論理Test Case ID・実テスト間のトレーサビリティが維持されている

## 13. PR分割案

各PRは、既存の仕様承認・論理テストケース・TDD Gateに従って小さく分割する。

1. DynamoDB Localテスト環境仕様と起動スクリプト
2. pytest fixtureとmodels層integration test
3. 購入物登録APIのDynamoDB integration test
4. GitHub ActionsのDynamoDB Local integration
5. 購入物登録の最小Playwright E2E
6. AWS stagingのTerraform基盤とOIDC
7. Backend/Frontendのstaging deploy
8. staging smoke・E2E workflow

AWS関連PRは、既存CRUD・コア仕様・計画UI・Cognitoの後に位置づける。AWS構築を先行させず、
現在進行中のアプリケーション仕様・テスト整備を優先する。
