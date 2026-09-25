# テスト実行環境構築計画（Work / Claude Code / Pull Request / main）

## 1. 文書の目的

この文書は、DynamoDBを本番の永続化方式として維持しながら、AIのリモート実行環境であるChatGPT Work、Claude Code、GitHub Actions、AWS stagingの各段階にテスト環境を構築する手順とゲートを定義する。

最初の目的は、承認済みの購入物登録TDDテストを作成する前に、WorkとClaude Code上でDynamoDB Localを安全かつ再現可能に起動し、環境障害とValid Redを区別できる状態にすることである。

この文書はテスト環境の契約と実装順序を定める。個別機能の期待動作は定義せず、機能仕様、論理テストケース、TDD計画をsource of truthとする。

| 項目 | 値 |
|---|---|
| 更新日 | 2026-09-25 |
| 現行方式のEnvironment Gate検証済みSHA | `c0b0e38772f91dfd789a590dfcd9f5ffcde07a45` |
| 旧CloudFront方式の参考SHA | `2983f363565f09cf364dfd0d6ae20c7846c3cc01` |
| 環境整備PR | PR #16（マージ済み）、PR #19（Maven移行）、PR #23（miseツールチェーン統一）、PR #24（mise bootstrapラッパー）、PR #25（uvによるPython管理） |
| 対象 | ChatGPT Work、Claude Code、Pull Request Actions、`main`マージ後のAWS staging |
| 採用DB | DynamoDB Local / AWS DynamoDB |
| 状態 | `ENVIRONMENT_READY` / Work連続2回、Ubuntu/macOS CI、人間承認済み |

## 2. 基本方針

SQLiteやPostgreSQLで代替せず、Work、Claude Code、PRではAWS公式のDynamoDB Localを使用する。

| 実行場所 | DB | 起動方法 | 主な検証 |
|---|---|---|---|
| ChatGPT Work | DynamoDB Local | Maven WrapperでMaven Centralから解決し、Java 17以上で起動 | TDD、models/API integration、実装中検証 |
| Claude Code | DynamoDB Local | Workと同じMaven Wrapper・POM・Pythonランナー | TDD、models/API integration、実装中検証 |
| Pull Request | DynamoDB Local | Work・Claude Codeと同じ共通ランナー | unit、component、integration、主要E2E |
| `main`マージ後 | AWS staging DynamoDB | Terraformで管理 | IAM、デプロイ、smoke、AWS固有挙動、重要E2E |
| production | AWS DynamoDB | Terraformで管理 | デプロイ前後の最小確認 |

原則:

- PRから実AWSへ接続しない。
- Work、Claude Code、PRはdummy credentialだけを使用する。
- TDDのRedは、環境起動やfixtureの失敗ではなく、承認済み契約の不成立を理由にする。
- WorkとClaude Codeで検証したMaven Wrapper、POM、起動・初期化処理をGitHub Actionsでも再利用し、二重実装を避ける。
- 自動テストはin-memoryモードを標準とする。
- E2Eを含む実装後テストはTDD Green後に追加する。
- AWS stagingはWork・PRのテスト基盤が安定してから構築する。
- productionへのデプロイはstagingと別の承認ゲートを持つ。

## 3. 現在地

### 3.1 アプリケーション

| 領域 | 現状 |
|---|---|
| Backend | FastAPI、boto3、Python 3.14.7、uv 0.12.18 |
| Frontend | React、TypeScript、Vite、bun |
| 永続化 | PK/SKとGSIを使うDynamoDBシングルテーブル |
| 接続切替 | `DYNAMODB_ENDPOINT_URL`の有無 |
| テーブル作成 | `backend/scripts/bootstrap_local_table.py` |
| ローカル開発 | Docker Compose上のDynamoDB Local |
| Work | Dockerなし。コミット済みmiseラッパーから固定uv・Javaを導入し、uvから固定Pythonを導入。HTTP proxyをMaven一時設定へ変換 |
| Claude Code | Docker利用可否やglobal miseに依存せず、`mise.jdx.dev`とMaven Centralを共通経路として使用 |

正式に対応するホストは、POSIXシェルを持つLinux（WSL2を含む）とmacOSとする。WindowsネイティブのPowerShell / `cmd.exe`はEnvironment Gateの実行環境に含めない。WSL2ではWindows側のPythonやJavaを混在させず、WSLディストリビューション内のmiseからuv・Javaを、uvからPythonを導入する。シェルスクリプトと`mvnw`は`.gitattributes`でLFへ固定する。

### 3.2 Baseline

- 最新`main`（`c0b0e38772f91dfd789a590dfcd9f5ffcde07a45`）でEnvironment Gateが連続2回Pass
- Backend / Frontendのtest・lint・formatは最新`main`のGitHub ActionsでPass
- Ubuntu / macOSのhost prerequisitesは最新`main`のGitHub ActionsでPass
- Backend integration基盤、環境スモーク、fail-closed、Maven設定テストはPass
- Frontend buildの`src/routeTree.gen`不足は機能開発側の既知課題（GAP-003）
- E2EはREADMEのみで、最初の垂直スライスの実装後テストとして追加予定

### 3.3 承認済みTDD計画との関係

購入物登録の最小TDDセットには、APIからDynamoDBまでを接続する統合テストと同時重複登録テストが含まれる。

したがって、DynamoDB Local実行基盤はTDDテスト作成後ではなく、その前にEnvironment Gateを通過させる。

## 4. Work / Claude Code環境仕様

### 4.1 Pythonとuv

- Pythonは`3.14.7`、uvは`0.12.18`へ固定する。
- mise 2026.9.12を固定した公式生成ラッパー`bin/mise`をコミットし、`mise.jdx.dev`から取得した配布物を埋め込みSHA-256で検証して`.mise/`へ配置する。global mise、npm、GitHub Releasesには依存しない。
- Pythonの固定値はルートと`backend/`の`.python-version`、uvとJavaの固定値はルートの`mise.toml`をsource of truthとし、CI、コンテナでも一致させる。
- `scripts/setup_host_prerequisites.sh --install`は`bin/mise`を使い、Environment Gateに必要なuvとJavaを`mise install --jobs=1`で逐次導入した後、uvでPython 3.14.7を`.mise/uv-python/`へ導入する。クラウド環境ではmiseの並列インストールを使用しない。
- `mise.toml`で`exec_auto_install = false`と`UV_MANAGED_PYTHON = 1`を設定し、miseによる暗黙のツール取得とuvによるsystem Pythonへのフォールバックを禁止する。`UV_PYTHON_INSTALL_DIR`はリポジトリ内の`.mise/uv-python/`へ固定する。
- 非対話環境ではshell activationに依存せず、`./bin/mise exec --`経由で固定ツールと`JAVA_HOME`を子プロセスへ渡す。
- `backend/`で`../bin/mise exec -- uv sync --python 3.14.7 --frozen`を実行し、既存のPython 3.14 prerelease環境を再利用しない。
- ラッパー欠落、mise bootstrap・checksum、uv / Javaの取得、uvによるPython 3.14.7の導入、固定バージョンの選択・検証失敗は`ENVIRONMENT_FAILURE`として扱い、機能TDDへ進まない。
- mise更新時は`MISE_VERSION`で別バージョンを動的指定せず、新しい固定バージョンで`bin/mise`を再生成し、専用PRで両環境のGateを再検証する。

### 4.2 MavenとDynamoDB Local

- Java 17以上を実行ランタイムとし、Temurin Java 17を`mise.toml`で選択する。Java自体のインストールやバージョン管理はMavenの責務にしない。
- Javaはmiseで導入し、Mavenはグローバル導入せず固定Maven Wrapperだけを使う。`./bin/mise exec --`によりMaven WrapperとDynamoDB Localへ選択済み`JAVA_HOME`を渡す。
- Maven Wrapper `3.3.4`とApache Maven `3.9.16`をリポジトリ直下へ固定する。
- Maven配布物はMaven Centralの固定URLから取得し、`.mvn/wrapper/maven-wrapper.properties`のSHA-256で検証する。
- DynamoDB LocalはMaven Centralの`software.amazon.dynamodb:DynamoDBLocal:3.3.1`として固定する。
- `tools/java-runtime/pom.xml`をJava製テストツール依存関係のsource of truthとする。
- POMではreleaseだけを有効にし、checksum不一致を失敗として扱う。
- Maven Wrapper、Maven Central解決、POM読取、Java起動の失敗はすべて`ENVIRONMENT_FAILURE`、exit 70とする。
- Workで`HTTPS_PROXY`等が設定されている場合、ランナーが認証情報をGit管理せず一時的なMaven settingsへ変換し、実行後に削除する。
- WorkやClaude Codeで追加CA証明書が設定されている場合、mise管理Javaの既定truststoreへ一時的に取り込み、Maven終了後に削除する。
- Mavenのローカルリポジトリ、解決済みJAR、native library、DBファイル、PID、ログはGit管理しない。

管理ファイル:

```text
scripts/setup_host_prerequisites.sh
bin/mise
.gitattributes
.python-version
backend/.python-version
mise.toml
mvnw
mvnw.cmd
.mvn/wrapper/maven-wrapper.properties
tools/java-runtime/pom.xml
```

キャッシュ:

```text
.cache/dynamodb-local/
├── maven-user-home/
├── maven-repository/
└── 3.3.1/
    ├── dependencies/
    ├── logs/
    └── maven-resolved.json
```

POMまたは固定バージョンを変更した場合、POMのSHA-256とmarkerが一致しなくなるため、ランナーは依存関係を再解決する。バージョン更新は専用PRで行い、WorkとClaude CodeのEnvironment Gateを再実行する。

### 4.3 起動モード

自動テストでは、Mavenが解決したclasspathとnative library directoryを使って起動する。

```bash
java \
  -Djava.library.path=<cache>/dependencies \
  -cp '<cache>/dependencies/*' \
  software.amazon.dynamodb.services.local.main.ServerRunner \
  -inMemory \
  -sharedDb \
  -port <port> \
  -disableTelemetry
```

ラッパーはpytestセッションの開始前にDynamoDB Localを1回だけ起動し、子コマンド終了後に停止する。pytest fixtureはプロセスを起動・停止せず、ラッパーが用意した接続先を使用する。ラッパーを介さずintegration testを実行した場合は`ENVIRONMENT_FAILURE`として停止する。

手動デバッグで状態保持が必要な場合だけ、`-inMemory`を外して専用の`-dbPath`を指定する。

### 4.4 ポート

- 既定値は現在のDocker Composeと合わせて`8001`とする。
- `DYNAMODB_LOCAL_PORT`で上書き可能にする。
- 起動前に使用中か検査し、既存プロセスを無条件に終了しない。
- ラッパーが起動したPIDだけを記録し、終了時にそのPIDだけを停止する。

### 4.5 接続設定

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
- [x] DynamoDB Local 3.3.1、Maven 3.9.16、Maven Wrapper配布物SHA-256を固定する
- [x] port、キャッシュ場所、テスト用table prefixを固定する
- [x] pytestセッション、テーブル再作成、空の初期状態を固定する
- [x] Environment Gateの判定項目を承認する

完了条件: 環境仕様と基準コミットが固定されている。

### Step 1: 共通ランタイムラッパーを実装する（実装・検証済み）

成果物:

```text
scripts/setup_host_prerequisites.sh
.gitattributes
.python-version
backend/.python-version
mise.toml
mvnw
mvnw.cmd
.mvn/wrapper/maven-wrapper.properties
tools/java-runtime/pom.xml
backend/scripts/run_with_dynamodb_local.py
.gitignore
```

共通の環境構築・実行経路は次を行う。

0. [x] 対応OSとコミット済みmiseラッパーを検査し、Windowsネイティブではfail closedする
1. [x] miseからuv 0.12.18を選択する
2. [x] uvからPython 3.14.7をリポジトリローカルへ導入・選択する
3. [x] `--jobs=1`で逐次導入したTemurin Java 17を選択し、Java 17以上を確認する
4. [x] Maven WrapperとMaven配布物SHA-256を固定
5. [x] POMからDynamoDB Local 3.3.1とdependency pluginの固定バージョンを読む
6. [x] 環境proxyを認証情報を残さない一時Maven settingsへ変換
7. [x] Maven Centralから本体、推移依存、native libraryを解決
8. [x] POM SHA-256と解決済みmarkerを照合してcacheを再利用
9. [x] 実行時にDynamoDB Localのversion出力を検証
10. [x] 未使用portを確認
11. [x] in-memoryモードで起動
12. [x] APIレベルのready check
13. [x] 子コマンドをサニタイズしたAWS環境変数で実行
14. [x] 終了コードを保持
15. [x] 自分が起動したDynamoDB Localだけを停止
16. [x] ログと終了理由を出力

ホスト前提の構築とGate本体を次の順序で実行する。miseの事前導入は不要で、`bin/mise`が固定版をbootstrapする。`--install`はmiseでuvとJavaを逐次導入した後、uvで固定Pythonを導入する。`--check`はネットワーク取得を行わず、mise管理のuv / Javaとuv管理のPythonを検証する。

```bash
bash scripts/setup_host_prerequisites.sh --install
bash scripts/setup_host_prerequisites.sh --check
cd backend
../bin/mise exec -- uv sync --python 3.14.7 --frozen
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local \
  -- ../bin/mise exec -- uv run pytest -m integration
```

Maven Wrapper bootstrap、Maven Central解決、checksum、Java、起動、ready checkの失敗は`ENVIRONMENT_FAILURE`として扱い、Valid Redへ数えない。

完了条件: **達成済み。** クリーンなWorkで共通手順を連続2回実行し、Ubuntu/macOSのActionsでもhost prerequisitesが成功した。Claude Code固有環境での結果は補足証跡として後日追記できる。

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

### Step 3: Environment Gateを再検証する（完了・人間承認済み）

最低限、各環境で次を記録する。

| 検証 | 期待結果 |
|---|---|
| host OS | Linux（WSL2を含む）またはmacOS。WindowsネイティブはFail |
| host prerequisites | Linux（WSL2を含む）またはmacOS、`curl`または`wget`、`tar`、`sha256sum`または`shasum` |
| mise bootstrap | `bin/mise`からmise 2026.9.12を`mise.jdx.dev`経由で取得し、埋め込みSHA-256検証 |
| mise tool selection | uv 0.12.18、Temurin Java 17 |
| uv Python selection | repository-local Python 3.14.7（system fallback不可） |
| uv version | 0.12.18 |
| Python version | 3.14.7（prerelease不可） |
| Java version | 17以上 |
| Maven Wrapper | 3.3.4、固定SHA-256検証 |
| Maven version | 3.9.16 |
| Maven repository | `https://repo.maven.apache.org/maven2` |
| DynamoDB Local coordinate | `software.amazon.dynamodb:DynamoDBLocal:3.3.1` |
| DynamoDB Local version | 3.3.1 |
| API ready check | Pass |
| テーブル作成・DescribeTable | Pass |
| 環境スモーク | Pass |
| 既存Backend unit | 53件以上、既存分がPass |
| 連続2回実行 | Maven cache再利用時も、前回データ・プロセス・portを引き継がずPass |
| endpoint未設定 | SDK呼び出し前にFail |
| 非loopback endpoint | SDK呼び出し前にFail |
| Maven Wrapper / Central解決失敗 | `ENVIRONMENT_FAILURE`、exit 70 |
| POM不正・依存関係不完全 | Java起動前に`ENVIRONMENT_FAILURE`、exit 70 |
| Javaプロセス起動失敗 | `ENVIRONMENT_FAILURE`、exit 70 |
| ログ作成等のOS失敗 | `ENVIRONMENT_FAILURE`、exit 70 |
| 子コマンド失敗 | 終了コードを保持し、DynamoDB Localを停止 |

Environment Gate:

- [x] Maven Wrapper、Maven、DynamoDB Local、pluginのバージョンが固定されている
- [x] 対応OSとホスト前提の検査・明示的な構築経路が定義されている
- [x] shell scriptと`mvnw`がLFへ固定されている
- [x] Maven配布物SHA-256とMaven repository checksum policyが設定されている
- [x] Work proxyとproxyなし環境を同じランナーで扱う
- [x] 単一コマンドで依存解決、起動、ready check、子コマンド、停止を行う
- [x] 実AWSへ接続しないfail-closed検査がある
- [x] mise / uv管理ツールチェーンでWorkの環境スモークと既存unit testが連続2回成功
- [x] Ubuntu/macOS Actionsでhost prerequisitesと既存testが成功
- [x] mise / uv管理ツールチェーンでWorkのMaven・安全性・OSレベルの失敗を`ENVIRONMENT_FAILURE`として再確認
- [x] Maven方式の検証済みSHAを記録
- [x] 人間が更新後のEnvironment Gateを承認
- [ ] Claude Code固有のクラウド実行結果を補足証跡として追記（非ブロッキング）

PR #25マージ後の最新`main`で現行方式の正式Gateと人間承認が完了した。旧CloudFront方式の証跡は履歴としてのみ保持する。Claude Code固有環境の補足検証で不具合が見つかった場合はGateを再度開く。

### Step 4: TDD計画へ環境証跡を反映する

- [x] Maven・mise・uv移行後の環境整備コミットSHAを記録する
- [x] Workの正式GateとUbuntu/macOS Actionsの結果を記録する
- [x] PR #14で記録したGAP-002の解消状況を更新する
- [x] 環境整備とTDDテストのコミットを分離する（機能TDDテストは未作成）
- [x] 環境整備PRをマージする
- [x] 最新`main`でBaselineを再実行する
- [x] Maven・mise・uv方式のEnvironment Gate検証済みSHAを固定する

`c0b0e38772f91dfd789a590dfcd9f5ffcde07a45`を現行方式の検証済み環境コードSHAとして固定する。以後も環境コードまたはテスト基盤を変更した場合は再検証し、文書だけの変更では更新しない。TDDを開始するAgentは、その時点の最新`main`からブランチを作成し、
実際の分岐元をTDD作業開始SHAとしてTDD実行記録へ記録する。

Steps 0〜4は完了した。購入物登録TDDテストコードは、人間による明示的な「TDD開始」指示後に作成する。

## 7. TDD開始後

Environment Gateと人間承認は完了済みである。次に開発サイクル実行Skillsを整備し、その後の人間による明示的な「TDD開始」を起点として、[4エージェント＋オーケストレーター開発運用](../FOUR-AGENT-DEVELOPMENT-WORKFLOW.md)を開始する。

1. 仕様エージェントの承認済み仕様、論理テストケース、中心的契約、TDD計画を入力として固定する
2. 新しいテストエージェントが承認済み最小TDDセットをテストコードへ変換する
3. 環境スモークを実行し、Greenを確認する
4. TDD対象テストのRedと承認済みRed例外を記録する
5. オーケストレーターがAutomated Red Gateを判定する
6. 新しい実装エージェントが凍結済みテストを変更せず実装する
7. オーケストレーターがAutomated Green Gateを判定する
8. 実装時の会話を引き継がない新しいテストエージェントが実装後テストを作成・実行する
9. オーケストレーターがCompletion Gateを判定する
10. 新しいレビューエージェントが仕様、テスト、実装、証跡を統合的に確認する
11. 人間がSlice Completeを最終判断する

環境スモークが失敗した場合は`ENVIRONMENT_FAILURE`で停止する。機能テストの失敗と混在させない。仕様上の問題は仕様エージェント、テスト上の問題はテストエージェント、実装上の問題は実装エージェントへ戻し、影響するGate以降を再実行する。

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
- 独立したレビュー担当が安全性と再現性をレビューする
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

### 完了済み

1. PR #15: 環境構築計画
2. PR #16: Work用DynamoDB Localランタイム、fail-closed検査、pytest integration fixture、marker、環境スモーク
3. PR #17: 最新`main`での旧CloudFront方式Environment Gate証跡と文言整合
4. PR #19: DynamoDB Localの取得をMaven Centralへ統一し、Work・Claude Codeの共通経路を構築
5. PR #23: miseによるツールチェーン統一
6. PR #24: 固定mise bootstrapラッパーと逐次インストール
7. PR #25: uvによるPython管理
8. 最新`main`のEnvironment Gate連続2回成功と人間承認

現行のMaven・mise・uv方式は`ENVIRONMENT_READY`である。旧CloudFront方式の証跡は履歴として保持する。

### 次の準備

9. 4エージェント＋オーケストレーターの各工程を実行するSkills

### TDD開始後

10. 承認済み購入物登録TDDテストとValid Red
11. 購入物登録の垂直スライス実装とTDD Green
12. 実装後テスト、代表E2E、独立した最終レビュー
13. GitHub Actions integration / E2E

### 後続

14. AWS stagingのTerraformとOIDC
15. Backend/Frontendのstaging deploy
16. staging smoke・重要E2E

## 13. TDD開始前の最終チェックリスト

- [x] PR #14がマージ済み
- [x] PR #15がマージ済み
- [x] Work用環境整備PR（PR #16）がマージ済み
- [x] Maven Wrapper 3.3.4、Maven 3.9.16、DynamoDB Local 3.3.1が固定済み
- [x] fail-closed検査が自動テスト済み
- [x] APIレベルready checkが成功
- [x] pytest integration fixtureが実AWSへ接続しない
- [x] 設定キャッシュを開始前後にクリア
- [x] mise / uv管理ツールチェーンで環境スモークが連続2回成功
- [x] mise / uv管理ツールチェーンで既存unit testが成功
- [x] TDD計画のGAP-002を解消済み
- [x] mise / uv管理ツールチェーンを含むMaven方式のEnvironment Gate検証済みSHAを記録
- [x] 人間がMaven方式のEnvironment Gateを再承認
- [ ] 人間が「TDD開始」を指示

Environment Gate再検証・再承認は完了済みである。開発サイクル実行Skillsを整備し、その後に人間が明示的な「TDD開始」を指示するまで、購入物登録のTDDテスト作成へ進まない。
