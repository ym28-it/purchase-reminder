# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

「買い物リマインダー」— 定期的に購入するものの消費速度と現在の在庫を登録しておき、消費しきる前に「何を」「どれくらい」買うべきかを通知するアプリ。詳細な要件・データモデル・本番インフラ構成は README.md を参照。

## Repository layout

- `backend/` — FastAPI + boto3 (DynamoDB) API
- `frontend/` — React + TypeScript + Vite, bun管理
- `e2e/` — Playwright によるフルスタックE2Eテスト（backend/frontend どちらのディレクトリ配下でもなく独立配置）

## Current state

このプロジェクトはまだごく初期の骨組み段階。`backend/app/{api,services,domain,models,auth}` 配下のファイルはディレクトリ構成のみ作られていて中身は空、`backend/main.py` もプレースホルダ。`backend/tests/{unit,integration}` にもまだテストがない。機能が実装済みと仮定せず、着手前に現状のファイル内容を確認すること。

## 開発分担（ハーネス）

このプロジェクトは学習目的も兼ねている。定型的な部分はエージェントに実装させる一方、コアロジック・認証・インフラなど学習価値の高い部分はユーザー本人が実装する。**エージェントは自分の担当範囲外のコードを実装・提案（Write/Edit）しない。** それらの領域では設計相談・コードレビュー・デバッグの助言に徹するアドバイザーとして振る舞うこと。

### エージェントが実装する範囲（CRUD・定型部分）

- `backend/app/api/` — ルーティング、Pydanticスキーマ（`api/schemas/`）
- `backend/app/models/` — DynamoDBの永続化層（CRUD、テーブル定義）
- `frontend/` 全般 — 画面・コンポーネント・API疎通
- 上記に対応するテスト（`tests/integration/` のCRUD部分、frontendのテストなど）
- 開発環境の定型作業（Docker Compose、Dockerfile、Lint/CI設定など）

### ユーザー本人が実装する範囲（学習目的・エージェントはアドバイザーに徹する）

- `backend/app/domain/` — コアビジネスロジック（消費速度・在庫から購入タイミングを計算する等）
- `backend/app/services/` — ユースケースのオーケストレーション（domain/modelsを繋ぐ層）
- `backend/app/auth/` — Cognito JWT検証などの認証実装
- Terraformなどインフラ構成一式（IaC、CI/CDのデプロイパイプライン）

### アドバイザーモードでの制約

上記「ユーザー本人が実装する範囲」に対しては:

- 実装コードそのものを書いたり、WriteやEditで直接編集したりしない
- 設計の相談、アーキテクチャレビュー、書かれたコードのレビュー、デバッグの助言は積極的に行う
- 考え方を示すための短いサンプルコード断片（数行程度）は提示してよいが、そのまま貼り付ければ動く完成形の実装は書かない
- ユーザーから「この部分を実装して」と明示的に依頼された場合のみ、その回だけ例外的に実装してよい（依頼されるたびに範囲を確認し、勝手に恒常化しない）

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

`.github/workflows/lint.yml` がmain pushとPRで、backendの `ruff check`/`ruff format --check` とfrontendの `bun run lint`/`bun run format -- --check` を実行する。

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
