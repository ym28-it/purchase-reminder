# 購入タイミング計算用の登録項目（PTF） 実装後テストレポート

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `docs/superpowers/specs/2026-11-12-purchase-timing-fields-design.md`（PTF-001〜016） |
| 論理テストケースSSOT | `docs/superpowers/specs/2026-11-12-purchase-timing-fields-test-cases.md` |
| 論理テストケースの参照コミット | `74eba69` |
| TDD計画 | `docs/superpowers/specs/2026-11-12-purchase-timing-fields-tdd-plan.md` |
| TDD Greenコミット | `e849821`（Backend Green）、`4ed3f29`（編集の書き込み条件の修正）、`2a62311`（Frontend Green） |
| 対象スライス | 登録画面の7項目 → `POST /purchases` → DynamoDB（新項目と`stock_counted_at`の永続化）→ `GET /purchases` → 一覧表示。あわせて既存の編集（PUT）が新項目を失わず、在庫変更時に`stock_counted_at`を更新すること |
| 状態 | Draft |
| 確認者 | （人間の確認待ち） |
| 確認日 | - |

論理テストケースの期待結果をこの文書で再定義しない。期待結果はTest Case IDを通じてSSOTを参照する。検証対象の実装SHAは、本レポートのコミット直前の`2a62311`（プロダクトコードは`2a62311`以降変更なし）。

## 入力と引き継ぎ

### TDDからの引き継ぎ

| Test Case ID | TDDでの扱い | 実装後に必要な確認 |
|---|---|---|
| PTF-001-TC4 | 候補外 | `speed`を無視して登録できる（Integration） |
| PTF-002-TC3 | 候補外 | 日数0が一時的な購入の真偽どちらでも登録できる（Integration） |
| PTF-004-TC1、TC2 | 候補外（既存テスト） | PURC-004-TC9/10の改名後テストが維持されている |
| PTF-005-TC4 | 候補外 | 登録画面の入力エラー（Component） |
| PTF-010-TC1 | 候補外 | ラベルが日数・購入単位の意味を示す（Component）とレビュー |
| PTF-012-TC2 | 候補外 | 編集画面に保存済みの日数が表示される（Component） |
| PTF-012-TC3 | 候補外（既存テスト） | PURC-022-TC1のテストが維持されている |
| PTF-016-TC1 | 候補外 | 購入単位違いでも409（Integration） |
| PTF-001-TC2、PTF-006-TC1、PTF-015-TC1 | 中心的契約だが最小セット外 | レスポンスと再取得の両方（Integration） |
| PTF-002-TC1、PTF-005-TC1/TC2/TC3、PTF-003-TC2、PTF-014-TC2/TC3/TC5、PTF-013-TC2、PTF-003-TC1、PTF-009-TC1 | 中心的契約だが最小セット外 | 境界の受け付け・型・空白・初期値・一覧表示の網羅 |
| 上記以外の15件（TDD計画の最小セット） | TDD済み | Green記録のとおり維持されていること（全体回帰で確認） |

### 実装分析で新たに見つかった観点

| ID | 観点 | 種別 | 仕様・Test Case ID上の根拠 | 対応 |
|---|---|---|---|---|
| IMPL-RISK-001（Review Focus 1） | 編集で`created_at`が変わる | 状態遷移 | PTF-012、PURC既存仕様（作成日時は不変） | Add test（Unit `test_review_focus_1_and_ptf_012_*`、Integration `test_review_focus_1_edit_keeps_created_at`、再試行後も`created_at`を確認） |
| IMPL-RISK-002（Review Focus 2） | `speed`形式の古いアイテムが残っている | 接続 | 仕様の対象外「既存データの移行」 | Justified（下記「古いアイテムの挙動」。テストでは固定しない） |
| IMPL-RISK-003（Review Focus 3） | 編集の再試行で最新の在庫と比べる | 並行性・状態遷移 | PTF-013（在庫が保存済みの値から変わったときだけ更新） | Add test（Integration、決定的な競合注入） |
| IMPL-RISK-004（Review Focus 4） | `stock_counted_at`のUTC ISO 8601形式 | 境界 | 設計書（`created_at`と同じ形式） | Add test（Integration） |
| IMPL-RISK-005（Review Focus 5） | PUTの在庫`2`と`2.0` | 境界・型 | PTF-013（在庫が変わらない編集では更新しない） | Add test（Unit、Integration） |
| IMPL-RISK-006 | 編集画面のPUT本文が`days_per_unit`を送り、`unit`・`buffer_days`を送らない | 接続 | 設計書「PUTのリクエストに`unit`と`buffer_days`を含めない」、PTF-012 | Add test（Component） |

## 実装した処理フロー

登録画面（`CreatePurchaseDialog`）が7項目をzodで検証し、`POST /purchases`へ送る。APIのPydanticスキーマが`days_per_unit`（0〜365）、`buffer_days`（0〜30）、`unit`（1〜10文字、空白だけを拒否）、`stock`を厳密な整数として検証し、`speed`などの未知の項目は無視する。サービス層が1つの`now`を`stock_counted_at`・`created_at`・`updated_at`へ設定し、models層がアイテムと名前・カテゴリの予約をトランザクションで書き込む。一覧（`GET /purchases`）が読み戻したものを`Purchase.tsx`が単位名付き（「2パック」「1パック3日」「余裕 N日」）で表示する。編集（`PUT`）では、`put_purchase_item`が強い整合性で読み取った現在値へドメインの`apply_edit`を適用し、`unit`・`buffer_days`・`created_at`を引き継ぎ、在庫が変わったときだけ`stock_counted_at`を`updated_at`と同じ時刻にする。書き込みは名前・カテゴリ・`updated_at`が読み取り時のままであることを条件にし、競合したら読み直して`apply_edit`を適用し直す。

## 実装範囲

- Frontend: `CreatePurchaseDialog.tsx`、`Purchase.tsx`、`EditPurchaseDialog.tsx`（`days_per_unit`への改名）、`api/schema.d.ts`
- API: `api/schemas/purchase.py`、`api/purchase.py`
- Services / Domain: `purchase_service.py`、`domain/purchase.py`（`apply_edit`）
- Persistence: `models/purchase.py`（新項目、`updated_at`を含む書き込み条件）
- External systems: なし
- 対象外: 購入時期の計算、在庫の入れ直し、編集画面の作り直し、既存データの移行

## カバレッジ

### 実行条件

- コマンド（Backend）: `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -q --cov=app --cov-branch --cov-report=term-missing`（unit + integration、224 passed）
- コマンド（Frontend）: `cd frontend && bun run test -- --run --coverage --coverage.include='src/features/*.tsx' --coverage.include='src/api/purchases.ts' --coverage.reporter=text`（97 passed）
- 対象: `backend/app`全体、`frontend/src/features/*.tsx`と`src/api/purchases.ts`
- ツール: pytest-cov 7.1（branch有効）、@vitest/coverage-v8 4.1.10

### 結果

| 対象 | Line | Branch | 備考 |
|---|---:|---:|---|
| `app/api/purchase.py` | 100% | 100% | |
| `app/api/schemas/purchase.py` | 100% | 100% | |
| `app/domain/purchase.py` | 100% | 100% | |
| `app/services/purchase_service.py` | 100% | 100% | |
| `app/models/purchase.py` | 94%（5行未実行） | 未実行分岐5 | 未実行: 97、140、171、270、295行（下記GAP-001/002） |
| `backend/app`全体 | 94%（18行未実行） | 11分岐未実行 | 残りはPTF範囲外の既存コード |
| `CreatePurchaseDialog.tsx` | 100% | 97.7% | 147行の1分岐 |
| `Purchase.tsx` | 72.7% | 66.7% | 未実行116〜142行は編集・削除ダイアログの配線（GAP-003） |
| `EditPurchaseDialog.tsx` | 62.5%（本レポートのPUT送信テスト追加前の測定） | 50% | 追加後に54〜66行（送信処理）を実行 |
| `api/purchases.ts` | 58.3% | 50% | 25〜30、40〜43行は`putPurchase`・`deletePurchase`（編集・削除。追加後のPUT送信テストで`putPurchase`は通過） |

カバレッジ率は未検証箇所の発見に使用し、数値だけを完了条件にしない。Frontendの数値は、PUT送信テストを追加する前に測定したため、`EditPurchaseDialog.tsx`・`api/purchases.ts`は追加後に改善している（再測定はしていない）。

## 未カバー箇所の評価

| ID | 箇所・契約 | 分類 | リスク | 対応 | 仕様・Test Case ID上の根拠 |
|---|---|---|---|---|---|
| GAP-001 | `models/purchase.py` 97・140行、270・295行: トランザクション失敗が重複・競合以外のときの再送出（`raise`） | Low risk | 予期しないDynamoDBエラーをそのまま伝える1行。PTFで変更していない既存分岐 | Justified | PTF外（PURC既存実装） |
| GAP-002 | `models/purchase.py` 171行: PUT・DELETE対象が存在しない場合の`ItemNotFoundError` | Low risk | PTFで変更しておらず、404の契約はPTFの仕様IDにない | Justified | PTF外（編集・削除スライスで仕様化する） |
| GAP-003 | `Purchase.tsx` 116〜142行、`EditPurchaseDialog.tsx`の送信エラー、`deletePurchase`: 編集・削除ダイアログの開閉と失敗表示 | Low risk | 編集・削除の画面は未仕様化（CLAUDE.md）。PTFで触ったのはラベルと`days_per_unit`の送信本文だけで、後者はIMPL-RISK-006で検証済み | Justified | PTF-012-TC2、IMPL-RISK-006 |
| GAP-004 | PUT側のスキーマ（`PurchasePutRequest`）が`days_per_unit: gt=0`で、登録の0〜365・整数とは異なる | Specification gap | 設計書は「編集は仕様化されていないため既存の検証をそのまま残す」としているため、PUTで0や366を拒否する・しないはPTFの期待結果として定義されていない。期待結果を決めずテストも追加していない | Spec confirmation（編集スライスで仕様化） | 設計書「編集（PUT）の入力検証」、PTF-012は項目の保持だけを定義 |

CriticalまたはImportantな未カバー箇所はない。

## 追加した単体・コンポーネントテスト

| Test Case ID / Risk ID | テストレベル | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PTF-013-TC1、PTF-013-TC2、PTF-007-TC1、IMPL-RISK-001、IMPL-RISK-005 | Unit | `backend/tests/unit/domain/test_purchase_edit.py`（6件） | 在庫比較・`created_at`/`unit`/`buffer_days`の引き継ぎはAPI不要で最も速く決定的に確認できる（`2`と`2.0`、`0`と`0.0`を含む） | Pass |
| PTF-005-TC4 | Component | `frontend/src/features/CreatePurchaseDialog.post.test.tsx`（余裕日数の負数・小数・31） | 既存のPURC-003の入力エラー検証へ新項目を足す | Pass |
| PTF-014-TC2、TC4（画面側） | Component | 同上（購入単位の空・空白・U+3000・11文字・サロゲート11文字） | 購入単位は画面でも送信前に拒否する（仕様IDはPTF-014） | Pass |
| PTF-003-TC2、PTF-014-TC3、PTF-014-TC5（画面側） | Component | 同上（余裕日数0・30、購入単位10文字・前後空白保持が入力どおり送信される） | 境界の受け付け側 | Pass |
| PTF-010-TC1 | Component | 同上（ラベルが「1単位…使い切る日数…日」「余裕日数…日」「購入単位」を含む） | 文言全体は固定せず、意味を読み取れる語の存在だけを確認する | Pass |
| PTF-009-TC1 | Component | `frontend/src/features/Purchase.ptf.post.test.tsx` | 一覧が全項目を表示し、`stock_counted_at`の日時を表示しない | Pass |
| PTF-012-TC2 | Component | 同上 | 編集画面を開くと保存済みの日数が表示される | Pass |
| IMPL-RISK-006（PTF-012） | Component | 同上（PUT送信テスト） | 編集の送信本文が`days_per_unit`を使い、`unit`・`buffer_days`を含まない | Pass |

## 統合テスト

| Test Case ID / Risk ID | 接続する境界 | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PTF-001-TC2 | API + DynamoDB Local | `backend/tests/integration/api/test_purchase_ptf_post.py::test_ptf_001_tc2_*` | レスポンスと再取得の両方で`days_per_unit`が一致し、`speed`が含まれない | Pass |
| PTF-001-TC4 | 同上 | `test_ptf_001_tc4_*` | `speed`は無視され、`days_per_unit`が使われる | Pass |
| PTF-002-TC1、PTF-002-TC3、PTF-003-TC2、PTF-004-TC1、PTF-014-TC3、PTF-014-TC5 | 同上 | `test_accepted_boundaries_are_stored_unchanged`（11件） | 境界の受け付けと、再取得した値が入力と一致すること | Pass |
| PTF-002-TC2、PTF-003-TC3、PTF-004-TC2、PTF-005-TC1、TC2、TC3、PTF-014-TC2、TC4 | 同上 | `test_out_of_range_or_wrong_type_is_rejected_with_field_and_not_stored`（18件。1.0・文字列`"3"`・`"1"`を含む） | 該当項目が識別でき、一覧が空のまま（永続化されない） | Pass |
| PTF-006-TC1 | 同上 | `test_ptf_006_tc1_*` | レスポンスと再取得の両方で`stock_counted_at == created_at` | Pass |
| PTF-013-TC2 | 同上 | `test_ptf_013_tc2_*` | 名前だけの変更で`stock_counted_at`が不変、`updated_at`は進む | Pass |
| IMPL-RISK-001 | 同上 | `test_review_focus_1_edit_keeps_created_at` | 編集後も`created_at`が変わらない（レスポンス・再取得・DB上の値） | Pass |
| IMPL-RISK-005 | 同上 | `test_review_focus_5_*`（`2`、`2.0`） | PUTの在庫`2`と`2.0`は同じ在庫で、`stock_counted_at`を更新しない | Pass |
| IMPL-RISK-004 | 同上 | `test_review_focus_4_*` | `stock_counted_at`が`created_at`と同じUTCのISO 8601で、レスポンス・一覧・DBに保存される | Pass |
| PTF-016-TC1 | 同上 | `test_ptf_016_tc1_*` | 購入単位違いでも409で、元の購入物だけが残る | Pass |
| IMPL-RISK-003 | 同上（models層のフック） | `test_review_focus_3_retry_compares_with_latest_stock_equal_keeps_counted_at`、`..._different_recounts`、`..._unrelated_concurrent_write_does_not_recount_stock` | 下記「Review Focusの消化」 | Pass |

## E2E

| Test Case ID / Risk ID | ユーザーフロー | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PTF-001-TC1、PTF-003-TC1、PTF-015-TC2、PTF-009-TC1、PTF-006-TC1、PTF-008-TC1、PTF-011-TC1（既存のPURC-009-TC2ほかを維持） | 購入単位「パック」・1パック3日・余裕日数2・在庫4を入力して登録 → 一覧表示 → 再読み込み後の一覧にも「1パック3日」「余裕 2日」「4パック」が表示される → APIの保存値（`unit`・`days_per_unit`・`buffer_days`、`speed`なし、`stock_counted_at == created_at`）→ 同名・同カテゴリの再登録が重複として拒否され入力が保持される | `e2e/tests/purchase-create.spec.ts`の1件目（消費スピード/speedを新項目へ更新） | 実際のブラウザ・Vite・FastAPI・DynamoDB Localを通した代表1経路。PURC-009/013/014/016のE2E網羅を維持 | Pass |
| PURC-013-TC2 | 連打しても1件だけ登録される | 同2件目（入力を新項目へ更新） | 既存のE2Eを新しい7項目に合わせる | Pass |

各表では前提、操作、期待結果を再記述せず、論理Test Case IDまたは根拠を記録した実装リスクIDを参照する。

## Review Focusの消化

1. 編集で作成日時が変わる: `apply_edit`は`created_at`を引き継ぐ（Unit）。API経由でも編集後の`created_at`が、レスポンス・再取得・DB上の値とも登録時と一致する。再試行後のPUTでも不変（IMPL-RISK-003のテストで確認）。**確認済み**
2. 新項目のない古いアイテム: 下記「古いアイテムの挙動」。**確認し、手順を記録**
3. 編集の競合と在庫比較: models層の`_read_current`を包み、編集の最初の読み取りの直後・書き込みの前に、別の編集をサービス層経由で割り込ませる決定的なテストにした（スリープや実際の並行実行は使わない）。
   - 割り込みが在庫7へ変更し、本編集も在庫7を送った場合: 本編集の書き込みは`updated_at`条件で失敗して再試行され（読み取り2回）、再読み込みした在庫7と同じため`stock_counted_at`は割り込み編集の値のまま（本編集の時刻で上書きしない）。`updated_at`は割り込み後の時刻に進み、`created_at`は不変
   - 割り込みが在庫9へ変更し、本編集は在庫2を送った場合: 再試行で最新の9と比べて変更と判定し、`stock_counted_at == updated_at`になる
   - 割り込みが名前系の変更（在庫は2のまま）で、本編集が在庫`2.0`を送った場合: 再試行しても`stock_counted_at`は登録時の値のまま
   - 突き合わせ: `updated_at`の書き込み条件（`_unchanged_since_read_for_edit`）だけを一時的に外すと、3件とも失敗することを確認した（変異テスト。確認後にプロダクトコードを復元し、`git status`で`backend/app`に差分がないことを確認）。**確認済み**
4. 日時の形式: `stock_counted_at`・`created_at`はレスポンス（登録・編集・一覧）とDB上の文字列で、同じUTCのISO 8601形式（`Z`または`+00:00`の同じ表記）。**確認済み**
5. 在庫の比較の型: PUTの在庫`2`と`2.0`は同じ在庫で`stock_counted_at`を更新しない（Unit・Integration）。**確認済み**

### 古いアイテムの挙動

`speed`形式で保存された古いアイテム（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`がない）をDynamoDB Localへ直接書き込み、`GET /purchases`を呼ぶと、`PurchaseItem`の検証エラー（Pydantic ValidationError）になり、一覧取得は成功しない（アプリはHTTP 500になる）。同じ利用者の古いアイテムが1件でも残っていると、一覧全体が取得できなくなる。この挙動は仕様が定義しておらず（既存データの移行は対象外）、期待値を決めないため自動テストでは固定しない（検証時の使い捨てテストで確認）。

ローカルのデータを作り直す手順:

1. `docker-compose down`でAPIとDynamoDB Localを停止する
2. DynamoDB Localのデータを消す（`docker-compose down -v`でボリュームごと削除する。インメモリで起動している場合は再起動だけでよい）
3. `docker-compose up`で起動し直し、テーブルを新しく作る
4. 登録画面から購入物を登録し直す

## 論理テストケースの消化確認

| Test Case ID | 最終的な検証先 | 実テスト・証跡 | 結果 | 対象外理由 |
|---|---|---|---|---|
| PTF-001-TC1 | TDD、Component | `CreatePurchaseDialog.ptf.test.tsx`（PTF-TDD-013）、`CreatePurchaseDialog.post.test.tsx`（7項目の初期状態）、E2E | Pass | |
| PTF-001-TC2 | Integration | `test_purchase_ptf_post.py::test_ptf_001_tc2_*`（TDD側は`test_purchase_ptf.py` PTF-008-TC1/PTF-011-TC1） | Pass | |
| PTF-001-TC3 | TDD | `test_purchase_ptf.py`（PTF-TDD-005） | Pass | |
| PTF-001-TC4 | Integration | `test_purchase_ptf_post.py::test_ptf_001_tc4_*` | Pass | |
| PTF-002-TC1 | Integration、既存テスト | `test_purchase_ptf_post.py`（days 0、365）、`test_purchase_create_post.py`（PURC-004-TC7） | Pass | 重複はPURC第2版テストの読み替え維持のため |
| PTF-002-TC2 | TDD | `test_purchase_ptf.py`（PTF-TDD-004）、`test_purchase_ptf_post.py`（366） | Pass | 後者は同じ値を拒否側の網羅へ含めたもの |
| PTF-002-TC3 | Integration | `test_purchase_ptf_post.py`（日数0で一時的な購入true/false） | Pass | |
| PTF-003-TC1 | Component | `CreatePurchaseDialog.post.test.tsx`（初期値）、`CreatePurchaseDialog.rev2.post.test.tsx`系の再オープン確認 | Pass | |
| PTF-003-TC2 | Integration、Component | `test_purchase_ptf_post.py`（0、30）、`CreatePurchaseDialog.post.test.tsx` | Pass | |
| PTF-003-TC3 | TDD | `test_purchase_ptf.py`（PTF-TDD-007） | Pass | |
| PTF-003-TC4 | TDD | `test_purchase_ptf.py`（PTF-TDD-006） | Pass | |
| PTF-003-TC5 | TDD | `CreatePurchaseDialog.ptf.test.tsx`（PTF-TDD-014） | Pass | |
| PTF-004-TC1 | 既存テスト、Integration | `test_purchase_create_post.py`（PURC-004-TC9）、`test_purchase_ptf_post.py`（0、100000） | Pass | |
| PTF-004-TC2 | 既存テスト、Integration | `test_purchase_create_post.py`（PURC-004-TC10）、`test_purchase_ptf_post.py` | Pass | |
| PTF-005-TC1 | Integration | `test_purchase_ptf_post.py`（-1、1.5、1.0） | Pass | |
| PTF-005-TC2 | Integration | 同上（`"3"`） | Pass | |
| PTF-005-TC3 | Integration | 同上（余裕日数 -1、1.5、1.0、`"1"`） | Pass | |
| PTF-005-TC4 | Component | `CreatePurchaseDialog.post.test.tsx`（日数の負数・小数・366は既存の読み替え、余裕日数の負数・小数・31を追加） | Pass | |
| PTF-006-TC1 | Integration、TDD | `test_purchase_ptf_post.py::test_ptf_006_tc1_*`、`test_purchase_ptf.py`（PTF-008-TC1） | Pass | 重複はレスポンスと再取得の両方を確認するため |
| PTF-006-TC2 | TDD | `test_purchase_ptf.py`（PTF-TDD-003） | Pass | |
| PTF-007-TC1 | TDD、Unit | `test_purchase_ptf.py`（PTF-TDD-011）、`test_purchase_edit.py` | Pass | 重複は項目比較のロジックを最速で確認するため |
| PTF-008-TC1 | TDD | `test_purchase_ptf.py`（PTF-TDD-001） | Pass | |
| PTF-009-TC1 | Component | `Purchase.ptf.post.test.tsx::PTF-009-TC1`、E2E | Pass | |
| PTF-010-TC1 | Component、レビュー | `CreatePurchaseDialog.post.test.tsx`（PTF-010-TC1） | Pass | 文言そのものは固定せず、語の存在だけを確認する。表現の妥当性は最終レビュー |
| PTF-011-TC1 | TDD | `test_purchase_ptf.py`（PTF-TDD-002）、E2E | Pass | |
| PTF-012-TC1 | TDD、Component | `test_purchase_ptf.py`（PTF-TDD-012）、`Purchase.ptf.post.test.tsx`（PUT送信本文） | Pass | |
| PTF-012-TC2 | Component | `Purchase.ptf.post.test.tsx::PTF-012-TC2` | Pass | |
| PTF-012-TC3 | 既存テスト | `test_purchase_uniqueness_rev2.py`（PURC-022-TC1） | Pass | |
| PTF-013-TC1 | TDD、Unit | `test_purchase_ptf.py`（PTF-TDD-010）、`test_purchase_edit.py` | Pass | 重複は上記と同じ |
| PTF-013-TC2 | Integration、Unit | `test_purchase_ptf_post.py::test_ptf_013_tc2_*`、`test_purchase_edit.py` | Pass | |
| PTF-014-TC1 | TDD | `test_purchase_ptf.py`（PTF-TDD-008） | Pass | |
| PTF-014-TC2 | Integration、Component | `test_purchase_ptf_post.py`（空・空白・U+3000）、`CreatePurchaseDialog.post.test.tsx` | Pass | |
| PTF-014-TC3 | Integration、Component | `test_purchase_ptf_post.py`（10文字、サロゲート10文字）、`CreatePurchaseDialog.post.test.tsx` | Pass | |
| PTF-014-TC4 | TDD、Component | `test_purchase_ptf.py`（PTF-TDD-009）、`test_purchase_ptf_post.py`、`CreatePurchaseDialog.post.test.tsx` | Pass | |
| PTF-014-TC5 | Integration、Component | `test_purchase_ptf_post.py`（` パック `）、`CreatePurchaseDialog.post.test.tsx` | Pass | |
| PTF-015-TC1 | Integration、TDD | `test_purchase_ptf.py`（PTF-008-TC1、PTF-011-TC1）、`test_purchase_ptf_post.py::test_ptf_001_tc2_*` | Pass | |
| PTF-015-TC2 | TDD、E2E | `Purchase.ptf.test.tsx`（PTF-TDD-015）、E2E（再読み込み後） | Pass | |
| PTF-016-TC1 | Integration | `test_purchase_ptf_post.py::test_ptf_016_tc1_*`、`test_purchase_create_post.py`（PURC-014-TC2に`unit`を追加済み） | Pass | |

38件すべてに検証先がある。対象外とした項目はない。

## 全体検証

| 検証 | コマンド | 結果 | 備考 |
|---|---|---|---|
| Backend tests（unit） | `cd backend && ../bin/mise exec -- uv run pytest -m "not integration" -q` | Pass | 79 passed（新規`test_purchase_edit.py` 6件を含む）、exit 0 |
| Integration | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration -q` | Pass | 145 passed（104 + 新規41）、exit 0。DynamoDB Local 3.3.1。カバレッジ付きの全体実行は224 passed |
| Frontend tests | `cd frontend && bun run test -- --run` | Pass | 9 files / 97 tests passed |
| E2E | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- bash -c 'cd ../e2e && bunx playwright test --config playwright.ccr-local.config.ts'` | Pass | 2 passed。下記の環境上の注記を参照 |
| Backend lint / format | `cd backend && ../bin/mise exec -- uv run ruff check . && ... ruff format --check .` | Pass | 55 files formatted |
| Frontend lint / format | `cd frontend && bun run lint && bun run format:check` | Pass | |
| Type check | `bun run build`（`vite build && tsc -b`に含まれる） | Pass | exit 0 |
| Build | `cd frontend && bun run build` | Pass | exit 0 |
| Infrastructure validation | - | Not run | このスライスにインフラ変更なし |

実行SHAの基準: `2a62311`（ワークツリーの追加はテストコード・TDD計画の1文・本レポートのみ）。

### 環境上の注記

- このクラウドセッションには`e2e/`が指定するPlaywrightのブラウザ（chromium_headless_shell-1194）がなく、`bash e2e/run-e2e.sh`はブラウザ起動前に失敗するため実行していない。Baselineと同じ方法で、コミットしない一時設定`e2e/playwright.ccr-local.config.ts`（`launchOptions.executablePath`に`/opt/pw-browsers/chromium`を指定）から同じrunner（`run_with_dynamodb_local`）でE2Eを実行し、Passを確認した。一時設定は削除済みで、コミットしていない。リポジトリの環境コードは変更していない
- Maven・DynamoDB Localの取得は今回すべて成功し、`ENVIRONMENT_FAILURE`は発生しなかった

## 未実行・残存リスク

| 項目 | 理由 | 影響 | 後続対応 |
|---|---|---|---|
| `bash e2e/run-e2e.sh`そのものの実行 | このセッションにPlaywrightの指定ブラウザがない | 同じrunnerとspecを、Chromiumの実行ファイルだけ差し替えて実行済み。CI・開発機のブラウザ差は検証していない | integration / E2EのCIワークフロー（`docs/todo/test-environment-rollout.md`）で確認 |
| Infrastructure validation | インフラ変更なし | なし | - |
| 古い`speed`形式のアイテムによる一覧取得失敗（HTTP 500） | 既存データの移行は仕様の対象外 | ローカルで古いデータが残ると一覧全体が取得できない | 上記「ローカルのデータを作り直す」手順。本番データ移行が必要になれば別スライスで仕様化 |
| 編集（PUT）スキーマの検証（GAP-004） | 編集は未仕様化 | PUTの`days_per_unit`が0以下を拒否する・366以上を許す等、登録と非対称 | 編集スライスの仕様で定義する |
| 編集・削除画面の失敗表示、404 | 未仕様化 | 低 | 編集・削除スライス |
| `PTF-010-TC1`の表現の妥当性 | 文言を固定しない契約 | 自動テストは語の存在だけを確認 | 最終コードレビューで画面文言を確認 |

### Deferred・文書の修正

- 人間の判断（2026-11-22 ym28-it）: 日数0の品目の一覧表示は「1パック0日」でよい。日数0の品目を編集画面で保存できない制約（GAP-004）は編集スライスで扱う

- TDD計画のRed記録に残っていた「日数0の表示は論理テストケースで定義されないため断定しない」という文は、修正ラウンドで復元した「1パック0日」の確認と矛盾していたため、同じ意味になるよう1文だけ修正した（文書のみの変更。凍結済みテストと期待結果は変更していない）
- 凍結済みTDDテスト（`test_purchase_ptf.py`、`CreatePurchaseDialog.ptf.test.tsx`、`Purchase.ptf.test.tsx`）はRed記録コミット（`0690622`、`f1d260b`）から差分なし
- プロダクトコード（`backend/app`、`frontend/src`の非テストファイル）は`2a62311`から変更していない

## Slice Complete Gate

- [x] 実装した垂直スライスが仕様の開始点から終了点まで成立する（E2Eで登録→再読み込み→一覧の単位名付き表示→APIの保存値まで確認）
- [x] 論理テストケースの参照コミットを記録した（`74eba69`）
- [x] すべての論理Test Case IDに検証先または対象外理由がある（38件）
- [x] Criticalな未カバー箇所が残っていない
- [x] Importantな未カバー箇所をテストしたか、残す理由を記録した（Importantな未カバーはなし）
- [x] 必要な単体・コンポーネント・統合・E2Eを実行した
- [x] 全体回帰、Lint、型チェック、ビルドを確認した
- [x] 未実行の検証と残存リスクを明示した
- [x] 仕様または論理テストケースの変更時に影響する承認を取り直した（変更なし）
- [ ] 人間がテスト内容、実行結果、対象外理由、残存リスクを確認した
