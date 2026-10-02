# 購入物登録・一覧反映 実装後テストレポート

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `docs/specs/purchase-create.md` 第2版（PURC-001〜024） |
| 論理テストケースSSOT | `docs/specs/purchase-create-test-cases.md` 第2版（64件） |
| 論理テストケースの参照コミット | `b06800e87a4a42199c87f961e3e876f41f45c02e`（第2版の承認。仕様第2版も同コミットが最終変更。検証対象SHAまで差分なし） |
| TDD計画 | `docs/specs/purchase-create-tdd-plan.md`（「第2版の追加」2026-10-02承認、PURC-TDD-008〜014） |
| TDD Greenコミット | 第1版 `669c726abd03c94426d2614da2b741c81baaf82e` / 第2版 `e8afdab0488b757760404fb1151e60c84d465a7d`（証跡: `docs/specs/purchase-create-tdd-execution.md`「第2版 Red」「第2版 Green」） |
| 凍結TDDテストの版 | 第1版3ファイル `15e48f6f4339874d8636b9659f58f7dd52825c10`、第2版2ファイル `8e939a26c81bc80a7ba8b06842a377f2cafb7544`（検証対象SHAで5ファイルとも差分なし） |
| 検証対象SHA（プロダクトコード） | `e8afdab0488b757760404fb1151e60c84d465a7d`（ブランチ `verify/purchase-create`。第2版Green。以後の`29f5f1e`と本検証コミットはドキュメントとテストのみで、`git diff e8afdab HEAD -- backend/app frontend/src`は空） |
| 前回の実装後検証 | 第1版 `09092c27e72974cd2edc0c3b9e9e08f2deb9f6f2`（DEFECT-001〜003、Baseline GAP-003を検出）→ 再検証 `db1ecbf`（プロダクトコード`f807d68`、53件） |
| 対象スライス | 一覧の「追加」操作から、現在利用者への永続化と一覧反映まで |
| 状態 | Reviewed-ready（第2版検証済み、最終コードレビューと人間確認待ち） |
| 確認者 | Pending（ym28-it） |
| 確認日 | Pending（第1版検証: 2026-10-01、第2版検証: 2026-10-02） |

期待結果は承認済み論理Test Case IDをSSOTとし、本レポートでは再定義しない。

## 入力と引き継ぎ

### TDDからの引き継ぎ

| Test Case ID | TDDでの扱い | 実装後に必要な確認 |
|---|---|---|
| PURC-005-TC1, 008-TC1〜3, 009-TC1, 004-TC12 | TDD済み（PURC-TDD-001） | 維持。009-TC2はE2E |
| PURC-011-TC1, 012-TC1, 004-TC12 | TDD済み（PURC-TDD-002） | 成功後UI・失敗UIを補完 |
| PURC-003-TC1 | TDD済み（PURC-TDD-003、空白名のみ） | 他の入力境界・空欄をComponentで補完 |
| PURC-003-TC2 | TDD済み（PURC-TDD-004、空白名のみ） | 他の入力境界と欠落をIntegrationで補完 |
| PURC-007-TC1, 019-TC2 | TDD済み（PURC-TDD-005、Red例外） | 維持 |
| PURC-014-TC8 | TDD済み（PURC-TDD-006） | 競合窓を決定的に再現する補完 |
| PURC-014-TC7 | TDD済み（PURC-TDD-007、Red例外） | 維持 |
| PURC-002-TC2, 006-TC2, 010-TC1/2, 012-TC2〜4, 013-TC1/2, 015-TC1, 016-TC1/2, 017-TC1/2, 018-TC1/2 | 候補外（TDD計画「TDD候補外と実装後テストへの引き継ぎ」） | 暫定検証先に従い実施 |
| 上記以外（001-TC1, 002-TC1, 003-TC3, 004-TC1〜11, 006-TC1, 014-TC1〜6, 019-TC1） | 中心的契約に属するがTDD対象外 | 実装後テストで実施 |

### 第2版TDDからの引き継ぎ（TDD計画「第2版の追加」）

| Test Case ID | TDDでの扱い | 実装後に必要な確認 |
|---|---|---|
| PURC-024-TC2 | TDD済み（PURC-TDD-008） | 再試行を使い切った場合も一意性が崩れないこと |
| PURC-024-TC1 | TDD済み（PURC-TDD-009） | 名前を変えない編集と名前変更の競合（TDD計画で実装後へ送付） |
| PURC-022-TC1, 023-TC1, 023-TC2 | TDD済み（PURC-TDD-010、承認済みRed例外） | 編集の事前確認をすり抜けた場合の予約による409 |
| PURC-004-TC14 | TDD済み（PURC-TDD-011） | 維持 |
| PURC-020-TC1 | TDD済み（PURC-TDD-012、500のみ） | 409・422・通信失敗後の開き直し |
| PURC-021-TC1 | TDD済み（PURC-TDD-013、nameのみ） | 他の項目、複数項目、未知項目・不正な本文 |
| PURC-016-TC1 | TDD済み（PURC-TDD-014、`detail: "conflict"`のみ） | 本文の形によらず409で判定されること |
| PURC-004-TC13 | 実装後へ送付 | API統合で検証 |
| PURC-004-TC15 | 実装後へ送付（DEFECT-003で修正済み） | 既存テストで足りるか確認 |
| PURC-023-TC3 | 実装後へ送付 | API統合で検証 |

### 実装分析で新たに見つかった観点

| ID | 観点 | 種別 | 仕様・Test Case ID上の根拠 | 対応 |
|---|---|---|---|---|
| IMPL-RISK-003 | 削除後に同じ名前・カテゴリで再登録できる（一意性予約が残らない） | 状態遷移 | PURC-014（重複は「存在する」購入物との比較）。2026-09-30の人間判断で期待どおりと確認 | Add test（Integration） |
| IMPL-RISK-004 | 一意性予約を持たない既存購入物（予約導入前のデータ）との重複 | 接続 / 永続化 | PURC-014-TC1 | Add test（Integration） |
| IMPL-RISK-005 | 事前読み取り（Query）と予約付きトランザクションの二段構えのうち、トランザクション側の重複検出はTDD-006では実行タイミング次第でしか通らない（カバレッジ実行ごとに`models/purchase.py` 75-78, 115-118行の実行有無が変動した） | 競合 | PURC-014-TC8 | Add test（事前読み取りを空にして競合窓を決定的に再現） |
| IMPL-RISK-006 | 実DynamoDBでの同時トランザクションが`TransactionConflict`で取り消された場合、409ではなく再送出→500になる | 競合 / エラー | PURC-014-TC8 | Justified（DynamoDB Localで決定的に再現不可）。残存リスクへ |
| IMPL-RISK-007 | Frontendの重複判定がAPIの`detail`文字列の完全一致に依存する | 接続 | PURC-016-TC1、仕様第2版§6「画面はHTTPステータスで重複を判定し、エラーメッセージの文言に依存しない」 | **Resolved（第2版）**。`e8afdab`で`ApiError.status === 409`判定へ変更。PURC-TDD-014と`CreatePurchaseDialog.rev2.post`の409×5（英語・detailなし・内部情報入り・平文・空本文）、および逆向きの「重複文言入りの500は共通エラー」でPass。E2E 1（実APIの409）もPass |
| SCOPE-001 | 実装がPUT（編集）とDELETEの挙動を変更した（下記「範囲外の変更」） | 範囲 | 仕様第2版PURC-022〜024、§6「編集時の重複」、§8（一意性の維持を除外から除いた） | **Resolved（第2版）**。編集・削除時の一意性維持は仕様第2版の範囲に入り、PURC-TDD-008〜010と本検証の統合テストで検証した。編集画面での409の表示方法は引き続き§8の対象外 |
| IMPL-RISK-008 | 編集・削除の読み直しを5回使い切ると`ConditionalCheckFailedError`（HTTPハンドラ未登録）→500になる | エラー / 競合 | PURC-024（一意性）、仕様§6「その他の失敗」、§8（編集・削除の画面と操作は対象外） | Add test（使い切った後も一覧にない組は201、一覧にある組は409、応答に内部情報なし）。HTTPステータス自体は仕様で定まらないため期待しない。残存リスクへ |
| IMPL-RISK-009 | 編集の事前確認（一覧Query）と予約トランザクションの間に別の登録が入ると、予約側（`models/purchase.py` 209-212行）だけが409の防壁になる | 競合 | PURC-023-TC2 | Add test（事前確認を空にして決定的に再現） |
| OBS-001 | `PurchasePutRequest`は`speed > 0`（`gt=0`）、`float`、上限なしで、登録（0以上の整数、上限100,000）と制約が異なる | 観察 | 仕様§8（編集の操作は対象外） | 本スライスの欠陥としない。PURC-023-TC3の前提を満たすため、編集では`speed=3`を使った。編集の仕様化時に扱う |
| SCOPE-002 | 以前の実装後テスト（PR #31）が凍結TDDテスト3ファイルへ追記・変更していた（PURC-TDD-003のrender呼び出しのヘルパー化、docstring変更を含む） | プロセス | `docs/TDD-WORKFLOW.md` 2.1「TDDテストを凍結する」 | 凍結版`15e48f6`へ復元し、実装後テストを別ファイルへ移した |

### 範囲外の変更（SCOPE-001、第2版で解消）

仕様第2版でPURC-022〜024（編集・削除時の名前・カテゴリの一意性維持）が追加され、以下の変更は仕様の範囲内になった。以下は第1版時点の記録として残す。

`git diff 0c0fee2 origin/feat/purchase-create-implementation -- backend/app` で次を確認した。

- `put_purchase_item`: 旧アイテムを読み取り、名前・カテゴリが変わる場合は一意性を事前確認し、予約の削除と新規予約を本体更新と同じトランザクションで行う。既存の完全一致ペアへの変更は新たに409となる（変更前は許可されていた）。Frontendの編集画面は409を「更新に失敗しました」の共通表示で扱う。
- `delete_purchase_item`: 旧アイテムを読み取ってから、本体と予約を同じトランザクションで削除する。
- 以前のPR #31にあったPUTの予約追随テスト（旧IMPL-RISK-001/002）は、編集が本スライスの仕様外であるため削除した。IMPL-RISK-003（削除後の再登録）は期待どおりの既存挙動維持として残した。

## 実装した処理フロー

1. 一覧画面（`features/Purchase.tsx`）の「追加」で登録ダイアログ（`features/CreatePurchaseDialog.tsx`）を開く。
2. react-hook-form + zodで5項目を検証する。名前・カテゴリは`trim()`後の空判定とコードポイント単位（`[...value].length`）の長さ上限、消費スピード・在庫は`valueAsNumber`で数値化し、空欄（`NaN`）を必須エラー、整数・0〜100,000を判定する（9f29e1d以降）。違反時は項目下にエラーを表示し送信しない。
3. `useCreatePurchase` → `api/purchases.ts` の `createPurchase`（openapi-fetch）で `POST /purchases` を送る。送信中は登録ボタンを無効化して「登録中...」と表示する。
4. API（`api/purchase.py`）は`PurchaseCreateRequest`（Pydantic、strict int、`max_length`、空白のみ拒否、`is_temporary`は既定値なしの必須項目）で検証し422を返す。利用者IDは依存関係（現在は固定`dev-user`スタブ）から取得する。
5. `services/purchase_service.create_purchase`がUUIDと日時をサーバー側で生成し、`models/purchase.create_purchase_item`が強整合Queryで既存の完全一致を確認後、本体アイテムと利用者単位の一意性予約（`PURCHASE_UNIQUE#sha256([name, category])`）を1トランザクションで書き込む。重複は`ItemAlreadyExistsError`→409。
6. 成功時はダイアログを閉じて入力を初期化し、`["purchases"]`クエリを無効化して`GET /purchases`で一覧を再取得する。失敗時はダイアログを開いたまま入力を維持する（第2版、`e8afdab`以降）。
   - `createPurchase`は`!response.ok`（または本文なし）で`ApiError(status, body)`を送出する。fetch自体の失敗は元の例外のまま伝播する。
   - 409は`ApiError.status === 409`で判定し、名前またはカテゴリの変更を促す重複表示を出す。本文は見ない。
   - 422は`detail[].loc`が`["body", <5項目のいずれか>]`の要素だけを項目エラー（`setError`）にし、その場合は共通エラーを出さない。対応する項目がない422（未知項目、本文全体、不正JSON位置、`detail`が配列でない、非JSON本文）は共通エラー「登録に失敗しました」になる。
   - それ以外（500、503、404、通信失敗）は共通エラー。
   - ダイアログを閉じるとフォームとmutationの状態を両方`reset()`し、開き直すと失敗表示は残らない。
7. 編集（PUT）・削除（DELETE）は、強整合で読み取った名前・カテゴリのまま本体が存在することを条件に、本体と予約（旧組の削除・新組の作成）を1トランザクションで書く。条件が失敗したら読み直して最大5回まで再試行し、使い切ると`ConditionalCheckFailedError`（500）。名前・カテゴリが変わる編集は事前に一覧Queryで重複を確認し、予約の作成失敗も409にする。

## 実装範囲

- Frontend: 登録フォーム検証、送信中状態、成功・失敗表示、一覧再取得、消費スピードと一時的購入の表示
- API: `POST /purchases`、既存`GET /purchases`、例外ハンドラ（409）
- Services / Domain: `create_purchase`（domainは変更なし）
- Persistence: DynamoDB本体アイテムと一意性予約（create / put / delete。第2版でput / deleteに読み取り時の名前・カテゴリを条件とする再試行を追加）
- External systems: DynamoDB Local 3.3.1（統合テスト・E2E）
- 対象外: Cognito認証（固定`dev-user`スタブ）、本番AWS、通知、購入時期計算、編集・削除の画面と操作（PURC-022〜024の一意性維持を除く）

## カバレッジ

### 実行条件

- Backend（`backend/`）: `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -q --cov=app --cov-branch --cov-report=term-missing`（unit + integration、162 passed、xfailなし。2026-10-02第2版検証）
- Frontend（`frontend/`）: `bun run test -- --run --coverage --coverage.include=src/features/CreatePurchaseDialog.tsx --coverage.include=src/api/client.ts --coverage.include=src/api/purchases.ts --coverage.reporter=text`（第2版の変更ファイル。`client.ts`と`purchases.ts`の分岐は`--coverage.reporter=json`で確認）
- ツール: coverage 7.16.2 / pytest-cov 7.1.0（backend dev依存に追加）、@vitest/coverage-v8 4.1.10（frontend dev依存に追加）

### 結果

| 対象 | Line | Branch | 備考 |
|---|---:|---:|---|
| `backend/app/api/schemas/purchase.py` | 100%（23/23） | 100%（2/2） | 第2版の`is_temporary`のstrict化を含む |
| `backend/app/models/purchase.py` | 94.2%（81/86） | 77.3%（17/22） | 第2版検証値。未カバーは81, 124（登録の重複以外の`ClientError`、GAP-002）、155（読み直しで本体なし、GAP-010）、215, 240（編集・削除の重複以外の`ClientError`、GAP-011）。第2版の変更行のうち再試行ループ、条件式、予約側409（209-212）、使い切り（217, 242）は実行済み。合算91% |
| `backend/app/api/purchase.py` | 100%（21/21） | 分岐なし | PUT・DELETEエンドポイントも実行 |
| `backend/app/services/purchase_service.py` | 100%（20/20） | 分岐なし | |
| `backend/app/api/exception_handlers.py` | 90% | - | 15は404ハンドラ（GAP-010と同じ経路） |
| `backend/app/api/deps.py` | 67% | - | 12はテストで依存を上書き。E2Eでは実行 |
| `frontend/src/features/CreatePurchaseDialog.tsx` | 100% | 97.43% | 第2版検証値。未カバーは137の`if (!next)`の偽側（`onOpenChange(true)`。一覧の「追加」はDialog外から開くため到達しない、GAP-012）。`invalidFormFields`の全ガード、`setError`、409判定、閉じる時の`reset()`（旧GAP-005）は実行済み |
| `frontend/src/api/client.ts` | 100% | 100% | `ApiError` |
| `frontend/src/api/purchases.ts` | 46.67%（7/15） | 第2版変更行の分岐は100% | `createPurchase`の`!response.ok || data === undefined`は両側実行済み。未カバー25-30, 40-43は`putPurchase`/`deletePurchase`、35は`getAllPurchases`のエラー分岐（いずれも第2版で未変更、GAP-006） |

coverage行番号は`models/purchase.py`の文単位。カバレッジ率は未検証箇所の発見に使用し、数値だけを完了条件にしない。

## 未カバー箇所の評価

| ID | 箇所・契約 | 分類 | リスク | 対応 | 仕様・Test Case ID上の根拠 |
|---|---|---|---|---|---|
| GAP-001 | `models/purchase.py` 75-78, 115-118（予約トランザクションの重複検出） | Critical | 同時登録時の唯一の永続化上の防壁。TDD-006では事前Queryで先に弾かれる場合があり、実行ごとに未実行になる | Add test（`test_reservation_rejects_duplicate_when_both_requests_pass_the_precheck`） | PURC-014-TC8 |
| GAP-002 | `models/purchase.py` 76, 118（重複以外の`ClientError`を再送出→500） | Important | 実DynamoDBの`TransactionConflict`等で409ではなく500になる（IMPL-RISK-006） | Justified。500時に内部情報を出さないことはUnitで確認。競合理由別の期待結果はDynamoDB Localで再現できないため残存リスク | PURC-014-TC8, PURC-017-TC2 |
| GAP-003 | `models/purchase.py` 146-185, `api/purchase.py` 51-60, `services` 55-68（PUT） | Resolved（第2版） | 仕様第2版PURC-022〜024でPUT/DELETEの一意性維持が範囲内になった | PURC-TDD-008〜010と`test_purchase_rev2_post.py`で実行・検証済み | PURC-022〜024 |
| GAP-004 | `models/purchase.py` 197, 212-215（存在しない購入物の削除） | Low risk | 削除は対象外。正常削除と再登録はIMPL-RISK-003で確認 | Justified | 仕様§8 |
| GAP-005 | `CreatePurchaseDialog.tsx` 閉じる操作での`reset()` | Resolved（第2版） | PURC-020で開き直し時の初期値が仕様化された | PURC-TDD-012と`CreatePurchaseDialog.rev2.post`の開き直し5ケースで実行 | PURC-020-TC1 |
| GAP-006 | `Purchase.tsx` 100-135、`usePurchases.ts` 29-31, 47、`api/purchases.ts` 21-26, 36-39 | Low risk | 編集・削除UIと一覧取得失敗。いずれも本スライス外 | Justified | 仕様§8 |
| GAP-007 | APIの422がクライアント検証を通過した後に返った場合の画面表示 | Resolved（仕様第2版で決定） | PURC-021で「項目ごとに識別できる形で表示」と定まった | PURC-TDD-013（name）と`CreatePurchaseDialog.rev2.post` PURC-021の6ケース（category、speed、stock、is_temporary、複数項目、既知＋未知項目）でPass。項目を名指ししない422は共通エラー（7ケース） | PURC-021-TC1, PURC-016-TC2 |
| GAP-008 | 「50文字」「30文字」の数え方 | Resolved（仕様第2版で決定） | 仕様§3「文字数はUnicodeコードポイント単位」と定まった | 既存のUI・APIテスト（`𠮷`×50/51、×30/31）がPURC-004-TC15をそのまま満たす（下表） | PURC-004-TC15 |
| GAP-009 | JSONの`1.0`や`"1"`を整数として扱うか | Resolved（仕様第2版で決定） | 仕様§3「JSONの整数値だけを受け付ける」と定まった | `test_purc_004_tc13_...`（speed・stockの`1.0`と`"1"`、4ケース）でPass | PURC-004-TC13 |
| GAP-010 | `models/purchase.py` 155（読み直しで本体が存在しない→`ItemNotFoundError`→404）、`exception_handlers.py` 15 | Low risk | 存在しない購入物の編集・削除、または削除と削除の競合。書き込みは行われず一意性に影響しない。編集・削除の応答は仕様§8の対象外 | Justified | 仕様§8、PURC-024 |
| GAP-011 | `models/purchase.py` 215, 240（編集・削除で重複・条件失敗以外の`ClientError`を再送出→500） | Important | 実DynamoDBの`TransactionConflict`等。トランザクションが取り消されるため予約は孤立しないが、応答は500。IMPL-RISK-006の編集・削除版 | Justified（DynamoDB Localで決定的に再現できず、編集・削除の応答は仕様§8の対象外）。500時に内部情報を出さないことは使い切りテストと`test_persistence_failure_returns_500_without_internal_details`で確認。残存リスクへ | PURC-024、仕様§6 |
| GAP-012 | `CreatePurchaseDialog.tsx` 137の`if (!next)`偽側 | Unreachable | 登録ダイアログは一覧の「追加」（Dialog外の状態）から開くため、Dialogが`onOpenChange(true)`を呼ぶ経路がない | Justified | - |

## 実装欠陥（仕様違反）

第2版検証（2026-10-02）では新たな実装欠陥は見つからなかった。以下は第1版の記録。

前回検証（09092c2）では、テストを削除・緩和せず、厳格な期待失敗（pytest `xfail(strict=True)` / Vitest `test.fails`）としてスイートに残した。実装の差し戻し修正（9f29e1d、プロダクトコードのみ）後、本再検証で期待失敗の指定を外して通常テストへ戻し、アサーションは変更せずにPassを確認した（DEFECT-003のテストには他の境界値テストと同じ`toHaveBeenCalledTimes(1)`を追加し、強化のみ行った）。

| ID | 状態 | 修正内容（`git diff 09092c2 HEAD`） | 仕様適合の判断 | 解消の証跡 |
|---|---|---|---|---|
| DEFECT-001 | Resolved | `PurchaseCreateRequest.is_temporary: bool = False` → `Field(description=...)`（既定値なし） | 仕様§3の必須に適合。PUT（`PurchasePutRequest`）は変更なしで範囲外の挙動追加なし | `test_missing_is_temporary_is_rejected_with_field_and_not_stored` Pass（422、`loc`に`is_temporary`、永続化なし） |
| DEFECT-002 | Resolved | `z.coerce.number()` → `register(..., { valueAsNumber: true })` + `z.number({ error })`。空欄は`NaN`となり項目別エラー | PURC-003-TC1・PURC-004「補正しない」に適合。初期値0（PURC-002-TC2）は維持 | 「emptied speed/stock」2ケース Pass（項目別エラー、他項目エラーなし、未送信）。PURC-002-TC2初期値テスト、境界値・小数・負数ケースも Pass |
| DEFECT-003 | Resolved | 文字数を`[...value].length`（コードポイント）で数える`requiredText`へ置換。空判定は`trim()`後 | API（Pythonの`len`、コードポイント）と一致しPURC-003のUI/API一貫性に適合。書記素とコードポイントが食い違う文字はGAP-008のまま | 「50 surrogate name」「30 surrogate category」Pass。51/31（`𠮷`・ASCII）拒否、50/30（ASCII）受理もPass |
| Baseline GAP-003（クリーンビルド） | Resolved | `frontend/package.json`の`build`を`tsc -b && vite build` → `vite build && tsc -b`（Viteの TanStack Routerプラグインが`routeTree.gen.ts`を生成してから型検査） | TDD計画でGreen Gateまでに解消すると定めた既存失敗の修正。期待動作は変えない | `rm -f src/routeTree.gen.ts && bun run build` 終了0（生成後に`tsc -b`も成功） |

修正は上記4ファイルの差分のみで、新しい利用者向け振る舞いは追加されていない。観察事項（いずれも期待動作に影響しない）: `CLAUDE.md`のCommands節は`bun run build`を旧順序`tsc -b && vite build`と記載したまま。`frontend/src/api/schema.d.ts`の作成リクエスト`is_temporary`は型としては必須だが、生成時の`@default false`コメントが残る（OpenAPIからの再生成で解消）。

前回検証時の欠陥記録（参考）:

| ID | Test Case ID | 内容 | 失敗アサーション（`--runxfail`または`test.each`へ一時変更して確認） | 実テスト |
|---|---|---|---|---|
| DEFECT-001 | PURC-003-TC3 | APIで`is_temporary`を欠落させても201で登録される（仕様§3で「一時的な購入」は必須。初期値falseは登録画面の初期値）。スライス前からの既存挙動（`is_temporary: bool = False`） | `assert response.status_code == 422` → `assert 201 == 422` | `backend/tests/integration/api/test_purchase_create_post.py::test_missing_is_temporary_is_rejected_with_field_and_not_stored` |
| DEFECT-002 | PURC-003-TC1（PURC-004「補正しない」） | 消費スピード・在庫の入力欄を空にして登録すると、`z.coerce.number("")`により0として送信される | `expect(fieldError(key)).not.toBeNull()` が `expected null not to be null`。送信内容は`{speed: 0}`／`{stock: 0}`を確認 | `frontend/src/features/CreatePurchaseDialog.post.test.tsx` 「PURC-003-TC1 emptied speed/stock」 |
| DEFECT-003 | PURC-004-TC3, PURC-004-TC5（PURC-003のUI/API一貫性） | UIはUTF-16コード単位で数えるため、`𠮷`×50の名前・`𠮷`×30のカテゴリを拒否する（APIは受け付ける） | `expect(createPurchase).toHaveBeenCalledWith(...)` が `Number of calls: 0` | 同ファイル「PURC-004-TC3 50 surrogate name」「PURC-004-TC5 30 surrogate category」 |

## 追加した単体・コンポーネントテスト

| Test Case ID / Risk ID | テストレベル | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PURC-017-TC2（API） | Unit | `backend/tests/unit/api/test_purchase_create_errors.py` | 永続化層の内部エラーで500となり、ARN・テーブル名・例外名を返さない | Pass |
| PURC-002-TC1/TC2 | Component | `CreatePurchaseDialog.post.test.tsx`「five inputs exist with the approved initial values」 | 5項目と初期値 | Pass |
| PURC-003-TC1, PURC-004-TC1/2/4/6/8/10, PURC-016-TC2 | Component | 同「invalid input is not sent」17ケース（空、ASCII空白、U+3000、混在空白、51/31文字のASCIIと`𠮷`、負数、小数、100,001） | 項目別エラー、他項目にエラーなし、未送信 | Pass |
| PURC-003-TC1（空欄） | Component | 同「emptied speed/stock」2ケース | 必須数値の空欄（`NaN`経路） | Pass（DEFECT-002解消。旧Expected fail） |
| PURC-004-TC3/5/7/9/11/12, PURC-014-TC5/6（UI側の非正規化） | Component | 同「accepted boundaries are sent unchanged」10ケース | 境界値と文字列が変更されずに1回だけ送信される | Pass |
| PURC-004-TC3/5（`𠮷`） | Component | 同「50 surrogate name」「30 surrogate category」 | 文字数の数え方のUI/API一貫性（コードポイント50/30） | Pass（DEFECT-003解消。旧Expected fail） |
| PURC-001-TC1 | Component | `Purchase.post.test.tsx`「the add action on the list opens the registration screen」 | 一覧から登録画面を開く | Pass |
| PURC-012-TC2/TC3 | Component | 同「only the temporary purchase is marked temporary」 | 一時的購入表示の両極性 | Pass |
| PURC-010-TC1/TC2, PURC-011-TC1, PURC-012-TC4 | Component（fetch境界） | 同「closes, refetches, shows no extra success message, and reopens with initial values」 | 実APIクライアント・フック経由の成功後状態 | Pass |
| PURC-013-TC1 | Component（fetch境界） | 同「submit action is disabled while the request is pending」 | 処理中の無効化と追加送信なし | Pass |
| PURC-013-TC1/TC2 | Component（fetch境界） | 同「a rapid double click sends exactly one request」 | 同一画面操作の二重送信 | Pass |
| PURC-015-TC1, 016-TC1, 017-TC1/2, 018-TC1 | Component（fetch境界） | 同「failed registration」5ケース（409、内部情報入り500、平文500、通信失敗、422） | ダイアログ維持、5項目維持、原因別／共通表示、内部情報非表示、1.5秒待機中に自動再送なし | Pass |
| PURC-016-TC1 | Component（fetch境界） | 同「duplicate and generic failures are distinguishable」 | 重複表示と共通エラーが識別可能 | Pass |
| PURC-018-TC2 | Component（fetch境界） | 同「after a network failure a manual retry sends exactly one new request」 | 手動再試行で新しい要求が1回だけ | Pass |

### 第2版で追加したコンポーネントテスト

すべて`frontend/src/features/CreatePurchaseDialog.rev2.post.test.tsx`（28ケース）。`fetch`だけを置き換え、実際の`ApiError`変換、フック、ダイアログ、一覧を通す。共通エラーは、同じテスト内で先に通信失敗を起こして表示された文言を基準とし、文言そのものは固定しない（仕様§7）。

| Test Case ID / Risk ID | 実テスト（describe） | 追加理由 | 結果 |
|---|---|---|---|
| PURC-016-TC1, 015-TC1, 017-TC2, 018-TC1, IMPL-RISK-007 | 「409 is a duplicate by status, whatever the body says」5ケース（英語detail、detailなし、内部情報入りdetail、平文、空本文） | 409を本文によらず重複として表示し、名前・カテゴリの変更を促す。入力維持、内部情報非表示、自動再送なし | Pass |
| PURC-017-TC1/TC2, 015-TC1, 018-TC1 | 「other failures are generic even if the body looks like a known cause」4ケース（重複文言入り500、422形式の500、503 HTML、内部情報入り404） | 原因の判定をステータスだけで行う（文言・本文形に依存しない）。共通エラーと同じ表示、項目エラー・重複表示なし | Pass |
| PURC-021-TC1, 016-TC2, 015-TC1 | 「an API 422 is shown on the offending fields」6ケース（category、speed、stock、speed＋stock、未知項目＋name、is_temporary） | 該当項目だけにエラー、他項目にエラーなし、入力維持。is_temporaryはチェックボックス直後に、共通エラーと異なる表示 | Pass |
| PURC-015-TC1, 017-TC1/TC2, 018-TC1 | 「a 422 that names no input field is a generic failure」7ケース（未知項目`user_id`、`["body"]`、不正JSON位置`["body", 12]`、`detail`が文字列、`detail: [null]`、detailなし、平文） | 識別できる項目がない422は共通エラー。項目エラー・重複表示なし、内部情報（`user_id`、`json_invalid`等）非表示 | Pass |
| PURC-020-TC1 | 「reopening clears every kind of failure display」5ケース（409、422 name、422 is_temporary、422 未知項目、通信失敗） | 開き直した画面の表示が初回と一致し、初期値に戻る | Pass |
| PURC-018-TC2（仕様§7-6） | 「a manual retry after an API 422 sends one new request」 | 項目エラーの後も同じ入力から手動再試行でき、要求が1回だけ送られる | Pass |

500・通信失敗の共通エラー、内部情報非表示、1.5秒待機中の自動再送なしは既存の`Purchase.post.test.tsx`「failed registration」5ケースでも第2版実装に対してPass（期待値は変更していない）。

`Purchase.post.test.tsx`は`@/api/purchases`をモックせず`fetch`だけを置き換え、openapi-fetchのエラー変換からUI表示までを通して検証する。

## 統合テスト

すべて`backend/tests/integration/api/test_purchase_create_post.py`（`pytestmark = pytest.mark.integration`、承認済みrunner経由、各テストで空テーブルを再作成）。

| Test Case ID / Risk ID | 接続する境界 | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PURC-003-TC2, PURC-004-TC1/2/4/6/8/10, PURC-016-TC2（API） | API → Pydantic → DynamoDB Local | `test_invalid_input_is_rejected_with_field_and_not_stored`（18ケース。U+3000、`𠮷`×51/×31、`null`を含む） | 422、`loc`による項目識別、永続化なし | Pass |
| PURC-003-TC3 | 同上 | `test_missing_required_field_is_rejected_with_field_and_not_stored`（name/category/speed/stock） | 欠落項目の422と識別 | Pass |
| PURC-003-TC3（is_temporary） | 同上 | `test_missing_is_temporary_is_rejected_with_field_and_not_stored` | 必須項目の欠落 | Pass（DEFECT-001解消。旧Expected fail） |
| PURC-004-TC3/5/7/9/11 | 同上 | `test_boundary_input_is_created_and_stored_unchanged`（9ケース。`𠮷`×50/×30を含む） | 201と、再取得値が送信値と一致（切り詰め・丸めなし） | Pass |
| PURC-006-TC1/TC2 | API → services → DynamoDB Local | `test_each_create_gets_distinct_id_and_server_timestamps` | クライアント指定のid・日時を無視し、異なるIDとサーバー日時を付与 | Pass |
| PURC-014-TC1, PURC-016-TC1（API） | 同上 | `test_exact_duplicate_is_rejected_with_409_and_original_kept` | 409、重複を識別できるdetail、元の購入物が不変 | Pass |
| PURC-014-TC2 | 同上 | `test_duplicate_ignores_non_key_fields`（4ケース） | 名前・カテゴリ以外の差を無視 | Pass |
| PURC-014-TC3/4/5/6 | 同上 | `test_non_identical_pairs_are_distinct_and_not_normalized`（5ケース） | 完全一致のみ重複。文字列を正規化せず保存 | Pass |
| IMPL-RISK-004 | 予約なし既存アイテム → create | `test_duplicate_of_item_without_reservation_is_rejected` | 予約導入前データとの重複 | Pass |
| IMPL-RISK-003 | DELETE → 予約解放 → create | `test_delete_then_recreate_same_pair_succeeds` | 削除後の再登録（既存挙動の維持） | Pass |
| PURC-019-TC1 | 利用者依存 → Query | `test_list_contains_only_current_users_purchases` | 利用者ごとの一覧分離 | Pass |
| PURC-014-TC8, IMPL-RISK-005 | 予約トランザクション | `test_reservation_rejects_duplicate_when_both_requests_pass_the_precheck` | 事前Queryを空にして競合窓を決定的に再現し、予約側で201/409・1件保存 | Pass |

### 第2版で追加した統合テスト

すべて`backend/tests/integration/api/test_purchase_rev2_post.py`（14ケース、`pytestmark = pytest.mark.integration`、承認済みrunner経由）。競合は凍結TDDファイル`test_purchase_uniqueness_rev2.py`と同じ手法（`app.models.purchase.get_table`を、対象キーの`get_item`だけ名前変更前のスナップショットを返すプロキシへ差し替える）で決定的に再現する。編集・削除のHTTPステータスは仕様§8の対象外のため期待せず、PURC-024で観測できる結果（一覧にない組は201、一覧にある組は409）だけを判定する。

| Test Case ID / Risk ID | 接続する境界 | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PURC-004-TC13 | API → Pydantic → DynamoDB Local | `test_purc_004_tc13_integer_valued_non_integer_json_is_rejected_and_not_stored`（speed・stockの`1.0`、`"1"`の4ケース） | 422、`loc`による項目識別、永続化なし | Pass |
| PURC-023-TC3 | PUT → 予約 → POST | `test_purc_023_tc3_edit_without_pair_change_keeps_duplicate_rejected`（speed、stock、is_temporary、3項目同時、同一内容の5ケース） | 名前・カテゴリを変えない編集の後も同じ組の登録が409、一覧不変 | Pass |
| PURC-024（TDD計画で実装後へ送付した競合） | 古い読み取りのPUT → 条件付きトランザクション | `test_purc_024_same_pair_edit_racing_rename_leaves_no_orphaned_pair`（stockのみ、is_temporaryのみの2ケース） | 名前変更前に読んだ、名前を変えない編集が名前変更と競合しても、一覧にない組は201、一覧にある組は409。差し込みが1回実行されたことも確認 | Pass |
| PURC-024, IMPL-RISK-008 | 再試行の使い切り（PUT） | `test_purc_024_edit_whose_retries_are_exhausted_leaves_no_orphaned_pair` | 毎回古い読み取りを返して5回使い切らせる。応答に内部情報なし、購入物は残り、一覧に従って201/409 | Pass（観測した応答は500 `Internal Server Error`） |
| PURC-024, IMPL-RISK-008 | 再試行の使い切り（DELETE） | `test_purc_024_delete_whose_retries_are_exhausted_leaves_no_orphaned_pair` | 同上（削除） | Pass（同上） |
| PURC-023-TC2, IMPL-RISK-009 | 編集の事前確認 → 予約トランザクション | `test_purc_023_tc2_rename_into_existing_pair_is_409_even_when_precheck_misses_it` | 事前確認を空にしても予約で409、AとBは不変 | Pass |

PURC-004-TC15は新規テストを作らず、既存テストを引用する（期待結果がそのまま一致するため）。

| 側 | 50文字・30文字（受理） | 51文字・31文字（拒否） |
|---|---|---|
| 画面 | `CreatePurchaseDialog.post.test.tsx`「PURC-004-TC3 50 surrogate name」「PURC-004-TC5 30 surrogate category」（1回だけ送信、値は不変） | 同「invalid input is not sent」の「PURC-004-TC4 51 surrogate name」「PURC-004-TC6 31 surrogate category」（項目エラー、未送信） |
| API | `test_boundary_input_is_created_and_stored_unchanged[PURC-004-TC3-name-50-surrogate]`、`[PURC-004-TC5-category-30-surrogate]`（201、保存値一致） | `test_invalid_input_is_rejected_with_field_and_not_stored[PURC-004-TC4-name-51-surrogate]`、`[PURC-004-TC6-category-31-surrogate]`（422、項目識別、永続化なし） |

## E2E

`e2e/`（`@playwright/test` 1.56.1、Chromium 1194）。`bash e2e/run-e2e.sh` が承認済みrunnerでDynamoDB Localと空のテストテーブルを用意し、子コマンドとしてPlaywrightを起動する。Playwrightの`webServer`がuvicorn（`main:app`、8000番）とVite dev（`localhost:5173`）を起動する。Dockerは使わない。認証は固定`dev-user`スタブのためCognito資格情報は不要。

| Test Case ID / Risk ID | ユーザーフロー | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
| PURC-009-TC2（+001-TC1, 005-TC1, 010-TC1, 011-TC1, 012-TC1/2, 014-TC1, 015-TC1, 016-TC1, IMPL-RISK-007） | ブラウザで登録 → 一覧表示 → 再読み込み後も表示・APIで1件 → 同一名前・カテゴリを再登録 → 原因表示・入力維持・1件のまま | `e2e/tests/purchase-create.spec.ts`「PURC-009-TC2 ...」 | 代表正常系の全経路と実APIの409表示 | Pass |
| PURC-013-TC2 | 登録ボタンのダブルクリック → POST 1回・永続化1件 | 同「PURC-013-TC2 ...」 | 同一画面操作の二重送信を実ブラウザで確認 | Pass |

## 論理テストケースの消化確認

全64件（第2版）。「TDD」は凍結済みテスト（第1版: `test_purchase_create.py`、`Purchase.test.tsx`、`CreatePurchaseDialog.test.tsx`、第2版: `test_purchase_uniqueness_rev2.py`、`CreatePurchaseDialog.rev2.test.tsx`）。「rev2.post」は`CreatePurchaseDialog.rev2.post.test.tsx`、「rev2 Integration」は`test_purchase_rev2_post.py`。重複検証は、TDDが代表1値だけを固定しているため境界値を補う場合、または同じ契約を別レイヤーの接続（UI⇔API、API⇔実ブラウザ）で確認する場合に限った。

| Test Case ID | 最終的な検証先 | 実テスト・証跡 | 結果 | 対象外理由 |
|---|---|---|---|---|
| PURC-001-TC1 | Component + E2E | `Purchase.post` PURC-001-TC1 / E2E 1 | Pass | |
| PURC-002-TC1 | Component | `CreatePurchaseDialog.post` PURC-002 | Pass | |
| PURC-002-TC2 | Component | 同上、`Purchase.post` PURC-001-TC1 | Pass | |
| PURC-003-TC1 | TDD + Component | PURC-TDD-003 / invalid input 17ケース / emptied 2ケース | Pass（DEFECT-002解消） | |
| PURC-003-TC2 | TDD + Integration | PURC-TDD-004 / `test_invalid_input_...` | Pass | |
| PURC-003-TC3 | Integration | `test_missing_required_field_...` / `test_missing_is_temporary_...` | Pass（DEFECT-001解消） | |
| PURC-004-TC1 | Component + Integration | 空・空白・U+3000・混在空白 | Pass | |
| PURC-004-TC2 | Component + Integration | 同上（カテゴリ） | Pass | |
| PURC-004-TC3 | Component + Integration | 50文字ASCII・`𠮷` | Pass（DEFECT-003解消） | |
| PURC-004-TC4 | Component + Integration | 51文字ASCII・`𠮷` | Pass | |
| PURC-004-TC5 | Component + Integration | 30文字ASCII・`𠮷` | Pass（DEFECT-003解消） | |
| PURC-004-TC6 | Component + Integration | 31文字ASCII・`𠮷` | Pass | |
| PURC-004-TC7 | TDD + Component + Integration | speed 0（TDD-001/002）、100000 | Pass | |
| PURC-004-TC8 | Component + Integration | speed -1 / 1.5 / 100001 | Pass | |
| PURC-004-TC9 | Component + Integration | stock 0 / 100000 | Pass | |
| PURC-004-TC10 | Component + Integration | stock -1 / 1.5 / 100001 | Pass | |
| PURC-004-TC11 | Component + Integration | temporary + speed 0 | Pass | |
| PURC-004-TC12 | TDD + Component | PURC-TDD-001/002 | Pass | |
| PURC-004-TC13 | rev2 Integration | `test_purc_004_tc13_...`（4ケース） | Pass | |
| PURC-004-TC14 | TDD | PURC-TDD-011（`"true"`、`1`） | Pass | |
| PURC-004-TC15 | Component + Integration（既存） | `CreatePurchaseDialog.post` 50/51 surrogate name、30/31 surrogate category / `test_boundary_input_...`・`test_invalid_input_...`のsurrogate 4ケース | Pass | |
| PURC-005-TC1 | TDD + E2E | PURC-TDD-001 / E2E 1 | Pass | |
| PURC-006-TC1 | TDD + Integration | PURC-TDD-001 / `test_each_create_gets_distinct_id_and_server_timestamps` | Pass | |
| PURC-006-TC2 | Integration | 同上 | Pass | |
| PURC-007-TC1 | TDD | PURC-TDD-005 | Pass | |
| PURC-008-TC1 | TDD | PURC-TDD-001 | Pass | |
| PURC-008-TC2 | TDD | PURC-TDD-001 | Pass | |
| PURC-008-TC3 | TDD | PURC-TDD-001 | Pass | |
| PURC-009-TC1 | TDD | PURC-TDD-001 | Pass | |
| PURC-009-TC2 | E2E | E2E 1（再読み込み後の一覧とAPI再取得） | Pass | |
| PURC-010-TC1 | Component + E2E | `Purchase.post` successful registration / E2E 1 | Pass | |
| PURC-010-TC2 | Component | 同上（再オープン時の初期値） | Pass | |
| PURC-011-TC1 | TDD + Component + E2E | PURC-TDD-002 / successful registration（GET 2回） / E2E 1 | Pass | |
| PURC-012-TC1 | TDD + E2E | PURC-TDD-002 / E2E 1 | Pass | |
| PURC-012-TC2 | Component + E2E | temporary badge / E2E 1 | Pass | |
| PURC-012-TC3 | Component | temporary badge | Pass | |
| PURC-012-TC4 | Component | successful registration（status/alertロールと成功文言なし） | Pass | |
| PURC-013-TC1 | Component | pending / double click | Pass | |
| PURC-013-TC2 | Component + E2E | double click / E2E 2 | Pass | |
| PURC-014-TC1 | Integration + E2E | `test_exact_duplicate_...`、`test_duplicate_of_item_without_reservation_...` / E2E 1 | Pass | |
| PURC-014-TC2 | Integration | `test_duplicate_ignores_non_key_fields` | Pass | |
| PURC-014-TC3 | Integration | `test_non_identical_pairs_...` | Pass | |
| PURC-014-TC4 | Integration | 同上 | Pass | |
| PURC-014-TC5 | Integration + Component | 同上 / UI非トリム送信 | Pass | |
| PURC-014-TC6 | Integration + Component | 同上 / UI全角送信 | Pass | |
| PURC-014-TC7 | TDD | PURC-TDD-007 | Pass | |
| PURC-014-TC8 | TDD + Integration | PURC-TDD-006 / `test_reservation_rejects_duplicate_...` | Pass | |
| PURC-015-TC1 | Component + E2E | failed registration 5ケース / rev2.post 409・共通・422の全22ケースで入力維持 / E2E 1（409） | Pass | |
| PURC-016-TC1 | TDD + Integration + Component + E2E | PURC-TDD-014 / 409 detail / distinguishable / rev2.post 409×5 / E2E 1 | Pass | |
| PURC-016-TC2 | TDD + Component + Integration | PURC-TDD-003/004 / invalid input（項目別）/ API `loc` / rev2.post PURC-021（サーバー422の項目別表示） | Pass | |
| PURC-017-TC1 | Component | failed registration（500×2、通信失敗）/ rev2.post 共通エラー11ケース | Pass | |
| PURC-017-TC2 | Unit + Component + Integration | `test_persistence_failure_returns_500_without_internal_details` / 内部情報非表示 / 使い切り2ケースの応答 | Pass | |
| PURC-018-TC1 | Component | failed registration（1.5秒待機でPOST 1回）/ rev2.post 全失敗ケース（0.5秒待機で追加POSTなし） | Pass | |
| PURC-018-TC2 | Component | manual retry / rev2.post 422後の手動再試行 | Pass | |
| PURC-019-TC1 | Integration | `test_list_contains_only_current_users_purchases` | Pass | |
| PURC-019-TC2 | TDD | PURC-TDD-005 | Pass | |
| PURC-020-TC1 | TDD + Component | PURC-TDD-012（500）/ rev2.post 開き直し5ケース | Pass | |
| PURC-021-TC1 | TDD + Component | PURC-TDD-013（name）/ rev2.post PURC-021 6ケース | Pass | |
| PURC-022-TC1 | TDD + Integration | PURC-TDD-010 / `test_delete_then_recreate_same_pair_succeeds` | Pass | |
| PURC-023-TC1 | TDD | PURC-TDD-010 | Pass | |
| PURC-023-TC2 | TDD + rev2 Integration | PURC-TDD-010 / `test_purc_023_tc2_rename_into_existing_pair_..._precheck_misses_it` | Pass | |
| PURC-023-TC3 | rev2 Integration | `test_purc_023_tc3_...`（5ケース） | Pass | |
| PURC-024-TC1 | TDD + rev2 Integration | PURC-TDD-009 / 名前を変えない編集との競合2ケース / 編集の使い切り | Pass | |
| PURC-024-TC2 | TDD + rev2 Integration | PURC-TDD-008 / 削除の使い切り | Pass | |

64/64割り当て済み。未割り当て0件。対象外0件。Fail 0件。BLOCKED_SPEC 0件。期待失敗（xfail / test.fails）の指定はない。

## 全体検証

2026-10-02、Linux（Claude Code）、第2版検証。プロダクトコードは`e8afdab0488b757760404fb1151e60c84d465a7d`、テストは本レポートと同じコミットの作業ツリーで実行した。Backendは`backend/`から、Frontendは`frontend/`から実行。事前に`bash scripts/setup_host_prerequisites.sh --check`（終了0、mise 2026.9.12 / uv 0.12.18 / Python 3.14.7 / Java 17.0.20.1）を確認した。

| 検証 | コマンド | 結果 | 備考 |
|---|---|---|---|
| Backend lint / format | `../bin/mise exec -- uv run ruff check .` / `../bin/mise exec -- uv run ruff format --check .` | Pass（終了0 / 0） | All checks passed / 50 files already formatted |
| Backend unit | `../bin/mise exec -- uv run pytest -m "not integration" -q` | Pass（終了0） | 73 passed, 89 deselected |
| Integration（全体） | `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q` | Pass（終了0） | 89 passed（第2版Green時75＋本検証14）、73 deselected、Child exit 0、DynamoDB Local停止確認 |
| Frontend lint / format | `bun run lint` / `bun run format:check` | Pass（終了0 / 0） | 42 files / 37 files、No fixes applied |
| Frontend tests | `bun run test -- --run` | Pass（終了0） | 6 files、77 passed（第2版Green時49＋本検証28） |
| Type check + Build（クリーン） | `rm -f src/routeTree.gen.ts && bun run build`（`vite build && tsc -b`） | Pass（終了0） | built、`tsc -b`成功 |
| E2E | `bash e2e/run-e2e.sh` | Pass（終了0） | 2 passed、Child exit 0、DynamoDB Local停止確認 |
| Coverage（Backend全体） | 「カバレッジ」節のコマンド | Pass | 162 passed |
| Infrastructure validation | Environment smoke（runnerのAPI ready、`--check`） | Pass | Terraformは未実装のため対象なし |

凍結TDDテストは`git diff 15e48f6 HEAD -- backend/tests/integration/api/test_purchase_create.py frontend/src/features/Purchase.test.tsx frontend/src/features/CreatePurchaseDialog.test.tsx`と`git diff 8e939a2 HEAD -- backend/tests/integration/api/test_purchase_uniqueness_rev2.py frontend/src/features/CreatePurchaseDialog.rev2.test.tsx`で差分なし。`git diff e8afdab HEAD -- backend/app frontend/src`は空（本検証の追加はテスト2ファイルの新規作成と本レポートの更新のみ）。プロダクトコード、仕様、論理テストケース、TDD計画は変更していない。

## 未実行・残存リスク

| 項目 | 理由 | 影響 | 後続対応 |
|---|---|---|---|
| 仕様§10: 保存完了後に応答だけ失われる | 冪等性キーと結果照合は本スライス対象外 | 利用者には失敗と表示され、手動再試行は409（重複）になる | 後続課題（仕様§10） |
| IMPL-RISK-006 `TransactionConflict`（登録） | DynamoDB Localで決定的に再現できない（GAP-002） | 実DynamoDBの同時登録で敗者が409ではなく500となる可能性。重複自体は防止される | 実環境での負荷検証、またはエラー変換の仕様確認 |
| IMPL-RISK-008 編集・削除の再試行の使い切り→500 | 仕様§8で編集・削除の応答は対象外で、期待ステータスを導けない。テストでは一意性（PURC-024）と内部情報非表示だけを確認した | 同じ購入物に5回連続で競合した利用者には、編集画面の共通エラー（「更新に失敗しました」）として見える。予約は孤立しない。重複以外の`ClientError`（GAP-011）も同様に500 | 編集の仕様化時に、競合時の応答（409／再試行の案内など）を決める |
| DynamoDB Local統合テストとE2EがCI未実行 | `.github/workflows/integration.yml`と`e2e.yml`が未作成（`test.yml`はunitとVitest。第2版で`--passWithNoTests`は削除済み） | PRごとの自動検出は統合・E2E・競合系に及ばない | テスト実行環境構築計画どおり`integration.yml`と`e2e.yml`を追加 |
| Cognito認証 | 未実装（固定`dev-user`スタブ） | 実際の利用者分離はAPI依存の上書きでのみ検証 | 認証実装時にE2Eへ追加 |
| CIでbuildを実行していない | `lint.yml`・`test.yml`は`bun run build`を含まない | クリーンビルドの回帰はローカル検証でしか検出できない | Low。CI整備時に判断 |
| 一覧Queryのページネーションなし | 既存実装。登録・編集の事前確認も同じ関数を使う | 1MBを超える利用者パーティションでは事前確認の漏れや一覧の欠落が起こりうる（予約トランザクションで重複自体は防止。IMPL-RISK-009のテスト参照） | Low。件数増加時に対応 |
| is_temporaryの項目エラーの関連付け | 項目エラーはチェックボックスの直後に表示され、共通エラーと同じ位置に出る（文言は異なる）。`aria-describedby`等の関連付けはない | 支援技術での識別が文言に依存する。仕様はアクセシビリティ上の関連付けを定めていない | Low。UI改善時に判断 |
| OBS-001 編集の入力制約が登録と異なる | 仕様§8で編集の操作は対象外 | 編集画面では消費スピード0や小数の扱いが登録と異なる | 編集の仕様化時に扱う |

解消済み: SCOPE-001（仕様第2版の範囲に入った）、GAP-007/008/009（仕様第2版で決定し、テストでPass）、IMPL-RISK-007（409をステータスで判定）。

## Completion Gate（`docs/TDD-WORKFLOW.md` 5.7）

対象SHA: プロダクトコード`e8afdab0488b757760404fb1151e60c84d465a7d`、テスト・レポートは本検証コミット（`verify/purchase-create`、親`29f5f1ecb9a2eb43cd2b1cdd6b15811956019270`）。

| 条件 | 判定 | 根拠 |
|---|---|---|
| 全必須テストと回帰テストがGreen | 満たす | unit 73、integration 89、Vitest 77、E2E 2、すべてPass。期待失敗なし |
| 必須の静的検査とbuildが完了 | 満たす | ruff check / format、biome lint / format、クリーンビルド（`tsc -b`含む）が終了0 |
| 全Test Case IDの対応が記録済みで、未割り当てがない | 満たす | 64/64、Fail 0、BLOCKED_SPEC 0 |
| Criticalな未カバー箇所が残っていない | 満たす | 第2版の変更行のうち未実行は`models/purchase.py` 155（Low、GAP-010）、215, 240（Important・Justified、GAP-011）、`CreatePurchaseDialog.tsx` 137偽側（Unreachable、GAP-012）のみ。予約側409（209-212）はIMPL-RISK-009のテストで実行 |
| 未検証項目、Deferred、既知制約、残存リスクが明示済み | 満たす | 仕様§10、IMPL-RISK-006、IMPL-RISK-008（使い切り→500）、統合・E2EのCI未実行、Cognitoスタブ等を「未実行・残存リスク」に記載 |
| 実装後テストレポートが対象SHAと整合 | 満たす | プロダクトコード`e8afdab`（以後`backend/app`、`frontend/src`に差分なし）、テストは本レポートと同一コミット |
| 未承認の仕様変更、テスト緩和、範囲外変更がない | 満たす | 仕様・論理テストケース・TDD計画・凍結テスト5ファイルは変更なし。SCOPE-001は仕様第2版（2026-10-02承認）で範囲内になった。第2版Greenの`.github/workflows/test.yml`（`--passWithNoTests`削除）と`CLAUDE.md`1行はTDD計画の既定方針（テスト作成後に外す）に沿う |

Completion Gateはすべて満たす。最終コードレビューと人間によるレポート確認は未実施。

## Slice Complete Gate

- [x] 実装した垂直スライスが仕様の開始点から終了点まで成立する（E2Eで確認）
- [x] 論理テストケースの参照コミットを記録した（`b06800e`、第2版）
- [x] すべての論理Test Case IDに検証先または対象外理由がある（64/64）
- [x] Criticalな未カバー箇所が残っていない
- [x] Importantな未カバー箇所をテストしたか、残す理由を記録した（GAP-002、GAP-011）
- [x] 必要な単体・コンポーネント・統合・E2Eを実行した
- [x] 全体回帰、Lint、型チェック、ビルドを確認した（クリーンビルドを含めすべてPass。2026-10-02第2版検証）
- [x] 未実行の検証と残存リスクを明示した
- [x] 仕様または論理テストケースの変更時に影響する承認を取り直した（第2版は2026-10-02にym28-itが承認済み。本検証では変更なし）
- [ ] 人間がテスト内容、実行結果、対象外理由、残存リスクを確認した

第2版で新たな実装欠陥はなく、BLOCKED_SPECもない。最終コードレビューと人間によるレポート確認が残るため、本レポート時点ではスライス完了と判定しない。
