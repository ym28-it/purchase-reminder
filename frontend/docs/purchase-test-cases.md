# Frontend テストケース一覧（purchase機能）

`purchase-spec.md`（2026-08-12時点の実装から逆算した仕様）に基づくテストケース一覧です。
`purchase-spec.md` は「7. 確認事項」に8件の未確定事項を残したままで、本来は
「ドキュメントを修正・確定 → それに基づいてテスト実装」という順番が想定されていましたが、
7章の項目は主に**将来の挙動変更を検討するための論点**（エラー表示の詳細化、楽観的更新の
要否、認証配線など）であり、**現状の実装がどう動くか**自体は1〜6章で確定的に記述されて
います。そのため本ドキュメントは1〜6章の内容のみを根拠にテストケースを列挙し、7章に
関係する項目は該当ケースに **[7-n]** として注記しています（挙動が変わればテストも
追随して直す前提）。

対象: `src/api/purchases.ts` / `src/hooks/usePurchases.ts` / `src/features/Purchase.tsx` /
`src/features/CreatePurchaseDialog.tsx` / `src/features/EditPurchaseDialog.tsx` /
`src/features/DeletePurchaseDialog.tsx`。`features/Auth.tsx` は空ファイルのため対象外
**[7-6]**。

## テスト方針

- ランナーは `vitest`（`environment: jsdom`）、コンポーネントは `@testing-library/react` +
  `@testing-library/user-event`。
- `api/purchases.ts` 自体のテストは `apiClient`（`api/client.ts`）を `vi.mock` し、
  `POST`/`GET`/`PUT`/`DELETE` の呼び出し引数と戻り値/エラーの受け渡しのみを検証する
  （実HTTP・DynamoDB Localには依存しない）。
- hooks・componentsのテストは `@/api/purchases` モジュールを `vi.mock` して、実際の
  ネットワーク層を経由させない。`useQuery`/`useMutation` を動かすため、テストごとに
  新しい `QueryClient`（`defaultOptions.queries.retry: false` などリトライ無効化）を
  生成し `QueryClientProvider` でラップする。
- `usePurchases.ts` は内部で `@/api/queryClient` のシングルトン `queryClient` を直接
  `invalidateQueries` しているため、hooks/componentsのテストではこのシングルトンを
  `QueryClientProvider` に渡す必要がある点に注意（テスト用に差し替え不可・現状の実装制約）。

---

## 1. `api/purchases.ts`

| ID | ケース | 内容 |
|---|---|---|
| API-01 | `createPurchase` 正常系 | `apiClient.POST` が `{ data }` を返すとき、`POST("/purchases", { body: input })` が呼ばれ、`data` がそのまま返る |
| API-02 | `createPurchase` 異常系 | `apiClient.POST` が `{ error }` を返すとき、その `error` オブジェクトがそのまま `throw` される（変換されない） |
| API-03 | `putPurchase` 正常系 | `PUT("/purchases/{purchase_id}", { params: { path: { purchase_id } }, body: input })` が呼ばれ、`data` が返る |
| API-04 | `putPurchase` 異常系 | `error` がそのまま `throw` される |
| API-05 | `getAllPurchases` 正常系 | `GET("/purchases")` が呼ばれ、配列がそのまま返る |
| API-06 | `getAllPurchases` 異常系 | `error` がそのまま `throw` される |
| API-07 | `deletePurchase` 正常系 | `DELETE("/purchases/{purchase_id}", { params: { path: { purchase_id } } })` が呼ばれ、戻り値は `undefined` |
| API-08 | `deletePurchase` 異常系 | `error` がそのまま `throw` される |

## 2. `hooks/usePurchases.ts`

| ID | ケース | 内容 |
|---|---|---|
| HOOK-01 | `usePurchases` 成功 | `getAllPurchases` が解決すると `isPending → false`、`data` に一覧が入る |
| HOOK-02 | `usePurchases` 失敗 | `getAllPurchases` が reject すると `isError` が `true` になる |
| HOOK-03 | `usePurchases` queryKey | `queryKey: ["purchases"]` で登録されている（他ミューテーションからのinvalidateと連動することの前提確認） |
| HOOK-04 | `useCreatePurchase` 成功時invalidate | `mutate()` 成功後、`["purchases"]` の `invalidateQueries` が呼ばれる（`queryClient.invalidateQueries` をspyして検証） |
| HOOK-05 | `useCreatePurchase` 失敗時invalidateなし | `mutationFn` がrejectした場合は `invalidateQueries` が呼ばれない |
| HOOK-06 | `usePutPurchase` 引数の受け渡し | `mutate({ purchaseId, input })` で呼ぶと `putPurchase(purchaseId, input)` に正しく分解されて渡る |
| HOOK-07 | `usePutPurchase` 成功時invalidate | 成功後に `["purchases"]` がinvalidateされる |
| HOOK-08 | `useDeletePurchase` 引数の受け渡し | `mutate(purchaseId)` で `deletePurchase(purchaseId)` が呼ばれる |
| HOOK-09 | `useDeletePurchase` 成功時invalidate | 成功後に `["purchases"]` がinvalidateされる |

## 3. `features/Purchase.tsx`

| ID | ケース | 内容 |
|---|---|---|
| PUR-01 | ローディング表示 | `usePurchases` が `isPending: true` を返す間、「読み込み中...」がヘッダー・本文双方に表示される |
| PUR-02 | 空状態表示 | `data: []` かつ `isPending: false` のとき、空状態メッセージ（「まだ登録されていません」）が表示され、一覧行は0件 |
| PUR-03 | 件数表示 | `data` が3件のとき、ヘッダーに「3件」と表示される |
| PUR-04 | 一覧行の表示内容 | 各行に `name`・`category`・`在庫 {stock}` バッジが表示される |
| PUR-05 | `is_temporary` バッジの出し分け | `is_temporary: true` の行にのみ「一時的」バッジが表示され、`false` の行には表示されない |
| PUR-06 | `speed` 非表示 **[7-5]** | 一覧のどの行にも消費スピードの値がテキストとして表示されていない（現状仕様のリグレッションガード。表示する仕様に変わったら要修正） |
| PUR-07 | 編集ボタン押下 | 行の編集ボタン（`aria-label="編集"`）を押すと `EditPurchaseDialog` が開き、その行の `purchase` が渡る（ダイアログ内のフォームに値が反映されることで確認） |
| PUR-08 | 削除ボタン押下 | 行の削除ボタン（`aria-label="削除"`）を押すと `DeletePurchaseDialog` が開き、確認文言にその行の `name` が含まれる |
| PUR-09 | 追加ボタン押下 | ヘッダーの「追加」ボタンで `CreatePurchaseDialog` が開く |
| PUR-10 | 編集ダイアログを閉じるとstateがリセットされる | `EditPurchaseDialog` を閉じたあと再度別の行の編集を開くと、前回の行ではなく新しい行の値が表示される（`editingPurchase` state経由のopen制御の確認） |

## 4. `features/CreatePurchaseDialog.tsx`

| ID | ケース | 内容 |
|---|---|---|
| CRE-01 | 初期値 | ダイアログを開いた直後、`isTemporary` チェックボックスは未チェック、他フィールドは空/0 |
| CRE-02 | `name` 必須 | 空のまま送信すると「名前を入力してください」が表示され、`createPurchase` は呼ばれない |
| CRE-03 | `category` 必須 | 空のまま送信すると「カテゴリを入力してください」が表示される |
| CRE-04 | `speed` 正の数必須（0拒否） | `speed=0` で送信すると「0より大きい値を入力してください」が表示される |
| CRE-05 | `speed` 正の数必須（負数拒否） | `speed=-1` で送信するとエラーが表示される |
| CRE-06 | `stock` 0以上（負数拒否） | `stock=-1` で送信すると「0以上を入力してください」が表示される |
| CRE-07 | `stock` 0許容 | `stock=0` は許容され、バリデーションエラーが出ない |
| CRE-08 | 正常送信・キー変換 | 全項目正しく入力して送信すると、`createPurchase` が `{ name, category, speed, stock, is_temporary }`（`isTemporary`→`is_temporary` に変換済み）で呼ばれる |
| CRE-09 | 成功時のフォームリセット＆クローズ | 送信成功後、`reset()` されダイアログが閉じる（`onOpenChange(false)`） |
| CRE-10 | 失敗時の固定エラー文言 **[7-3]** | `createPurchase` がrejectすると「登録に失敗しました」が表示され、ダイアログは閉じない（バックエンドのエラー詳細は出ない。詳細表示化する仕様に変わったら要修正） |
| CRE-11 | キャンセルで入力破棄 | 何か入力した状態でキャンセル操作（`onOpenChange(false)` 相当の外側クリック/Escapeも含む）をすると `reset()` が呼ばれ、次回開いたときに空の状態に戻る |
| CRE-12 | 送信中はボタン無効化 | `createPurchase.isPending` の間、送信ボタンが無効化され文言が「登録中...」になる |

## 5. `features/EditPurchaseDialog.tsx`

| ID | ケース | 内容 |
|---|---|---|
| EDIT-01 | `purchase=null` で非表示 | `purchase` が `null` のとき `open` は `false`（ダイアログが表示されない） |
| EDIT-02 | `purchase` の値でフォーム初期化 | `purchase` を渡して開くと、`name`/`category`/`speed`/`stock`/`isTemporary` の各フィールドがその値で埋まっている |
| EDIT-03 | `purchase` 切り替え時の再同期 | 開いた状態で異なる `purchase` に切り替わると（`values` オプション経由で）フォームの表示値も新しい `purchase` の値に更新される |
| EDIT-04 | バリデーション（Createと同一ルール） | `name`/`category` 必須、`speed` 正数、`stock` 0以上の各違反で対応するエラーメッセージが表示される（CRE-02〜CRE-07相当） |
| EDIT-05 | 正常送信 | 送信すると `usePutPurchase().mutate` が `{ purchaseId: purchase.id, input: {...} }` で呼ばれる（`is_temporary` へのキー変換込み） |
| EDIT-06 | 成功時クローズのみ・`reset()`未呼び出し | 送信成功後は `onOpenChange(false)` のみが呼ばれ、明示的な `reset()` は呼ばれない（`values` 同期に依存する現状実装のリグレッションガード） |
| EDIT-07 | 失敗時の固定エラー文言 **[7-3]** | `putPurchase` がrejectすると「更新に失敗しました」が表示され、ダイアログは閉じない |
| EDIT-08 | `purchase=null` のとき送信しても何も起きない | フォームがない状態（理論上到達しないが）で `onSubmit` が呼ばれても `putPurchase.mutate` は呼ばれない（`if (!purchase) return;` のガード確認） |
| EDIT-09 | 送信中はボタン無効化 | `putPurchase.isPending` の間、送信ボタンが無効化され文言が「更新中...」になる |

## 6. `features/DeletePurchaseDialog.tsx`

| ID | ケース | 内容 |
|---|---|---|
| DEL-01 | `purchase=null` で非表示 | `purchase` が `null` のとき `open` は `false` |
| DEL-02 | 確認文言に名前が入る | `purchase.name` がダイアログの説明文に含まれる（例: 「"卵" を削除します。」） |
| DEL-03 | キャンセル | キャンセルボタン押下で `deletePurchase.mutate` は呼ばれず、`onOpenChange` が閉じる方向で呼ばれる |
| DEL-04 | 削除確定・正常系 | 削除ボタン押下で `deletePurchase.mutate(purchase.id, ...)` が呼ばれ、成功後 `onOpenChange(false)` が呼ばれる |
| DEL-05 | 削除確定・異常系の固定文言 **[7-3]** | `deletePurchase` がrejectすると「削除に失敗しました」が表示され、ダイアログは閉じない |
| DEL-06 | 送信中はボタン無効化 | `deletePurchase.isPending` の間、キャンセル・削除の両ボタンが無効化され、削除ボタンの文言が「削除中...」になる |

---

## 7章との対応関係（テストへの影響サマリ）

| 7章の項目 | このテストケース一覧への影響 |
|---|---|
| 1. `App.tsx`/`App.css` デッドコード | テスト対象外（未import・未使用のため） |
| 2. バリデーションスキーマ重複 | CRE-02〜07とEDIT-04は同一ルールの重複テストになるが、実装が重複している以上テストも重複させておく（共通化されたらテストも1本化） |
| 3. エラー表示が固定文言のみ | CRE-10 / EDIT-07 / DEL-05に **[7-3]** として注記。詳細表示化する場合はこれらのケースを差し替える |
| 4. 楽観的更新なし | HOOK-04〜09・PUR系は「成功後に再フェッチされる」現状挙動を前提にしている。楽観的更新を入れる場合はhooksのテスト方針から見直しが必要 |
| 5. 一覧に`speed`が非表示 | PUR-06に **[7-5]** として注記 |
| 6. 認証未配線 | `Auth.tsx`・認証ヘッダ関連のテストケースは本一覧に含めていない（対象外） |
| 7. 削除・更新対象の特定方法 | 404などサーバー側競合時の挙動は3.のエラー表示方針に従うため、個別ケース化していない（3.が確定次第、CRE-10/EDIT-07/DEL-05に統合できる） |
| 8. テスト基盤はあるがテスト0件 | 本ドキュメントがその解消の第一歩 |

---

次のステップとして、上記ケースを実際の `*.test.ts(x)` として実装できます。実装に進める前に、
7章のうち特にテストの当落を左右する **3.（エラー表示の詳細化要否）** と **4.（楽観的更新の要否）**
だけでも先に方針を確定させておくと、後からテストを書き直す手戻りを避けられます。
