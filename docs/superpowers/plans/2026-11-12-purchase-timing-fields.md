# 購入タイミング計算用の登録項目（PTF） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. このリポジトリでは`CLAUDE.md`と`docs/TDD-WORKFLOW.md`がsuperpowersより優先する。`superpowers:test-driven-development`は使わず、Redタスクは`create-tdd-tests`、Greenタスクは`implement-tdd-slice`、検証タスクは`verify-feature-slice`を使う。

**Goal:** 購入物を購入単位・1単位あたりの日数・余裕日数付きで登録し、在庫を数えた日時とともに永続化・一覧表示する。

**Architecture:** `speed`を`days_per_unit`へ改名し、`unit`・`buffer_days`・`stock_counted_at`をPydanticスキーマ → domain → models（DynamoDB）→ 画面まで通す。編集時の「在庫を変えたときだけ在庫を数えた日時を更新し、購入単位・余裕日数・作成日時を引き継ぐ」規則はdomainの純粋関数に置き、modelsの読み取り・再試行ループの中で適用する。

**Tech Stack:** FastAPI、Pydantic v2、boto3（DynamoDB Local）、pytest。React 19、react-hook-form + zod、TanStack Query、openapi-fetch、Vitest + Testing Library。

**Spec:** `docs/superpowers/specs/2026-11-12-purchase-timing-fields-design.md`（PTF-001〜016、2026-11-22承認）。論理テストケース`docs/superpowers/specs/2026-11-12-purchase-timing-fields-test-cases.md`（参照コミット`74eba69`）。TDD計画`docs/superpowers/specs/2026-11-12-purchase-timing-fields-tdd-plan.md`（Test Plan Approved、`cee6f52`）。関連仕様`docs/specs/purchase-create.md`（PURC第3版）。

## Global Constraints

- API名: `unit`、`days_per_unit`、`buffer_days`、`stock`、`stock_counted_at`。旧名`speed`はリクエストで無視し（未知の項目）、レスポンスに含めない
- 登録の`unit`: 必須、空白文字だけは拒否、1〜10文字（コードポイント単位）、正規化・前後空白の除去をしない
- 登録の`days_per_unit`: 必須、JSONの整数のみ（strict）、0〜365
- 登録の`buffer_days`: 必須、JSONの整数のみ（strict）、0〜30。画面の初期値は0
- 登録の`stock`: 0〜100,000の整数（PURC第2版のまま）
- 登録時の`stock_counted_at`は`created_at`と同じ時刻。クライアントの値は使わない
- 編集（PUT）は`unit`と`buffer_days`を受け取らず、保存済みの値を引き継ぐ。在庫が保存済みの値から変わったときだけ`stock_counted_at`をその編集の`updated_at`と同じ時刻にする
- `unit`は重複判定に含めない（名前・カテゴリの完全一致のみ）
- 一覧は在庫と1単位あたりの日数を単位名付きで表示し、`stock_counted_at`を表示しない
- 依存の向き`api → services → domain / models`を守る。TDDテストはRed記録後に凍結し、Greenで変更しない

## Review Focus

1. **編集で作成日時が変わる**: 現在の`put_purchase`は`created_at`を編集時刻で上書きしている。新しい編集処理では保存済みの`created_at`を引き継ぐ。検証タスクで「編集後も作成日時が変わらない」を確認する
2. **新項目のない古いアイテム**: 開発環境のDynamoDB Localに`speed`形式のアイテムが残っていると、一覧取得で検証エラーになる。仕様どおり移行はしないが、検証タスクで挙動を確認し、PRに「ローカルのデータを作り直す」手順を書く
3. **編集の競合と在庫比較**: 再試行のたびに最新の保存値と比べて`stock_counted_at`を決める必要がある。検証タスクで、編集が再試行された場合も最新値と比べることを確認する
4. **日時の形式**: `stock_counted_at`は`created_at`と同じUTCのISO 8601文字列で保存・返却する。検証タスクで形式をそろえて確認する
5. **在庫の比較の型**: PUTの在庫は小数を受け付ける（既存の検証のまま）。`2`と`2.0`は同じ在庫として扱われ、`stock_counted_at`を更新しない。検証タスクで確認する

---

### Task 1: Backend Red（PTF-CORE-001〜007、`create-tdd-tests`）

**Files:**
- Create: `backend/tests/integration/api/test_purchase_ptf.py`
- Modify: `backend/tests/integration/api/test_purchase_create.py`、`test_purchase_create_post.py`、`test_purchase_rev2_post.py`、`test_purchase_uniqueness_rev2.py`、`test_purchase_rename_self_race.py`、`backend/tests/unit/api/test_purchase_create_errors.py`（PURC第3版への読み替え）
- Modify: `docs/superpowers/specs/2026-11-12-purchase-timing-fields-tdd-plan.md`（Red記録）

**Interfaces:**
- Consumes: なし（HTTP契約だけを使う）
- Produces: 凍結済みテストファイル`test_purchase_ptf.py`とRed記録SHA

- [ ] **Step 1: 環境スモークとBaselineを確認する**

Run（`backend/`）: `../bin/mise exec -- uv run pytest -m "not integration" -q` と `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration -q`
Expected: 73 passed / 90 passed（TDD計画のBaselineと一致）

- [ ] **Step 2: `test_purchase_ptf.py`にTDDテスト12件を書く**

既存の`test_purchase_create.py`と同じく`pytestmark = pytest.mark.integration`、`client`フィクスチャ、`as_user`を使う。基準入力は`{"name": "牛乳", "category": "食品", "unit": "パック", "days_per_unit": 3, "buffer_days": 0, "stock": 2, "is_temporary": False}`。「永続化されない」は`GET /purchases`が空であることで確かめる。テスト名にTest Case IDを入れる。

| テスト名 | Test Case ID | 主なassertion |
|---|---|---|
| `test_ptf_tdd_001_ptf_008_tc1_create_returns_new_fields` | PTF-008-TC1 | 201。`unit == "パック"`、`days_per_unit == 3`、`buffer_days == 0`、`stock_counted_at == created_at`、`"speed" not in body` |
| `test_ptf_tdd_002_ptf_011_tc1_list_reads_back_new_fields` | PTF-011-TC1 | 登録後の`GET /purchases`の1件が、登録レスポンスの`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`と一致 |
| `test_ptf_tdd_003_ptf_006_tc2_client_stock_counted_at_is_ignored` | PTF-006-TC2 | `stock_counted_at: "2000-01-01T00:00:00Z"`を付けて201。`stock_counted_at == created_at`かつ`!= "2000-01-01T00:00:00Z"` |
| `test_ptf_tdd_004_ptf_002_tc2_days_per_unit_366_is_rejected` | PTF-002-TC2 | `days_per_unit=366`で422、`detail[].loc`に`["body", "days_per_unit"]`、一覧が空 |
| `test_ptf_tdd_005_ptf_001_tc3_legacy_speed_only_is_rejected` | PTF-001-TC3 | `days_per_unit`を除き`speed: 3`を付けて422、`loc`に`["body", "days_per_unit"]`、一覧が空 |
| `test_ptf_tdd_006_ptf_003_tc4_missing_buffer_days_is_rejected` | PTF-003-TC4 | `buffer_days`を除いて422、`loc`に`["body", "buffer_days"]`、一覧が空 |
| `test_ptf_tdd_007_ptf_003_tc3_buffer_days_31_is_rejected` | PTF-003-TC3 | `buffer_days=31`で422、`loc`に`["body", "buffer_days"]`、一覧が空 |
| `test_ptf_tdd_008_ptf_014_tc1_missing_unit_is_rejected` | PTF-014-TC1 | `unit`を除いて422、`loc`に`["body", "unit"]`、一覧が空 |
| `test_ptf_tdd_009_ptf_014_tc4_unit_of_11_chars_is_rejected` | PTF-014-TC4 | `unit="あ" * 11`で422、`loc`に`["body", "unit"]`、一覧が空 |
| `test_ptf_tdd_010_ptf_013_tc1_stock_edit_recounts_at_updated_at` | PTF-013-TC1 | 登録後、`PUT /purchases/{id}`で`{"name": "牛乳", "category": "食品", "days_per_unit": 3, "stock": 5, "is_temporary": False}`。200。`stock_counted_at == updated_at`かつ登録時の`stock_counted_at`より後。`GET`でも同じ値 |
| `test_ptf_tdd_011_ptf_007_tc1_rename_keeps_stock_counted_at` | PTF-007-TC1 | `PUT`で名前・カテゴリだけ変更（在庫2のまま）。`updated_at`は登録時より後、`stock_counted_at`は登録時の値のまま |
| `test_ptf_tdd_012_ptf_012_tc1_edit_keeps_unit_and_buffer_days` | PTF-012-TC1 | `buffer_days=2`で登録し、`PUT`で`days_per_unit=5`。レスポンスと`GET`で`days_per_unit == 5`、`unit == "パック"`、`buffer_days == 2` |

時刻の前後比較は`datetime.fromisoformat`で行う。登録とPUTの間で時刻が同じになるのを避けるため、PUTの前に`time.sleep(0.01)`を置く。

- [ ] **Step 3: PURC第2版の既存テストを第3版へ読み替える**

基準入力を上の基準入力へ置き換え、`speed`を`days_per_unit`へ読み替える。期待動作が第3版で変わるものだけ期待値を変える: PURC-004-TC7/8（`speed`の範囲 → `days_per_unit`の0・365と366・負数・小数）、5項目の確認（→ PTFの項目）。`test_purchase_create_post.py:266`の`PurchaseItem(...)`の直接生成は、Task 2で追加する`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`を渡す形にする。各ファイルの変更理由をRed記録に1行ずつ書く。

- [ ] **Step 4: Valid Redを確認する**

Run（`backend/`）: `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q`
Expected: 12 failed。失敗理由は新項目の未実装（`KeyError`/422で`unit`等が未知、`speed`だけで201など）。収集エラー・import エラー・環境エラーがない。読み替えた既存テストも未実装を理由に失敗する

- [ ] **Step 5: Red記録を書いてコミットする**

TDD計画の「TDD実行記録 > Red」へ、コマンド、件数、代表的な失敗、凍結ファイル（`backend/tests/integration/api/test_purchase_ptf.py`）を記録する。

```bash
git add backend/tests docs/superpowers/specs/2026-11-12-purchase-timing-fields-tdd-plan.md
git commit -m "test: add PTF backend TDD tests and adapt PURC tests to v3 (Red)"
```

---

### Task 2: Backend Green（`implement-tdd-slice`）

**Files:**
- Modify: `backend/app/domain/purchase.py`、`backend/app/models/purchase.py`、`backend/app/services/purchase_service.py`、`backend/app/api/purchase.py`、`backend/app/api/schemas/purchase.py`
- Modify: `frontend/src/api/schema.d.ts`（OpenAPIから再生成）
- Modify: TDD計画（Green記録）

**Interfaces:**
- Consumes: Task 1の凍結テスト
- Produces:
  - `domain.Purchase`: `id: UUID, user_id: str, name: str, category: str, unit: str, days_per_unit: float, buffer_days: int, stock: float, is_temporary: bool, stock_counted_at: datetime, created_at: datetime, updated_at: datetime`
  - `domain.apply_edit(current: Purchase, *, name: str, category: str, days_per_unit: float, stock: float, is_temporary: bool, now: datetime) -> Purchase`
  - `models.put_purchase_item(user_id: str, id: UUID, edit: Callable[[Purchase], Purchase], *, table_name: str | None = None) -> PurchaseItem`
  - `services.create_purchase(user_id, name, category, unit, days_per_unit, buffer_days, stock, is_temporary) -> Purchase`
  - `services.put_purchase(user_id, id, name, category, days_per_unit, stock, is_temporary) -> Purchase`
  - OpenAPIの`PurchaseCreateRequest`・`PurchasePutRequest`・`PurchaseResponse`（Global Constraintsの項目名）

- [ ] **Step 1: 凍結テストが未変更であることを確認する**

Run: `git diff <Red記録SHA> -- backend/tests/integration/api/test_purchase_ptf.py`
Expected: 差分なし

- [ ] **Step 2: domainに項目と`apply_edit`を追加する**

`Purchase`へ`unit`、`days_per_unit`（`speed`を改名）、`buffer_days`、`stock_counted_at`を追加する。`apply_edit`は`id`・`user_id`・`unit`・`buffer_days`・`created_at`を`current`から引き継ぎ、`updated_at = now`、`stock_counted_at = now if stock != current.stock else current.stock_counted_at`とした新しい`Purchase`を返す。

- [ ] **Step 3: modelsを更新する**

`PurchaseItem`へ同じ項目を追加し、`from_domain`は`created_at`・`updated_at`・`stock_counted_at`も渡す。`put_purchase_item`は再試行ループ内で`_read_current`の結果に`edit(old.to_domain())`を適用して書き込むアイテムを作る（重複判定・条件付き書き込み・再試行の既存ロジックはそのまま）。

- [ ] **Step 4: servicesとapiを更新する**

`create_purchase`は`now = datetime.now(UTC)`を1回取り、`created_at = updated_at = stock_counted_at = now`。`put_purchase`は`put_purchase_item(user_id, id, edit=lambda current: apply_edit(current, ..., now=datetime.now(UTC)))`。`PurchaseCreateRequest`に`unit: str = Field(min_length=1, max_length=10)`（`reject_whitespace_only`の対象に追加）、`days_per_unit: int = Field(ge=0, le=365, strict=True)`、`buffer_days: int = Field(ge=0, le=30, strict=True)`。`PurchasePutRequest`は`speed`を`days_per_unit`へ改名するだけ（`float`、`gt=0`のまま）。`PurchaseResponse`は`speed`を外し、`unit: str`、`days_per_unit: float`、`buffer_days: int`、`stock_counted_at: datetime`を追加。

- [ ] **Step 5: TDDテストと回帰を確認する**

Run（`backend/`）: `../bin/mise exec -- uv run ruff check . && ../bin/mise exec -- uv run ruff format --check . && ../bin/mise exec -- uv run pytest -m "not integration" -q && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration -q`
Expected: すべてPass（`test_purchase_ptf.py`の12件を含む）

- [ ] **Step 6: `schema.d.ts`を再生成する**

`backend/`でuvicornを起動し（`../bin/mise exec -- uv run uvicorn main:app --port 8000`）、`frontend/`で`bun run gen:api`を実行して停止する。`schema.d.ts`に`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`があり、`speed`がないことを確認する。この時点でfrontendの型検査は失敗してよい（Task 4で解消）。

- [ ] **Step 7: Green記録を書いてコミットする**

```bash
git add backend/app frontend/src/api/schema.d.ts docs/superpowers/specs/2026-11-12-purchase-timing-fields-tdd-plan.md
git commit -m "feat: add unit, days_per_unit, buffer_days and stock_counted_at to purchases (Green)"
```

---

### Task 3: Frontend Red（PTF-CORE-008、009、`create-tdd-tests`）

**Files:**
- Create: `frontend/src/features/CreatePurchaseDialog.ptf.test.tsx`、`frontend/src/features/Purchase.ptf.test.tsx`
- Modify: `frontend/src/features/CreatePurchaseDialog.test.tsx`、`CreatePurchaseDialog.post.test.tsx`、`CreatePurchaseDialog.rev2.test.tsx`、`CreatePurchaseDialog.rev2.post.test.tsx`、`Purchase.test.tsx`、`Purchase.post.test.tsx`（PURC第3版への読み替え）
- Modify: TDD計画（Red記録）

**Interfaces:**
- Consumes: Task 2の`schema.d.ts`（`PurchaseResponse`の新項目）
- Produces: 凍結済みテストファイル2件とRed記録SHA

- [ ] **Step 1: TDDテスト3件を書く**

既存の`CreatePurchaseDialog.rev2.test.tsx`と同じく`globalThis.fetch`をmockし、`Purchase`画面を描画して操作する。入力欄はラベル（正規表現）で取得する: 購入単位`/購入単位/`、1単位あたりの日数`/使い切る日数/`、余裕日数`/余裕日数/`、在庫`/在庫/`。

| テスト名 | Test Case ID | 主なassertion |
|---|---|---|
| `PTF-TDD-013 (PTF-001-TC1): the create dialog has the seven fields` | PTF-001-TC1 | 名前、カテゴリ、購入単位、使い切る日数、余裕日数、在庫の入力欄と、一時的な購入のチェックボックスがある |
| `PTF-TDD-014 (PTF-003-TC5): untouched buffer days is sent as 0` | PTF-003-TC5 | 名前・カテゴリ・購入単位「パック」・日数3・在庫2を入れて登録。POSTの本文が`{name: "牛乳", category: "食品", unit: "パック", days_per_unit: 3, buffer_days: 0, stock: 2, is_temporary: false}`と一致 |
| `PTF-TDD-015 (PTF-015-TC2): the list shows stock and days with the unit` | PTF-015-TC2 | `GET`が`unit: "パック", days_per_unit: 3, stock: 2`の1件を返す。一覧に`2パック`と`1パック3日`を含む文字列がある |

- [ ] **Step 2: 既存のfrontendテストを読み替える**

`speed`と「消費スピード」のラベルを、`days_per_unit`と`/使い切る日数/`へ読み替え、mockのレスポンスにPTFの項目を加える。5項目の確認と`speed`の範囲（0〜100,000）を前提にするものだけ、PTFの項目と範囲（0〜365）に変える。

- [ ] **Step 3: Valid Redを確認する**

Run（`frontend/`）: `bun run test -- --run src/features/CreatePurchaseDialog.ptf.test.tsx src/features/Purchase.ptf.test.tsx`
Expected: 3 failed。理由は入力欄・表示の未実装（ラベルが見つからない、POST本文に`unit`がない、`2パック`が表示されない）。

- [ ] **Step 4: Red記録を書いてコミットする**

```bash
git add frontend/src/features docs/superpowers/specs/2026-11-12-purchase-timing-fields-tdd-plan.md
git commit -m "test: add PTF frontend TDD tests and adapt PURC tests to v3 (Red)"
```

---

### Task 4: Frontend Green（`implement-tdd-slice`）

**Files:**
- Modify: `frontend/src/features/CreatePurchaseDialog.tsx`、`frontend/src/features/Purchase.tsx`、`frontend/src/features/EditPurchaseDialog.tsx`
- Modify: TDD計画（Green記録）

**Interfaces:**
- Consumes: Task 2の`schema.d.ts`、Task 3の凍結テスト
- Produces: PTFの登録画面・一覧表示

- [ ] **Step 1: 凍結テストが未変更であることを確認する**

Run: `git diff <Task 3のRed記録SHA> -- frontend/src/features/CreatePurchaseDialog.ptf.test.tsx frontend/src/features/Purchase.ptf.test.tsx`
Expected: 差分なし

- [ ] **Step 2: 登録画面を更新する**

フォーム項目を`name`、`category`、`unit`、`daysPerUnit`、`bufferDays`、`stock`、`isTemporary`にする。`unit`は`requiredText("購入単位を入力してください", 10)`。`daysPerUnit`・`bufferDays`は既存の`quantity`と同じ整数検証で上限をそれぞれ365・30にする（`quantity`に上限の引数を足す）。初期値は空・0・0。`apiFieldToFormField`に`unit`・`days_per_unit`・`buffer_days`を加える。ラベル: 「購入単位（パック、本など）」「1単位を使い切る日数（日）」「余裕日数（日）」「在庫（購入単位の数）」。

- [ ] **Step 3: 一覧と編集画面を更新する**

一覧は`消費スピード {speed}`を`1{unit}{days_per_unit}日`と`余裕 {buffer_days}日`の表示に、在庫のバッジを`在庫 {stock}{unit}`にする。`EditPurchaseDialog`は`speed`を`days_per_unit`へ改名し、ラベルを「1単位を使い切る日数（日）」にする（検証は既存のまま）。

- [ ] **Step 4: TDDテストと回帰を確認する**

Run（`frontend/`）: `bun run lint && bun run format:check && bun run test -- --run && bun run build`
Expected: すべてPass

- [ ] **Step 5: Green記録を書いてコミットする**

```bash
git add frontend/src docs/superpowers/specs/2026-11-12-purchase-timing-fields-tdd-plan.md
git commit -m "feat: show and register purchase unit, days per unit and buffer days (Green)"
```

---

### Task 5: 検証（`verify-feature-slice`）

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-purchase-timing-fields-post-test-report.md`
- Modify/Create: 実装後テスト（凍結済みTDDテストを除く）、`e2e/tests/purchase-create.spec.ts`

**Interfaces:**
- Consumes: Task 1〜4の成果物
- Produces: 実装後テストレポート、全Test Case IDの割り当て

- [ ] **Step 1: TDD計画の候補外9件と、最小セットから外した中心的契約のTest Case IDを実装後テストで検証する**
- [ ] **Step 2: Review Focusの5項目をテストまたは確認記録で消化する**
- [ ] **Step 3: E2Eを新しい項目に合わせて更新する**（購入単位・日数・余裕日数を入力して登録し、再読み込み後の一覧に単位名付きで表示されること）
- [ ] **Step 4: 全体検証を実行する**

Run: Backendのruff check / format check / unit / integration、Frontendのlint / format check / test / build、`bash e2e/run-e2e.sh`
Expected: すべてPass。実行できない検証は内容・理由・影響をレポートに書く

- [ ] **Step 5: 実装後テストレポートを書いてコミットする**

```bash
git add backend/tests frontend/src e2e/tests docs/superpowers/specs/2026-11-12-purchase-timing-fields-post-test-report.md
git commit -m "test: verify PTF slice and add post-implementation report"
```
