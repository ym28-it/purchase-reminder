# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

「買い物リマインダー」— 定期的に購入するものの消費速度と現在の在庫を登録しておき、消費しきる前に「何を」「どれくらい」買うべきかを通知するアプリ。詳細な要件・データモデル・本番インフラ構成は README.md を参照。

## Repository layout

- `backend/` — FastAPI + boto3 (DynamoDB) API
- `frontend/` — React + TypeScript + Vite, bun管理
- `e2e/` — Playwright によるフルスタックE2Eテスト（backend/frontend どちらのディレクトリ配下でもなく独立配置）

## Current state

ローカル環境では、FastAPI + DynamoDB Localの購入物CRUD（一覧・登録・更新・削除）と、それを操作するReact画面まで実装済み。DynamoDBの汎用モデル基盤には単体テストがあるが、purchase CRUD、services、API、frontendのテストは未整備。Cognito認証、購入タイミングのドメインロジック、通知、Terraform、デプロイ、E2Eは未実装。開発ワークフローはsuperpowersへ移行し、TDD部分だけを独自制御としている。着手前に実際のファイルとCI結果を確認し、この記述よりコードを優先して現在地を判断すること。

### 現在の優先作業: superpowersで購入物登録の実装計画を作成

テスト環境は`ENVIRONMENT_READY`であり、Work、Claude Code、Ubuntu/macOS Actionsで共通経路を確認済みである。[テスト実行環境構築計画](docs/todo/test-environment-rollout.md)と[Environment Gate実行証跡](docs/test-environment-gate-evidence.md)を環境契約のsource of truthとする。環境コードまたはテスト基盤を変更した場合だけ、同じGateを再実行して人間の再承認を得る。環境の確認・修復には独立した`setup-test-environment` Skillを使用する。

購入物登録（`docs/specs/purchase-create*.md`）は仕様、論理テストケース、中心的契約、最小TDD計画が承認済みである。次は`superpowers:writing-plans`で、この承認済み成果物を入力とした実装計画を作成する。人間が計画を承認して実行方式を選択するまで、テストコードやプロダクトコードを変更しない。

## 開発ワークフロー（superpowers＋独自TDD）

開発ワークフロー全体は[superpowers](https://github.com/obra/superpowers)プラグイン（`.claude/settings.json`で有効化）が制御する。TDDとテストに関わる部分だけを、[TDDワークフロー（superpowers連携）](docs/TDD-WORKFLOW.md)の独自制御に置き換える。

```
superpowers:brainstorming → [独自] design-tdd-tests → superpowers:writing-plans
  → superpowers:subagent-driven-development（Red: create-tdd-tests / Green: implement-tdd-slice / 検証: verify-feature-slice）
  → superpowers 最終コードレビュー → verification-before-completion → finishing-a-development-branch
```

### Claude CodeとCodexの役割

- **Claude Code**: 開発作業の実行基盤。superpowersと独自TDD Skills（`.claude/skills/`）による仕様化、計画、テスト、実装、検証、コミット、Pull Requestを担当する
- **Codex（ChatGPT Workを含む）**: レビューと助言の相談役。ワークフローの工程、コード変更、承認は行わない。役割は[`AGENTS.md`](AGENTS.md)に定める
- Codexの指摘は判断材料として扱い、`superpowers:receiving-code-review`に従って根拠を検証してから反映する。相談の時点は`docs/TDD-WORKFLOW.md`の「実行環境とCodexの位置づけ」を参照

### superpowersより優先する規則

このファイルと`docs/TDD-WORKFLOW.md`はsuperpowersのSkillより優先する。

- `superpowers:test-driven-development`は使わない。superpowersのSkillがTDDを指示した場合は`docs/TDD-WORKFLOW.md`と独自Skills（`design-tdd-tests`、`create-tdd-tests`、`implement-tdd-slice`、`verify-feature-slice`）を適用する。実装前テストはTDD計画で承認した中心的契約だけとし、網羅は実装後テストで行う
- 仕様・論理テストケース・期待結果・凍結済みTDDテストに関わる判断は、`subagent-driven-development`のRulingで決めない。仕様から一意に導けない場合は停止して人間へ戻す
- Valid Red記録後のTDDテストは凍結し、実装やレビュー指摘の修正のために変更しない
- 仕様（brainstormingのdesign doc）では各要件に`<PREFIX>-<3桁連番>`の仕様IDを付け、確認事項をBlocking / Important / Deferredに分類してBlockingを0件にしてから承認する
- 新しいユーザー価値は最小垂直スライス（入力から最終的な出力・永続状態まで観測でき、単独で検証・リリースできる最小の機能単位）で進める。フロントエンド全体の後にバックエンド全体を作るような水平分割はしない。既存APIで価値が完結するならフロントエンドだけの変更でもよい

### 成果物の配置

- 仕様: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`（superpowers既定）
- 論理テストケース: `docs/superpowers/specs/YYYY-MM-DD-<topic>-test-cases.md`
- TDD計画: `docs/superpowers/specs/YYYY-MM-DD-<topic>-tdd-plan.md`（[テンプレート](docs/templates/minimum-tdd-test-plan.md)）
- 実装計画: `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`（superpowers既定）
- 実装後テストレポート: `docs/superpowers/specs/YYYY-MM-DD-<topic>-post-test-report.md`（[テンプレート](docs/templates/post-implementation-test-report.md)）
- superpowers導入前の購入物登録は`docs/specs/purchase-create*.md`に置いたまま同じ契約で扱う

### 人間とAIの分担

- 人間は機能の目的・要求・制約を提示し、仕様、論理テストケース、中心的契約、TDD計画、実装計画を承認し、最終レビューと証跡を確認してマージ（Slice Complete）を判断する
- AIは仕様の曖昧さ・矛盾・不足を指摘し、判断が必要な項目を勝手に補完しない
- AIはdomain / services / auth / frontend / infrastructureを含むすべてのレイヤーのテストコード・アプリケーションコード・インフラコードを実装する
- 実装中に仕様変更が必要になった場合は、先に仕様と論理テストケースを更新し、再承認後にコードを変更する
- テストの選定と品質判定には`docs/MINIMUM-TDD-TEST-PRINCIPLES.md`、中心的契約の選定には`docs/CORE-CONTRACT-SELECTION.md`を適用する
- 局所変更（Bounded、不具合修正、リファクタリング、保守）では論理テストケースとTDD計画のファイルを省略できるが、`docs/TDD-WORKFLOW.md`の「局所変更」に従う
- 現在のpurchase CRUDのうち仕様とテストがない既存実装へテストを追加する場合は、`docs/TDD-WORKFLOW.md`のretrofitを適用する

## Commands

### 環境セットアップ

- `bash scripts/setup_host_prerequisites.sh --install` — `bin/mise`でmise 2026.9.12をbootstrapし、uv 0.12.18 / Temurin Java 17を`--jobs=1`で逐次導入した後、uvでPython 3.14.7を導入
- `bash scripts/setup_host_prerequisites.sh --check` — ネットワーク取得を行わず、mise管理のuv / Javaとuv管理のPythonを検証。Windowsネイティブやラッパー／bootstrap前提の欠落は`ENVIRONMENT_FAILURE`
- `./bin/mise exec -- <command>` — Environment Gateのコマンドへリポジトリローカルなmise管理の`PATH`と`JAVA_HOME`を適用。`backend/`からは`../bin/mise`を使用する
- `./bin/mise install` — `mise.toml`にある開発ツール全体を導入（Environment Gateだけなら上記`--install`を使う）
- `pre-commit install` — ローカルのpre-commitフック（backendはruff check/format、frontendはbiome check）を有効化

### Backend（`backend/` から、またはdocker-compose経由）

- `docker-compose up` — API（uvicorn、8000番、`--reload`）とDynamoDB Local（8001番）を起動。`backend/` はbind mountされ、ローカルのコードが正
- `uv run --project backend ruff check --fix`
- `uv run --project backend ruff format`
- `uv run --project backend pytest` — テスト追加後の実行用。単一テストは `uv run --project backend pytest path/to/test.py::test_name`
  - `tests/unit/` — domain / services 中心、モックでテスト
  - `tests/integration/` — DynamoDB Localを使ったmodels層・API結合テスト

### Frontend（`frontend/` から）

- `bun install`
- `bun run dev` — Viteのローカル直起動（frontendはDocker化せず常にローカル起動する方針）
- `bun run build` — `vite build && tsc -b`（TanStack Routerの`src/routeTree.gen.ts`をvite buildで生成してから型検査する）
- `bun run lint` / `bun run format` / `bun run check` — Biome
- `bun run preview`

### E2E（リポジトリ直下 `e2e/`）

テストはソースコードだけを読んで推測で書くのではなく、Playwright MCP（`claude mcp add playwright npx @playwright/mcp@latest`）でClaude Codeが実際にブラウザ操作しながら生成する（frontendの実装がまだ薄くDOM構造が固まっていないため）。事前に `docker-compose up`（backend + DynamoDB Local）と `frontend/` での `bun run dev` を起動しておく必要があり、認証は実際のCognito User Poolに接続するためテスト用ユーザーの認証情報も要る。生成後の `.spec.ts` は通常の `@playwright/test` で実行する（実行用のpackage.json等はe2e/に別途追加）。

### CI

現在はmain pushとPRで次の2つのワークフローが動く。

- `.github/workflows/lint.yml` — backendの `ruff check`/`ruff format --check` とfrontendの `bun run lint`/`bun run format:check`
- `.github/workflows/test.yml` — backendのunit testとfrontendのVitest。frontendはまだテストが無いため `--passWithNoTests` を付けている（テストを書き始めたら外す）

DynamoDB Localを使うintegration testは、`test.yml`のunit testへ混在させない。[テスト実行環境構築計画](docs/todo/test-environment-rollout.md)に従い、Work・Claude Codeと同じMaven Wrapper、POM、Python実行ラッパーを`.github/workflows/integration.yml`から呼び出し、unitとintegrationを別checkとして表示する。Actions固有のサービスコンテナ起動処理は追加しない。E2EはTDD Green後に独立した`e2e.yml`として追加する。

## Architecture

### Backendの層構造（`backend/app/`）

依存は `api → services → domain / models` の一方向のみ。下位層が上位層を知ることはない。

- **api/** — HTTPのリクエスト/レスポンスのみ。ルーティング（`purchase.py`）とPydanticスキーマ（`api/schemas/`）。ビジネスロジックは書かずservicesを呼ぶだけ
- **services/** — 1ユースケース＝1関数のオーケストレーション層。domainのロジックとmodelsの永続化を組み合わせて繋ぐだけで、自身はビジネスルールを持たない（`purchase_service.py`, `notification_service.py`）
- **domain/** — FastAPI/boto3に依存しない純粋なPythonのコアビジネスロジック・エンティティ（`purchase.py`: 消費速度と在庫から補充タイミングを計算する等、`exception.py`: ドメイン例外）。ここが単体テストの主対象
- **models/** — DynamoDBのテーブル定義・読み書きに専念する永続化層。domainエンティティとDBアイテムの変換もここで行う
- **auth/** — Cognito JWT検証（`cognito.py`）。apiのDependsとして横断的に利用
- **core/** — 設定値・クライアント初期化の集約（環境変数やboto3クライアントを他層が直接扱わずに済むように）
- **utils/** — ドメイン知識を含まない汎用処理のみ

### Frontendの構造（`frontend/src/`）

- **api/** — バックエンドへのHTTP通信のみ（fetchラッパー、エンドポイント別関数、レスポンス型）。UIロジックは含めない
- **components/** — 特定の画面・機能に依存しない汎用UIパーツ
- **features/** — 画面・機能単位のまとまり。components/api/hooksを組み合わせて画面を構成
- **hooks/** — 状態管理やAPI呼び出しをラップするカスタムフック（例: `usePurchases`）

### データモデル

コアエンティティは `purchase`: `id`(UUID) / `name` / `category` / `speed`（消費スピード） / `stock`（在庫） / `is_temporary`（定期購入しないもの）。フィールドの詳細と本番インフラ（S3+CloudFront、API Gateway、Lambda(LWA)、ECR、DynamoDB、Cognito、Route53、ACM、Terraform管理）はREADME.md参照。

### 設計上の狙い（実装時に意識すること）

- **型の連動**: backendはDBスキーマ→APIエンドポイントまでを連動させ、frontendは（できれば）backendのOpenAPIからレスポンス型を生成する方針。Pydanticスキーマ（`api/schemas/`）をAPI契約のsource of truthとして扱う
- **本番はコンテナイメージでデプロイ**（ECR→Lambda、LWA経由）するため、`backend/Dockerfile` はdev/prod-build/prodのマルチステージで、devステージはdocker-compose側のbind mountでソースを供給する前提（依存関係のみ先にインストール）
