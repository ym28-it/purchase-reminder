# 購入物登録・一覧反映 実装後テストレポート

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `docs/specs/purchase-create.md` (PURC-001〜019) |
| 論理テストケースSSOT | `docs/specs/purchase-create-test-cases.md` |
| 論理テストケースの参照コミット | `3ec240c9ffb1a927318482de883cd1304c811899` |
| TDD計画 | `docs/specs/purchase-create-tdd-plan.md` |
| TDD Greenコミット | `669c726abd03c94426d2614da2b741c81baaf82e` |
| 対象スライス | 一覧の追加操作から、現在利用者への永続化と一覧反映まで |
| 状態 | Draft |
| 確認者 | Pending |
| 確認日 | Pending |

期待結果は承認済み論理Test Case IDをSSOTとし、本レポートでは再定義しない。

## 入力と引き継ぎ

### TDDからの引き継ぎ

| Test Case ID | TDDでの扱い | 実装後に必要な確認 |
|---|---|---|
| PURC-005-TC1, 008-TC1〜3, 009-TC1, 004-TC12 | Backend TDD済み | 維持 |
| PURC-003-TC2 | Backend TDD済み（空白名） | 他の入力境界を補完 |
| PURC-007-TC1, 019-TC2 | Backend TDD済み | 維持 |
| PURC-014-TC7/8 | Backend TDD済み | 通常重複・完全一致規則を補完 |
| PURC-003-TC1 | Frontend TDD済み（空白名） | 他の入力境界を補完 |
| PURC-011-TC1, 012-TC1, 004-TC12 | Frontend TDD済み | 成功後UIと失敗UIを補完 |

### 実装分析で新たに見つかった観点

| ID | 観点 | 種別 | 仕様・Test Case ID上の根拠 | 対応 |
|---|---|---|---|---|
| IMPL-RISK-001 | 更新で名前・カテゴリを変更した後、旧一意性予約が残存しないこと | 状態遷移 / Persistence | PURC-014 の登録一意性を維持する実装上の必要条件 | Integration test |
| IMPL-RISK-002 | 更新先が既存の完全一致ペアの場合も一意性が壊れないこと | 競合 / Persistence | PURC-014 | Integration test |
| IMPL-RISK-003 | 削除後に同じ名前・カテゴリを再登録できること | 状態遷移 / Persistence | PURC-014 の登録一意性を維持する実装上の必要条件 | Integration test |

## 実装した処理フロー

Frontendの登録フォームが5項目を検証してcreate APIを呼び、成功時にQueryをinvalidateして一覧を再取得する。BackendはPydanticで入力制約を検証し、現在利用者IDを依存関係から取得する。DynamoDBでは購入物本体と利用者単位の名前・カテゴリ完全一致予約をトランザクションで作成し、競合を409へ変換する。更新・削除では同予約も追随させる。

## 実装範囲

- Frontend: 登録フォーム検証、成功/失敗状態、一覧再取得・表示
- API: POST /purchases と既存GET/PUT/DELETEとの接続
- Services / Domain: create処理
- Persistence: DynamoDB本体アイテムと一意性予約
- External systems: DynamoDB Local（統合テスト）
- 対象外: Cognito実装、本番AWS、通知、購入時期計算

## 追加した単体・コンポーネントテスト

| Test Case ID / Risk ID | テストレベル | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PURC-001-TC1, 002-TC1/2 | Component | `CreatePurchaseDialog.test.tsx` defaults/fields | 登録開始と5項目・初期値 | Not run |
| PURC-003-TC1, 004-TC4/6/8/10 | Component | invalid field parameterized test | Frontend境界検証 | Not run |
| PURC-010-TC1/2 | Component | success closes and resets | 成功後状態遷移 | Not run |
| PURC-015-TC1, 016-TC1 | Component | duplicate keeps input | 既知失敗の表示と入力維持 | Not run |
| PURC-017-TC1/2, 018-TC1/2 | Component | generic failure/manual retry | 内部情報非表示、自動再送なし、手動再試行 | Not run |

## 統合テスト

| Test Case ID / Risk ID | 接続する境界 | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PURC-003-TC2/3, 004-TC2〜11 | API → DynamoDB Local | `test_purchase_create.py` boundary tests | API境界と非永続化 | Not run |
| PURC-006-TC2 | API → DynamoDB Local | distinct system IDs | システム生成ID | Not run |
| PURC-014-TC1〜6 | API → DynamoDB Local | duplicate/exact-match tests | 完全一致契約 | Not run |
| IMPL-RISK-001〜003 | PUT/DELETE → uniqueness reservation | reservation lifecycle tests | 実装固有の回帰リスク | Not run |

## E2E

| Test Case ID / Risk ID | ユーザーフロー | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PURC-009-TC2, 013-TC2 | ブラウザ→Frontend→API→DynamoDB | Deferred | `e2e/` はREADMEのみでPlaywright実行設定・認証用テストユーザー未整備。推測ベースのE2Eを作らない | Not run |

## 論理テストケースの消化確認

| Test Case ID | 最終的な検証先 | 実テスト・証跡 | 結果 | 対象外理由 |
|---|---|---|---|---|
| PURC-001-TC1 | Component | CreatePurchaseDialog fields/defaults | Not run | |
| PURC-002-TC1/2 | Component | CreatePurchaseDialog fields/defaults | Not run | |
| PURC-003-TC1 | TDD + Component | whitespace TDD + invalid parameterized | Not run | |
| PURC-003-TC2/3 | TDD + Integration | API invalid/missing tests | Not run | |
| PURC-004-TC1〜12 | TDD + Component + Integration | boundary suites | Not run | |
| PURC-005-TC1 | TDD | PURC-TDD-001 | Pass (Green evidence) | |
| PURC-006-TC1 | TDD | PURC-TDD-001 | Pass (Green evidence) | |
| PURC-006-TC2 | Integration | distinct system IDs | Not run | |
| PURC-007-TC1 | TDD | PURC-TDD-005 | Pass (Green evidence) | |
| PURC-008-TC1〜3 | TDD | PURC-TDD-001 | Pass (Green evidence) | |
| PURC-009-TC1 | TDD | PURC-TDD-001 | Pass (Green evidence) | |
| PURC-009-TC2 | E2E | Deferred | Not run | E2E harness/auth fixture未整備 |
| PURC-010-TC1/2 | Component | success closes/resets | Not run | |
| PURC-011-TC1 | TDD | PURC-TDD-002 | Pass (Green evidence) | |
| PURC-012-TC1 | TDD | PURC-TDD-002 | Pass (Green evidence) | |
| PURC-012-TC2/3 | 既存画面 + Component候補 | Purchase表示 | Not run | post-testで追加検証が必要 |
| PURC-012-TC4 | Component候補 | 成功UI | Not run | post-testで追加検証が必要 |
| PURC-013-TC1 | Component候補 | pending button | Not run | post-testで追加検証が必要 |
| PURC-013-TC2 | E2E | Deferred | Not run | E2E harness/auth fixture未整備 |
| PURC-014-TC1〜6 | Integration | duplicate/exact-match tests | Not run | |
| PURC-014-TC7/8 | TDD | PURC-TDD-007/006 | Pass (Green evidence) | |
| PURC-015-TC1 | Component | duplicate keeps input | Not run | |
| PURC-016-TC1 | Component | duplicate message | Not run | |
| PURC-016-TC2 | TDD + Component | field validation | Not run | |
| PURC-017-TC1/2 | Component | generic safe error | Not run | |
| PURC-018-TC1/2 | Component | no auto retry/manual retry | Not run | |
| PURC-019-TC1 | Integration | multi-user list separation via TDD-007 | Pass (Green evidence) | |
| PURC-019-TC2 | TDD | PURC-TDD-005 | Pass (Green evidence) | |

## 全体検証

| 検証 | コマンド | 結果 | 備考 |
|---|---|---|---|
| Backend tests | `uv run pytest -m 'not integration' -q` | Not run | CI/実行環境で実行予定 |
| Frontend tests | `bun run test --run` | Not run | CI/実行環境で実行予定 |
| Integration | DynamoDB Local runner + `pytest -m integration` | Not run | Environment smoke後に実行 |
| E2E | — | Not run | harness/auth fixture未整備 |
| Backend lint / format | `ruff check .` / `ruff format --check .` | Not run | |
| Frontend lint / format | `bun run lint` / `bun run format:check` | Not run | |
| Type check | `bun run build` 内 | Not run | |
| Build | `bun run build` | Not run | |
| Infrastructure validation | Environment smoke | Not run | |

## 未実行・残存リスク

| 項目 | 理由 | 影響 | 後続対応 |
|---|---|---|---|
| 実装後テストの実行 | このGitHub編集コンテキストには任意コマンド実行環境がない | 追加テストのGreenは未確認 | PR CIおよび実行可能なWork環境で検証 |
| PURC-009-TC2 / 013-TC2 E2E | Playwright harnessと認証fixture未整備 | ブラウザからDBまでの完全経路は未検証 | E2E基盤整備後に実施 |
| PURC-012-TC2/3/4, 013-TC1 | 追加テスト未実装 | UI表示・pending状態の一部が未検証 | 同PRで追加するかCompletion Gateで差し戻し |

## Slice Complete Gate

- [x] 実装した垂直スライスの開始点から終了点をテスト設計上追跡した
- [x] 論理テストケースの参照コミットを記録した
- [x] すべての論理Test Case IDに検証先またはDeferred理由を割り当てた
- [ ] Criticalな未カバー箇所が残っていないことを実行で確認した
- [x] Importantな実装固有リスクにテストを追加した
- [ ] 必要な単体・コンポーネント・統合・E2Eを実行した
- [ ] 全体回帰、Lint、型チェック、ビルドを確認した
- [x] 未実行の検証と残存リスクを明示した
- [x] 仕様・論理テストケースは変更していない
- [ ] 人間がテスト内容、実行結果、対象外理由、残存リスクを確認した
