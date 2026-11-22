# 購入物編集の項目と検証（PEDT） 実装後テストレポート

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `docs/superpowers/specs/2026-11-22-purchase-edit-fields-design.md`（PEDT-001〜010） |
| 論理テストケースSSOT | `docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md` |
| 論理テストケースの参照コミット | `90f68f9` |
| TDD計画 | `docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md` |
| TDD Greenコミット | `92bed1f`（Backend Green）、`ef4924f`（Frontend Green） |
| 対象スライス | 編集ダイアログの全7項目 → `PUT /purchases/{id}`（登録と同じ検証）→ DynamoDB（`unit`・`buffer_days`の永続化、`stock_counted_at`は在庫変更時のみ更新）→ 一覧表示 |
| 状態 | Draft |
| 確認者 | （人間の確認待ち） |
| 確認日 | - |

論理テストケースの期待結果をこの文書で再定義しない。期待結果はTest Case IDを通じてSSOTを参照する。検証対象の実装SHAは`b248568`（プロダクトコードは`ef4924f`以降、本タスクで変更していない）。

## 入力と引き継ぎ

### TDDからの引き継ぎ

| Test Case ID | TDDでの扱い | 実装後に必要な確認 |
|---|---|---|
| PEDT-001-TC3 | 候補外 | 受け取らない項目と`speed`の無視（Integration） |
| PEDT-006-TC4 | 候補外 | 在庫を変えない複数項目の同時変更（Integration） |
| PEDT-007-TC3 | 候補外 | 項目名・説明から日数・購入単位の意味を読み取れる（Component） |
| PEDT-008-TC3 | 候補外 | 入力エラーの解除後に保存できる（Component） |
| PEDT-009-TC3 | 候補外 | 存在しないIDの編集が404で何も作成されない（Integration） |
| PEDT-009-TC4 | 候補外（既存テスト） | 書き直し後の`test_purchase_uniqueness_rev2.py`が維持されている |
| PEDT-009-TC5 | 候補外（既存テスト） | 書き直し後のPURC-024テスト群が7項目入力でGreen |
| PEDT-010-TC2 | 候補外（既存テスト） | 編集済み購入物の削除と再登録を確認 |
| PEDT-001-TC2（名前・カテゴリ・日数・在庫の欠落） | TDD契約に含めきれなかった部分 | 4項目の欠落を項目ごとに422（Integration） |
| PEDT-002-TC1/TC2/TC3のうちTDDで扱わなかった値、登録との一致 | TDD契約に含めきれなかった部分 | 値表の全行で編集と登録が同じ判定（Integration、Component） |
| 上記以外（TDD計画の最小セット15行） | TDD済み | Green記録のとおり維持されていること（全体回帰で確認） |

### 実装分析で新たに見つかった観点

| ID | 観点 | 種別 | 仕様・Test Case ID上の根拠 | 対応 |
|---|---|---|---|---|
| IMPL-RISK-001 | 以前のPUTで保存された小数の在庫（例: 1.5）の購入物を編集ダイアログで開く（実装計画Review Focus 1） | 境界 | PEDT-008-TC1（在庫の小数は入力エラー） | Add test（Component）。保存済みの値を表示し、整数へ直すまで送信しない |
| IMPL-RISK-002 | 数値欄を空にした保存で`NaN`や0を送らない（Review Focus 3） | 境界 | PEDT-008-TC1（入力エラー、送信なし） | Add test（Component、日数・余裕日数・在庫） |
| IMPL-RISK-003 | PUTを呼ぶ他のコード・E2E・手順書が旧形式のまま残っていない（Review Focus 2） | 接続 | PEDT-001（7項目すべて必須） | 検証済み（下記「Review Focusの消化」） |
| IMPL-RISK-004 | 保存済みの在庫（`Decimal`由来）と、PUTの整数の在庫が同値のとき`stock_counted_at`が更新されない（Review Focus 4） | 状態遷移 | PEDT-006-TC2/TC3/TC4 | 既存の整数側テストを維持し、名前を整理（Add test） |
| IMPL-RISK-005 | 再試行が起きても、`unit`・`buffer_days`の最新の編集内容が失われず、`created_at`が上書きされない（Review Focus 5） | 状態遷移 | PEDT-001-TC1、PEDT-005-TC1 | Add test（Integration、競合の差し込み） |
| IMPL-RISK-006 | 編集後の拒否（409）で、既存の購入物Aが変わらない。単位だけの編集がDynamoDB上の項目に保存される | 永続化 | PEDT-009-TC1、TC2 | Add test（Integration、凍結テストはレスポンスと編集対象のみを確認） |

いずれも新しい利用者向けの期待結果を追加していない。

## 実装した処理フロー

編集ダイアログ（`EditPurchaseDialog.tsx`）が、保存済みの7項目を初期値として表示し、登録ダイアログと共有する`purchaseFormSchema`（`purchaseFormSchema.ts`）で検証する。有効なら7項目を`PUT /purchases/{id}`（`PurchasePutRequest`、登録と共通の`PurchaseWriteRequest`を継承）で送る。`purchase_service.put_purchase`が`apply_edit`で7項目をすべて引数の値で置き換え、`created_at`を引き継ぎ、在庫が変わったときだけ`stock_counted_at`を更新して、DynamoDBへ条件付きで書き込む（名前・カテゴリの重複は409、存在しないIDは404）。保存後にダイアログを閉じ、一覧を再取得して購入単位・余裕日数などを表示する。

## 実装範囲

- Frontend: `EditPurchaseDialog.tsx`（購入単位・余裕日数の入力欄、7項目の送信）、`purchaseFormSchema.ts`（登録・編集の共有検証）、`CreatePurchaseDialog.tsx`（共有検証への切り替え）、`schema.d.ts`の再生成
- API: `PurchaseWriteRequest`基底スキーマ、`PUT /purchases/{id}`
- Services / Domain: `put_purchase`、`apply_edit`
- Persistence: 既存の`models/purchase.py`（変更なし）
- External systems: なし
- 対象外: PATCH、既存データの移行、購入タイミングの計算、編集ダイアログの失敗表示（422・409）の仕様化

## カバレッジ

### 実行条件

- Backend: `backend/`で`DYNAMODB_LOCAL_PORT=18001 ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q --cov=app --cov-branch --cov-report=term-missing`（統合テスト全件に対するカバレッジ。unitは別実行のため含まない）
- Frontend: `frontend/`で`bun run test -- --run --coverage --coverage.provider=v8 --coverage.include='src/features/**' --coverage.include='src/api/**' --coverage.include='src/hooks/**'`（`@vitest/coverage-v8`は導入済み。生成された`coverage/`は削除済み）
- ツール: pytest-cov 7.1.0（coverage 7.16.2）、Vitest v8

### 結果

| 対象 | Line | Branch | 備考 |
|---|---:|---:|---|
| Backend `app/` 全体（integration実行） | 86%（408 stmts中58未カバー） | 部分分岐18（branch 90） | 統合テストのみの測定。ツールのTOTAL（line+branch合算）は80% |
| `app/api/purchase.py`、`app/api/schemas/purchase.py`、`app/domain/purchase.py`、`app/services/purchase_service.py` | 100% | 100% | 今回の変更の中心。未カバーなし |
| `app/models/purchase.py` | 93% | - | 未カバー: 97、140、270、295（後述） |
| Frontend 対象全体 | 89.28% | 83.5% | features / api / hooks |
| `EditPurchaseDialog.tsx` | 87.5%（Stmts）/ 100%（Lines） | 85% | 未カバー: 48、150-156（後述） |
| `purchaseFormSchema.ts` | 測定対象外（`--coverage.include`に含めていない） | - | 登録・編集の全コンポーネントテストから実行される。値表の全行を`Purchase.edit*.test.tsx`が通す |

カバレッジ率は未検証箇所の発見に使用し、数値だけを完了条件にしない。

## 未カバー箇所の評価

| ID | 箇所・契約 | 分類 | リスク | 対応 | 仕様・Test Case ID上の根拠 |
|---|---|---|---|---|---|
| GAP-001 | `EditPurchaseDialog.tsx` 150-156（保存失敗時の「更新に失敗しました」表示、保存中の「更新中...」） | Specification gap（既知。PEDTが仕様化していない） | 現状の挙動を変えていない。期待結果を一意に導けない | Justified（仕様化は別スライス。推測でテストしない） | 論理テストケース§9、TDD計画の対象外 |
| GAP-002 | `EditPurchaseDialog.tsx` 48（`purchase`が`null`のときの送信ガード） | Unreachable | ダイアログが閉じている間はフォームが表示されない | Justified | - |
| GAP-003 | `models/purchase.py` 97、140、270、295（重複以外の`ClientError`の再送出、`TransactionCanceled`以外のエラー分岐） | Low risk | 変更していない既存コード。DynamoDB Localで再現が難しい障害経路 | Justified | PEDT-009（既存の振る舞いの維持） |
| GAP-004 | `models/keys.py`、`serialization.py`、`table.py` の一部 | Low risk | 今回変更していない。unit側（`tests/unit/models/`）で保護 | Justified | - |
| GAP-005 | `api/purchases.ts` 40-43（`deletePurchase`のエラー分岐） | Low risk | 削除は今回の変更対象外 | Justified | - |

Criticalな未カバー箇所はない。

## 追加した単体・コンポーネントテスト

すべて`frontend/src/features/Purchase.edit.post.test.tsx`（新規、`test.each`の行を含めて20件）。

| Test Case ID / Risk ID | テストレベル | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PEDT-007-TC3 | Component | `PEDT-007-TC3: labels explain unit, days, buffer days and stock` | 候補外の引き継ぎ（編集ダイアログのラベルが日数・購入単位の意味を示す。文言は固定せず意味の語で確認） | Pass |
| PEDT-008-TC1（残りの行） | Component | `PEDT-008-TC1: the remaining invalid values ...`（名前・カテゴリの空・空白・U+3000・51文字、購入単位11文字、負数の日数・余裕日数・在庫の12行） | TDDの凍結テストに含まれない行（特に負数）の補完。登録ダイアログの同種テストと同じ値 | Pass |
| PEDT-008-TC2（コードポイント境界） | Component | `PEDT-008-TC2: boundary text lengths count code points` | 𠮷×50/30/10文字が受理される（コードポイント単位） | Pass |
| PEDT-008-TC3 | Component | `PEDT-008-TC3: an input error clears once the value is fixed` | 候補外の引き継ぎ | Pass |
| IMPL-RISK-002（Review Focus 3） | Component | `PEDT Review Focus 3: an emptied numeric field ...`（日数・余裕日数・在庫） | 空欄を`NaN`・0で送らない | Pass |
| IMPL-RISK-001（Review Focus 1） | Component | `PEDT Review Focus 1: a stale non-integer saved value` | 保存済みの在庫1.5を表示、エラーで送信せず、整数へ直せば保存 | Pass |
| PEDT-007-TC4 / PEDT-001（一時的な購入） | Component | `the temporary flag is edited and sent` | 一時的な購入を変更して7項目が送られる | Pass |

## 統合テスト

すべて`backend/tests/integration/api/test_purchase_edit_fields_post.py`（新規）。`test_purchase_ptf_post.py`は整理と1件追加。

| Test Case ID / Risk ID | 接続する境界 | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PEDT-001-TC2（名前・カテゴリ・日数・在庫の欠落） | API → スキーマ検証 → 永続状態 | `test_pedt_001_tc2_missing_name_category_days_or_stock_is_rejected`（4件） | TDDに含めきれなかった4項目の欠落が422で、保存済みが変わらない | Pass |
| PEDT-001-TC3 | API → 編集の適用 → DynamoDB | `test_pedt_001_tc3_server_owned_fields_and_legacy_speed_are_ignored` | 受け取らない項目と`speed`が無視され、`id`・`created_at`・`stock_counted_at`が変わらず、`speed`が保存・返却されない | Pass |
| PEDT-002-TC2 | API（編集と登録） | `test_pedt_002_tc2_edit_and_registration_reject_the_same_values`（26件） | 値表の全行（名前・カテゴリの空文字・負数を含む）で編集と登録がともに422で、対象項目を識別できる | Pass |
| PEDT-002-TC1 | API（編集と登録） | `test_pedt_002_tc1_edit_and_registration_accept_the_same_boundaries`（9件） | 境界値を編集と登録のどちらも受理し、入力どおり保存する | Pass |
| PEDT-002-TC3 | API → DynamoDB | `test_pedt_002_tc3_padded_name_is_stored_as_is_and_is_a_distinct_pair` | 名前の前後空白を保持し、`牛乳`とは別の組になる（登録でも` 牛乳 `は409） | Pass |
| PEDT-006-TC4 | API → 編集の適用 | `test_pedt_006_tc4_multi_field_edit_without_stock_change_keeps_stock_counted_at` | 在庫を変えない複数項目の変更で`stock_counted_at`が変わらない | Pass |
| PEDT-009-TC3 | API → サービス | `test_pedt_009_tc3_edit_of_unknown_id_is_404_and_creates_nothing` | 存在しないIDが404で何も作られない | Pass |
| PEDT-009-TC2（永続化）、IMPL-RISK-006 | API → DynamoDB | `test_pedt_009_tc2_unit_only_edit_is_persisted_in_storage` | 凍結テストはレスポンスのみを確認するため、保存された項目の`unit`を確認 | Pass |
| PEDT-009-TC1、IMPL-RISK-006 | API → DynamoDB | `test_pedt_009_tc1_rejected_rename_leaves_the_other_purchase_unchanged` | 凍結テストは編集対象のBのみ確認するため、既存のAが変わらないことを確認 | Pass |
| PEDT-009-TC4 | API | `test_pedt_009_tc4_pre_edit_pair_can_be_registered_after_multi_field_edit` | 複数項目の編集後も編集前の組を登録できる（既存テストの補完） | Pass |
| PEDT-010-TC2 | API | `test_pedt_010_tc2_edited_purchase_can_be_deleted_and_pair_registered_again` | 既存の削除テストは編集を経ないため、編集済み購入物の削除と再登録を確認 | Pass |
| IMPL-RISK-005（Review Focus 5） | API → DynamoDB（競合の差し込み） | `test_purchase_ptf_post.py::test_pedt_review_focus_5_retried_edit_keeps_latest_unit_buffer_and_created_at` | 再試行後も`unit`・`buffer_days`・`is_temporary`が最新の編集内容で、`created_at`・`stock_counted_at`が保たれる | Pass |
| IMPL-RISK-004（Review Focus 4） | API → DynamoDB | `test_purchase_ptf_post.py::test_review_focus_5_same_integer_stock_does_not_update_stock_counted_at` | 単一値の`parametrize([2])`と`2.0`を含む古い名前を整理（期待は変更なし） | Pass |

## E2E

| Test Case ID / Risk ID | ユーザーフロー | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PEDT-007-TC4、PEDT-005-TC1、PEDT-006-TC2 | 登録 → 一覧 → 編集ダイアログで購入単位と余裕日数を変更 → 一覧に反映 → リロード後も反映 → APIで永続状態、`created_at`・`stock_counted_at`不変を確認 | `e2e/tests/purchase-edit.spec.ts` | UIから永続化までの主要正常系を実環境で1件確認する（境界値は下位のテストと重複させない） | Pass |

既存の`purchase-create.spec.ts`（2件）もPass。PUTを呼ぶ他のE2Eはない。

各表では前提、操作、期待結果を再記述せず、論理Test Case IDまたは根拠を記録した実装リスクIDを参照する。

## Review Focusの消化

| # | 項目 | 消化方法 | 結果 |
|---|---|---|---|
| 1 | 古い非整数の保存値を編集ダイアログで開く | Componentテスト（IMPL-RISK-001） | Pass |
| 2 | 全項目を送らない古いPUT呼び出し元 | `grep -rnE "PUT\|\.put\(\|usePutPurchase\|putPurchase\|method: \"PUT\"" e2e frontend/src backend/app README.md docs/specs`（テスト・生成型を除く）を実行。製品側の呼び出し元は`frontend/src/api/purchases.ts`の`putPurchase`→`usePutPurchase`→`EditPurchaseDialog.tsx`のみで、7項目を送る。`e2e/`・`README.md`に`purchases`のPUT記述はなく、`docs/specs/purchase-create-tdd-execution.md`の記述は設計記録であり手順書ではない。E2E（`purchase-create.spec.ts`、`purchase-edit.spec.ts`）がPass | Pass |
| 3 | 空欄の数値入力 | Componentテスト（IMPL-RISK-002） | Pass |
| 4 | `stock_counted_at`の比較型 | 整数の在庫`2`のままの編集（`test_review_focus_5_same_integer_stock_...`、`test_pedt_006_tc4_*`、`test_pedt_tdd_008_*`）がGreen | Pass |
| 5 | 全項目が変わる同時編集 | 競合差し込みテスト（IMPL-RISK-005）。既存の再試行テスト（`test_review_focus_3_*`、`test_purc_024_*`）も7項目の入力でGreen | Pass |

## 論理テストケースの消化確認

TDD = 凍結済みの`test_purchase_edit_fields.py`（`te`）、`Purchase.edit.test.tsx`、`Purchase.ptf.post.test.tsx`のPEDT-010-TC1。post = `test_purchase_edit_fields_post.py`（`pe-post`）、`Purchase.edit.post.test.tsx`（`fe-post`）。

| Test Case ID | 最終的な検証先 | 実テスト・証跡 | 結果 | 対象外理由 |
|---|---|---|---|---|
| PEDT-001-TC1 | TDD | `te::test_pedt_tdd_001_*` | Pass | |
| PEDT-001-TC2 | TDD + Integration | `te::test_pedt_tdd_002_*`（unit、buffer_days、is_temporary）+ `pe-post::..._missing_name_category_days_or_stock_...`（4件） | Pass | 項目の分担 |
| PEDT-001-TC3 | Integration | `pe-post::test_pedt_001_tc3_*` | Pass | |
| PEDT-002-TC1 | TDD + Integration + Component | `te::test_pedt_tdd_005_*`・`_007_*`、`pe-post::..._accept_the_same_boundaries`（登録との一致）、`fe-post`のコードポイント境界 | Pass | TDDは編集のみ、postは登録との一致を追加 |
| PEDT-002-TC2 | TDD + Integration | `te::test_pedt_tdd_004_*`・`_006_*`、`pe-post::..._reject_the_same_values`（26件、空文字・負数を追加、登録との一致） | Pass | |
| PEDT-002-TC3 | TDD + Integration | `te::test_pedt_tdd_007_*`（購入単位）、`pe-post::test_pedt_002_tc3_*`（名前と別の組） | Pass | |
| PEDT-003-TC1 | TDD | `te::test_pedt_tdd_005_*`（日数0、真偽両方） | Pass | |
| PEDT-004-TC1 | TDD | `te::test_pedt_tdd_003_*` | Pass | |
| PEDT-005-TC1 | TDD + E2E | `te::test_pedt_tdd_001_*`、`e2e/tests/purchase-edit.spec.ts` | Pass | 実環境でのUI到達を確認 |
| PEDT-005-TC2 | TDD | `te::test_pedt_tdd_001_*`（レスポンスと一覧の一致、`user_id`なし） | Pass | |
| PEDT-006-TC1 | TDD（既存テストの書き直し） | `test_purchase_ptf.py::test_ptf_tdd_010_ptf_013_tc1_stock_edit_recounts_at_updated_at` | Pass | |
| PEDT-006-TC2 | TDD + E2E | `te::test_pedt_tdd_008_*`（unit）、`purchase-edit.spec.ts` | Pass | |
| PEDT-006-TC3 | TDD | `te::test_pedt_tdd_008_*`（buffer_days） | Pass | |
| PEDT-006-TC4 | Integration | `pe-post::test_pedt_006_tc4_*` | Pass | |
| PEDT-007-TC1 | TDD | `Purchase.edit.test.tsx`（PEDT-007-TC1/TC2） | Pass | |
| PEDT-007-TC2 | TDD | 同上 | Pass | |
| PEDT-007-TC3 | Component | `fe-post`（PEDT-007-TC3） | Pass | 文言は固定せず、意味を示す語のみ確認 |
| PEDT-007-TC4 | TDD + Component + E2E | `Purchase.edit.test.tsx`（PEDT-007-TC4）、`fe-post`（一時的な購入）、`purchase-edit.spec.ts` | Pass | |
| PEDT-008-TC1 | TDD + Component | `Purchase.edit.test.tsx`（8行）、`fe-post`（12行、負数・名前・カテゴリ・購入単位11文字） | Pass | 登録との同一判定は共有`purchaseFormSchema`で担保（下記の残存リスク） |
| PEDT-008-TC2 | TDD + Component | `Purchase.edit.test.tsx`（PEDT-008-TC2）、`fe-post`（コードポイント境界） | Pass | |
| PEDT-008-TC3 | Component | `fe-post`（PEDT-008-TC3） | Pass | |
| PEDT-009-TC1 | TDD + Integration | `te::test_pedt_tdd_009_*`、`pe-post::test_pedt_009_tc1_*`（Aが変わらない） | Pass | |
| PEDT-009-TC2 | TDD + Integration | `te::test_pedt_tdd_010_*`、`pe-post::test_pedt_009_tc2_*`（DynamoDB上のunit） | Pass | |
| PEDT-009-TC3 | Integration | `pe-post::test_pedt_009_tc3_*` | Pass | |
| PEDT-009-TC4 | 既存テスト + Integration | `test_purchase_uniqueness_rev2.py::test_purc_tdd_010_purc_023_tc1_*`、`pe-post::test_pedt_009_tc4_*` | Pass | |
| PEDT-009-TC5 | 既存テスト | `test_purchase_uniqueness_rev2.py::test_purc_tdd_008_*`・`_009_*`、`test_purchase_rev2_post.py::test_purc_024_*`、`test_purchase_rename_self_race.py`（いずれも7項目の入力） | Pass | 同時実行の整合性は変更なし |
| PEDT-010-TC1 | TDD | `Purchase.ptf.post.test.tsx`（PEDT-010-TC1） | Pass | |
| PEDT-010-TC2 | 既存テスト + Integration | `test_purchase_uniqueness_rev2.py::test_purc_tdd_010_purc_022_tc1_*`、`pe-post::test_pedt_010_tc2_*`（編集を経た削除と再登録） | Pass | |

28件すべてに検証先がある（Not run・対象外なし）。

## 全体検証

実行SHA: `b248568`に本タスクのテスト・ドキュメント変更を加えた作業ツリー。

| 検証 | コマンド | 結果 | 備考 |
|---|---|---|---|
| Backend tests | `backend/`で`../bin/mise exec -- uv run pytest -m "not integration" -q` | Pass | 79 passed、228 deselected（終了コード0） |
| Frontend tests | `frontend/`で`bun run test -- --run` | Pass | 128 passed、11ファイル（Baseline 97、TDD Green 108、実装後テスト+20） |
| Integration | `DYNAMODB_LOCAL_PORT=18001 ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q` | Pass | 228 passed（TDD Green時180、実装後テスト+48）、終了コード0。ポート8001は利用者のdocker-composeが使用中のため18001を使用 |
| E2E | `E2E_API_PORT=18000 E2E_WEB_PORT=15173 DYNAMODB_LOCAL_PORT=18001 bash e2e/run-e2e.sh` | Pass | 3 passed（`purchase-create`2件、`purchase-edit`1件）。利用者のdocker-composeと開発サーバー（8000/8001/5173）には触れず、代替ポートで実行した |
| Backend lint / format | `../bin/mise exec -- uv run ruff check .`、`ruff format --check .` | Pass | ruff check通過、57ファイル整形済み |
| Frontend lint / format | `bun run lint`、`bun run format:check` | Pass | Biome、エラーなし（カバレッジ生成物`coverage/`削除後） |
| Type check | `bun run build`（`tsc -b`を含む） | Pass | |
| Build | `bun run build` | Pass | `vite build`成功 |
| Infrastructure validation | - | Not run | このスライスにインフラ変更はない |

## 未実行・残存リスク

| 項目 | 理由 | 影響 | 後続対応 |
|---|---|---|---|
| 編集ダイアログの保存失敗表示（422・409、保存中の表示） | PEDTが仕様化していない（論理テストケース§9） | 現状の表示を変えていない。GAP-001 | 別スライスで仕様化 |
| 編集と登録ダイアログの並列比較テスト | 共有`purchaseFormSchema`で同じ検証を使うため、編集側の値表と登録側の既存テストで判定を担保している。同一値を同じテストで両ダイアログに入力する並列テストは追加していない | 両ダイアログの`useForm`設定の差（`valueAsNumber`など）が将来乖離した場合の検知が間接的 | 低リスク。必要ならレビューで判断 |
| pre-commitフック、CIワークフロー（unit/integration/E2E） | ローカル検証の対象外。integration/E2EのCIは未実装 | CIでの再確認は未実施 | 既存の後続項目（CLAUDE.md） |
| Playwright Chromiumの導入 | `~/.cache/ms-playwright`が空でE2Eが起動できなかったため、`e2e/`で`playwright install chromium`（104.3 MiB、リポジトリ外のキャッシュ）を実行した | 環境の追加導入。リポジトリのコード・環境契約は変更していない | 新規マシンでは同じ導入が必要（e2e/README.mdへの追記は別途判断） |

## Slice Complete Gate

- [x] 実装した垂直スライスが仕様の開始点から終了点まで成立する（E2Eで確認）
- [x] 論理テストケースの参照コミットを記録した（`90f68f9`）
- [x] すべての論理Test Case IDに検証先または対象外理由がある（28件）
- [x] Criticalな未カバー箇所が残っていない
- [x] Importantな未カバー箇所をテストしたか、残す理由を記録した（Importantなし。GAP-001は仕様化待ち）
- [x] 必要な単体・コンポーネント・統合・E2Eを実行した
- [x] 全体回帰、Lint、型チェック、ビルドを確認した
- [x] 未実行の検証と残存リスクを明示した
- [x] 仕様または論理テストケースの変更時に影響する承認を取り直した（仕様・論理テストケースの変更なし）
- [ ] 人間がテスト内容、実行結果、対象外理由、残存リスクを確認した
