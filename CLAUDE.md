# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

「買い物リマインダー」— 定期的に購入するものの消費速度と現在の在庫を登録しておき、消費しきる前に「何を」「どれくらい」買うべきかを通知するアプリ。詳細な要件・データモデル・本番インフラ構成は README.md を参照。

## Repository layout

- `backend/` — FastAPI + boto3 (DynamoDB) API
- `frontend/` — React + TypeScript + Vite, bun管理
- `e2e/` — Playwright によるフルスタックE2Eテスト（backend/frontend どちらのディレクトリ配下でもなく独立配置）

## Current state

ローカル環境では、FastAPI + DynamoDB Localの購入物CRUD（一覧・登録・更新・削除）と、それを操作するReact画面まで実装済み。DynamoDBの汎用モデル基盤には単体テストがあるが、purchase CRUD、services、API、frontendのテストは未整備。Cognito認証、購入タイミングのドメインロジック、通知、Terraform、デプロイ、E2Eは未実装。着手前に実際のファイルとCI結果を確認し、この記述よりコードを優先して現在地を判断すること。

### 現在の優先作業: テスト環境構築

購入物登録の機能TDDを開始する前に、[テスト実行環境構築計画](docs/todo/test-environment-rollout.md)のStep 1〜3を実装し、Work Environment Gateを通過させる。計画書をこの作業のsource of truthとし、Environment Gateが人間に承認されるまで購入物登録の機能テストとプロダクトコードを変更しない。

この作業は、Claude Codeでは`/setup-test-environment`、対応するWork環境では`$setup-test-environment` Skillを明示的に呼び出して開始する。Skillは環境構築と検証だけを担当し、Environment Gate通過後も人間の承認なしに機能TDDへ進まない。

## 開発分担（仕様駆動）

このプロジェクトでは、実装レイヤーごとに人間とAIの担当を分けない。人間とAIが共同でMarkdown形式の仕様を確定し、AIがその仕様を根拠として、すべてのテストコード・アプリケーションコード・インフラコードを実装する。

### 基本原則

- 機能仕様は `docs/specs/<feature-slug>.md` をsource of truthとする
- 人間とAIが仕様を共同作成し、人間が最終承認する
- AIは仕様の曖昧さ・矛盾・不足を指摘し、判断が必要な項目を勝手に補完しない
- 仕様書の「確認事項」が解消されるまで、AIはその機能のテスト・実装を開始しない
- AIは承認済み仕様から論理テストケースを作成し、人間の確認後にテストコードへ翻訳する
- AIはdomain / services / auth / frontend / infrastructureを含む、すべてのレイヤーを実装する
- 人間は実装コードを直接担当するのではなく、仕様・論理テストケース・テスト結果を通じて実装を検証する
- 実装中に仕様変更が必要になった場合は、先にMarkdown仕様と論理テストケースを更新し、再承認後にコードを変更する

### 役割

- **人間**
  - 機能の目的・要求・制約を提示する
  - AIとともに仕様を決め、Markdownの内容を最終承認する
  - 論理テストケースを確認し、期待する振る舞いを承認する
  - テスト内容と実行結果を通じて、実装が仕様に適合しているか最終判断する
- **AI**
  - 仕様書のたたき台を作成し、曖昧さ・矛盾・不足を確認事項として提示する
  - 承認済み仕様と対応する論理テストケースを作成する
  - テストコード、アプリケーションコード、認証、インフラ、CI/CDを含む全コードを実装する
  - lint・型チェック・単体テスト・統合テスト・E2E・ビルドを実行し、結果を報告する
  - 失敗を実装のバグと仕様理解の相違に分類し、仕様を無断で実装へ合わせない

## テスト・開発フロー

0→1開発と新しいユーザー価値を追加する機能開発は `docs/VERTICAL-SLICE-DEVELOPMENT-WORKFLOW.md` に従い、最小垂直スライスとして、仕様作成から実装後テスト・統合テスト・E2E・全体検証までを1サイクルで完了する。フロントエンド全体を先に作り、その後でバックエンド全体を作るような大規模な水平分割は行わない。

垂直スライスは全レイヤーのコード変更を要求しない。既存APIなどを利用してユーザー価値が完成する場合は、フロントエンドだけのコード変更でもよい。部分的な不具合修正、外部挙動を変えないリファクタリング、UI改善、テスト・依存関係・CI・インフラ・文書の保守では、影響範囲内で独立して検証可能な最小変更を単位とし、関係のないレイヤーの変更やテストを要求しない。

実装前の最小TDDには `docs/TDD-WORKFLOW.md` を適用する。TDD Greenは機能全体のテスト完了ではなく、その後に実装後テスト分析へ進む。

テストの選定と品質判定には `docs/MINIMUM-TDD-TEST-PRINCIPLES.md` を必ず適用し、論理テストケースと実行証跡は `docs/templates/minimum-tdd-test-plan.md` を基に記録する。

実装後のカバレッジ分析、追加単体テスト、統合テスト、E2E、全体検証は `docs/templates/post-implementation-test-report.md` を基に記録する。

このプロジェクトでの適用時の補足:

- 仕様ファイルの置き場所: `docs/specs/<feature-slug>.md`（新規機能）
- 論理テストケースファイルの置き場所: `docs/specs/<feature-slug>-test-cases.md`
- 実装前TDD計画: `docs/specs/<feature-slug>-test-plan.md`
- 実装後テストレポート: `docs/specs/<feature-slug>-post-test-report.md`
- 現在のpurchase CRUDは仕様書と機能テストがない既存実装なので、最初の整備ではTDD-WORKFLOW.mdのケースBを適用する
- 実装コードとテストコードはレイヤーを問わずAIが担当する。人間は仕様・論理テストケース・テスト結果を確認し、実装が仕様に適合しているかを最終判断する

## Commands

### 環境セットアップ

- `mise install` — `.mise.toml` で固定された python 3.14 / uv / bun / terraform を導入
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
- `bun run build` — `tsc -b && vite build`
- `bun run lint` / `bun run format` / `bun run check` — Biome
- `bun run preview`

### E2E（リポジトリ直下 `e2e/`）

テストはソースコードだけを読んで推測で書くのではなく、Playwright MCP（`claude mcp add playwright npx @playwright/mcp@latest`）でClaude Codeが実際にブラウザ操作しながら生成する（frontendの実装がまだ薄くDOM構造が固まっていないため）。事前に `docker-compose up`（backend + DynamoDB Local）と `frontend/` での `bun run dev` を起動しておく必要があり、認証は実際のCognito User Poolに接続するためテスト用ユーザーの認証情報も要る。生成後の `.spec.ts` は通常の `@playwright/test` で実行する（実行用のpackage.json等はe2e/に別途追加）。

### CI

現在はmain pushとPRで次の2つのワークフローが動く。

- `.github/workflows/lint.yml` — backendの `ruff check`/`ruff format --check` とfrontendの `bun run lint`/`bun run format:check`
- `.github/workflows/test.yml` — backendのunit testとfrontendのVitest。frontendはまだテストが無いため `--passWithNoTests` を付けている（テストを書き始めたら外す）

DynamoDB Localを使うintegration testは、`test.yml`のunit testへ混在させない。[テスト実行環境構築計画](docs/todo/test-environment-rollout.md)に従い、Workと同じJava/JAR実行ラッパーを`.github/workflows/integration.yml`から呼び出し、unitとintegrationを別checkとして表示する。Actions固有のサービスコンテナ起動処理は追加しない。E2EはTDD Green後に独立した`e2e.yml`として追加する。

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
