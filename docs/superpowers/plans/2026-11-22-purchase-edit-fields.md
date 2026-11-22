# 購入物編集の項目と検証（PEDT） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 購入物の編集で、登録と同じ全7項目（`unit`・`buffer_days`を含む）を、登録と同じ検証で変更できるようにする。

**Architecture:** 登録と編集のリクエストが共通の基底Pydanticスキーマを継承し、検証の定義を1か所にそろえる。編集（PUT）は全項目必須の完全置き換えとし、domainの編集の適用関数が`unit`・`buffer_days`も受け取る。フロントエンドは、登録ダイアログの検証（Zodスキーマ）を共有モジュールへ切り出し、編集ダイアログへ`unit`・`buffer_days`の入力欄と同じ検証を与える。

**Tech Stack:** FastAPI、Pydantic v2、boto3（DynamoDB Local）、pytest。React 19、react-hook-form + zod、TanStack Query、openapi-fetch、Vitest + Testing Library。

**Spec:** `docs/superpowers/specs/2026-11-22-purchase-edit-fields-design.md`（PEDT-001〜010、2026-11-22承認）。論理テストケース`docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md`（参照コミット`90f68f9`）。TDD計画`docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md`（Test Plan Approved、`e9873a9`）。

## Global Constraints

- 編集（PUT）のリクエスト: `name`、`category`、`unit`、`days_per_unit`、`buffer_days`、`stock`、`is_temporary`をすべて必須とする。`is_temporary`の既定値は持たない。`stock_counted_at`・`created_at`・`updated_at`・`id`・`speed`は未知の項目として無視する（保存しない）
- 制約は登録と同一: `name`は1〜50文字、`category`は1〜30文字、`unit`は1〜10文字（いずれもコードポイント単位、空白文字だけは拒否、正規化・前後空白の除去をしない）、`days_per_unit`は0〜365の整数（strict）、`buffer_days`は0〜30の整数（strict）、`stock`は0〜100,000の整数（strict）、`is_temporary`は真偽値（strict）
- 入力制約違反・必須項目の欠落は422で、`detail[].loc`が`["body", <項目名>]`になる（項目ごとに識別できる）。違反時は保存済みの購入物を変えない
- `stock_counted_at`は在庫が保存済みの値から変わったときだけ、その編集の`updated_at`と同じ時刻に更新する。`unit`・`buffer_days`だけの変更では更新しない。`created_at`・`id`は変わらない
- 重複判定は名前・カテゴリの完全一致のみ（`unit`を含めない）で409。存在しないIDは404。同時編集時の読み直しと再試行は変えない
- 編集ダイアログの入力検証と項目名・説明は、登録ダイアログと同じにする。空欄の数値項目は`NaN`になり、0として送らず入力エラーにする
- 依存の向き`api → services → domain / models`を守る。TDDテストはRed記録後に凍結し、Greenで変更しない
- 論理テストケースの期待結果を計画やテストで変更しない。期待が合わないときは停止して人間へ戻す

## Review Focus

1. **古い非整数の保存値を編集ダイアログで開く**: 以前のPUTで小数の在庫（`1.5`）が保存された購入物は、整数だけを受け付けるダイアログで保存できなくなる。期待は、保存済みの値を表示し、整数へ直すまで入力エラーで送信しないこと（検証タスクのコンポーネントテスト）
2. **全項目を送らない古い呼び出し元**: PUTが`unit`・`buffer_days`・`is_temporary`の欠落で422になるため、PUTを呼ぶ他のコード・E2E・手順書が残っていないこと（検証タスクで`grep`し、`e2e/`の実行で確認する）
3. **空欄の数値入力**: 編集ダイアログで数値欄を空にして保存すると、`NaN`のまま送らず、入力エラーを表示する（検証タスクのコンポーネントテスト）
4. **`stock_counted_at`の比較型**: 保存済みの在庫（`Decimal`由来）と、PUTで受け取る整数の在庫が同じ値のとき、更新されない（検証タスクで`2`のまま編集する統合テストを確認。既存の`test_review_focus_5_*`の整数側を維持する）
5. **全項目が変わる同時編集**: 再試行が起きても、`unit`・`buffer_days`の最新の編集内容が失われず、`created_at`が上書きされない（検証タスクで、既存の再試行テストが7項目の入力でGreenであることを確認する）

---

### Task 1: Backend Red（PEDT-CORE-001〜006、`create-tdd-tests`）

**Files:**
- Create: `backend/tests/integration/api/test_purchase_edit_fields.py`
- Modify: `backend/tests/integration/api/test_purchase_ptf.py`、`test_purchase_ptf_post.py`、`test_purchase_rev2_post.py`、`test_purchase_uniqueness_rev2.py`、`test_purchase_rename_self_race.py`
- Modify: `docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md`（Red記録）

**Interfaces:**
- Consumes: なし（HTTP契約だけを使う）
- Produces: 凍結済みテストファイル`test_purchase_edit_fields.py`、書き直した既存テスト、Red記録SHA

- [ ] **Step 1: 環境スモークとBaselineを確認する**

Run（`backend/`）: `../bin/mise exec -- uv run pytest -m "not integration" -q` と `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q`（8001が使用中なら`DYNAMODB_LOCAL_PORT=18001`を前置する）
Expected: 79 passed / 145 passed（TDD計画のBaselineと一致）

- [ ] **Step 2: `test_purchase_edit_fields.py`にTDDテストを書く**

`test_purchase_ptf.py`と同じ`pytestmark = pytest.mark.integration`、`client`フィクスチャ、`as_user`、`valid_purchase`、`purchases`、`create`、`error_locs`、`when`を同じ形で用意し、次を加える。基準入力は論理テストケース2章の値（牛乳／食品／パック／3／0／2／false）。

- `def edit(client, created, **overrides) -> Response`: `PUT /purchases/{created["id"]}`へ`valid_purchase(**overrides)`（7項目）を送る
- `def assert_edit_rejected_on(client, created, field, **overrides) -> None`: `edit`が422、`["body", field]`が`error_locs`に含まれ、`purchases(client) == [created]`（保存済みの購入物が変わらない）を確認する

| テスト名 | Test Case ID | 主なassertion |
|---|---|---|
| `test_pedt_tdd_001_pedt_001_tc1_edit_changes_all_seven_fields` | PEDT-001-TC1、005-TC1、005-TC2 | 作成後に`time.sleep(0.01)`し、名前「豆乳」・カテゴリ「飲料」・`unit`「本」・`days_per_unit` 5・`buffer_days` 2・`stock` 7・`is_temporary` trueで編集。200。レスポンスと再取得の7項目が送った値と一致し、`created_at`は変わらず`updated_at`は作成時より後。レスポンスと一覧の同じ購入物が等しく、`user_id`を含まない |
| `test_pedt_tdd_002_pedt_001_tc2_missing_required_field_is_rejected` | PEDT-001-TC2 | `unit`・`buffer_days`・`is_temporary`をparametrizeし、その項目を除いたリクエストが422（`assert_edit_rejected_on`と同じ確認）。`is_temporary`が欠けても`false`で保存されない |
| `test_pedt_tdd_003_pedt_004_tc1_multiple_violations_are_identified_per_field` | PEDT-004-TC1 | `days_per_unit` 366と`buffer_days` 31を同時に送ると422で、`["body","days_per_unit"]`と`["body","buffer_days"]`の両方が含まれ、保存済みの購入物は変わらない |
| `test_pedt_tdd_004_pedt_002_tc2_out_of_range_or_wrong_numeric_type_is_rejected` | PEDT-002-TC2（数値項目） | `(field, value)`をparametrize: `days_per_unit`に366・`1.5`・`1.0`・`"3"`、`buffer_days`に31・`1.5`・`"1"`、`stock`に100001・`1.5`・`2.0`・`"2"`、`is_temporary`に`"true"`・`1`。いずれも422で該当項目を識別でき、購入物は変わらない |
| `test_pedt_tdd_005_pedt_002_tc1_pedt_003_tc1_numeric_boundaries_are_accepted` | PEDT-002-TC1（数値項目）、003-TC1 | `days_per_unit` 0と365、`buffer_days` 0と30、`stock` 0と100000で、それぞれ編集して200。再取得した値が送った値と一致する（`days_per_unit` 0でも`is_temporary`のtrue・falseの両方で受理） |
| `test_pedt_tdd_006_pedt_002_tc2_text_limits_and_blank_are_rejected` | PEDT-002-TC2（文字列項目） | parametrize: `name`に51文字・`"  "`、`category`に31文字・`" "`、`unit`に11文字・`" "`・`""`。いずれも422で該当項目を識別でき、購入物は変わらない |
| `test_pedt_tdd_007_pedt_002_tc1_tc3_text_boundaries_and_padding_are_stored_as_is` | PEDT-002-TC1（文字列項目）、002-TC3 | `name` 50文字・`category` 30文字・`unit`が`𠮷`10文字で編集すると200で保存される。続けて`unit`を`" パック "`にすると前後空白を除去せず保存される |
| `test_pedt_tdd_008_pedt_006_tc2_tc3_unit_or_buffer_only_edit_keeps_stock_counted_at` | PEDT-006-TC2、006-TC3 | `("unit", "本")`・`("buffer_days", 5)`をparametrize。その1項目だけを変えて編集（在庫は2のまま）。200で変更が反映され、`stock_counted_at`は作成時の値のまま、`updated_at`は作成時より後 |
| `test_pedt_tdd_009_pedt_009_tc1_rename_into_pair_with_other_unit_is_409` | PEDT-009-TC1 | 牛乳／食品／パックの購入物Aと豆乳／食品／パックのBを作成。Bを名前「牛乳」・`unit`「本」で編集すると409。Bは変わらない |
| `test_pedt_tdd_010_pedt_009_tc2_unit_only_edit_is_not_a_self_duplicate` | PEDT-009-TC2 | 名前・カテゴリを変えず`unit`だけ「本」で編集すると200で`unit == "本"` |

- [ ] **Step 3: 既存の統合テストを書き直す**

PUTを送る既存テストの入力へ`unit`と`buffer_days`を加える（`payload()`・`put_body()`などの補助関数に既定値を足すのが最小）。
- `test_purchase_ptf.py`: `test_ptf_tdd_010_*`（PEDT-006-TC1）と`test_ptf_tdd_011_*`の入力を7項目にする。`test_ptf_tdd_012_ptf_012_tc1_edit_keeps_unit_and_buffer_days`は期待が反転するため削除する（PEDT-001-TC1が置き換える）
- `test_purchase_ptf_post.py`: `put_body`に`unit`「パック」・`buffer_days` 0を足す。在庫`2.0`を送るもの（`test_review_focus_5_*`の`2.0`の行、`test_review_focus_3_unrelated_concurrent_write_does_not_recount_stock`の`stock=2.0`）は整数`2`へ直す。それ以外の期待は変えない
- `test_purchase_rev2_post.py`、`test_purchase_uniqueness_rev2.py`、`test_purchase_rename_self_race.py`: `payload()`に同様の既定値を足す。期待は変えない

- [ ] **Step 4: Valid Redを確認する**

Run: `DYNAMODB_LOCAL_PORT=18001 ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q`
Expected: `test_purchase_edit_fields.py`のうち`test_pedt_tdd_009_*`以外が、承認済み契約の未実装（`unit`・`buffer_days`が保存されない、欠落や範囲外を受け付ける、日数0を拒否する、購入単位が変わらない）でFAILする。`test_pedt_tdd_009_*`と書き直した既存テストは、変更前もPASS（Red例外: 回帰・Characterization）。収集失敗、import失敗、fixture不備、既存テストの新規FAILがない。差分にプロダクトコードを含めない。`-m "not integration"`は79 passedのまま

- [ ] **Step 5: TDD計画へRed記録を追記し、コミットする**

TDD計画の「TDD実行記録 / Red」へ、コマンド、終了コード、失敗したassertion、件数、凍結するテストファイル（`test_purchase_edit_fields.py`）、Red記録コミットSHAを記入する。

```bash
git add backend/tests docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md
git commit -m "test: add PEDT backend TDD tests and adapt PUT payloads (Red)"
```

---

### Task 2: Backend Green（`implement-tdd-slice`）

**Files:**
- Modify: `backend/app/api/schemas/purchase.py`、`backend/app/api/purchase.py`、`backend/app/services/purchase_service.py`、`backend/app/domain/purchase.py`
- Modify: `backend/tests/unit/domain/test_purchase_edit.py`（実装と同時に追従。TDD対象外、承認済み）
- Modify: `frontend/src/api/schema.d.ts`（再生成）
- Modify: `docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md`（Green記録）

**Interfaces:**
- Consumes: Task 1の凍結済みテスト
- Produces: `PurchasePutRequest`が7項目必須。`put_purchase(user_id: str, id: UUID, name: str, category: str, unit: str, days_per_unit: int, buffer_days: int, stock: int, is_temporary: bool) -> Purchase`。`apply_edit(current, *, name, category, unit, days_per_unit, buffer_days, stock, is_temporary, now) -> Purchase`。Task 4が使う再生成済みの`PurchasePutRequest`型

- [ ] **Step 1: 凍結済みテストが変更されていないことを確認する**

Run: `git diff <Red記録SHA> -- backend/tests/integration/api/test_purchase_edit_fields.py`
Expected: 差分なし

- [ ] **Step 2: 検証を共有する基底スキーマを導入する**

`backend/app/api/schemas/purchase.py`に`PurchaseWriteRequest(BaseModel)`を追加し、現在の`PurchaseCreateRequest`の7フィールドと`reject_whitespace_only`バリデータ（`name`・`category`・`unit`）をそこへ移す。`PurchaseCreateRequest`と`PurchasePutRequest`は`PurchaseWriteRequest`を継承し、フィールドを持たない（docstringのみ）。OpenAPI上のスキーマ名`PurchaseCreateRequest`・`PurchasePutRequest`は維持する。

- [ ] **Step 3: PUTのエンドポイントとサービス・domainを7項目にする**

- `backend/app/api/purchase.py`の`put_purchase_endpoint`が`unit=request.unit`・`buffer_days=request.buffer_days`も渡す
- `put_purchase`と`apply_edit`を上記Interfacesの署名にする。`apply_edit`は`unit`・`buffer_days`を`current`から引き継がず引数の値で置き換え、`created_at`は引き継ぎ、`stock_counted_at`は在庫が変わったときだけ`now`にする（docstringの「変更できず」の記述を直す）
- `backend/tests/unit/domain/test_purchase_edit.py`を新しい署名に合わせ、`test_review_focus_1_and_ptf_012_*`は「`created_at`が変わらず、`unit`・`buffer_days`が引数の値になる」へ書き直す。他の期待は変えない

- [ ] **Step 4: 全バックエンドテストとlintを確認する**

Run（`backend/`）: `../bin/mise exec -- uv run ruff check .`、`ruff format --check .`、`pytest -m "not integration" -q`、`DYNAMODB_LOCAL_PORT=18001 ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q`
Expected: すべてPASS。`test_purchase_edit_fields.py`は全件PASS

- [ ] **Step 5: フロントエンドのAPI型を再生成する**

Run: `../bin/mise exec -- uv run python -c "import json; from main import app; print(json.dumps(app.openapi()))" > <scratchpadの一時ファイル>`（`backend/`）、`bunx openapi-typescript <同ファイル> -o src/api/schema.d.ts`（`frontend/`）
Expected: `PurchasePutRequest`に`unit`・`buffer_days`が必須で含まれ、差分は`schema.d.ts`のその部分に限られる。`bun run build`が通る

- [ ] **Step 6: TDD計画へGreen記録を追記し、コミットする**

```bash
git add backend frontend/src/api/schema.d.ts docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md
git commit -m "feat: edit all seven purchase fields with registration validation (Green)"
```

---

### Task 3: Frontend Red（PEDT-CORE-007、008、`create-tdd-tests`）

**Files:**
- Create: `frontend/src/features/Purchase.edit.test.tsx`
- Modify: `frontend/src/features/Purchase.ptf.post.test.tsx`（PTF-012-TC1のUI側テスト）
- Modify: `docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md`（Red記録）

**Interfaces:**
- Consumes: Task 2で再生成した`PurchasePutRequest`型。既存の`Purchase`コンポーネントと`queryClient`
- Produces: 凍結済み`Purchase.edit.test.tsx`とRed記録SHA

- [ ] **Step 1: 環境スモークとBaselineを確認する**

Run（`frontend/`）: `bun run test -- --run`
Expected: 97 passed（Baselineと一致）

- [ ] **Step 2: `Purchase.edit.test.tsx`にTDDテストを書く**

`Purchase.ptf.post.test.tsx`と同じ流儀（`vi.hoisted`で`globalThis.fetch`をモック、`renderList`、`userEvent`、一覧を`findByText`して行の「編集」ボタンから開く）。入力欄は`getByLabelText`で`/購入単位/`・`/使い切る日数/`・`/余裕日数/`・`/在庫/`・`/名前/`・`/カテゴリ/`を使い、PUTのボディは`request.clone().text()`で集める。購入物は牛乳／食品／パック／3／余裕2／在庫2／trueと、豆乳／飲料／本／5／余裕0／在庫7／falseの2件を用意する。

| テスト名 | Test Case ID | 主なassertion |
|---|---|---|
| `PEDT-007-TC1/TC2 (PEDT-CORE-007): the edit dialog shows all seven fields with the saved values and re-initialises per purchase` | PEDT-007-TC1、TC2 | 1件目の編集ダイアログに7項目があり、値が1件目の保存済みの値。閉じて2件目を開くと2件目の値になる |
| `PEDT-007-TC4 (PEDT-CORE-007): saving sends all seven fields and the list reflects the change` | PEDT-007-TC4 | `unit`を「本」、余裕日数を4にして保存。PUTのボディが`{name,category,unit:"本",days_per_unit:3,buffer_days:4,stock:2,is_temporary:true}`と等しく、成功後にダイアログが閉じ、一覧の再取得結果（モックが更新後を返す）に「本」と`/余裕\s*4日/`が表示される |
| `PEDT-008-TC1 (PEDT-CORE-008): invalid values are not sent and show a field error` | PEDT-008-TC1 | `test.each`: 購入単位が`""`・`"   "`、使い切る日数が`"1.5"`・`"366"`、余裕日数が`"1.5"`・`"31"`、在庫が`"1.5"`・`"100001"`。保存してもPUTが0件で、その入力欄と同じ項目の枠にエラーの`p`（`CreatePurchaseDialog`と同じ構造）が表示される |
| `PEDT-008-TC2 (PEDT-CORE-008): boundary values are sent` | PEDT-008-TC2 | 使い切る日数0、余裕日数30、在庫100000、購入単位が10文字で保存すると、PUTのボディにその値が入る |

- [ ] **Step 3: 既存のPTF-012-TC1（UI側）をPEDT-010-TC1へ書き直す**

`Purchase.ptf.post.test.tsx`の`PTF-012-TC1 (UI side)`を`PEDT-010-TC1`にし、使い切る日数だけを5に変えて保存したとき、PUTのボディが`{name:"牛乳",category:"食品",unit:"パック",days_per_unit:5,buffer_days:2,stock:2,is_temporary:true}`と等しいことを確認する。`PTF-012-TC2`は変えない。

- [ ] **Step 4: Valid Redを確認する**

Run: `bun run test -- --run`
Expected: 新規テストと書き直したPEDT-010-TC1が、入力欄がない・`unit`と`buffer_days`が送信されない・小数、上限超過、空の購入単位でもPUTが送信される・日数0を拒否する、という承認済み契約の未実装でFAILする。他の既存テストは97件から減らず、収集失敗・import失敗・mockの不備によるFAILがない。差分にプロダクトコードを含めない

- [ ] **Step 5: TDD計画へRed記録を追記し、コミットする**

```bash
git add frontend/src/features docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md
git commit -m "test: add PEDT frontend TDD tests (Red)"
```

---

### Task 4: Frontend Green（`implement-tdd-slice`）

**Files:**
- Create: `frontend/src/features/purchaseFormSchema.ts`
- Modify: `frontend/src/features/CreatePurchaseDialog.tsx`、`frontend/src/features/EditPurchaseDialog.tsx`
- Modify: `docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md`（Green記録）

**Interfaces:**
- Consumes: Task 2の`PurchasePutRequest`型、Task 3の凍結済みテスト
- Produces: `purchaseFormSchema`（Zod、7項目: `name`・`category`・`unit`・`daysPerUnit`・`bufferDays`・`stock`・`isTemporary`）。登録・編集の両ダイアログが共有する

- [ ] **Step 1: 凍結済みテストが変更されていないことを確認する**

Run: `git diff <Red記録SHA> -- frontend/src/features/Purchase.edit.test.tsx frontend/src/features/Purchase.ptf.post.test.tsx`
Expected: 差分なし

- [ ] **Step 2: 検証を共有モジュールへ切り出す**

`frontend/src/features/purchaseFormSchema.ts`を作り、`CreatePurchaseDialog.tsx`の`codePointLength`・`requiredText`・`quantity`・`createPurchaseFormSchema`をそのまま移して`purchaseFormSchema`として`export`する。`CreatePurchaseDialog.tsx`はそれをimportする（登録の振る舞いは変えない）。

- [ ] **Step 3: 編集ダイアログを7項目にする**

`EditPurchaseDialog.tsx`を、`purchaseFormSchema`を使い、`values`に`unit`・`bufferDays`を含め、数値欄を`register(..., { valueAsNumber: true })`（`z.coerce`は使わない）にし、保存時に7項目（`unit`・`buffer_days`を含む）を`PurchasePutRequest`として送る形に変更する。購入単位・余裕日数の入力欄を加え、項目名と説明は`CreatePurchaseDialog`と同じ文言にする（`id`は`edit-`接頭辞のまま）。既存の失敗表示（`更新に失敗しました`）は変えない。

- [ ] **Step 4: フロントエンド全体を確認する**

Run（`frontend/`）: `bun run test -- --run`、`bun run lint`、`bun run format:check`、`bun run build`
Expected: すべてPASS。`Purchase.edit.test.tsx`と書き直したPEDT-010-TC1がGreen。件数はRed前の97件以上

- [ ] **Step 5: TDD計画へGreen記録を追記し、コミットする**

```bash
git add frontend docs/superpowers/specs/2026-11-22-purchase-edit-fields-tdd-plan.md
git commit -m "feat: add unit and buffer days to the edit dialog with shared validation (Green)"
```

---

### Task 5: 検証（`verify-feature-slice`）

**Files:**
- Modify: 凍結済みTDDテストを除くテストコード、fixture、補助関数
- Create: `docs/superpowers/specs/2026-11-22-purchase-edit-fields-post-test-report.md`（[テンプレート](../../templates/post-implementation-test-report.md)）
- Modify（必要な場合のみ）: `e2e/tests/`（編集の代表シナリオ1件）

**Interfaces:**
- Consumes: Task 1〜4の成果物と、TDD計画の候補外一覧
- Produces: 実装後テストレポート。全28件のTest Case IDの割り当て

- [ ] **Step 1: 候補外のTest Case IDを引き継ぎ、検証先を確定する**

TDD計画の候補外8件（PEDT-001-TC3、006-TC4、007-TC3、008-TC3、009-TC3、009-TC4、009-TC5、010-TC2）と、TDD対象の契約に含めきれなかった部分（PEDT-001-TC2の名前・カテゴリ・日数・在庫の欠落）へテストを追加または既存テストを割り当てる。
- 統合: 受け取らない項目（`stock_counted_at`、`created_at`、`updated_at`、`id`、`speed`）を含む編集が200で、保存されず`id`・`created_at`が変わらない（PEDT-001-TC3）。存在しないIDの編集が404で何も作成されない（PEDT-009-TC3）。在庫を変えない複数項目の同時変更で`stock_counted_at`が変わらない（PEDT-006-TC4）
- コンポーネント: 項目名・説明から単位・日数の意味を読み取れる（PEDT-007-TC3）。入力エラーの解除後に保存できる（PEDT-008-TC3）
- 既存テスト: PEDT-009-TC4、009-TC5、010-TC2は書き直し後の既存テスト（`test_purchase_uniqueness_rev2.py`など）を、ID対応表に記録する

- [ ] **Step 2: Review Focusを検証する**

Review Focus 1〜5の各行を、テストの追加または既存テストの確認で消化する（1と3はコンポーネントテスト、2は`grep -rn "purchases" e2e docs README.md`で他のPUT呼び出し元がないことの確認と`e2e/run-e2e.sh`、4と5は統合テスト）。

- [ ] **Step 3: カバレッジ分析と追加テスト**

実装全体を読み、line / branch coverageを取得し、未カバー箇所をCritical / Important / Low risk / Specification gapに分類する。Criticalはテストを追加する。仕様から期待結果を導けないものは決めず、仕様へ戻す。E2Eは編集の代表シナリオ1件（購入単位・余裕日数を変更して一覧に反映）を追加するかを判断し、全境界値をE2Eへ重複させない。

- [ ] **Step 4: 全体検証を実行する**

Run: バックエンドのunit・integration・ruff check・ruff format --check、フロントエンドの`bun run test -- --run`・`lint`・`format:check`・`build`、`e2e/run-e2e.sh`（docker-composeとdevサーバーが必要。起動できない場合は理由と影響を記録する）
Expected: すべてPASS。失敗した検証をskip・削除・期待値の緩和で通過させない

- [ ] **Step 5: 実装後テストレポートを作成し、コミットする**

全28件のTest Case IDを、TDD・単体・コンポーネント・統合・E2E・既存テスト・根拠付き対象外のいずれかへ割り当て、未検証項目・Deferred・既知制約を記録する。

```bash
git add backend/tests frontend/src e2e docs/superpowers/specs/2026-11-22-purchase-edit-fields-post-test-report.md
git commit -m "test: verify PEDT slice and add post-implementation report"
```

---

## 完了後の流れ

検証タスクのCompletion Gateを通過したら、superpowersの最終コードレビュー（`superpowers:requesting-code-review`、仕様・論理テストケース・TDD計画・実装後テストレポートのパスを含める）→ `superpowers:verification-before-completion` → `superpowers:finishing-a-development-branch`の順に進み、人間がマージ（Slice Complete）を判断する。CLAUDE.mdの「現在地」の記述も、マージ前に編集スライスの完了へ更新する。
