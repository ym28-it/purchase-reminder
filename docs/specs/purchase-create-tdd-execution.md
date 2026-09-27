# 購入物登録 TDDテスト作成記録

## 対象と開始条件

- 対象: `ym28-it/purchase-reminder` の `main`、開始HEAD `0c0fee2d9bf99de7257dfc3d8c84ddfc628b261f`。作業ツリーは開始時クリーン。
- `docs/specs/purchase-create-cycle-state.md`: `READY`。記載の開始時Base SHAは `e4f834025fc50d94ee76d8d2035655dad8ecbc4d`。本テスト作成の分岐元は、その状態ファイルがmainへマージされた上記HEAD。
- 2026-09-27の利用者指示「購入物登録のTDD開始」により開始。Environment、Specification、Logical Test Case、Core Contract、Test Planの承認とBlocking 0件を確認。
- 承認済み期待結果: `docs/specs/purchase-create-test-cases.md`。最小7項目: `docs/specs/purchase-create-tdd-plan.md`。

## 環境と変更前Baseline

リポジトリ所定の `bash scripts/setup_host_prerequisites.sh --install` と `--check` を実行。mise 2026.9.12、uv 0.12.18、Python 3.14.7、Temurin Java 17.0.20.1、DynamoDB Local 3.3.1、Bun 1.4.2。Backend `uv sync --python 3.14.7 --frozen`、Frontend `bun install --frozen-lockfile` に成功。

| コマンド（各ディレクトリから、子コマンドも `bin/mise exec --` 経由） | 終了コード | 結果 |
|---|---:|---|
| Backend `uv run pytest -m 'not integration' -q` | 0 | 72 passed、16 deselected（追加前） |
| Backend `uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q` | 0 | API ready PASS、16 passed、72 deselected、子プロセス正常停止 |
| Frontend `bun run test --run --passWithNoTests` | 0 | 既存テスト0件 |
| Frontend `bun run lint` / `bun run format:check` | 0 / 0 | 既存チェック成功 |

環境スモークは新機能テスト追加より前に通過した。テスト実行時にもrunnerのAPI readyを確認した。

## 承認済み7項目の結果

| Plan ID | 実テスト | 結果 | 失敗した契約またはRed例外 |
|---|---|---|---|
| PURC-TDD-001 | `test_purc_tdd_001_create_zero_speed_and_reload_from_storage` | Red | POST `speed=0` が422（期待201）。収集・DynamoDB Local設定後の応答アサーション。 |
| PURC-TDD-002 | `Purchase.test.tsx` | Red | 有効な `speed=0` の画面登録で `createPurchase` が呼ばれない。レンダリング・操作後のアサーション。後続の再取得・表示アサーションはGreen時に到達する。 |
| PURC-TDD-003 | `CreatePurchaseDialog.test.tsx` | Red | 空白だけの名前で項目エラーが表示されない。レンダリング・操作後のアサーション。 |
| PURC-TDD-004 | `test_purc_tdd_004_whitespace_name_is_rejected_without_storage` | Red | 空白だけの名前が201（期待422）。収集・DynamoDB Local設定後の応答アサーション。後続で永続化なしも確認する。 |
| PURC-TDD-005 | `test_purc_tdd_005_client_user_id_cannot_change_owner` | Green（承認済みRed例外） | 別の利用者IDを混入しても現在利用者へ保存され、別利用者のGETは空。変更前コードで実証。 |
| PURC-TDD-006 | `test_purc_tdd_006_concurrent_identical_creates_leave_one_item` | Red | 同時要求4件すべて201（期待1件201と3件409）。収集・DynamoDB Local設定後の応答アサーション。 |
| PURC-TDD-007 | `test_purc_tdd_007_identical_names_are_allowed_for_different_users` | Green（承認済みRed例外） | 利用者A/Bそれぞれ201、各自の一覧は自分のIDのみ。変更前コードで実証。 |

実行コマンド:

- Backend (`backend/`): `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/api/test_purchase_create.py -q` → 終了1、3 failed / 2 passed。API ready PASS、runnerの子終了1、Java停止確認。
- Frontend (`frontend/`): `../bin/mise exec -- bun run test --run src/features/Purchase.test.tsx src/features/CreatePurchaseDialog.test.tsx --reporter=dot` → 終了1、2 failed / 0 passed。失敗位置は各テストの契約アサーション。

## 追加後のBaselineチェック

- Backend `../bin/mise exec -- uv run pytest -m 'not integration' -q` → 終了0、72 passed / 21 deselected。
- Backend `../bin/mise exec -- uv run ruff check .`、`ruff format --check .` → ともに終了0。
- Frontend `../bin/mise exec -- bun run lint`、`bun run format:check` → ともに終了0。
- Frontendのbuildは、TDD計画GAP-003の既知の `routeTree.gen` 不足があり、今回のRed判定には利用していない。

## 引き継ぎ差分

凍結候補のテストパス: `backend/tests/integration/api/test_purchase_create.py`、`frontend/src/features/Purchase.test.tsx`、`frontend/src/features/CreatePurchaseDialog.test.tsx`。BackendのTestClient用に `backend/pyproject.toml` と `backend/uv.lock` へ開発用 `httpx` を追加。その他は本記録のみ。プロダクトコード、承認済み期待結果・仕様・計画は変更していない。commit、push、PR作成は行っていない。

この記録はテスト担当からオーケストレーターへの証跡であり、担当者自身による `RED_VALIDATED` 宣言ではない。

## 実装担当からのGreen実行記録（2026-09-27）

- 入力: draft PR #29 `f5643cbf787cedc58ea715bd3dab4be627f6502c`。Red Gate判定記録 `3c2dc1489b0d6e7c883bc3e957500d3fb20e582b` を実装ブランチへ取り込み、状態 `RED_VALIDATED` を確認した。
- プロダクト実装コミット: `c5c50981aee7d06c732dd51edf3c0ff0a22a86d4`。変更範囲はBackend登録入力スキーマとDynamoDBの一意性確保、Frontend登録フォーム・一覧表示・API呼び出し。名前とカテゴリの文字列は保存時に変更しない。
- 凍結テスト3ファイルは `git diff f5643cb -- backend/tests/integration/api/test_purchase_create.py frontend/src/features/Purchase.test.tsx frontend/src/features/CreatePurchaseDialog.test.tsx` で差分なし。仕様・論理テストケース・TDD計画も変更なし。

| 実行（各ディレクトリから `../bin/mise exec --`） | 終了コード | 結果 |
|---|---:|---|
| Backend `uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/api/test_purchase_create.py -q --tb=short` | 0 | API ready PASS、TDD 5 passed、Java正常停止 |
| Frontend `bun run test --run src/features/Purchase.test.tsx src/features/CreatePurchaseDialog.test.tsx --reporter=dot` | 0 | TDD 2 passed |
| Backend `uv run pytest -m 'not integration' -q` | 0 | 72 passed、21 deselected |
| Backend `uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q --tb=short` | 0 | API ready PASS、21 passed、72 deselected、Java正常停止 |
| Backend `uv run ruff check .` / `uv run ruff format --check .` | 0 / 0 | 全対象成功 |
| Frontend `bun run lint` / `bun run build` | 0 / 0 | lint、TypeScriptチェック、Vite build成功。`routeTree.gen` はビルド時に生成された |
| Frontend `bunx biome format src/features/CreatePurchaseDialog.tsx src/features/Purchase.tsx src/hooks/usePurchases.ts` | 0 | 変更したプロダクト3ファイル成功 |
| Frontend `bun run format:check` | 1 | PR #29で凍結された `src/features/CreatePurchaseDialog.test.tsx` の既存の1行に整形差分。プロダクト2ファイルの整形は修正済み。凍結テストは実装担当の変更境界により未変更 |

上記は実装担当のGreen証跡であり、Automated Green Gateの判定や `TDD_GREEN` への状態遷移ではない。全体formatの例外はオーケストレーター／テスト担当へ差し戻す。実装後テストと完了判定は未実施。

## PR #29の整形修正後の再検証（2026-09-27）

- PR #29の新しいhead: `15e48f6f4339874d8636b9659f58f7dd52825c10`。追加コミットは `frontend/src/features/CreatePurchaseDialog.test.tsx` のアサーションを変えない整形だけ。PR #30の実装内容にこのテスト版を取り込み、上記のformat例外が解消した。
- 対象実装: `c5c50981aee7d06c732dd51edf3c0ff0a22a86d4`。PR #29の新headとPR #30の旧headを親とする統合コミット: `1cb12a90fc903da0b0ca7f8172791deb2870a660`。この版で以下を実行した。

| 実行（各ディレクトリから `../bin/mise exec --`） | 終了コード | 結果 |
|---|---:|---|
| Backend `uv run pytest -m 'not integration' -q` | 0 | 72 passed、21 deselected |
| Backend `uv run ruff check .` / `uv run ruff format --check .` | 0 / 0 | 全対象成功 |
| Backend `uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q --tb=short` | 0 | API ready PASS、21 passed（対象TDD 5件を含む）、72 deselected、Java正常停止 |
| Frontend `bun run test --run src/features/Purchase.test.tsx src/features/CreatePurchaseDialog.test.tsx --reporter=dot` | 0 | 対象TDD 2 passed |
| Frontend `bun run lint` / `bun run format:check` / `bun run build` | 0 / 0 / 0 | 全体lint・format、TypeScriptチェック、Vite build成功 |

前節のformat失敗は修正前コミットに対する履歴。実装担当は修正版の凍結テストを変更せず受け取り、Green Gate判定はオーケストレーターに委ねる。
