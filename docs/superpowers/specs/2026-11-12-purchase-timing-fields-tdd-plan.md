# 購入タイミング計算用の登録項目（PTF） TDD計画

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `docs/superpowers/specs/2026-11-12-purchase-timing-fields-design.md`（PTF-001〜016） |
| 論理テストケースSSOT | `docs/superpowers/specs/2026-11-12-purchase-timing-fields-test-cases.md` |
| 論理テストケースの参照コミット | `74eba69` |
| 変更単位 | 購入物を購入単位・1単位あたりの日数・余裕日数付きで登録し、在庫を数えた日時とともに永続化・一覧表示する |
| 文書状態 | Test Plan Approved |

論理テストケースの期待結果をこの文書で再定義しない。期待結果はTest Case IDを通じてSSOTを参照する。

## 機能目的

購入時期の計算（①-2）に必要な値（購入単位、1単位あたりの日数、余裕日数、在庫を数えた日時）を、購入物の登録時にそろえて永続化する。

## 対象範囲

- 対象: 登録画面、登録API、一覧API・一覧表示、永続化。既存の編集（PUT）が新しい項目を失わないこと、在庫変更時に在庫を数えた日時を更新すること
- 対象外: 購入時期の計算、在庫の入れ直し、編集画面の作り直し、既存データの移行

## 仕様不足・判断保留

| ID | 不足情報 | 影響する契約・Test Case ID | 分類 | 必要な確認 | 状態 |
|---|---|---|---|---|---|
| なし | - | - | - | - | - |

## 中心的契約候補

| Contract ID | 契約 | 仕様ID | 対応Test Case ID | 該当する選定条件 | 既存保護 | TDD適格性・Red例外 | AIの判定 |
|---|---|---|---|---|---|---|---|
| PTF-CORE-001 | 有効な入力で登録すると、購入単位・1単位あたりの日数・余裕日数が永続化され、在庫を数えた日時が作成日時と同じ時刻で記録され、登録と一覧取得のレスポンスに含まれる。旧名`speed`はレスポンスに含まれない | PTF-001, 006, 008, 011, 015 | PTF-001-TC2, PTF-006-TC1, PTF-008-TC1, PTF-011-TC1, PTF-015-TC1 | 1 / 2 / 4 / 5 | なし（既存テストは`speed`前提） | 適格。新項目が未実装のため、レスポンスに項目がない・422になることでRedになる | 候補 |
| PTF-CORE-002 | 在庫を数えた日時はサーバーが決め、クライアントの値を使わない | PTF-006 | PTF-006-TC2 | 3 / 4 | なし | 適格。未実装時はレスポンスに項目がなくRed | 候補 |
| PTF-CORE-003 | 1単位あたりの日数は0〜365の整数だけを受け付け、366・小数・文字列・負数を拒否する。旧名`speed`だけでは1単位あたりの日数の欠落として拒否する | PTF-001, 002, 005 | PTF-002-TC1, PTF-002-TC2, PTF-005-TC1, PTF-005-TC2, PTF-001-TC3 | 3 / 4 | なし（PURC-004-TC7/8は上限100,000の`speed`） | 適格。366が現在は受け付けられる・`speed`だけで登録できることでRed | 候補 |
| PTF-CORE-004 | 余裕日数は必須で、0〜30の整数だけを受け付ける | PTF-003, 005 | PTF-003-TC2, PTF-003-TC3, PTF-003-TC4, PTF-005-TC3 | 3 / 4 | なし | 適格。欠落・31が受け付けられることでRed | 候補 |
| PTF-CORE-005 | 購入単位は必須で、空白文字だけの値と11文字以上を拒否し、10文字まで（コードポイント単位）は入力どおり保存する | PTF-014 | PTF-014-TC1, PTF-014-TC2, PTF-014-TC3, PTF-014-TC4, PTF-014-TC5 | 3 / 4 | なし | 適格。欠落が受け付けられることでRed | 候補 |
| PTF-CORE-006 | 編集で在庫を変えたときだけ、在庫を数えた日時をその編集の更新日時と同じ時刻に更新する。名前・カテゴリだけの変更や在庫が同じ編集では変えない | PTF-007, 013 | PTF-007-TC1, PTF-013-TC1, PTF-013-TC2 | 3 / 4 / 5 | なし | 適格。項目と更新処理が未実装のためRed | 候補 |
| PTF-CORE-007 | 編集で購入単位と余裕日数を失わない | PTF-012 | PTF-012-TC1 | 3 / 4 | なし | 適格。PUTがアイテムを置き換えるため、未実装時は値が消えてRed | 候補 |
| PTF-CORE-008 | 登録画面に7項目があり、初期値（購入単位は空、日数・余裕日数・在庫は0）のまま余裕日数を変えずに登録すると余裕日数0で送信される | PTF-001, 003 | PTF-001-TC1, PTF-003-TC1, PTF-003-TC5 | 2 / 4 | なし（PURC-002-TC1/2は5項目） | 適格。入力欄がないためRed | 候補 |
| PTF-CORE-009 | 一覧に購入単位・1単位あたりの日数・余裕日数を表示し、在庫と1単位あたりの日数を単位名付きで表示する。在庫を数えた日時は表示しない | PTF-009, 015 | PTF-009-TC1, PTF-015-TC2 | 1 / 4 / 5 | なし（PURC-012-TC1は`speed`表示） | 適格。表示がないためRed | 候補 |

選定条件:

1. 失敗すると機能目的を達成できない
2. 必要な既存・新規レイヤーを通る主要正常系である
3. 影響が大きい、または修復困難な状態を防ぐ
4. 新設・変更され、既存テストで十分に保証されない
5. 実装方式が変わっても維持すべき観測可能な振る舞いである

## TDD候補外と実装後テストへの引き継ぎ

| Test Case ID | 候補外の理由 | 暫定的な検証先 |
|---|---|---|
| PTF-001-TC4 | 未知の項目を無視するのは既存のAPIの振る舞いで、新しい契約ではない | Integration（API） |
| PTF-002-TC3 | 0の意味（計算対象外）は①-2で使われ、このスライスでは0の受け付けだけを確認すればよい（PTF-002-TC1でカバー） | Integration（API） |
| PTF-004-TC1, PTF-004-TC2 | 在庫の範囲はPURC第2版から変わらない | 既存テスト（PURC-004-TC9/10、改名して維持） |
| PTF-005-TC4 | 画面側の検証は既存の登録画面の仕組み（PURC-003）に項目を足すだけで、新しい失敗の仕方がない | Component |
| PTF-010-TC1 | 文言を固定しない契約で、自動テストの期待値を一意に決められない | Component（項目名に日数・購入単位を含むことの確認）とレビュー |
| PTF-012-TC2 | 編集画面は改名だけで、新しい振る舞いがない | Component |
| PTF-012-TC3 | 削除の振る舞いは変わらない | 既存テスト（PURC-022-TC1: `test_purchase_uniqueness_rev2.py`） |
| PTF-016-TC1 | 重複判定は変わらず、購入単位を判定に含めないことだけを確認すればよい | Integration（API、PURC-014系の既存テストに購入単位違いの1件を追加） |

候補外にしても仕様上の契約が消えるわけではない。最終的な検証先と結果は実装後テストレポートで確定する。

## Core Contract Gate

- [x] 論理テストケースの参照コミットを記録した
- [x] すべての論理テストケースをスクリーニングした（38件: 候補29件、候補外9件）
- [x] 機能目的を代表する契約が含まれている（PTF-CORE-001）
- [x] 許容できない重大リスクが含まれている（PTF-CORE-002、006、007: 計算の起点と新項目の消失）
- [x] 網羅目的の詳細を中心的契約へ含めていない
- [x] 各契約の仕様IDとTest Case IDが正しい
- [x] 候補外の理由と暫定的な検証先が妥当である
- [x] AIが仕様上の判断を暗黙に追加していない
- [x] Blockingな判断保留が残っていない
- [x] 人間が中心的契約と対応Test Case IDを承認した

### 承認記録

- 承認したContract ID: PTF-CORE-001〜009
- 修正・除外した候補: なし
- 承認者: ym28-it
- 承認日: 2026-11-22
- 備考: 候補外9件の暫定検証先も承認

Core Contract Gate通過前に、最小TDDテストセット、テストコード、実装コードを確定しない。

## Baseline

- 基準コミットSHA: `f8edefa`（Core Contract Gate承認記録。プロダクトコードは`main`の`720f35c`と同一）
- 実行環境: Claude Code（クラウドセッション、Linux）。`bash scripts/setup_host_prerequisites.sh --install`の後、`--check`がPass（mise 2026.9.12、uv 0.12.18、Temurin Java 17.0.21.1、Python 3.14.7）
- 実行コマンドと結果:

| 検証 | コマンド（実行場所） | 結果 |
|---|---|---|
| Backend lint | `../bin/mise exec -- uv run ruff check .`（`backend/`） | Pass |
| Backend format | `../bin/mise exec -- uv run ruff format --check .`（`backend/`） | Pass（51 files） |
| Backend unit | `../bin/mise exec -- uv run pytest -m "not integration"`（`backend/`） | 73 passed |
| Backend integration | `../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration`（`backend/`） | 90 passed、exit 0 |
| Frontend lint | `bun run lint`（`frontend/`） | Pass |
| Frontend format | `bun run format:check`（`frontend/`） | Pass |
| Frontend Vitest | `bun run test -- --run`（`frontend/`） | 77 passed（6 files） |
| Frontend build・型検査 | `bun run build`（`frontend/`、`vite build && tsc -b`） | Pass |
| E2E | `bash e2e/run-e2e.sh`と同じrunnerで、Chromiumの実行ファイルだけを一時設定で指定 | 2 passed |

- 既存失敗: なし
- 環境上の注記:
  - Backend integrationの初回実行は、Maven Wrapperの配布物取得が`ENVIRONMENT_FAILURE`（exit 70）になった。同じURLは直後に`curl`・`wget`・`./mvnw -v`で取得でき、再実行でPassしたため、一時的なネットワーク障害と判断した
  - このクラウドセッションには`e2e/`が指定するPlaywrightのブラウザ（chromium_headless_shell-1194）がなく、`bash e2e/run-e2e.sh`はブラウザ起動前に失敗する。コミットしない一時設定（`launchOptions.executablePath`に`/opt/pw-browsers/chromium`を指定）で同じrunnerから実行し、Passを確認した。リポジトリの環境コードは変更していない
- 未実行の検証と理由: なし
- 既存失敗を今回の変更から分離できるか: Yes（既存失敗なし）

## 既存テストによる保護

| Contract ID | 既存テスト | Baseline結果 | 十分か | 新規テスト | 根拠 |
|---|---|---|---|---|---|
| PTF-CORE-001〜009 | なし（既存の登録・一覧テストは`speed`と上限100,000を前提にする） | Pass | No | Add | 新設・改名した契約で、既存テストでは観測されない |

PURC第2版の既存テスト（凍結済みTDDテストを含む）のうち、`speed`、上限100,000、5項目の入力、`speed`の表示を前提にするものは、PURC第3版（2026-11-22承認）を根拠に書き直す。書き直しはRedタスクで行い、期待動作が第3版で変わるテストだけを対象にする。期待動作が変わらないテストは、項目名と基準入力の読み替えだけを行う。書き直したテストと理由はRed記録に残す。

## 最小TDDテストセット

| Test Case ID | Contract ID | 役割 | テストレベル | 実テスト予定場所 | 変更前の期待状態 | 選定根拠 |
|---|---|---|---|---|---|---|
| PTF-008-TC1 | PTF-CORE-001 | 変更目的 | Integration（API + DynamoDB Local） | `backend/tests/integration/api/test_purchase_ptf.py` | Red | 新項目付きの登録が201で返り、在庫を数えた日時が作成日時と一致することを1本で識別する |
| PTF-011-TC1 | PTF-CORE-001 | 代表回帰 | Integration（API + DynamoDB Local） | 同上 | Red | 永続化した新項目を一覧取得で読み戻せることを識別する（レスポンスだけ返して保存しない実装を検出する） |
| PTF-006-TC2 | PTF-CORE-002 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | クライアントが送った在庫を数えた日時を使う実装を検出する |
| PTF-002-TC2 | PTF-CORE-003 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 新しい上限365を超える366が保存されないことを識別する（旧上限100,000のままの実装を検出する） |
| PTF-001-TC3 | PTF-CORE-003 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 旧名`speed`だけで登録できてしまう実装を検出する |
| PTF-003-TC4 | PTF-CORE-004 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 余裕日数を省略できてしまう実装を検出する |
| PTF-003-TC3 | PTF-CORE-004 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 余裕日数の上限30を超える31が保存されないことを識別する |
| PTF-014-TC1 | PTF-CORE-005 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 購入単位を省略できてしまう実装を検出する |
| PTF-014-TC4 | PTF-CORE-005 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 購入単位の上限10文字を超える11文字が保存されないことを識別する |
| PTF-013-TC1 | PTF-CORE-006 | 変更目的 | Integration（API + DynamoDB Local） | 同上 | Red | 編集で在庫を変えたとき、在庫を数えた日時が更新日時と同じ時刻に更新されることを識別する |
| PTF-007-TC1 | PTF-CORE-006 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 編集のたびに在庫を数えた日時を更新してしまう実装を検出する |
| PTF-012-TC1 | PTF-CORE-007 | 重大反例 | Integration（API + DynamoDB Local） | 同上 | Red | 編集で購入単位と余裕日数が消える実装を検出する |
| PTF-001-TC1 | PTF-CORE-008 | 変更目的 | Component | `frontend/src/features/CreatePurchaseDialog.ptf.test.tsx` | Red | 登録画面に7項目があることを識別する |
| PTF-003-TC5 | PTF-CORE-008 | 変更目的 | Component | 同上 | Red | 余裕日数を変えずに登録すると0で送信されることを、送信内容で識別する |
| PTF-015-TC2 | PTF-CORE-009 | 変更目的 | Component | `frontend/src/features/Purchase.ptf.test.tsx` | Red | 一覧が在庫と1単位あたりの日数を単位名付きで表示することを識別する |

すべての承認済み中心的契約（PTF-CORE-001〜009）を、少なくとも1つの新規テストで識別する。次は中心的契約に含まれるが、最小TDDセットから外して実装後テストへ送る。

| Test Case ID | Contract ID | 実装後へ送る理由 |
|---|---|---|
| PTF-001-TC2 | PTF-CORE-001 | PTF-008-TC1とPTF-011-TC1で、レスポンスと再取得の両方を識別済み |
| PTF-006-TC1 | PTF-CORE-001 | PTF-008-TC1が作成日時との一致を確認する |
| PTF-015-TC1 | PTF-CORE-001 | PTF-008-TC1とPTF-011-TC1が購入単位を含めて確認する |
| PTF-002-TC1 | PTF-CORE-003 | 境界の受け付け側（0、365）。拒否側の366で上限の取り違えを識別できる |
| PTF-005-TC1、TC2 | PTF-CORE-003 | 型と負数の拒否は既存の`stock`と同じ仕組みで、項目を足すだけで同じ失敗の仕方になる |
| PTF-003-TC2 | PTF-CORE-004 | 境界の受け付け側（0、30） |
| PTF-005-TC3 | PTF-CORE-004 | PTF-005-TC1、TC2と同じ理由 |
| PTF-014-TC2、TC3、TC5 | PTF-CORE-005 | 空白だけの拒否、10文字の受け付け、前後空白の保持は、名前・カテゴリと同じ仕組み（PURC-004-TC1〜6） |
| PTF-013-TC2 | PTF-CORE-006 | PTF-007-TC1が「在庫を変えない編集では更新しない」を識別する |
| PTF-003-TC1 | PTF-CORE-008 | 初期値の表示。PTF-003-TC5が余裕日数の初期値0を送信内容で識別する |
| PTF-009-TC1 | PTF-CORE-009 | 表示項目の網羅。PTF-015-TC2が新項目の表示を識別する |

## Test Plan Gate

- [x] Baselineを確認し、既存失敗を分離した
- [x] すべての承認済み中心的契約に保護方針がある
- [x] 各テストが対応するContract IDとTest Case IDを持つ
- [x] 最小テストセットが変更目的と重大リスクを識別できる
- [x] 既存テストで省略する場合の根拠がある
- [x] Red例外の理由が妥当である
- [x] 実装詳細を不必要に固定していない
- [x] 人間がAIによるテストコード作成を承認した

### 承認記録

- 承認者: ym28-it
- 承認日: 2026-11-22
- 備考: 最小TDDテストセット15件と、PURC第2版の既存テスト（凍結済みTDDテストを含む）を第3版を根拠にRedタスクで書き直す方針を承認

## TDD実行記録

### Red

| Test Case ID | 実行コマンド | 実際の失敗 | Valid Red | 判定根拠 |
|---|---|---|---|---|
| PTF-008-TC1 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | create後のPOSTが422（`speed`欠落）。`assert 422 == 201` | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-011-TC1 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 登録のセットアップ`assert 422 == 201`で失敗（新フィールド未実装） | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-006-TC2 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | `assert 422 == 201`（`days_per_unit`を受け付けない） | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-002-TC2 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 422の`loc`が`["body","speed"]`のみで`["body","days_per_unit"]`を含まない | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-001-TC3 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | `speed: 3`だけで`assert 201 == 422`（登録されてしまう） | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-003-TC4 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 422の`loc`が`["body","speed"]`のみで`["body","buffer_days"]`を含まない | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-003-TC3 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 同上（`buffer_days`の検証が未実装） | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-014-TC1 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 422の`loc`が`["body","speed"]`のみで`["body","unit"]`を含まない | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-014-TC4 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 同上（`unit`の検証が未実装） | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-013-TC1 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 登録のセットアップ`assert 422 == 201`で失敗 | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-007-TC1 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 登録のセットアップ`assert 422 == 201`で失敗 | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |
| PTF-012-TC1 | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration tests/integration/api/test_purchase_ptf.py -q` | 登録のセットアップ`assert 422 == 201`で失敗 | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`・`stock_counted_at`）が未実装であることによる失敗。収集・import・環境・fixtureエラーなし |

- 実装計画のRedタスク: Task 1 Backend Red（PTF-CORE-001〜007）
- 環境スモーク・Baselineの結果: 変更前に unit 73 passed、integration 90 passed（Baselineと一致）
- Red結果: `test_purchase_ptf.py` 12 failed（exit code 1）。変更後の全体は unit 72 passed / 1 failed（`test_purchase_create_errors.py`、422が返り500にならない）、integration 39 passed / 65 failed（104件。PTF 12件と第3版へ読み替えた既存53件が未実装を理由に失敗）
- PURC第3版への読み替え（Test Plan Gateで承認済み、凍結済みPURC TDDテストを含む。変更点は基準入力の置換と`speed`→`days_per_unit`の改名のみで、下記以外の期待値は変えていない）:
  - `test_purchase_create.py`: 基準入力を7項目へ。PURC-TDD-001の`speed=0`を`days_per_unit=0`へ、レスポンスの項目確認に新項目を追加（5項目の確認 → PTFの項目）
  - `test_purchase_create_post.py`: 基準入力と`speed`→`days_per_unit`の改名。PURC-004-TC7（0・365）、TC8（負数・小数・366）の範囲を365上限へ。PURC-014-TC2の非キー項目に`unit`・`buffer_days`を追加（PTF-016）。`PurchaseItem(...)`の直接生成を新4項目つきへ。保存値の比較に`unit`・`buffer_days`を追加
  - `test_purchase_rev2_post.py`: 基準入力と`speed`→`days_per_unit`の改名のみ
  - `test_purchase_uniqueness_rev2.py`: 基準入力と`speed`→`days_per_unit`の改名のみ
  - `test_purchase_rename_self_race.py`: 変更なし（`test_purchase_uniqueness_rev2.py`の基準入力を共有して読み替わる）
  - `tests/unit/api/test_purchase_create_errors.py`: 登録リクエストの基準入力のみ
- 凍結したテストファイル: `backend/tests/integration/api/test_purchase_ptf.py`
- Red記録コミットSHA: 本コミット（`git log`で確認）

### Red（frontend）

| Test Case ID | 実行コマンド | 実際の失敗 | Valid Red | 判定根拠 |
|---|---|---|---|---|
| PTF-001-TC1（PTF-TDD-013） | `cd frontend && bun run test -- --run src/features/CreatePurchaseDialog.ptf.test.tsx src/features/Purchase.ptf.test.tsx` | `Unable to find a label with the text of: /^購入単位/` | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`の入力欄、単位名付きの表示）が未実装であることによる失敗。収集・import・環境エラーなし |
| PTF-003-TC5（PTF-TDD-014） | `cd frontend && bun run test -- --run src/features/CreatePurchaseDialog.ptf.test.tsx src/features/Purchase.ptf.test.tsx` | 同上（購入単位の入力欄がなく、登録操作の前で失敗） | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`の入力欄、単位名付きの表示）が未実装であることによる失敗。収集・import・環境エラーなし |
| PTF-015-TC2（PTF-TDD-015） | `cd frontend && bun run test -- --run src/features/CreatePurchaseDialog.ptf.test.tsx src/features/Purchase.ptf.test.tsx` | 一覧の購入物に`2パック`が含まれない（`toHaveTextContent`） | Yes | 新項目（`unit`・`days_per_unit`・`buffer_days`の入力欄、単位名付きの表示）が未実装であることによる失敗。収集・import・環境エラーなし |

- 実装計画のRedタスク: Task 3 Frontend Red（PTF-CORE-008、009）
- 環境スモーク・Baselineの結果: 変更前のfrontend Vitestは8ファイル・77件すべてPass
- Red結果: PTF新規テスト3件がfailed（exit code 1）。変更後の全体は80件中79 failed / 1 passed（PTF 3件と、第3版へ読み替えた既存テスト76件が未実装を理由に失敗。残る1件は変更後も成立する既存テスト）
- 型検査（`bun run build`）はschema.d.tsの更新で製品コードが失敗する想定のためTask 4で対応し、本タスクでは実行しない
- PURC第3版への読み替え（人間承認済み、凍結済みPURC TDDテストを含む。変更点は基準入力の置換、`speed`→`days_per_unit`の改名、ラベル（購入単位`/^購入単位/`、日数`/使い切る日数/`、余裕日数`/余裕日数/`、在庫`/^在庫/`）の読み替え、モックのレスポンスと送信本文への新項目の追加のみ。下記以外の期待値は変えていない）:
  - `CreatePurchaseDialog.test.tsx`（PURC-TDD-003）: 消費スピードのラベルを`/使い切る日数/`へ
  - `Purchase.test.tsx`（PURC-TDD-002）: 入力・送信本文・レスポンスをPTFの項目へ。表示確認は`消費スピード 0`・`在庫 2`を、PTF-015の表示`2パック`へ置換（日数0の表示は論理テストケースで定義されないため断定しない）
  - `CreatePurchaseDialog.rev2.test.tsx`（PURC-TDD-012〜014）: 基準入力に購入単位を追加し、`speed`→`days`の改名。初期値・入力保持・無関係な項目にエラーがないことの確認に新項目を追加
  - `CreatePurchaseDialog.post.test.tsx`: 基準入力と`speed`→`days`の改名。PURC-004-TC7（0・365）、TC8（負数・小数・366）の範囲を365上限へ。送信本文に`unit`・`buffer_days`を追加。初期値の確認を7項目へ（PTF-001-TC1、PTF-003-TC1）
  - `CreatePurchaseDialog.rev2.post.test.tsx`: 基準入力と`speed`→`days`の改名。API 422の`loc`を`days_per_unit`へ。項目別エラー確認の対象に新項目を追加
  - `Purchase.post.test.tsx`: モックのレスポンスと入力・送信本文に新項目を追加し（余裕日数は保持確認のため2を入力）、`speed`→`days`の改名。関数名・テスト名の「5項目」表現を改称
- 凍結したテストファイル: `frontend/src/features/CreatePurchaseDialog.ptf.test.tsx`、`frontend/src/features/Purchase.ptf.test.tsx`
- 修正ラウンド（レビュー指摘）: `Purchase.test.tsx`（PURC-TDD-002）に日数表示`1パック0日`の確認をPTF-015-TC2の形式の機械的適用として復元。`CreatePurchaseDialog.post.test.tsx`のcreatePurchaseモックへ必須の`stock_counted_at`を追加（`bunx tsc -b`で`*.test.tsx`の型エラー0件を確認）。対象テストは引き続き未実装を理由に失敗（36 failed）
- Red記録コミットSHA: 本コミット（`git log`で確認。修正ラウンド後の再コミットを含む）

### Green

| Test Case ID | 実行コマンド | 結果 |
|---|---|---|
| PTF-008-TC1, PTF-011-TC1, PTF-006-TC2, PTF-002-TC2, PTF-001-TC3, PTF-003-TC4, PTF-003-TC3, PTF-014-TC1, PTF-014-TC4, PTF-013-TC1, PTF-007-TC1, PTF-012-TC1（PTF-CORE-001〜007。`test_purchase_ptf.py`の12件、backend integration全104件の一部） | `cd backend && ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- uv run pytest -m integration -q` | exit 0、104 passed |

- 実装計画のGreenタスク: Task 2（Backend Green）
- 凍結済みテストの差分確認: `git diff 0690622 -- backend/tests/integration/api/test_purchase_ptf.py`は差分なし（コミット前後で確認）
- Green記録コミットSHA: `e849821`（Green）、修正ラウンド: 本記録を含むコミット（`git log`で確認。編集の書き込み条件へ`updated_at`を追加し、読み取り後の他の書き込みと競合したら再読込して`edit`を適用し直す）

### Refactor・回帰

- 実行コマンド: `ruff check .`、`ruff format --check .`、`pytest -m "not integration" -q`（いずれも`backend/`から`../bin/mise exec -- uv run`経由）
- 結果: ruff Pass、unit 73 passed、integration 104 passed。`frontend/src/api/schema.d.ts`をOpenAPIから再生成済み
- 未実行の検証と理由: frontendの型検査・テストはTask 4で対応するため未実行（schema.d.tsの項目変更で失敗する想定）

## TDD Green Gate

- [x] Valid Redを確認した、または正当なRed例外を記録した
- [x] テストを緩和せずGreenになった
- [x] 凍結済みTDDテストがRed記録時から変更されていない
- [x] 承認済みの最小TDDテストがリファクタ後もGreenである
- [x] Contract ID、仕様ID、Test Case IDの対応を維持した
- [ ] TDD候補外のTest Case IDを実装後テストへ引き継いだ
- [ ] 論理テストケースの参照版が変わっていない、または再承認した
