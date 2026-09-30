# 購入物登録・一覧反映 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **このリポジトリ固有の規則（`CLAUDE.md`と`docs/TDD-WORKFLOW.md`がsuperpowersより優先）:** `superpowers:test-driven-development`は使わない。Redタスクは`create-tdd-tests`、Greenタスクは`implement-tdd-slice`、検証タスクは`verify-feature-slice`のSkillに従う。実装前テストは承認済みTDD計画の7項目だけで、それ以外のテストは検証タスク（Task 7）で追加する。凍結済みTDDテストは変更しない。仕様・期待結果に関わる判断をRulingで決めず、仕様から一意に導けない場合は停止して人間へ戻す。

**Goal:** 利用者が購入物を1件登録し、現在の利用者に紐づいて永続化された結果を一覧で確認できるようにする（仕様PURC-001〜019）。

**Architecture:** 既存のFastAPI + DynamoDB（シングルテーブル）+ React（TanStack Query、react-hook-form + zod）の購入物CRUDをretrofitする。APIはPydanticスキーマで入力領域を検証し、名前・カテゴリの重複は購入物本体と一意性マーカーを1つのDynamoDBトランザクションで書くことで同時要求を含めて防ぐ。フロントエンドは同じ入力領域をzodで検証し、APIの失敗を原因別に表示する。

**Tech Stack:** Python 3.14.7 / FastAPI / Pydantic v2 / boto3（DynamoDB Local 3.3.1）/ pytest、React 19 / TypeScript / TanStack Query 5 / react-hook-form 7 / zod 4 / Vitest 4 / Testing Library、Bun

**Spec:** `docs/specs/purchase-create.md`（Approved 2026-09-15）

**TDD inputs:**
- 論理テストケース: `docs/specs/purchase-create-test-cases.md`（参照コミット`69a00dc62c32ec80af59a7ad5875e564d039d57e`。以後`HEAD`まで仕様・論理テストケースとも変更なしを確認済み）
- TDD計画: `docs/specs/purchase-create-tdd-plan.md`（Core Contract Gate 2026-09-17、Test Plan Gate 2026-09-18 承認済み。中心的契約PURC-CORE-001〜004、最小TDDセットPURC-TDD-001〜007）
- 契約: `docs/TDD-WORKFLOW.md`

## Global Constraints

- 名前: 必須、空白文字だけは不可、50文字以内。カテゴリ: 必須、空白文字だけは不可、30文字以内
- 消費スピード・現在の在庫: 必須、0以上100,000以下の整数。小数・負数・上限超過は丸めず切り詰めず拒否する。消費スピード0は有効（`is_temporary`とは独立）
- 一時的な購入（`is_temporary`）: 必須のtrue / false。画面の初期値はfalse、名前・カテゴリは空、消費スピード・在庫は0
- 入力文字列は正規化しない（前後空白を除去しない、大文字・小文字や全角・半角を同一視しない）
- 利用者IDはクライアントから受け取らず、サーバー側の現在利用者から決める。レスポンスに利用者IDを含めない
- 重複: 同一利用者で名前とカテゴリの両方が完全一致する購入物は1件まで。同時登録もバックエンドの永続化で防ぐ。消費スピード・在庫・`is_temporary`の違いは考慮しない
- API: 成功は201で作成した購入物（ID、名前、カテゴリ、消費スピード、在庫、一時的な購入、作成日時、更新日時）を返す。入力制約違反は422で問題の項目を識別でき、永続化しない。重複は409で永続化しない。その他の失敗で内部情報を返さない
- 画面: 登録中は登録操作を無効化する。成功後は画面を閉じ、入力を初期化し、一覧を再取得する。成功メッセージやトーストは出さない。失敗時は画面を閉じず5項目を維持し、判明した原因は個別に、その他は共通エラーで表示する。自動再送しない
- 日本語文言は固定しない。原因と必要な対処が伝わることが契約
- 対象外: 編集・削除の仕様化、在庫の消費・補充、購入予定計算、通知、並び順、検索・ページネーション、カテゴリ候補、Cognito実装、冪等性キー、本番デプロイ、細かなUI装飾

## 既知の制約（人間の判断 2026-09-30）

一意性マーカーの導入に伴い、既存の削除は購入物本体に加えてマーカーも削除し、「削除後に同じ名前・カテゴリを再登録できる」既存の挙動を維持する（Task 3）。編集（PUT）はこのスライスで変更しない。そのため次を既知の制約とし、編集スライスで仕様化する。検証タスクは実装後テストレポートの残存リスクへ記録する。

- 編集で名前・カテゴリを変えると、変更前の組のマーカーが残り、その組で新規登録すると409になる
- 編集では名前・カテゴリの重複を防がない
- マーカー導入前に作成された購入物（開発用データ）はマーカーを持たないため、同じ組の新規登録を重複として検出しない

## Review Focus

TDDテストが直接検証しないが、仕様から導かれ利用者に影響しやすい入力・失敗モード。`docs/TDD-WORKFLOW.md`により実装前テストは追加せず、**Task 7（検証タスク）で必ずテストを追加する**。

1. 全角空白（U+3000）だけの名前・カテゴリ → 画面とAPIの両方で入力エラー、永続化されない（PURC-004-TC1/TC2）
2. 数値欄を空にして送信 → 0として登録されず入力エラー。APIへ項目を欠いた要求 → 422で欠けた項目を識別（PURC-003-TC3）
3. サロゲートペアを含む名前（例: `𠮷`を50文字）→ 画面とAPIが同じ数え方で受け付ける。51文字は両方で拒否（PURC-004-TC3/TC4）
4. 登録した購入物を削除した後、同じ名前・カテゴリで再登録 → 201（既存挙動の維持、IMPL-RISK-001）
5. 409・422・500・通信断のそれぞれで、画面が開いたまま5項目が維持され、原因別または共通のエラーが表示され、自動再送されない（PURC-015〜018）

## 実行環境

リポジトリ直下で一度だけ実行する（Environment Gateと同じ経路）。

```bash
bash scripts/setup_host_prerequisites.sh --install
bash scripts/setup_host_prerequisites.sh --check
(cd backend && ../bin/mise exec -- uv sync --python 3.14.7 --frozen)
(cd frontend && bun install --frozen-lockfile)
```

よく使うコマンド（`backend/`から）:

- unit: `../bin/mise exec -- uv run pytest -m "not integration" -q`
- 環境スモーク: `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/test_environment.py -q`
- 購入物登録TDD: `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/api/test_purchase_create.py -q`
- integration全体: `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q`
- lint / format: `../bin/mise exec -- uv run ruff check . && ../bin/mise exec -- uv run ruff format --check .`

ランナーが`ENVIRONMENT_FAILURE`（終了コード70）を返した場合は機能テストの失敗として扱わず停止し、`setup-test-environment`で確認する。

`tests/integration/`配下のテストはランナー外で実行するとconftestが`ENVIRONMENT_FAILURE`で終了するため、新しいテストファイルにも必ず`pytestmark = pytest.mark.integration`を付ける。

## File Structure

| ファイル | 責務 | タスク |
|---|---|---|
| `backend/pyproject.toml`, `backend/uv.lock` | dev依存`httpx2`（Starlette TestClientの必須依存）を追加 | 1 |
| `backend/tests/integration/api/__init__.py` | テストパッケージ | 1 |
| `backend/tests/integration/api/test_purchase_create.py` | **凍結対象** PURC-TDD-001/004/005/006/007 | 1 |
| `backend/app/api/schemas/purchase.py` | 登録リクエストの入力領域（`PurchaseCreateRequest`） | 2 |
| `backend/app/models/purchase.py` | 一意性マーカー、トランザクション登録、一覧の前方一致、削除時のマーカー削除 | 3 |
| `frontend/src/features/Purchase.test.tsx` | **凍結対象** PURC-TDD-002 | 4 |
| `frontend/src/features/CreatePurchaseDialog.test.tsx` | **凍結対象** PURC-TDD-003 | 4 |
| `.github/workflows/test.yml`, `CLAUDE.md` | frontendテストの`--passWithNoTests`を外す | 4 |
| `frontend/src/features/CreatePurchaseDialog.tsx` | 入力検証（Task 5）、失敗表示（Task 6） | 5, 6 |
| `frontend/src/features/Purchase.tsx` | 一覧に消費スピードを表示 | 5 |
| `frontend/src/api/schema.d.ts` | APIスキーマ変更に合わせて再生成 | 5 |
| `frontend/package.json` | buildの順序を`vite build && tsc -b`へ変更（GAP-003） | 5 |
| `frontend/src/api/purchases.ts` | HTTPステータスを保持する`ApiError` | 6 |
| `frontend/src/hooks/usePurchases.ts` | 登録mutationの自動再送を明示的に無効化 | 6 |
| `docs/specs/purchase-create-tdd-plan.md` | Red / Green実行記録 | 1, 2, 3, 4, 5 |
| `docs/specs/purchase-create-post-test-report.md` ほか追加テスト | 実装後テスト | 7 |

## タスク構成とTDD計画の対応

| Task | 種別 | Skill | TDD Plan ID | Contract ID |
|---|---|---|---|---|
| 1 | Red（Backend） | `create-tdd-tests` | PURC-TDD-001, 004, 005, 006, 007 | CORE-001〜004 |
| 2 | Green（Backend入力領域） | `implement-tdd-slice` | PURC-TDD-001, 004 | CORE-001, 002 |
| 3 | Green（Backend重複防止） | `implement-tdd-slice` | PURC-TDD-006（005, 007を維持） | CORE-004, 003 |
| 4 | Red（Frontend） | `create-tdd-tests` | PURC-TDD-002, 003 | CORE-001, 002 |
| 5 | Green（Frontend入力と一覧） | `implement-tdd-slice` | PURC-TDD-002, 003 | CORE-001, 002 |
| 6 | TDD対象外の実装（失敗表示） | `implement-tdd-slice`の変更境界に従う | なし（Task 7で検証） | — |
| 7 | 検証 | `verify-feature-slice` | 全Test Case ID | — |

`docs/TDD-WORKFLOW.md` 5.4は契約ごとのRed/Greenを求める。同じテストファイルを共有するBackend 4契約は1つのRedタスクにまとめ、Greenは独立して却下できる単位（入力領域／重複防止）に分けた。Frontendも同様にまとめた。各RedはそのGreenより前にある。

---

### Task 1: Backend TDDテスト作成とValid Red（Redタスク）

**Skill:** `create-tdd-tests`（プロダクトコードを変更しない）

**Files:**
- Modify: `backend/pyproject.toml`, `backend/uv.lock`（`uv add --dev httpx2`で生成）
- Create: `backend/tests/integration/api/__init__.py`（空ファイル）
- Create: `backend/tests/integration/api/test_purchase_create.py`
- Modify: `docs/specs/purchase-create-tdd-plan.md`（「TDD実行記録」へ追記）

**Interfaces:**
- Consumes: `main.app`（FastAPI）、`app.api.deps.get_current_user_id`（dependency override対象。GAP-001の決定どおり認証基盤ではなく利用者識別結果を差し替える）
- Produces: 凍結テスト`backend/tests/integration/api/test_purchase_create.py`。API契約: `POST /purchases`、`GET /purchases`、登録ボディ`{name, category, speed, stock, is_temporary}`

- [ ] **Step 1: 環境スモークとBaselineを確認する**

```bash
bash scripts/setup_host_prerequisites.sh --check
cd backend
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/test_environment.py -q
../bin/mise exec -- uv run pytest -m "not integration" -q
../bin/mise exec -- uv run ruff check . && ../bin/mise exec -- uv run ruff format --check .
```

Expected: 環境スモークPass（ランナー出力に`API ready check: PASS`、`Child command exit: 0`）、unit `72 passed`、ruff Pass。環境スモークが失敗したら`ENVIRONMENT_FAILURE`で停止する。

- [ ] **Step 2: TestClientの依存を追加する**

```bash
cd backend
../bin/mise exec -- uv add --dev httpx2
```

Expected: `backend/pyproject.toml`に`[dependency-groups] dev = ["httpx2>=2.13.1"]`が追加され、`uv.lock`が更新される（Starlette TestClientが`httpx2`を要求するため。テスト実行に必要な最小設定）。

- [ ] **Step 3: TDDテストを書く**

`backend/tests/integration/api/__init__.py`を空で作成し、`backend/tests/integration/api/test_purchase_create.py`を次の内容で作成する。

```python
"""購入物登録APIのTDDテスト。

docs/specs/purchase-create-tdd-plan.md の PURC-TDD-001, 004, 005, 006, 007。
期待結果は docs/specs/purchase-create-test-cases.md のTest Case IDを参照する。
"""

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from main import app

pytestmark = pytest.mark.integration

USER_A = "user-a"
USER_B = "user-b"

VALID_INPUT: dict[str, Any] = {
    "name": "牛乳",
    "category": "食品",
    "speed": 1,
    "stock": 2,
    "is_temporary": False,
}

RESPONSE_FIELDS = {
    "id",
    "name",
    "category",
    "speed",
    "stock",
    "is_temporary",
    "created_at",
    "updated_at",
}


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def act_as(user_id: str) -> None:
    """認証基盤ではなく、確定済みの利用者識別結果を境界入力として差し替える（GAP-001）。"""
    app.dependency_overrides[get_current_user_id] = lambda: user_id


def list_purchases(client: TestClient, user_id: str) -> list[dict[str, Any]]:
    act_as(user_id)
    response = client.get("/purchases")
    assert response.status_code == 200
    return response.json()


def test_purc_tdd_001_valid_input_with_speed_zero_is_created_for_current_user_and_listed() -> None:
    """PURC-005-TC1, PURC-008-TC1, PURC-008-TC2, PURC-008-TC3, PURC-009-TC1, PURC-004-TC12"""
    client = TestClient(app)
    act_as(USER_A)
    payload = {**VALID_INPUT, "speed": 0}

    response = client.post("/purchases", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == RESPONSE_FIELDS
    assert "user_id" not in body
    assert body["name"] == "牛乳"
    assert body["category"] == "食品"
    assert body["speed"] == 0
    assert body["stock"] == 2
    assert body["is_temporary"] is False
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]

    assert list_purchases(client, USER_A) == [body]


def test_purc_tdd_004_api_rejects_whitespace_only_name_without_persisting() -> None:
    """PURC-003-TC2"""
    client = TestClient(app)
    act_as(USER_A)

    response = client.post("/purchases", json={**VALID_INPUT, "name": "   "})

    assert response.status_code == 422
    locations = [error["loc"] for error in response.json()["detail"]]
    assert ["body", "name"] in locations
    assert list_purchases(client, USER_A) == []


def test_purc_tdd_005_owner_comes_from_current_user_not_request_body() -> None:
    """PURC-007-TC1, PURC-019-TC2"""
    client = TestClient(app)
    act_as(USER_A)

    response = client.post("/purchases", json={**VALID_INPUT, "user_id": USER_B})

    assert response.status_code == 201
    created_id = response.json()["id"]
    assert [item["id"] for item in list_purchases(client, USER_A)] == [created_id]
    assert list_purchases(client, USER_B) == []


def test_purc_tdd_006_concurrent_duplicates_persist_exactly_one_purchase() -> None:
    """PURC-014-TC8"""
    act_as(USER_A)
    attempts = 5
    barrier = threading.Barrier(attempts)

    def register() -> int:
        with TestClient(app) as client:
            barrier.wait()
            return client.post("/purchases", json=VALID_INPUT).status_code

    with ThreadPoolExecutor(max_workers=attempts) as executor:
        statuses = sorted(executor.map(lambda _: register(), range(attempts)))

    assert statuses == [201] + [409] * (attempts - 1)
    assert len(list_purchases(TestClient(app), USER_A)) == 1


def test_purc_tdd_007_same_name_and_category_are_allowed_for_different_users() -> None:
    """PURC-014-TC7"""
    client = TestClient(app)

    act_as(USER_A)
    first = client.post("/purchases", json=VALID_INPUT)
    act_as(USER_B)
    second = client.post("/purchases", json=VALID_INPUT)

    assert first.status_code == 201
    assert second.status_code == 201
    assert len(list_purchases(client, USER_A)) == 1
    assert len(list_purchases(client, USER_B)) == 1
```

- [ ] **Step 4: Redを確認する**

```bash
cd backend
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/api/test_purchase_create.py -q
```

Expected: `3 failed, 2 passed`。

| テスト | 期待する結果 | Valid Redの根拠 |
|---|---|---|
| PURC-TDD-001 | FAIL `assert 422 == 201` | 現行APIが`speed=0`を拒否する（契約未実装） |
| PURC-TDD-004 | FAIL `assert 201 == 422` | 空白だけの名前を受け付ける（契約未実装） |
| PURC-TDD-005 | PASS | 承認済みRed例外（既存dependencyとスキーマが満たす代表回帰） |
| PURC-TDD-006 | FAIL `assert [201, 201, 201, 201, 201] == [201, 409, 409, 409, 409]` | 名前・カテゴリの重複を防がない（契約未実装） |
| PURC-TDD-007 | PASS | 承認済みRed例外（利用者スコープの代表回帰） |

収集エラー、import失敗、`ENVIRONMENT_FAILURE`、上表と異なる理由の失敗は`INVALID_RED`として同じタスク内でテストを直す（プロダクトコードは変えない）。001/004/006のいずれかがPASSした場合も`INVALID_RED`として停止し、人間へ報告する。

- [ ] **Step 5: lintと差分を確認する**

```bash
cd backend
../bin/mise exec -- uv run ruff format . && ../bin/mise exec -- uv run ruff check --fix .
../bin/mise exec -- uv run pytest -m "not integration" -q
git status --short
```

Expected: ruff Pass、unit `72 passed`。変更は`backend/pyproject.toml`、`backend/uv.lock`、`backend/tests/integration/api/`だけで、`backend/app/`と`backend/main.py`に差分がない。

- [ ] **Step 6: テストをコミットする**

```bash
git add backend/pyproject.toml backend/uv.lock backend/tests/integration/api/
git commit -m "test: add purchase-create backend TDD tests (Red)"
```

- [ ] **Step 7: Red記録を追記してコミットする**

`docs/specs/purchase-create-tdd-plan.md`の「## TDD実行記録」の説明文の直後へ、Step 4の実際の出力で次を追記する。`<Step 6のSHA>`は`git rev-parse HEAD`の値。

```markdown
### Red（Backend）

- 実装計画のRedタスク: `docs/superpowers/plans/2026-09-30-purchase-create.md` Task 1
- 環境スモーク・Baselineの結果: 環境スモークPass、unit 72 passed、ruff Pass
- 実行コマンド: `uv run python -m scripts.run_with_dynamodb_local -- uv run pytest tests/integration/api/test_purchase_create.py -q`（`backend/`、`../bin/mise exec --`経由）
- 結果: 3 failed, 2 passed
- 凍結したテストファイル: `backend/tests/integration/api/test_purchase_create.py`
- Red記録コミットSHA: `<Step 6のSHA>`

| Plan ID | Test Case ID | 実際の失敗 | Valid Red | 判定根拠 |
|---|---|---|---|---|
| PURC-TDD-001 | PURC-005-TC1, PURC-008-TC1〜TC3, PURC-009-TC1, PURC-004-TC12 | `assert 422 == 201` | Yes | `speed=0`を拒否する。登録契約の未実装 |
| PURC-TDD-004 | PURC-003-TC2 | `assert 201 == 422` | Yes | 空白だけの名前を受け付ける。入力領域の未実装 |
| PURC-TDD-005 | PURC-007-TC1, PURC-019-TC2 | Pass | 例外 | 承認済みRed例外。変更前コードでGreen |
| PURC-TDD-006 | PURC-014-TC8 | `[201, 201, 201, 201, 201] != [201, 409, 409, 409, 409]` | Yes | 同時重複を防がない。永続化制約の未実装 |
| PURC-TDD-007 | PURC-014-TC7 | Pass | 例外 | 承認済みRed例外。変更前コードでGreen |
```

```bash
git add docs/specs/purchase-create-tdd-plan.md
git commit -m "docs: record purchase-create backend Red evidence"
```

---

### Task 2: API入力領域（Greenタスク）

**Skill:** `implement-tdd-slice`（凍結テストを変更しない）

**Files:**
- Modify: `backend/app/api/schemas/purchase.py`（`PurchaseCreateRequest`だけ。`PurchasePutRequest`と`PurchaseResponse`は変更しない）
- Modify: `docs/specs/purchase-create-tdd-plan.md`（Green記録）

**Interfaces:**
- Consumes: Task 1の凍結テスト
- Produces: `PurchaseCreateRequest(name: str, category: str, speed: int, stock: int, is_temporary: bool)`。定数`NOT_BLANK_PATTERN = r"\S"`、`NAME_MAX_LENGTH = 50`、`CATEGORY_MAX_LENGTH = 30`、`QUANTITY_MAX = 100_000`。未知フィールド（`user_id`など）は無視される（Pydantic既定）。`is_temporary`は必須になる

- [ ] **Step 1: 凍結テストが変わっていないことを確認する**

```bash
git diff <Task 1 Step 6のSHA> -- backend/tests/integration/api/test_purchase_create.py
```

Expected: 差分なし。

- [ ] **Step 2: 登録リクエストのスキーマを変更する**

`backend/app/api/schemas/purchase.py`の`PurchaseCreateRequest`クラスを次へ置き換え、直前にモジュール定数を追加する。

```python
#: 空白文字だけではないこと。前後空白の除去や正規化は行わない（仕様 3. 文字列の扱い）。
NOT_BLANK_PATTERN = r"\S"
NAME_MAX_LENGTH = 50
CATEGORY_MAX_LENGTH = 30
QUANTITY_MAX = 100_000


class PurchaseCreateRequest(BaseModel):
    """購入物の新規作成リクエスト（docs/specs/purchase-create.md 3. 入力仕様）。

    利用者IDは受け取らない。未知のフィールドは無視する。
    数値は整数だけを受け付け、小数や文字列を丸め・変換しない。
    """

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH, pattern=NOT_BLANK_PATTERN)
    category: str = Field(
        min_length=1, max_length=CATEGORY_MAX_LENGTH, pattern=NOT_BLANK_PATTERN
    )
    speed: int = Field(ge=0, le=QUANTITY_MAX, strict=True, description="消費スピード")
    stock: int = Field(ge=0, le=QUANTITY_MAX, strict=True, description="現在の在庫")
    is_temporary: bool = Field(strict=True, description="一時的な購入")
```

- [ ] **Step 3: 対象テストを実行する**

```bash
cd backend
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/api/test_purchase_create.py -q
```

Expected: `1 failed, 4 passed`。失敗は`test_purc_tdd_006_concurrent_duplicates_persist_exactly_one_purchase`だけ（Task 3の対象）。

- [ ] **Step 4: 回帰と静的検査を実行する**

```bash
cd backend
../bin/mise exec -- uv run ruff format . && ../bin/mise exec -- uv run ruff check --fix .
../bin/mise exec -- uv run pytest -m "not integration" -q
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/test_environment.py -q
git diff <Task 1 Step 6のSHA> -- backend/tests/integration/api/test_purchase_create.py
```

Expected: ruff Pass、unit `72 passed`、環境スモークPass、凍結テストの差分なし。

- [ ] **Step 5: コミットする**

```bash
git add backend/app/api/schemas/purchase.py
git commit -m "feat: enforce purchase-create input contract in API schema"
```

- [ ] **Step 6: Green記録を追記してコミットする**

`docs/specs/purchase-create-tdd-plan.md`の「### Red（Backend）」の後へ追記する。

```markdown
### Green（Backend入力領域）

- 実装計画のGreenタスク: Task 2
- 凍結済みテストの差分確認（`git diff <Red記録SHA> -- backend/tests/integration/api/test_purchase_create.py`）: 差分なし
- 結果: 4 passed, 1 failed（PURC-TDD-006はTask 3の対象）
- 回帰: unit 72 passed、環境スモークPass、ruff Pass
- Green記録コミットSHA: `<Step 5のSHA>`

| Plan ID | 実行コマンド | 結果 |
|---|---|---|
| PURC-TDD-001 | `pytest tests/integration/api/test_purchase_create.py` | Pass |
| PURC-TDD-004 | 同上 | Pass |
| PURC-TDD-005 | 同上 | Pass |
| PURC-TDD-007 | 同上 | Pass |
```

```bash
git add docs/specs/purchase-create-tdd-plan.md
git commit -m "docs: record purchase-create API input Green evidence"
```

---

### Task 3: 名前・カテゴリの重複防止（Greenタスク）

**Skill:** `implement-tdd-slice`（凍結テストを変更しない）

**Files:**
- Modify: `backend/app/models/purchase.py`
- Modify: `docs/specs/purchase-create-tdd-plan.md`（Green記録）

**Interfaces:**
- Consumes: Task 1の凍結テスト、`app.models.exceptions.ItemAlreadyExistsError`（既存の例外ハンドラが409 `{"detail": <メッセージ>}`へ変換する）
- Produces:
  - `UNIQUE_NAME_SORT_PREFIX = "UNIQUE#PURCHASE#"`
  - `unique_name_key(user_id: str, name: str, category: str) -> dict[str, str]`（`{"PK": "USER#<user_id>", "SK": "UNIQUE#PURCHASE#<sha256>"}`）
  - `create_purchase_item(item, *, table_name=None) -> PurchaseItem`: 重複時`ItemAlreadyExistsError`
  - `get_all_purchase_items(user_id, *, table_name=None)`: `SK`が`PURCHASE#`で始まる項目だけを返す（マーカーを含めない）
  - `delete_purchase_item(user_id, id, *, table_name=None)`: 本体を削除し、同じ購入物を指すマーカーも削除する

DynamoDB Local 3.3.1で事前確認済みの事実: `table.meta.client.transact_write_items`はresource経由のため素のPython値（`Decimal`を含む）を受け付ける。8並列の同一マーカー書き込みは1件成功、7件が`TransactionCanceledException`（`CancellationReasons`の2番目が`ConditionalCheckFailed`）になる。実AWSでは同時トランザクションが`TransactionConflict`で取り消される場合があるため、その場合だけ再試行する。

- [ ] **Step 1: 凍結テストが変わっていないことを確認する**

```bash
git diff <Task 1 Step 6のSHA> -- backend/tests/integration/api/test_purchase_create.py
```

Expected: 差分なし。

- [ ] **Step 2: importとマーカーのキーを追加する**

`backend/app/models/purchase.py`の先頭のimportを次にする。

```python
import hashlib
import json
from uuid import UUID

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.dynamodb import get_table
from app.domain.purchase import Purchase
from app.models.base import TimestampedItem
from app.models.exceptions import ItemAlreadyExistsError, ItemNotFoundError
from app.models.keys import ItemKeySchema, KeyTemplate

#: 名前・カテゴリの一意性を保証するマーカーアイテムのソートキー接頭辞。
#: 購入物本体（``PURCHASE#``）の前方一致に含まれないようにする。
UNIQUE_NAME_SORT_PREFIX = "UNIQUE#PURCHASE#"

#: 同時トランザクションの競合（``TransactionConflict``）時に試行する最大回数。
TRANSACTION_CONFLICT_ATTEMPTS = 3
```

`PurchaseItem`クラスの後に次の関数を追加する。

```python
def unique_name_key(user_id: str, name: str, category: str) -> dict[str, str]:
    """利用者・名前・カテゴリの組に対応するマーカーアイテムのキー。

    名前とカテゴリは正規化しない。区切り文字を含んでも組が衝突しないよう、
    JSON配列にしてからハッシュ化する。
    """
    digest = hashlib.sha256(
        json.dumps([name, category], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    schema = PurchaseItem.primary_key
    return {
        schema.partition_attribute: schema.partition_key.build(user_id=user_id),
        schema.sort_attribute: f"{UNIQUE_NAME_SORT_PREFIX}{digest}",
    }
```

- [ ] **Step 3: 登録をトランザクションにする**

`create_purchase_item`を次へ置き換える。

```python
def create_purchase_item(item: PurchaseItem, *, table_name: str | None = None) -> PurchaseItem:
    """購入物を新規作成する。

    同じ利用者に名前・カテゴリが完全一致する購入物が既にあれば、同時要求を含めて
    ``ItemAlreadyExistsError``。購入物本体と一意性マーカーを1つのトランザクションで書く。
    """
    table = get_table(table_name)
    not_exists = "attribute_not_exists(PK) AND attribute_not_exists(SK)"
    transact_items = [
        {
            "Put": {
                "TableName": table.name,
                "Item": item.to_item(),
                "ConditionExpression": not_exists,
            }
        },
        {
            "Put": {
                "TableName": table.name,
                "Item": {
                    **unique_name_key(item.user_id, item.name, item.category),
                    "purchase_id": str(item.id),
                },
                "ConditionExpression": not_exists,
            }
        },
    ]
    for attempt in range(1, TRANSACTION_CONFLICT_ATTEMPTS + 1):
        try:
            table.meta.client.transact_write_items(TransactItems=transact_items)
            return item
        except ClientError as error:
            if error.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            reasons = [
                reason.get("Code") for reason in error.response.get("CancellationReasons", [])
            ]
            if "ConditionalCheckFailed" in reasons:
                raise ItemAlreadyExistsError(
                    "同じ名前とカテゴリの購入物が既に登録されています"
                ) from error
            if "TransactionConflict" not in reasons or attempt == TRANSACTION_CONFLICT_ATTEMPTS:
                raise
    raise AssertionError("unreachable")
```

- [ ] **Step 4: 一覧からマーカーを除く**

`get_all_purchase_items`の本体を次へ置き換える。

```python
    table = get_table(table_name)
    schema = PurchaseItem.primary_key
    assert schema.sort_key is not None
    response = table.query(
        KeyConditionExpression=Key(schema.partition_attribute).eq(
            schema.partition_key.build(user_id=user_id)
        )
        & Key(schema.sort_attribute).begins_with(schema.sort_key.prefix()),
    )
    return [PurchaseItem.from_item(item) for item in response["Items"]]
```

- [ ] **Step 5: 削除でマーカーも削除する（既存挙動の維持）**

`delete_purchase_item`を次へ置き換える。

```python
def delete_purchase_item(user_id: str, id: UUID, *, table_name: str | None = None) -> None:
    """購入物を削除し、その購入物を指す一意性マーカーも削除する。

    同じキー（``user_id``+``id``）のアイテムが存在しなければ``ItemNotFoundError``。
    本体を先に削除し、マーカーは同じ購入物を指している場合だけ削除する。途中で失敗しても
    重複を許す状態にはならず、同じ組の再登録が409になる側へ倒れる。
    """
    table = get_table(table_name)
    try:
        response = table.delete_item(
            Key=PurchaseItem.build_key(user_id=user_id, id=id),
            ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
            ReturnValues="ALL_OLD",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ItemNotFoundError(f"購入物 {id}は存在しません。") from error
        raise
    deleted = PurchaseItem.from_item(response["Attributes"])
    try:
        table.delete_item(
            Key=unique_name_key(user_id, deleted.name, deleted.category),
            ConditionExpression="purchase_id = :purchase_id",
            ExpressionAttributeValues={":purchase_id": str(id)},
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
```

- [ ] **Step 6: 対象テストとintegration全体を実行する**

```bash
cd backend
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest tests/integration/api/test_purchase_create.py -q
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q
```

Expected: 対象 `5 passed`。integration全体 `21 passed`（環境テスト16件＋TDD 5件）。

- [ ] **Step 7: 削除後の再登録を手動で確認する（既存挙動の維持）**

TDDテストを追加せず、一時スクリプトで確認する（正式なテストはTask 7のReview Focus 4）。`backend/`で実行する。

```bash
cat > /tmp/verify_delete_recreate.py <<'EOF'
from fastapi.testclient import TestClient
from app.api.deps import get_current_user_id
from main import app
app.dependency_overrides[get_current_user_id] = lambda: "verify-user"
client = TestClient(app)
body = {"name": "牛乳", "category": "食品", "speed": 1, "stock": 2, "is_temporary": False}
first = client.post("/purchases", json=body)
deleted = client.delete(f"/purchases/{first.json()['id']}")
again = client.post("/purchases", json=body)
missing = client.delete("/purchases/8f7c1f8e-5a8d-4c3a-9d5b-0b1b2c3d4e5f")
print(first.status_code, deleted.status_code, again.status_code, missing.status_code)
EOF
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- env PYTHONPATH=. ../bin/mise exec -- uv run python /tmp/verify_delete_recreate.py
rm /tmp/verify_delete_recreate.py
```

Expected: `201 204 201 404`。

- [ ] **Step 8: 回帰と静的検査を実行する**

```bash
cd backend
../bin/mise exec -- uv run ruff format . && ../bin/mise exec -- uv run ruff check --fix .
../bin/mise exec -- uv run pytest -m "not integration" -q
git diff <Task 1 Step 6のSHA> -- backend/tests/integration/api/test_purchase_create.py
```

Expected: ruff Pass、unit `72 passed`、凍結テストの差分なし。

- [ ] **Step 9: コミットする**

```bash
git add backend/app/models/purchase.py
git commit -m "feat: prevent duplicate purchase name and category per user"
```

- [ ] **Step 10: Green記録を追記してコミットする**

`docs/specs/purchase-create-tdd-plan.md`の「### Green（Backend入力領域）」の後へ追記する。

```markdown
### Green（Backend重複防止）

- 実装計画のGreenタスク: Task 3
- 凍結済みテストの差分確認: 差分なし
- 結果: 5 passed（PURC-TDD-001, 004, 005, 006, 007）
- 回帰: integration全体 21 passed、unit 72 passed、ruff Pass、削除後の再登録 `201 204 201 404`
- 既知の制約: 編集では一意性マーカーを更新しない（実装計画「既知の制約」）
- Green記録コミットSHA: `<Step 9のSHA>`

| Plan ID | 実行コマンド | 結果 |
|---|---|---|
| PURC-TDD-006 | `pytest tests/integration/api/test_purchase_create.py` | Pass |
```

```bash
git add docs/specs/purchase-create-tdd-plan.md
git commit -m "docs: record purchase-create duplicate prevention Green evidence"
```

---

### Task 4: Frontend TDDテスト作成とValid Red（Redタスク）

**Skill:** `create-tdd-tests`（プロダクトコードを変更しない）

**Files:**
- Create: `frontend/src/features/Purchase.test.tsx`
- Create: `frontend/src/features/CreatePurchaseDialog.test.tsx`
- Modify: `.github/workflows/test.yml`（`--passWithNoTests`を外す）
- Modify: `CLAUDE.md`（CIの説明から`--passWithNoTests`の記述を更新）
- Modify: `docs/specs/purchase-create-tdd-plan.md`（Red記録）

**Interfaces:**
- Consumes（既存UIの観測点。Task 5以降も維持する）: 「追加」ボタン、`role="dialog"`、ラベル「名前」「カテゴリ」「現在の在庫」、「消費スピード」を含むラベル、「登録する」ボタン、空一覧の「まだ登録されていません」、一覧の`listitem`。`@/api/purchases`の`createPurchase`・`getAllPurchases`（テストでmock）、`@/api/queryClient`の`queryClient`
- Produces: 凍結テスト2ファイル

- [ ] **Step 1: Baselineを確認する**

```bash
cd frontend
bun run test -- --run --passWithNoTests
bun run lint && bun run format:check
```

Expected: テスト0件でPass、lint・format Pass。

- [ ] **Step 2: PURC-TDD-002を書く**

`frontend/src/features/Purchase.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	createPurchase,
	getAllPurchases,
	type PurchaseResponse,
} from "@/api/purchases";
import { queryClient } from "@/api/queryClient";
import { Purchase } from "@/features/Purchase";

// docs/specs/purchase-create-tdd-plan.md PURC-TDD-002
vi.mock("@/api/purchases", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/api/purchases")>()),
	createPurchase: vi.fn(),
	getAllPurchases: vi.fn(),
}));

const created: PurchaseResponse = {
	id: "8f7c1f8e-5a8d-4c3a-9d5b-0b1b2c3d4e5f",
	name: "牛乳",
	category: "食品",
	speed: 0,
	stock: 2,
	is_temporary: false,
	created_at: "2026-09-30T00:00:00Z",
	updated_at: "2026-09-30T00:00:00Z",
};

function renderPurchase() {
	return render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);
}

describe("購入物登録から一覧反映まで", () => {
	beforeEach(() => {
		vi.mocked(getAllPurchases)
			.mockResolvedValueOnce([])
			.mockResolvedValue([created]);
		vi.mocked(createPurchase).mockResolvedValue(created);
	});

	afterEach(() => {
		queryClient.clear();
		vi.resetAllMocks();
	});

	it("PURC-011-TC1 / PURC-012-TC1 / PURC-004-TC12: 消費スピード0の有効入力を登録すると、再取得した一覧に登録内容が表示される", async () => {
		const user = userEvent.setup();
		renderPurchase();
		await screen.findByText("まだ登録されていません");

		await user.click(screen.getByRole("button", { name: "追加" }));
		const dialog = await screen.findByRole("dialog");
		await user.type(within(dialog).getByLabelText("名前"), "牛乳");
		await user.type(within(dialog).getByLabelText("カテゴリ"), "食品");
		const speed = within(dialog).getByLabelText(/消費スピード/);
		await user.clear(speed);
		await user.type(speed, "0");
		const stock = within(dialog).getByLabelText("現在の在庫");
		await user.clear(stock);
		await user.type(stock, "2");
		await user.click(within(dialog).getByRole("button", { name: "登録する" }));

		await waitFor(() => expect(createPurchase).toHaveBeenCalledTimes(1));
		expect(vi.mocked(createPurchase).mock.calls[0][0]).toEqual({
			name: "牛乳",
			category: "食品",
			speed: 0,
			stock: 2,
			is_temporary: false,
		});
		await waitFor(() => expect(getAllPurchases).toHaveBeenCalledTimes(2));
		const item = await screen.findByRole("listitem");
		expect(within(item).getByText("牛乳")).toBeInTheDocument();
		expect(within(item).getByText("食品")).toBeInTheDocument();
		expect(within(item).getByText(/消費スピード\s*0/)).toBeInTheDocument();
		expect(within(item).getByText(/在庫\s*2/)).toBeInTheDocument();
	});
});
```

- [ ] **Step 3: PURC-TDD-003を書く**

`frontend/src/features/CreatePurchaseDialog.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createPurchase } from "@/api/purchases";
import { queryClient } from "@/api/queryClient";
import { CreatePurchaseDialog } from "@/features/CreatePurchaseDialog";

// docs/specs/purchase-create-tdd-plan.md PURC-TDD-003
vi.mock("@/api/purchases", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/api/purchases")>()),
	createPurchase: vi.fn(),
}));

describe("購入物登録画面の入力検証", () => {
	afterEach(() => {
		queryClient.clear();
		vi.resetAllMocks();
	});

	it("PURC-003-TC1: 空白文字だけの名前は項目エラーになり、登録要求を送信しない", async () => {
		const user = userEvent.setup();
		render(
			<QueryClientProvider client={queryClient}>
				<CreatePurchaseDialog open={true} onOpenChange={() => {}} />
			</QueryClientProvider>,
		);

		await user.type(screen.getByLabelText("名前"), "   ");
		await user.type(screen.getByLabelText("カテゴリ"), "食品");
		const speed = screen.getByLabelText(/消費スピード/);
		await user.clear(speed);
		await user.type(speed, "1");
		const stock = screen.getByLabelText("現在の在庫");
		await user.clear(stock);
		await user.type(stock, "2");
		await user.click(screen.getByRole("button", { name: "登録する" }));

		expect(await screen.findByLabelText("名前")).toHaveAttribute(
			"aria-invalid",
			"true",
		);
		expect(createPurchase).not.toHaveBeenCalled();
	});
});
```

- [ ] **Step 4: Redを確認する**

```bash
cd frontend
bun run test -- --run
```

Expected: `Test Files  2 failed (2)`、`Tests  2 failed (2)`。

| テスト | 期待する失敗 | Valid Redの根拠 |
|---|---|---|
| PURC-TDD-002 | `expected "vi.fn()" to be called 1 times, but got 0 times` | 画面が`speed=0`を拒否し登録要求を送らない（契約未実装）。一覧に消費スピードもない |
| PURC-TDD-003 | `toHaveAttribute("aria-invalid", "true")`の不一致 | 空白だけの名前を受け付け、項目エラーにならない（契約未実装） |

モジュール解決・描画の失敗など上表と異なる理由の失敗は`INVALID_RED`として同じタスク内でテストを直す。

- [ ] **Step 5: CIの`--passWithNoTests`を外す**

`.github/workflows/test.yml`のfrontendジョブの最後の3行（コメント2行と`run`）を次へ置き換える。

```yaml
      # --run: watchモードに入らず1回だけ実行する
      - run: bun run test -- --run
        working-directory: frontend
```

`CLAUDE.md`の次の行を置き換える。

- 変更前: ``- `.github/workflows/test.yml` — backendのunit testとfrontendのVitest。frontendはまだテストが無いため `--passWithNoTests` を付けている（テストを書き始めたら外す）``
- 変更後: ``- `.github/workflows/test.yml` — backendのunit testとfrontendのVitest``

- [ ] **Step 6: lintと差分を確認してコミットする**

```bash
cd frontend
bun run check
bun run lint && bun run format:check
cd .. && git status --short
```

Expected: lint・format Pass。変更はテスト2ファイル、`.github/workflows/test.yml`、`CLAUDE.md`だけで、`frontend/src`のプロダクトコードに差分がない。

```bash
git add frontend/src/features/Purchase.test.tsx frontend/src/features/CreatePurchaseDialog.test.tsx .github/workflows/test.yml CLAUDE.md
git commit -m "test: add purchase-create frontend TDD tests (Red)"
```

- [ ] **Step 7: Red記録を追記してコミットする**

`docs/specs/purchase-create-tdd-plan.md`の「### Green（Backend重複防止）」の後へ追記する。

```markdown
### Red（Frontend）

- 実装計画のRedタスク: Task 4
- Baselineの結果: テスト0件、lint・format Pass
- 実行コマンド: `bun run test -- --run`（`frontend/`）
- 結果: 2 failed
- 凍結したテストファイル: `frontend/src/features/Purchase.test.tsx`, `frontend/src/features/CreatePurchaseDialog.test.tsx`
- Red記録コミットSHA: `<Step 6のSHA>`

| Plan ID | Test Case ID | 実際の失敗 | Valid Red | 判定根拠 |
|---|---|---|---|---|
| PURC-TDD-002 | PURC-011-TC1, PURC-012-TC1, PURC-004-TC12 | `createPurchase`が0回 | Yes | 画面が`speed=0`を拒否する。一覧に消費スピードがない |
| PURC-TDD-003 | PURC-003-TC1 | 名前欄に`aria-invalid="true"`がない | Yes | 空白だけの名前を受け付ける |
```

```bash
git add docs/specs/purchase-create-tdd-plan.md
git commit -m "docs: record purchase-create frontend Red evidence"
```

---

### Task 5: 画面の入力検証と一覧表示（Greenタスク）

**Skill:** `implement-tdd-slice`（凍結テストを変更しない）

**Files:**
- Modify: `frontend/src/features/CreatePurchaseDialog.tsx`
- Modify: `frontend/src/features/Purchase.tsx`
- Modify: `frontend/src/api/schema.d.ts`（再生成）
- Modify: `frontend/package.json`（build順序。GAP-003）
- Modify: `docs/specs/purchase-create-tdd-plan.md`（Green記録、GAP-003の状態）

**Interfaces:**
- Consumes: Task 2のAPIスキーマ、Task 4の凍結テスト
- Produces: `CreatePurchaseDialog({ open, onOpenChange })`（シグネチャ不変）。フォーム値`{ name: string; category: string; speed: number; stock: number; isTemporary: boolean }`。各入力は検証エラー時に`aria-invalid="true"`

- [ ] **Step 1: 凍結テストが変わっていないことを確認する**

```bash
git diff <Task 4 Step 6のSHA> -- frontend/src/features/Purchase.test.tsx frontend/src/features/CreatePurchaseDialog.test.tsx
```

Expected: 差分なし。

- [ ] **Step 2: 登録画面の入力検証を実装する**

`frontend/src/features/CreatePurchaseDialog.tsx`を次の内容にする。

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreatePurchase } from "@/hooks/usePurchases";

const NAME_MAX_LENGTH = 50;
const CATEGORY_MAX_LENGTH = 30;
const QUANTITY_MAX = 100_000;

/** API（Python）と同じくコードポイント単位で文字数を数える。 */
function codePointLength(value: string): number {
	return [...value].length;
}

/** 空白だけを拒否するが、前後空白の除去などの正規化はしない。 */
function requiredText(label: string, maxLength: number) {
	return z
		.string()
		.refine((value) => value.trim().length > 0, `${label}を入力してください`)
		.refine(
			(value) => codePointLength(value) <= maxLength,
			`${label}は${maxLength}文字以内で入力してください`,
		);
}

/** 0以上100,000以下の整数。小数や範囲外の値を丸めずに拒否する。 */
function quantity(label: string) {
	return z
		.number({ error: `${label}を入力してください` })
		.int(`${label}は整数で入力してください`)
		.min(0, `${label}は0以上で入力してください`)
		.max(
			QUANTITY_MAX,
			`${label}は${QUANTITY_MAX.toLocaleString()}以下で入力してください`,
		);
}

const createPurchaseFormSchema = z.object({
	name: requiredText("名前", NAME_MAX_LENGTH),
	category: requiredText("カテゴリ", CATEGORY_MAX_LENGTH),
	speed: quantity("消費スピード"),
	stock: quantity("現在の在庫"),
	isTemporary: z.boolean(),
});

export function CreatePurchaseDialog({
	open,
	onOpenChange,
}: {
	open: boolean;
	onOpenChange: (open: boolean) => void;
}) {
	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(createPurchaseFormSchema),
		defaultValues: {
			name: "",
			category: "",
			speed: 0,
			stock: 0,
			isTemporary: false,
		},
	});
	const createPurchase = useCreatePurchase();

	const onSubmit = handleSubmit((values) => {
		createPurchase.mutate(
			{
				name: values.name,
				category: values.category,
				speed: values.speed,
				stock: values.stock,
				is_temporary: values.isTemporary,
			},
			{
				onSuccess: () => {
					reset();
					onOpenChange(false);
				},
			},
		);
	});

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!next) reset();
				onOpenChange(next);
			}}
		>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>購入物を追加</DialogTitle>
				</DialogHeader>

				<form onSubmit={onSubmit} className="flex flex-col gap-4">
					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-name">名前</Label>
						<Input
							id="create-name"
							aria-invalid={errors.name ? true : undefined}
							{...register("name")}
						/>
						{errors.name && (
							<p className="text-destructive text-sm">{errors.name.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-category">カテゴリ</Label>
						<Input
							id="create-category"
							aria-invalid={errors.category ? true : undefined}
							{...register("category")}
						/>
						{errors.category && (
							<p className="text-destructive text-sm">
								{errors.category.message}
							</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-speed">消費スピード（個/日）</Label>
						<Input
							id="create-speed"
							type="number"
							step="any"
							aria-invalid={errors.speed ? true : undefined}
							{...register("speed", { valueAsNumber: true })}
						/>
						{errors.speed && (
							<p className="text-destructive text-sm">{errors.speed.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-stock">現在の在庫</Label>
						<Input
							id="create-stock"
							type="number"
							step="any"
							aria-invalid={errors.stock ? true : undefined}
							{...register("stock", { valueAsNumber: true })}
						/>
						{errors.stock && (
							<p className="text-destructive text-sm">{errors.stock.message}</p>
						)}
					</div>

					<label className="flex items-center gap-2 text-sm">
						<input type="checkbox" {...register("isTemporary")} />
						一時的な購入（定期購入しない）
					</label>

					{createPurchase.isError && (
						<p className="text-destructive text-sm">登録に失敗しました</p>
					)}

					<DialogFooter>
						<Button type="submit" disabled={createPurchase.isPending}>
							{createPurchase.isPending ? "登録中..." : "登録する"}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
```

`step="any"`のままにするのは、ブラウザの制約検証ではなくzodで「整数で入力してください」と表示するため。

- [ ] **Step 3: 一覧に消費スピードを表示する**

`frontend/src/features/Purchase.tsx`で次の1行を置き換える。

変更前:

```tsx
									<Badge variant="outline">在庫 {purchase.stock}</Badge>
```

変更後:

```tsx
									<Badge variant="outline">
										消費スピード {purchase.speed}
									</Badge>
									<Badge variant="outline">在庫 {purchase.stock}</Badge>
```

- [ ] **Step 4: API型を再生成する**

リポジトリ直下から実行する。

```bash
(cd backend && ../bin/mise exec -- uv run python -c "import json; from main import app; print(json.dumps(app.openapi(), ensure_ascii=False))") > /tmp/purchase-openapi.json
(cd frontend && bunx openapi-typescript /tmp/purchase-openapi.json -o src/api/schema.d.ts && bunx biome format --write src/api/schema.d.ts)
rm /tmp/purchase-openapi.json
git diff --stat frontend/src/api/schema.d.ts
```

Expected: `PurchaseCreateRequest`の`speed`・`stock`が`number`のまま、`is_temporary`が必須（`?`なし）になり、名前・カテゴリの`maxLength`などの制約コメントが増える。`PurchasePutRequest`と`PurchaseResponse`は変わらない。

- [ ] **Step 5: buildの順序を直す（GAP-003）**

`frontend/package.json`の`"build"`を次にする。TanStack Routerのvite pluginが`src/routeTree.gen.ts`（gitignore対象）を生成してから型検査する。

```json
		"build": "vite build && tsc -b",
```

- [ ] **Step 6: 対象テストと検証を実行する**

```bash
cd frontend
rm -f src/routeTree.gen.ts
bun run test -- --run
bun run check
bun run lint && bun run format:check
bun run build
git diff <Task 4 Step 6のSHA> -- src/features/Purchase.test.tsx src/features/CreatePurchaseDialog.test.tsx
```

Expected: `Tests  2 passed (2)`、lint・format Pass、クリーンな状態から`bun run build`が成功、凍結テストの差分なし。

- [ ] **Step 7: コミットする**

```bash
git add frontend/src/features/CreatePurchaseDialog.tsx frontend/src/features/Purchase.tsx frontend/src/api/schema.d.ts frontend/package.json
git commit -m "feat: validate purchase-create input and show speed in list"
```

- [ ] **Step 8: Green記録とGAP-003を更新してコミットする**

`docs/specs/purchase-create-tdd-plan.md`の「### Red（Frontend）」の後へ追記し、「仕様不足・判断保留」表のGAP-003の状態を`Open`から`Resolved`へ変更して、必要な確認欄の末尾に「実装計画Task 5でbuildを`vite build && tsc -b`へ変更し解消」を加える。

```markdown
### Green（Frontend）

- 実装計画のGreenタスク: Task 5
- 凍結済みテストの差分確認: 差分なし
- 結果: 2 passed（PURC-TDD-002, 003）
- 回帰: lint・format Pass、`bun run build` Pass（GAP-003解消）
- Green記録コミットSHA: `<Step 7のSHA>`

| Plan ID | 実行コマンド | 結果 |
|---|---|---|
| PURC-TDD-002 | `bun run test -- --run` | Pass |
| PURC-TDD-003 | 同上 | Pass |
```

```bash
git add docs/specs/purchase-create-tdd-plan.md
git commit -m "docs: record purchase-create frontend Green evidence"
```

---

### Task 6: 登録失敗時の表示（TDD対象外の実装）

**Skill:** `implement-tdd-slice`の変更境界に従う（テストを追加・変更しない。検証はTask 7）

TDD計画でPURC-013、015〜018は候補外として実装後テストへ引き継がれている。`docs/TDD-WORKFLOW.md` 2.1により、このタスクでは実装前テストを書かない。タスクレビューではテスト不足を指摘事項とせず、Task 7で検証する。

**Files:**
- Modify: `frontend/src/api/purchases.ts`
- Modify: `frontend/src/hooks/usePurchases.ts`
- Modify: `frontend/src/features/CreatePurchaseDialog.tsx`

**Interfaces:**
- Consumes: Task 5の`CreatePurchaseDialog`
- Produces: `class ApiError extends Error { readonly status: number; readonly body: unknown }`（`@/api/purchases`）。`createPurchase`はHTTPエラーで`ApiError`を投げ、通信失敗では`fetch`の例外をそのまま伝える

- [ ] **Step 1: HTTPステータスを保持するエラーを追加する**

`frontend/src/api/purchases.ts`の型定義の後に追加し、`createPurchase`を置き換える。

```ts
/** APIがエラー応答を返したことを表す。原因別の表示にHTTPステータスを使う。 */
export class ApiError extends Error {
	readonly status: number;
	readonly body: unknown;

	constructor(status: number, body: unknown) {
		super(`API request failed with status ${status}`);
		this.name = "ApiError";
		this.status = status;
		this.body = body;
	}
}

export async function createPurchase(
	input: PurchaseCreateRequest,
): Promise<PurchaseResponse> {
	const { data, error, response } = await apiClient.POST("/purchases", {
		body: input,
	});
	if (!response.ok || data === undefined) {
		throw new ApiError(response.status, error);
	}
	return data;
}
```

- [ ] **Step 2: 登録の自動再送を明示的に無効化する（PURC-018）**

`frontend/src/hooks/usePurchases.ts`の`useCreatePurchase`を次にする。

```ts
export function useCreatePurchase() {
	return useMutation({
		mutationFn: createPurchase,
		// 通信失敗時も登録要求を自動再送しない（PURC-018）
		retry: false,
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["purchases"] });
		},
	});
}
```

- [ ] **Step 3: 失敗原因の表示と入力維持を実装する**

`frontend/src/features/CreatePurchaseDialog.tsx`を次の内容にする（Task 5の検証部分は同じ）。

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiError } from "@/api/purchases";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreatePurchase } from "@/hooks/usePurchases";

const NAME_MAX_LENGTH = 50;
const CATEGORY_MAX_LENGTH = 30;
const QUANTITY_MAX = 100_000;

/** API（Python）と同じくコードポイント単位で文字数を数える。 */
function codePointLength(value: string): number {
	return [...value].length;
}

/** 空白だけを拒否するが、前後空白の除去などの正規化はしない。 */
function requiredText(label: string, maxLength: number) {
	return z
		.string()
		.refine((value) => value.trim().length > 0, `${label}を入力してください`)
		.refine(
			(value) => codePointLength(value) <= maxLength,
			`${label}は${maxLength}文字以内で入力してください`,
		);
}

/** 0以上100,000以下の整数。小数や範囲外の値を丸めずに拒否する。 */
function quantity(label: string) {
	return z
		.number({ error: `${label}を入力してください` })
		.int(`${label}は整数で入力してください`)
		.min(0, `${label}は0以上で入力してください`)
		.max(
			QUANTITY_MAX,
			`${label}は${QUANTITY_MAX.toLocaleString()}以下で入力してください`,
		);
}

const createPurchaseFormSchema = z.object({
	name: requiredText("名前", NAME_MAX_LENGTH),
	category: requiredText("カテゴリ", CATEGORY_MAX_LENGTH),
	speed: quantity("消費スピード"),
	stock: quantity("現在の在庫"),
	isTemporary: z.boolean(),
});

type FormField = keyof z.infer<typeof createPurchaseFormSchema>;

const API_FIELD_TO_FORM_FIELD: Record<string, FormField> = {
	name: "name",
	category: "category",
	speed: "speed",
	stock: "stock",
	is_temporary: "isTemporary",
};

/** 422応答の`detail[].loc`から、問題のある入力項目を取り出す。 */
function invalidFormFields(body: unknown): FormField[] {
	if (
		typeof body !== "object" ||
		body === null ||
		!("detail" in body) ||
		!Array.isArray(body.detail)
	) {
		return [];
	}
	const fields = new Set<FormField>();
	for (const issue of body.detail) {
		const location: unknown = issue?.loc;
		if (
			Array.isArray(location) &&
			location[0] === "body" &&
			typeof location[1] === "string" &&
			location[1] in API_FIELD_TO_FORM_FIELD
		) {
			fields.add(API_FIELD_TO_FORM_FIELD[location[1]]);
		}
	}
	return [...fields];
}

/** 判明している原因は個別に、それ以外は内部情報を含まない共通文言にする。 */
function submitErrorMessage(error: Error): string {
	if (error instanceof ApiError && error.status === 409) {
		return "同じ名前とカテゴリの購入物が既に登録されています。名前かカテゴリを変更してください。";
	}
	if (error instanceof ApiError && error.status === 422) {
		return "入力内容に誤りがあります。表示された項目を修正してください。";
	}
	return "登録に失敗しました。時間をおいて、もう一度お試しください。";
}

export function CreatePurchaseDialog({
	open,
	onOpenChange,
}: {
	open: boolean;
	onOpenChange: (open: boolean) => void;
}) {
	const {
		register,
		handleSubmit,
		reset,
		setError,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(createPurchaseFormSchema),
		defaultValues: {
			name: "",
			category: "",
			speed: 0,
			stock: 0,
			isTemporary: false,
		},
	});
	const createPurchase = useCreatePurchase();

	const onSubmit = handleSubmit((values) => {
		if (createPurchase.isPending) return;
		createPurchase.mutate(
			{
				name: values.name,
				category: values.category,
				speed: values.speed,
				stock: values.stock,
				is_temporary: values.isTemporary,
			},
			{
				onSuccess: () => {
					reset();
					onOpenChange(false);
				},
				onError: (error) => {
					// 入力値はリセットせず維持する（PURC-015）
					if (error instanceof ApiError && error.status === 422) {
						for (const field of invalidFormFields(error.body)) {
							setError(field, { message: "この項目を確認してください" });
						}
					}
				},
			},
		);
	});

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!next) {
					reset();
					createPurchase.reset();
				}
				onOpenChange(next);
			}}
		>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>購入物を追加</DialogTitle>
				</DialogHeader>

				<form onSubmit={onSubmit} className="flex flex-col gap-4">
					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-name">名前</Label>
						<Input
							id="create-name"
							aria-invalid={errors.name ? true : undefined}
							{...register("name")}
						/>
						{errors.name && (
							<p className="text-destructive text-sm">{errors.name.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-category">カテゴリ</Label>
						<Input
							id="create-category"
							aria-invalid={errors.category ? true : undefined}
							{...register("category")}
						/>
						{errors.category && (
							<p className="text-destructive text-sm">
								{errors.category.message}
							</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-speed">消費スピード（個/日）</Label>
						<Input
							id="create-speed"
							type="number"
							step="any"
							aria-invalid={errors.speed ? true : undefined}
							{...register("speed", { valueAsNumber: true })}
						/>
						{errors.speed && (
							<p className="text-destructive text-sm">{errors.speed.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-stock">現在の在庫</Label>
						<Input
							id="create-stock"
							type="number"
							step="any"
							aria-invalid={errors.stock ? true : undefined}
							{...register("stock", { valueAsNumber: true })}
						/>
						{errors.stock && (
							<p className="text-destructive text-sm">{errors.stock.message}</p>
						)}
					</div>

					<label className="flex items-center gap-2 text-sm">
						<input type="checkbox" {...register("isTemporary")} />
						一時的な購入（定期購入しない）
					</label>

					{createPurchase.error && (
						<p role="alert" className="text-destructive text-sm">
							{submitErrorMessage(createPurchase.error)}
						</p>
					)}

					<DialogFooter>
						<Button type="submit" disabled={createPurchase.isPending}>
							{createPurchase.isPending ? "登録中..." : "登録する"}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
```

- [ ] **Step 4: 回帰と静的検査を実行する**

```bash
cd frontend
bun run check
bun run test -- --run
bun run lint && bun run format:check
rm -f src/routeTree.gen.ts && bun run build
git diff <Task 4 Step 6のSHA> -- src/features/Purchase.test.tsx src/features/CreatePurchaseDialog.test.tsx
```

Expected: `Tests  2 passed (2)`、lint・format・build Pass、凍結テストの差分なし。

- [ ] **Step 5: コミットする**

```bash
git add frontend/src/api/purchases.ts frontend/src/hooks/usePurchases.ts frontend/src/features/CreatePurchaseDialog.tsx
git commit -m "feat: show purchase-create failure causes and keep input"
```

---

### Task 7: 実装後テストと全体検証（検証タスク）

**Skill:** `verify-feature-slice`（新しいコンテキスト。プロダクトコード・凍結テスト・仕様を変更しない）

このタスクのテスト内容は、`docs/TDD-WORKFLOW.md` 5.7により、実装の会話を引き継がない検証者が仕様と論理テストケースから独立して設計する。この計画では入力、必須の対象、コマンド、完了条件だけを定める。

**Files:**
- Create: `docs/specs/purchase-create-post-test-report.md`（`docs/templates/post-implementation-test-report.md`から作成）
- Create / Modify: 追加テスト（例: `backend/tests/integration/api/test_purchase_create_post.py`、`backend/tests/unit/...`、`frontend/src/features/*.test.tsx`の新規ファイル、`e2e/`配下）。凍結テスト3ファイルは変更しない

**Interfaces:**
- Consumes: 仕様、論理テストケース、TDD計画のRed/Green記録、Task 1〜6の差分
- Produces: 実装後テストレポートとCompletion Gateの判定

- [ ] **Step 1: 全Test Case IDの割り当てを作る**

論理テストケース53件を、TDD済み、追加テスト、既存テスト、根拠付き対象外のいずれかへ割り当てる。TDDテストが直接検証するのは14件（PURC-003-TC1/TC2、004-TC12、005-TC1、007-TC1、008-TC1〜TC3、009-TC1、011-TC1、012-TC1、014-TC7/TC8、019-TC2）だけで、中心的契約に属していても残りの23件（PURC-001-TC1、002-TC1、003-TC3、004-TC1〜TC11、006-TC1、009-TC2、014-TC1〜TC6、019-TC1）は検証先を決める必要がある。TDD計画「TDD候補外と実装後テストへの引き継ぎ」の16件（PURC-002-TC2、006-TC2、010-TC1/TC2、012-TC2〜TC4、013-TC1/TC2、015-TC1、016-TC1/TC2、017-TC1/TC2、018-TC1/TC2）は、同表の暫定的な検証先を出発点にする。

- [ ] **Step 2: カバレッジと処理フローを分析する**

Backendは`pytest --cov`相当（`coverage`の追加が必要ならdev依存として追加）、Frontendは`bun run test -- --run --coverage`（`@vitest/coverage-v8`の追加が必要ならdev依存として追加）で、変更したファイルのline / branch coverageを取得する。`create_purchase_item`の`TransactionConflict`再試行分岐、`delete_purchase_item`のマーカー削除分岐、`invalidFormFields`、`submitErrorMessage`を必ず確認する。

- [ ] **Step 3: 必須の追加テストを書く**

少なくとも次を含める。

- Review Focus 1〜5のすべて
- PURC-004の残りの境界値（50/51文字、30/31文字、速度・在庫の0/100,000/100,001/負数/小数）をAPIとFrontendの適切なレベルで
- PURC-014-TC1〜TC6（完全一致・属性だけ違う・名前またはカテゴリだけ違う・前後空白・大文字小文字・全角半角）
- PURC-003-TC3（必須項目の欠落）
- PURC-013、015〜018のFrontendコンポーネントテスト（409・422・500・通信断の表示、入力維持、自動再送なし、手動再試行で1回送信）
- `TransactionConflict`時の再試行と、再試行後も競合する場合の例外伝播（boto3の`ClientError`を使う単体テスト）
- PURC-009-TC2を含む代表E2E（ブラウザ→API→DynamoDB Local→一覧）。Dockerが使えない環境では、`backend/`で`run_with_dynamodb_local`の子コマンドとして`uvicorn main:app`を起動し、`frontend/`で`bun run dev`を起動して`e2e/`のPlaywright（Chromiumは`/opt/pw-browsers`）から実行する。現在の認証は`dev-user`固定の仮実装なのでCognitoの認証情報は不要。実行できない場合は理由と影響をレポートへ記録する

期待結果を仕様から一意に導けない項目は`BLOCKED_SPEC`として停止し、人間へ戻す。

- [ ] **Step 4: 全体検証を実行する**

```bash
bash scripts/setup_host_prerequisites.sh --check
cd backend
../bin/mise exec -- uv run ruff check . && ../bin/mise exec -- uv run ruff format --check .
../bin/mise exec -- uv run pytest -m "not integration" -q
../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q
cd ../frontend
bun run lint && bun run format:check
bun run test -- --run
rm -f src/routeTree.gen.ts && bun run build
```

加えてE2Eを実行する。Expected: すべてPass。失敗をskip・削除・期待値の緩和で通さない。

- [ ] **Step 5: 実装後テストレポートを完成させてコミットする**

レポートに、全Test Case IDの検証先、カバレッジ分析、追加テスト、実行コマンドと結果、未実行の検証、残存リスクを記録する。残存リスクには少なくとも次を含める: 仕様10章の通信切断時の結果不明、実装計画「既知の制約」の3項目、DynamoDB Localを使うintegrationテストがまだCIで実行されないこと（`docs/todo/test-environment-rollout.md`の後続項目）。

```bash
git add docs/specs/purchase-create-post-test-report.md <追加したテストファイル>
git commit -m "test: add purchase-create post-implementation tests and report"
```

Completion Gateの条件（`docs/TDD-WORKFLOW.md` 5.7）を満たしたかを報告して終了する。最終コードレビューとマージは行わない。

---

## 完了後

1. superpowersの最終コードレビュー（`requesting-code-review`）。依頼に仕様、論理テストケース、TDD計画、実装後テストレポートのパスを含め、`docs/TDD-WORKFLOW.md` 5.8の確認項目を渡す
2. `superpowers:verification-before-completion`
3. `superpowers:finishing-a-development-branch`。人間がSlice Completeとマージを判断する

## 対象外（後続）

- DynamoDB Localを使うintegrationテストとE2EのCIワークフロー（`.github/workflows/integration.yml`、`e2e.yml`。`docs/todo/test-environment-rollout.md`の項目14）
- 編集スライスでの重複の扱いとマーカーの更新
