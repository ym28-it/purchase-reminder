# Frontend 仕様（現状整理）

このドキュメントは、2026-08-12時点の実装コードを読んで抽出した「現状の仕様」です。
仕様書から実装したものではなく実装から仕様を逆算したものなので、意図と実装がずれている
箇所・未確定の箇所は「7. 確認事項」にまとめています。ここを見て仕様を確定・修正してください。
確定した後、それに基づいてテストを実装します（`backend/docs/purchase-spec.md` と対の
ドキュメントです）。

対象範囲: `frontend/src/` 全般（CLAUDE.mdの分担上、frontendはエージェント実装担当）。

## 1. 概要

購入物（purchase）のCRUD操作を行う単一ページのSPA。ルーティングはTanStack Router、
サーバー状態管理はTanStack Query、フォームは react-hook-form + zod、APIクライアントは
openapi-fetch（バックエンドのOpenAPIスキーマから型生成）。

## 2. ディレクトリ構成と役割

| ディレクトリ | 役割 | 現状 |
|---|---|---|
| `api/` | バックエンドへのHTTP通信 | 実装済み（purchases全操作） |
| `components/ui/` | 汎用UIパーツ（shadcn） | 実装済み（button/card/dialog/alert-dialog/input/label/badge） |
| `features/` | 画面・機能単位 | `Purchase.tsx`（一覧＋CRUD操作の起点）、`CreatePurchaseDialog.tsx`、`EditPurchaseDialog.tsx`、`DeletePurchaseDialog.tsx`、`Auth.tsx`（**中身は空**） |
| `hooks/` | 状態管理・API呼び出しのラップ | `usePurchases.ts` |
| `routes/` | TanStack Routerのファイルベースルート | `/`（`index.tsx`）のみ、`__root.tsx`で devtools を差し込み |

## 3. API通信層（`api/`）

### 3.1 `client.ts`

`openapi-fetch` の `createClient<paths>` で生成した `apiClient`。
`baseUrl` は環境変数 `VITE_API_BASE_URL`、未設定時は `http://localhost:8000`。

- 認証ヘッダの付与は一切行っていない（Authorizationヘッダなし）。バックエンドが
  ダミーユーザー固定の現状と整合しているが、Cognito導入後は要対応。

### 3.2 `schema.d.ts`

`openapi-typescript` によりバックエンドの `/openapi.json` から自動生成
（`bun run gen:api`）。手動編集禁止（ファイル冒頭にコメントあり）。バックエンドの
Pydanticスキーマ（`PurchaseCreateRequest`/`PurchasePutRequest`/`PurchaseResponse`）と
1対1対応。

### 3.3 `purchases.ts`

4関数。いずれもエラー時は `openapi-fetch` が返す `error` オブジェクトをそのまま
`throw` する（独自のエラー型への変換なし）。

- `createPurchase(input)` → `POST /purchases`
- `putPurchase(purchaseId, input)` → `PUT /purchases/{purchase_id}`
- `getAllPurchases()` → `GET /purchases`
- `deletePurchase(purchaseId)` → `DELETE /purchases/{purchase_id}`

### 3.4 `queryClient.ts`

`new QueryClient()`（オプション既定値のまま。`staleTime`/`retry`等のカスタマイズなし）。

## 4. データフェッチ・更新（`hooks/usePurchases.ts`)

- `usePurchases()`: `useQuery({ queryKey: ["purchases"], queryFn: getAllPurchases })`
- `useCreatePurchase()` / `usePutPurchase()` / `useDeletePurchase()`:
  いずれも `useMutation`。`onSuccess` で `queryClient.invalidateQueries({ queryKey: ["purchases"] })`
  を呼び、一覧を再取得させる（楽観的更新は行わない＝ミューテーション成功後に
  再フェッチが走るまでUIは更新されない）。
- `usePutPurchase` は `{ purchaseId, input }` を1引数にまとめて受け取る。

## 5. 画面構成

### 5.1 `Purchase.tsx`（一覧画面、`/`ルートのコンポーネント）

- `usePurchases()` の `isPending` でローディング表示、0件で空状態表示を出し分け。
- 各行に `name`/`category`/`stock`（Badge表示）/`is_temporary`（trueの時のみ「一時的」Badge）
  と、編集・削除ボタン。
- 編集中/削除対象の `purchase` を `useState<PurchaseResponse | null>` で保持し、
  それぞれ `EditPurchaseDialog`/`DeletePurchaseDialog` に渡す（`null`で非表示、
  値ありでダイアログ表示 = `open`制御を親のstateの有無で行っている）。
- `speed`（消費スピード）は一覧に表示されていない。

### 5.2 `CreatePurchaseDialog.tsx`

フォームスキーマ（zod、`CreatePurchaseDialog.tsx`内にローカル定義）:

| フィールド | 検証 |
|---|---|
| name | `min(1)` |
| category | `min(1)` |
| speed | `z.coerce.number().positive()` |
| stock | `z.coerce.number().min(0)` |
| isTemporary | `boolean`（既定 `false`） |

- 送信時に `isTemporary` → `is_temporary` にキー変換してAPIへ渡す。
- 成功時: フォームを `reset()` してダイアログを閉じる。
- 失敗時: 「登録に失敗しました」という固定文言のみ（エラー内容の詳細表示なし）。
- キャンセル・外側クリックでダイアログを閉じた場合も `reset()`（入力内容を破棄）。

### 5.3 `EditPurchaseDialog.tsx`

- フォームスキーマは `CreatePurchaseDialog` と**同一定義がコピーされている**
  （共有化されていない）。
- react-hook-formの `values`オプションで`purchase`propの変更に同期（`purchase`が
  `null`の間は`undefined`＝フォーム値なし）。
- 成功時: `onOpenChange(false)` のみ（`reset()`は呼んでいないが、`values`同期のため
  次に開いた時は最新の`purchase`で上書きされる）。
- 失敗時: 「更新に失敗しました」の固定文言。

### 5.4 `DeletePurchaseDialog.tsx`

- 確認ダイアログ。`purchase` propが非`null`なら開く。
- 削除確認文言に `purchase?.name` を埋め込み。
- 成功時: `onOpenChange(false)`。失敗時: 「削除に失敗しました」の固定文言。

## 6. 認証・ルーティング

- **`features/Auth.tsx` は空ファイル。** 認証UIは未実装。
- `main.tsx` はTanStack Routerの `RouterProvider` と `QueryClientProvider` のみをマウント。
  認証プロバイダ（`react-oidc-context`等）は組み込まれていない。
- `package.json` には `oidc-client-ts`/`react-oidc-context` が依存関係として入っているが、
  現状どこからも import されていない（未使用）。
- ルートは `/`（`routes/index.tsx` → `Purchase`コンポーネント）の1つのみ。ログイン画面や
  認証ガード（未ログイン時のリダイレクト等）は存在しない。

## 7. 確認事項（実装から見つかった、仕様として未確定・疑わしい点）

1. **`App.tsx`/`App.css` はデッドコード。** `main.tsx`からimportされておらず、
   Viteテンプレートのデフォルト画面（カウンターボタン等）が残ったまま。
   削除して問題ないか確認したい（別途削除の提案済み）。

2. **フォームバリデーションスキーマの重複。** `CreatePurchaseDialog`と
   `EditPurchaseDialog`が同一のzodスキーマを個別に定義している。共通化するか、
   現状のまま（画面ごとに独立させておく）でよいか。

3. **エラー表示が固定文言のみ。** バックエンドが返す `422`（バリデーションエラーの詳細）
   や `404`/`409` のメッセージを画面に出していない。詳細表示が必要か、
   「失敗しました」で十分か。

4. **楽観的更新なし。** 作成・更新・削除はいずれも成功後に一覧を再フェッチする方式。
   体感速度より実装のシンプルさを優先している状態だが、この方針でよいか。

5. **一覧に`speed`（消費スピード）が表示されていない。** 編集ダイアログを開かないと
   確認できない。意図的か、表示漏れか。

6. **認証が全く未配線。** `Auth.tsx`が空、`react-oidc-context`が未使用、APIクライアントに
   認証ヘッダの付与がない。CLAUDE.md上は `app/auth/`（バックエンド）はユーザー実装担当
   だが、フロントエンドの認証配線（ログイン画面・ProtectedRoute・トークン添付）は
   frontend全般としてエージェント担当範囲に含まれる認識でよいか、それとも認証まわりは
   バックエンドと合わせてユーザーが実装したいか確認したい。

7. **削除・更新の対象特定が「一覧から選んだ行のオブジェクトをそのまま渡す」方式。**
   別タブや他クライアントでの変更によって一覧が古くなっている場合、
   楽観的なUUID指定で操作することになる（サーバー側の404は6.のエラー表示方針に依存）。
   現状は許容でよいか。

8. **テスト基盤はあるがテストが1件もない。** `vitest`/`@testing-library/react`/
   `jest-dom` は devDependencies に入っており `test-setup.ts` も用意済みだが、
   `*.test.tsx` 等のテストファイルはまだ存在しない。

---

このドキュメントを修正・追記した上で教えてください。確定した内容に沿って
`usePurchases.ts`（hooks）、`api/purchases.ts`、各ダイアログ・`Purchase.tsx`の
コンポーネントテストを実装します。
