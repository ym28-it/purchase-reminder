# Purchase API 仕様

2026-08-12時点の実装コードから抽出した仕様と、ユーザーによる確認事項への回答（同日）を
反映した確定版です。「6. 確認事項への回答（確定仕様）」に回答内容と、それに伴うコード変更を
まとめています。この仕様に基づいてテストを実装します。

対象範囲: `backend/app/api/`, `backend/app/models/`（エージェント実装担当範囲）。
`backend/app/domain/`, `backend/app/services/`, `backend/app/auth/` は本来ユーザー実装担当
だが、`services/purchase_service.py` の created_at保持・`field()`誤用の修正（6.1, 6.2）
のみ、本人からの明示的な依頼により今回一回限りの例外としてエージェントが実装した。
それ以外（`domain/`, `auth/`, `services/notification_service.py`）は現状の中身
（空 or 仮実装）をそのまま記載するに留めます。

## 1. 概要

購入物（purchase）1件に対する CRUD API。認証は未実装で、全リクエストが固定のダミーユーザー
`"dev-user"` として扱われる。

## 2. データモデル

### 2.1 ドメインエンティティ（`app/domain/purchase.py`）

```python
@dataclass()
class Purchase:
    id: UUID
    user_id: str
    name: str
    category: str
    speed: float  # 消費スピード
    stock: float  # 現在の在庫
    is_temporary: bool  # 定期購入しないものかどうか
    created_at: datetime
    updated_at: datetime
```

バリデーションやビジネスルール（消費速度と在庫から補充タイミングを計算する等）はまだ何も
実装されていない、フィールドを保持するだけの入れ物。

### 2.2 DynamoDBアイテム（`app/models/purchase.py` の `PurchaseItem`）

シングルテーブル設計。キー構成:

| 属性 | 値 |
|---|---|
| PK | `USER#{user_id}` |
| SK | `PURCHASE#{id}` |
| EntityType | `"PURCHASE"` |

GSI1（`app/models/table.py` で定義済み）は現状 `PurchaseItem` からは使われていない
（`index_keys` を宣言していないため sparse index にすら載らない）。

保持フィールド: `user_id`, `id`, `name`, `category`, `speed`, `stock`, `is_temporary`,
`created_at`, `updated_at`（`created_at`/`updated_at` は `TimestampedItem` 由来で、
アイテム構築時に `datetime.now(UTC)` が既定値として入る）。

## 3. API仕様（`app/api/purchase.py`）

ベースパス: `/purchases`

### 3.1 `GET /purchases` — 一覧取得

- 認証ユーザー（現状ダミー固定）の購入物を全件返す。
- 並び順の指定なし（DynamoDBのQuery結果順＝SKの辞書順、実質は作成順に近いが保証はない）。
- レスポンス: `200 OK`, `PurchaseResponse` の配列。0件なら空配列。

### 3.2 `POST /purchases` — 新規作成

リクエストボディ（`PurchaseCreateRequest`）:

| フィールド | 型 | 制約 | 既定値 |
|---|---|---|---|
| name | string | 1文字以上 | 必須 |
| category | string | 1文字以上 | 必須 |
| speed | float | `> 0`, `<= 100`, 無限大・NaN不可 | 必須 |
| stock | float | `>= 0`, `<= 100`, 無限大・NaN不可 | 必須 |
| is_temporary | bool | なし | `False` |

- `id` はサーバー側で `uuid4()` により採番（クライアント指定不可）。
- レスポンス: `201 Created`, `PurchaseResponse`。
- 同一キーが既に存在する場合（`id`衝突。UUIDなので実質発生しない）は `409 Conflict`
  （`{"detail": "..."}`）。
- 同一ユーザー内で `name`+`category` の組み合わせが既存の購入物と一致する場合も
  `409 Conflict`（`{"detail": "..."}`）。詳細は6.4。

### 3.3 `PUT /purchases/{purchase_id}` — 更新

リクエストボディ（`PurchasePutRequest`）は `PurchaseCreateRequest` と同一のフィールド・制約
（`name`, `category`, `speed`, `stock`, `is_temporary`）。

- 全フィールック必須の完全上書き（PATCHではなくPUT）。指定しなかったフィールドを保持する
  部分更新は行わない。
- `purchase_id` はパスパラメータ（UUID）。
- 対象が存在しない場合は `404 Not Found`（`{"detail": "..."}`）。
- 更新後、同一ユーザー内で他の購入物と `name`+`category` の組み合わせが一致する場合は
  `409 Conflict`（自分自身との一致は除外。詳細は6.4）。
- `created_at` は更新されない（元のアイテムの値を保持する。詳細は6.1）。`updated_at` は
  更新のたびに現在時刻になる。
- レスポンス: `200 OK`, `PurchaseResponse`。

### 3.4 `DELETE /purchases/{purchase_id}` — 削除

- 対象が存在しない場合は `404 Not Found`（`{"detail": "..."}`）。
- 成功時: `204 No Content`（ボディなし）。

### 3.5 共通レスポンス表現（`PurchaseResponse`）

```python
id: UUID
name: str
category: str
speed: float
stock: float
is_temporary: bool
created_at: datetime
updated_at: datetime
```

`user_id` はレスポンスに含まれない。

## 4. 認証（`app/api/deps.py`）

`get_current_user_id()` は Cognito 実装前の仮実装で、常に固定文字列 `"dev-user"` を返す。
リクエストヘッダ等は一切見ない。全エンドポイントがこの依存関数経由でユーザーIDを取得する。

## 5. 永続化層の挙動（`app/models/purchase.py`）

- `create_purchase_item`: `attribute_not_exists(PK) AND attribute_not_exists(SK)` 条件で
  `put_item`。条件失敗時は `ItemAlreadyExistsError`。
- `put_purchase_item`: `attribute_exists(PK) AND attribute_exists(SK)` 条件で `put_item`
  （＝アイテム全体を新しい内容で置き換える）。条件失敗時は `ItemNotFoundError`。
- `delete_purchase_item`: `attribute_exists(PK) AND attribute_exists(SK)` 条件で
  `delete_item`。条件失敗時は `ItemNotFoundError`。
- `get_all_purchase_items`: パーティションキー（`USER#{user_id}`）に対する `Query`。
  ページネーション（`LastEvaluatedKey`）は未対応 — 1MBを超える件数がある場合は
  取りこぼす。

`app/api/exception_handlers.py` により、`ItemNotFoundError` → `404`、
`ItemAlreadyExistsError` → `409` にアプリ全体で変換される（`purchase.py` 固有のハンドラでは
なく、models層の汎用例外に対する一括登録）。

## 6. 確認事項への回答（確定仕様）

### 6.1 `created_at` の扱い（PUT）

**回答: 編集（PUT）では `created_at` は変更しない。** 元のアイテムが持つ `created_at` を
引き継ぐ。`updated_at` は毎回現在時刻に更新する（このルールに変更なし）。

対応: `app/models/purchase.py` に単体取得用の `get_purchase_item(user_id, id)` を追加し、
`PurchaseItem.from_domain()` が `Purchase.created_at`/`updated_at` をそのまま使うよう変更。
`app/services/purchase_service.put_purchase` は更新前に既存アイテムを取得し、
その `created_at` を引き継いだ上で `updated_at` のみ現在時刻にする
（`app/services/`はユーザー実装担当領域だが、今回は明示的な依頼により一回限りの例外として
エージェントが実装する）。

### 6.2 `dataclasses.field()` の誤用

**回答: バグとして修正する。** `app/services/purchase_service.py` の
`create_purchase`/`put_purchase` から `field(default_factory=...)` の誤用を除去し、
`datetime.now(UTC)` を直接使うよう修正（6.1の対応と合わせて実施）。

### 6.3 `is_temporary`

CRUD層としては「値がそのまま保存・返却される」ことのみをテスト対象とする
（通知ロジックへの影響は対象外、現状通知ロジック自体が未実装）。

### 6.4 `name`/`category` の重複チェック

**回答: `name`+`category` の組み合わせで一意。** 同一ユーザー内で同じ`name`かつ同じ
`category`の購入物は1件までしか登録できない。`name`だけの重複（`category`が異なる）、
`category`だけの重複（`name`が異なる）はどちらも許可する。

対応:
- `app/models/exceptions.py` に `DuplicatePurchaseError(PersistenceError)` を追加。
- `app/models/purchase.py` の `create_purchase_item`/`put_purchase_item` で、書き込み前に
  同一ユーザー内の既存アイテム（PUTの場合は自分自身のIDを除外）と `name`+`category` が
  一致するものがないかを確認し、あれば `DuplicatePurchaseError` を送出する。
- `app/api/exception_handlers.py` に `DuplicatePurchaseError` → `409 Conflict` の
  ハンドラを追加登録する。

### 6.5 並び順

`GET /purchases` の並び順についてフロントエンド側の依存はなし。保証なしのまま
（テストでは順序を assert しない）。

### 6.6 `speed`/`stock` の制約

**回答: マイナス不可、Not null、Infinityなし、上限は100（以上・以下として含む、`<= 100`）。**

| フィールド | 制約（確定） |
|---|---|
| speed | `> 0`（既存のまま。0や負数は不可）、`<= 100`、無限大・NaN不可、必須（null不可） |
| stock | `>= 0`（既存のまま。負数は不可）、`<= 100`、無限大・NaN不可、必須（null不可） |

対応: `app/api/schemas/purchase.py` の `PurchaseCreateRequest`/`PurchasePutRequest` の
`speed`/`stock` に `le=100`, `allow_inf_nan=False` を追加する（`Not null`は元々
必須フィールドとして満たされている）。

### 6.7 GSI1

現時点でCRUD層のテスト対象には含めない（未使用のまま）。

---

上記の確定仕様に基づいて、以下を実装する:

- コード変更: `app/api/schemas/purchase.py`、`app/models/exceptions.py`、
  `app/models/purchase.py`、`app/api/exception_handlers.py`、
  `app/services/purchase_service.py`（一回限りの例外実装）
- テスト: `tests/unit/api/schemas/`（スキーマ検証）、`tests/unit/services/`
  （`purchase_service`のモックテスト）、`tests/integration/models/`、
  `tests/integration/api/`（DynamoDB Localを使ったmodels層・API結合テスト）
