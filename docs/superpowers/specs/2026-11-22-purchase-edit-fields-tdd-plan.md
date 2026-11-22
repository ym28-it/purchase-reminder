# 購入物編集の項目と検証（PEDT） TDD計画

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `docs/superpowers/specs/2026-11-22-purchase-edit-fields-design.md`（PEDT-001〜010） |
| 論理テストケースSSOT | `docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md` |
| 論理テストケースの参照コミット | `90f68f9` |
| 変更単位 | 購入物の編集で、登録と同じ全7項目を、登録と同じ検証で変更して永続化する |
| 文書状態 | Test Plan Approved |

論理テストケースの期待結果をこの文書で再定義しない。期待結果はTest Case IDを通じてSSOTを参照する。

## 機能目的

入力したのに直せない項目（購入単位、余裕日数）をなくし、登録では拒否される値を編集経由で保存できる状態をなくす。

## 対象範囲

- 対象: 編集ダイアログ、編集API（PUT）の項目と検証、`stock_counted_at`の更新条件、重複・404・同時実行の既存の振る舞いの維持
- 対象外: 部分更新（PATCH）、既存データの移行、購入タイミングの計算、在庫の入れ直し、編集ダイアログの失敗表示（422・409）の仕様化

## 既存テストへの影響（メモ）

既存のPUTを使うテストの多くは、`unit`と`buffer_days`を送らない、または小数の在庫・`days_per_unit`を送る前提である（`backend/tests/integration/api/`の`test_purchase_ptf.py`、`test_purchase_ptf_post.py`、`test_purchase_rev2_post.py`、`test_purchase_uniqueness_rev2.py`、`test_purchase_rename_self_race.py`、`backend/tests/unit/domain/test_purchase_edit.py`、`frontend/src/features/Purchase.ptf.post.test.tsx`など）。PEDTの承認を根拠に書き直す対象であり、期待動作が変わらないものは編集の入力へ`unit`と`buffer_days`を加える改名だけを行う（設計書 §5）。書き直しは承認済み（2026-11-22 ym28-it）。書き直しの単位と順序は実装計画で定める。

## 仕様不足・判断保留

| ID | 不足情報 | 影響する契約・Test Case ID | 分類 | 必要な確認 | 状態 |
|---|---|---|---|---|---|
| なし | - | - | - | - | - |

## 中心的契約候補

| Contract ID | 契約 | 仕様ID | 対応Test Case ID | 該当する選定条件 | 既存保護 | TDD適格性・Red例外 | AIの判定 |
|---|---|---|---|---|---|---|---|
| PEDT-CORE-001 | 編集で購入単位と余裕日数を含む全7項目を変更でき、レスポンスと再取得した購入物に反映される。作成日時は変わらず、更新日時は更新される | PEDT-001, 005 | PEDT-001-TC1, PEDT-005-TC1, PEDT-005-TC2 | 1 / 2 / 4 / 5 | なし（既存の編集テストは`unit`・`buffer_days`を引き継ぐ前提） | 適格。現在は`unit`・`buffer_days`が変更されないためRed | 候補 |
| PEDT-CORE-002 | 編集で必須項目（購入単位、余裕日数、一時的な購入を含む全7項目）が欠けると422で拒否し、保存済みの購入物を変えない。複数の違反は項目ごとに識別できる | PEDT-001, 004 | PEDT-001-TC2, PEDT-004-TC1 | 3 / 4 | なし | 適格。現在は欠落を受け付ける（一時的な購入は`false`になる）ためRed | 候補 |
| PEDT-CORE-003 | 編集の数値項目は登録と同じ範囲・型だけを受け付ける（1単位あたりの日数0〜365の整数、余裕日数0〜30の整数、在庫0〜100,000の整数、一時的な購入は真偽値）。範囲外・小数・文字列を丸めずに拒否し、1単位あたりの日数0は受け付ける | PEDT-002, 003 | PEDT-002-TC1, PEDT-002-TC2, PEDT-003-TC1 | 3 / 4 | なし（PUTの検証は登録と別定義） | 適格。現在は小数・上限超過を受け付け、0を拒否するためRed | 候補 |
| PEDT-CORE-004 | 編集の文字列項目は登録と同じ制約（名前50文字、カテゴリ30文字、購入単位10文字（コードポイント単位）、空白だけを拒否、前後空白を保持）に従う | PEDT-002 | PEDT-002-TC2（文字列項目の部分）, PEDT-002-TC3 | 3 / 4 | なし | 適格。現在は上限なし・空白だけを受け付けるためRed | 候補 |
| PEDT-CORE-005 | 編集で在庫を変えたときだけ`stock_counted_at`を更新し、購入単位や余裕日数だけの変更では更新しない | PEDT-006 | PEDT-006-TC1, PEDT-006-TC2, PEDT-006-TC3 | 3 / 4 | PTF-013-TC1の既存テスト（`test_ptf_tdd_010_ptf_013_tc1_stock_edit_recounts_at_updated_at`。`unit`・`buffer_days`を送らないため書き直し対象） | 適格。TC1は書き直し後に既存保護、TC2・TC3は購入単位・余裕日数が変更されないためRed | 候補 |
| PEDT-CORE-006 | 編集後も、別の購入物と同じ名前・カテゴリへの変更は購入単位が違っても409で拒否され、購入単位だけの変更は自分自身との重複にならず保存される | PEDT-009 | PEDT-009-TC1, PEDT-009-TC2 | 3 / 4 | PURC-023・PTF-016の既存テスト（`test_purchase_uniqueness_rev2.py`、`test_purchase_rev2_post.py`。PUTの入力が旧形式のため書き直し対象） | TC1は代表回帰（書き直し後に既存保護、Red例外）。TC2は購入単位が変更されないためRed | 候補 |
| PEDT-CORE-007 | 編集ダイアログに全7項目があり、保存済みの値が初期値で、保存すると全7項目が送信されて一覧に反映される。購入単位・余裕日数を変えない編集では保存済みの値のまま残る | PEDT-007, 010 | PEDT-007-TC1, PEDT-007-TC2, PEDT-007-TC4, PEDT-010-TC1 | 1 / 2 / 4 / 5 | `Purchase.ptf.post.test.tsx`のPTF-012-TC1（UI側、購入単位・余裕日数を送らないことを検証。期待が反転するため書き直し対象） | 適格。入力欄がなく送信項目が足りないためRed | 候補 |
| PEDT-CORE-008 | 編集ダイアログの入力検証は登録ダイアログと同じ結果になる。範囲外・小数・空は送信せず項目ごとにエラーを表示し、境界値（0、30、100,000、10文字）は送信する | PEDT-008 | PEDT-008-TC1, PEDT-008-TC2 | 3 / 4 | なし（編集ダイアログは名前・カテゴリ・日数・在庫・一時的な購入だけ、上限なし） | 適格。現在は上限・小数・購入単位の検証がなく、0を拒否するためRed | 候補 |

選定条件:

1. 失敗すると機能目的を達成できない
2. 必要な既存・新規レイヤーを通る主要正常系である
3. 影響が大きい、または修復困難な状態を防ぐ
4. 新設・変更され、既存テストで十分に保証されない
5. 実装方式が変わっても維持すべき観測可能な振る舞いである

## TDD候補外と実装後テストへの引き継ぎ

| Test Case ID | 候補外の理由 | 暫定的な検証先 |
|---|---|---|
| PEDT-001-TC3 | 受け取らない項目（`id`、`created_at`、`stock_counted_at`など）や`speed`を無視するのは、Pydanticの既存の振る舞いと編集の適用処理の引数が決まっていることで成立し、最初からGreenになる見込みの回帰である（中心的契約PEDT-CORE-009として提案したが、2026-11-22に人間が候補外とした。IDは欠番） | Integration（API） |
| PEDT-006-TC4 | 在庫を変えない複数項目の同時変更は、PEDT-006-TC2・TC3と同じ契約の組み合わせで、新しい失敗の仕方がない | Unit（編集の適用）またはIntegration（API） |
| PEDT-007-TC3 | 文言を固定しない契約で、自動テストの期待値を一意に決められない（PTF-010-TC1と同じ） | Component（項目名に日数・購入単位を含むことの確認）とレビュー |
| PEDT-008-TC3 | 入力エラーの解除は、フォームライブラリの標準の振る舞いで、アプリ固有の契約ではない | Component |
| PEDT-009-TC3 | 存在しないIDの404は変更前から変わらない既存の振る舞いで、既存のテストが見当たらないため、実装後に追加する | Integration（API） |
| PEDT-009-TC4 | 名前の変更後に変更前の組で再登録できる契約は変わらない（PURC-023-TC1） | 既存テスト（`test_purchase_uniqueness_rev2.py`、書き直し後） |
| PEDT-009-TC5 | 同時実行の整合性は変わらず、PURC-024の既存テストが保護している | 既存テスト（`test_purchase_uniqueness_rev2.py`、`test_purchase_rev2_post.py`、`test_purchase_rename_self_race.py`、書き直し後） |
| PEDT-010-TC2 | 削除の振る舞いは変わらない（PTF-012-TC3、PURC-022-TC1） | 既存テスト（`test_purchase_uniqueness_rev2.py`） |

候補外にしても仕様上の契約が消えるわけではない。最終的な検証先と結果は実装後テストレポートで確定する。

## スクリーニング結果

論理テストケース28件のうち、中心的契約に対応するのは20件（8契約）、候補外は8件である。全28件に、候補または候補外のどちらかを割り当てた。

## Core Contract Gate

- [x] 論理テストケースの参照コミットを記録した
- [x] すべての論理テストケースをスクリーニングした（28件: 候補20件、候補外8件）
- [x] 機能目的を代表する契約が含まれている（PEDT-CORE-001、007）
- [x] 許容できない重大リスクが含まれている（PEDT-CORE-002、003、005、006: 不正値の保存、在庫を数えた日時の誤更新、重複）
- [x] 網羅目的の詳細を中心的契約へ含めていない
- [x] 各契約の仕様IDとTest Case IDが正しい
- [x] 候補外の理由と暫定的な検証先が妥当である
- [x] AIが仕様上の判断を暗黙に追加していない
- [x] Blockingな判断保留が残っていない
- [x] 人間が中心的契約と対応Test Case IDを承認した

### 承認記録

- 承認したContract ID: PEDT-CORE-001〜008
- 修正・除外した候補: PEDT-CORE-009を除外し、PEDT-001-TC3を候補外（Integration）へ移した。IDは欠番とする
- 承認者: ym28-it
- 承認日: 2026-11-22
- 備考: 既存のPUT関連テスト（凍結済みを含む）は、PEDTの承認を根拠に書き直すことを承認した（2026-11-22 ym28-it）

Core Contract Gate通過前に、最小TDDテストセット、テストコード、実装コードを確定しない。

## Baseline

Core Contract Gate通過後、最初のテストコードまたは実装コード変更前に確認する。

- 基準コミットSHA: `ea4e4f0`（ブランチ`feat/purchase-edit-fields`）
- 実行コマンド（`backend/`と`frontend/`から）:
  - `../bin/mise exec -- uv run ruff check .` / `ruff format --check .`
  - `../bin/mise exec -- uv run pytest -m "not integration" -q`
  - `DYNAMODB_LOCAL_PORT=18001 ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q`
  - `bun install --frozen-lockfile`、`bun run test -- --run`、`bun run lint`、`bun run format:check`、`bun run build`（`tsc -b`を含む）
- 結果: ruff check Pass、ruff format 55ファイル整形済み、Backend unit 79 passed、Backend integration 145 passed、Frontend Vitest 97 passed（9ファイル）、Biome lint Pass、format:check Pass、build Pass
- 既存失敗: なし
- 未実行の検証と理由: E2E（`e2e/run-e2e.sh`）は、起動中のdocker-composeスタックとフロントエンドdevサーバーを要し、TDD前のBaselineの対象外としたため実行していない。pre-commitフックは実行していない
- 既存失敗を今回の変更から分離できるか: Yes（既存失敗なし）
- 分離できない場合の判断: 該当なし
- 環境の備考: 実行開始時、このマシンにuvとJavaのmise管理の導入がなく`ENVIRONMENT_FAILURE`（実装の失敗ではない）となったため、承認済みの`bash scripts/setup_host_prerequisites.sh --install`で導入した（`--check`はPass、環境コードの変更なし）。docker-composeのDynamoDB Localがポート8001を使用中だったため、統合テストは`DYNAMODB_LOCAL_PORT=18001`で実行した（起動中の開発サーバーは停止していない）

## 既存テストによる保護

| Contract ID | 既存テスト | Baseline結果 | 十分か | 新規テスト | 根拠 |
|---|---|---|---|---|---|
| PEDT-CORE-005 | `test_purchase_ptf.py::test_ptf_tdd_010_ptf_013_tc1_stock_edit_recounts_at_updated_at`（PEDT-006-TC1の期待と同じ） | Pass | Yes（編集の入力を7項目へ書き直した後） | TC1は書き直しで保護、TC2・TC3はAdd | 在庫変更時の更新は変わらない。購入単位・余裕日数だけの変更は新しい契約 |
| PEDT-CORE-006 | `test_purchase_uniqueness_rev2.py::test_purc_tdd_010_purc_023_tc2_rename_to_other_purchase_pair_is_409_and_not_persisted`、`test_purchase_rev2_post.py::test_purc_023_tc2_rename_into_existing_pair_is_409_even_when_precheck_misses_it` | Pass | 一部（購入単位が違う編集の409と、購入単位だけの編集は未保護） | PEDT-009-TC1・TC2をAdd | 重複判定の基本は既存テストで保護されるが、購入単位の絡む新しい経路は未保護 |
| PEDT-CORE-007 | `Purchase.ptf.post.test.tsx`のPTF-012-TC1（UI側）、PTF-012-TC2 | Pass | No（TC1は期待が反転する） | Add（書き直しを含む） | PTF-012-TC1は「購入単位・余裕日数を送らない」ことを検証しており、PEDTで期待が反転する |
| PEDT-CORE-001〜004、008 | なし | - | No | Add | 編集の項目・検証は新設または変更 |

## 最小TDDテストセット

承認済み（2026-11-22 ym28-it）。論理テストケースの前提・操作・期待結果はSSOTを参照し、複製しない。

| Test Case ID | Contract ID | 役割 | テストレベル | 実テスト予定場所 | 変更前の期待状態 | 選定根拠 |
|---|---|---|---|---|---|---|
| PEDT-001-TC1、PEDT-005-TC1、PEDT-005-TC2 | PEDT-CORE-001 | 変更目的 | Integration（API） | `backend/tests/integration/api/test_purchase_edit_fields.py`（新規） | Red（`unit`・`buffer_days`が変更されない） | 編集で全7項目を変更し、レスポンスと再取得で確認する。`unit`・`buffer_days`の変更と、作成日時・更新日時、レスポンスの形を1件で識別できる |
| PEDT-001-TC2（`unit`、`buffer_days`、`is_temporary`の欠落） | PEDT-CORE-002 | 重大反例 | Integration（API、項目ごとのparametrize） | 同上 | Red（欠落を受け付ける。`is_temporary`は`false`になる） | 新しく必須になる3項目の欠落を識別する。名前・カテゴリ・日数・在庫の欠落は現在も422でGreenのため、実装後テストへ送る |
| PEDT-004-TC1 | PEDT-CORE-002 | 重大反例 | Integration（API） | 同上 | Red（1単位あたりの日数366と余裕日数31を受け付ける） | 複数違反を項目ごとに識別でき、保存済みの購入物が変わらないことを確認する |
| PEDT-002-TC2（数値項目: 日数366・小数、在庫100,001・小数、一時的な購入が文字列） | PEDT-CORE-003 | 重大反例 | Integration（API、値ごとのparametrize） | 同上 | Red（現在は受け付ける） | 登録で拒否される値が編集経由で保存される問題を直接表す。丸めずに拒否し、保存済みの購入物が変わらないことを確認する |
| PEDT-002-TC1（数値項目の境界）、PEDT-003-TC1 | PEDT-CORE-003 | 変更目的 | Integration（API） | 同上 | Red（日数0を拒否する） | 日数0・365、余裕日数0・30、在庫0・100,000を受け付けることを1件で確認する。0の許可が現在との差を識別する |
| PEDT-002-TC2（文字列項目: 名前51・カテゴリ31・購入単位11文字、空白だけ） | PEDT-CORE-004 | 重大反例 | Integration（API、値ごとのparametrize） | 同上 | Red（上限なし、空白だけを受け付ける） | 登録と同じ文字列の制約が編集に効くことを確認する |
| PEDT-002-TC1（文字列項目の境界）、PEDT-002-TC3 | PEDT-CORE-004 | 変更目的 | Integration（API） | 同上 | Red（`unit`が保存されない） | 名前50・カテゴリ30・購入単位10文字（`𠮷`を含む）と、前後空白の保持を確認する |
| PEDT-006-TC1 | PEDT-CORE-005 | 代表回帰 | Integration（API） | `test_purchase_ptf.py`の既存テストを7項目の入力へ書き直す | Green（Red例外: 既存保護の書き直し） | 在庫変更時の更新は変わらないことを維持する |
| PEDT-006-TC2、PEDT-006-TC3 | PEDT-CORE-005 | 重大反例 | Integration（API、購入単位・余裕日数のparametrize） | `test_purchase_edit_fields.py` | Red（変更が保存されない） | 購入単位・余裕日数だけの変更で`stock_counted_at`が動かないことを確認する |
| PEDT-009-TC1 | PEDT-CORE-006 | 代表回帰 | Integration（API） | `test_purchase_edit_fields.py` | Green（Red例外: Characterization。重複判定は変わらない） | 購入単位が違っても409で拒否され、変更が永続化されないことを確認する |
| PEDT-009-TC2 | PEDT-CORE-006 | 重大反例 | Integration（API） | `test_purchase_edit_fields.py` | Red（購入単位が変更されない） | 購入単位だけの変更が自分自身との重複にならないことを確認する |
| PEDT-007-TC1、PEDT-007-TC2 | PEDT-CORE-007 | 変更目的 | Component | `frontend/src/features/Purchase.edit.test.tsx`（新規） | Red（購入単位・余裕日数の入力欄がない） | 全7項目の入力と、保存済みの値が初期値で、別の購入物へ切り替えると入れ替わることを確認する |
| PEDT-007-TC4 | PEDT-CORE-007 | 変更目的 | Component | 同上 | Red（購入単位・余裕日数が送信されない） | 変更して保存すると全7項目が送信され、一覧へ反映される。UIから永続化経路までの主要正常系 |
| PEDT-010-TC1 | PEDT-CORE-007 | 代表回帰 | Component | `Purchase.ptf.post.test.tsx`のPTF-012-TC1（UI側）を書き直す | Red（購入単位・余裕日数が送信されない） | 変更していない購入単位・余裕日数が保存済みの値のまま送られ、失われないことを確認する |
| PEDT-008-TC1 | PEDT-CORE-008 | 重大反例 | Component（値ごとのparametrize） | `Purchase.edit.test.tsx` | Red（現在は小数・上限超過・空の購入単位の検証がなく、要求が送信される） | 範囲外・小数・空は送信せず、項目ごとにエラーを表示する |
| PEDT-008-TC2 | PEDT-CORE-008 | 変更目的 | Component | `Purchase.edit.test.tsx` | Red（日数0を拒否する） | 境界値（0、30、100,000、10文字）が送信されることを確認する |

各承認済み中心的契約（PEDT-CORE-001〜008）を、少なくとも1つのテストで識別できる。新規テスト行は15行（parametrizeを除く）。

### 既存テストの書き直し（承認済み）

PUTの入力が7項目の完全置き換えに変わるため、次の既存テストを書き直す。期待動作が変わらないものは、編集の入力へ`unit`と`buffer_days`を加えるだけとし、書き直し後は変更前も変更後もGreenを保つ。

- `backend/tests/integration/api/`: `test_purchase_ptf.py`、`test_purchase_ptf_post.py`、`test_purchase_rev2_post.py`、`test_purchase_uniqueness_rev2.py`、`test_purchase_rename_self_race.py`のPUTを送る箇所
- `test_purchase_ptf.py`のPTF-012-TC1（購入単位・余裕日数を引き継ぐ）は、期待が反転するため、PEDT-001-TC1・PEDT-005-TC1へ置き換えて削除する
- `test_purchase_ptf_post.py`のうち、在庫`2.0`や`days_per_unit`の小数を送るもの（`test_review_focus_5_*`、`test_review_focus_3_unrelated_concurrent_write_does_not_recount_stock`）は、整数のみの検証に合わせて整数へ直す
- `frontend/src/features/Purchase.ptf.post.test.tsx`のPTF-012-TC1（UI側）は、PEDT-010-TC1へ書き直す
- `backend/tests/unit/domain/test_purchase_edit.py`は、編集の適用関数を直接呼ぶ実装結合のテストで、関数の引数が`unit`・`buffer_days`を含むように変わる。実装方法の詳細のため、TDDの対象には含めず、Greenタスクで実装と同時に追従する（確認事項はTest Plan Gateで人間に確認する）

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
- 備考: 最小TDDテストセット（新規15行）を承認した。`test_purchase_edit.py`（編集の適用関数を直接呼ぶ実装結合のテスト）はTDD対象外とし、Greenタスクで実装と同時に追従する。AIによるテストコード作成を承認した

## TDD実行記録

### Red

| Test Case ID | 実行コマンド | 実際の失敗 | Valid Red | 判定根拠 |
|---|---|---|---|---|
| PEDT-001-TC1、005-TC1、005-TC2 | 上記（`test_pedt_tdd_001_*`） | `unit`・`buffer_days`が保存されず、7項目の一致assertionでFAIL | Valid Red | 収集・環境設定後のassertion失敗。未実装の契約が原因 |
| PEDT-001-TC2 | 同上（`test_pedt_tdd_002_*` 3件） | `assert 200 == 422`（`unit`・`buffer_days`・`is_temporary`の欠落を受け付ける） | Valid Red | 同上 |
| PEDT-004-TC1 | 同上（`test_pedt_tdd_003_*`） | `assert 200 == 422`（366と31を受け付ける） | Valid Red | 同上 |
| PEDT-002-TC2（数値項目） | 同上（`test_pedt_tdd_004_*` 13件） | `assert 200 == 422`（範囲外・小数・文字列・非真偽値を受け付ける） | Valid Red | 同上 |
| PEDT-002-TC1（数値項目）、003-TC1 | 同上（`test_pedt_tdd_005_*` 7件中4件） | `assert 422 == 200`（日数0、2件）、`assert 1 == 0`・`assert 1 == 30`（`buffer_days`が保存されない）。日数365・在庫0・在庫100000の3件は現在もPASS（実装後の回帰保護） | Valid Red（失敗4件） | 失敗は日数0の拒否と`buffer_days`の未保存による |
| PEDT-002-TC2（文字列項目） | 同上（`test_pedt_tdd_006_*` 7件） | `assert 200 == 422`（51/31/11文字、空白だけ、空の`unit`を受け付ける） | Valid Red | 同上 |
| PEDT-002-TC1（文字列項目）、002-TC3 | 同上（`test_pedt_tdd_007_*`） | `unit`が保存されずassertion失敗 | Valid Red | 同上 |
| PEDT-006-TC2、006-TC3 | 同上（`test_pedt_tdd_008_*` 2件） | `assert 'パック' == '本'`、`assert 1 == 5`相当（変更が反映されない） | Valid Red | 同上 |
| PEDT-009-TC1 | 同上（`test_pedt_tdd_009_*`） | PASS | Red例外（Characterization） | 重複判定は変更前から409で拒否 |
| PEDT-009-TC2 | 同上（`test_pedt_tdd_010_*`） | `unit`が「本」にならずFAIL | Valid Red | 同上 |
| PEDT-006-TC1（書き直し既存） | 同上（`test_ptf_tdd_010_*`） | PASS | Red例外（既存保護の書き直し） | 7項目入力へ書き直し、変更前から成立 |

- 実装計画のRedタスク: Task 1（Backend Red）
- 環境スモーク・Baselineの結果: 変更前 unit 79 passed、integration 145 passed。Red後 unit 79 passed（変更なし）、integration 33 failed / 147 passed（新規`test_purchase_edit_fields.py`のみがFAIL、既存テストの新規FAILなし、収集・import失敗なし）。失敗した33件の内訳は上表。統合テスト総数は180（旧145から、削除`test_ptf_tdd_012_*`、`[2.0]`行の整数化による除去、新規約37件の追加）。実行コマンド: `DYNAMODB_LOCAL_PORT=18001 ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q`（`backend/`、終了コード1）
- 書き直した既存テスト: `test_purchase_ptf.py`（010・011を7項目へ、`test_ptf_tdd_012_*`を削除）、`test_purchase_ptf_post.py`（`put_body`に`unit`・`buffer_days`、在庫`2.0`を整数`2`へ）。`test_purchase_rev2_post.py`、`test_purchase_uniqueness_rev2.py`、`test_purchase_rename_self_race.py`の`payload()`は既に7項目のため変更なし
- 凍結したテストファイル: `backend/tests/integration/api/test_purchase_edit_fields.py`
- Red記録コミットSHA: `7261023`

#### Frontend Red（Task 3）

| Test Case ID | 実行コマンド | 実際の失敗 | Valid Red | 判定根拠 |
|---|---|---|---|---|
| PEDT-007-TC1、TC2 | `bun run test -- --run`（`frontend/`） | `Unable to find a label with the text of: /^購入単位/`（購入単位・余裕日数の入力欄がない） | Valid Red | モック・import・収集は正常で、編集ダイアログが全7項目を持たない契約未実装による |
| PEDT-007-TC4 | 同上 | `Unable to find a label with the text of: /^購入単位/` | Valid Red | 同上 |
| PEDT-008-TC1（購入単位 空・空白だけ） | 同上 | `Unable to find a label with the text of: /^購入単位/` | Valid Red | 購入単位の入力欄と検証がない |
| PEDT-008-TC1（日数1.5・366、在庫1.5・100001） | 同上 | `expected null not to be null`（エラーの`p`が表示されない。要求は検証されずに送信される） | Valid Red | 小数・上限の検証がない |
| PEDT-008-TC1（余裕日数1.5・31） | 同上 | `Unable to find a label with the text of: /余裕日数/` | Valid Red | 余裕日数の入力欄がない |
| PEDT-008-TC2 | 同上 | `Unable to find a label with the text of: /^購入単位/`（編集ダイアログに購入単位・余裕日数の欄がない。日数0も現行スキーマは拒否する） | Valid Red | 同上 |
| PEDT-010-TC1（書き直し既存） | 同上 | `expected { name, category, …(3) } to deeply equal { name, category, …(5) }`（`unit`・`buffer_days`が送信されない） | Valid Red | 送信項目が足りない |

- 実装計画のRedタスク: Task 3（Frontend Red）
- 環境スモーク・Baselineの結果: 変更前 97 passed。Red後 12 failed / 96 passed（108件）。失敗12件は新規11件（TC1/TC2が1、TC4が1、TC1のtest.each 8、TC2が1）と書き直したPEDT-010-TC1の1件で、それ以外の既存96件の新規FAILはなく、収集・import失敗もない。`bun run lint`・`bun run format:check`は通過。実行コマンド: `bun run test -- --run`（`frontend/`、終了コード1）
- 書き直した既存テスト: `Purchase.ptf.post.test.tsx`の`PTF-012-TC1 (UI side)`を`PEDT-010-TC1`へ（PUTボディが7項目で、`unit`・`buffer_days`が保存済みの値のまま）。`PTF-012-TC2`は変更なし
- 凍結したテストファイル: `frontend/src/features/Purchase.edit.test.tsx`、`frontend/src/features/Purchase.ptf.post.test.tsx`のPEDT-010-TC1
- Red記録コミットSHA: `ab0ca60`（Backend Redの`7261023`とは別）

### Green

| Test Case ID | 実行コマンド | 結果 |
|---|---|---|
| PEDT-CORE-001〜006（`test_purchase_edit_fields.py`全件、Red時の失敗33件を含む） | `DYNAMODB_LOCAL_PORT=18001 ../bin/mise exec -- uv run python -m scripts.run_with_dynamodb_local -- ../bin/mise exec -- uv run pytest -m integration -q`（`backend/`） | 180 passed、0 failed（終了コード0）。Red時の33件のFAILはすべてPASS |

- 実装計画のGreenタスク: Task 2（Backend Green）
- 凍結済みテストの差分確認（`git diff 7261023 -- backend/tests/integration/api/test_purchase_edit_fields.py`）: 差分なし
- Green記録コミットSHA: `92bed1f`
- 実装: `PurchaseWriteRequest`基底スキーマを導入し`PurchaseCreateRequest`・`PurchasePutRequest`が継承。`put_purchase_endpoint`・`put_purchase`・`apply_edit`が`unit`・`buffer_days`を受け取り、7項目を引数の値で置き換える（`created_at`は引き継ぎ、`stock_counted_at`は在庫変更時のみ更新）。`frontend/src/api/schema.d.ts`を再生成（`PurchasePutRequest`に`unit`・`buffer_days`が必須で追加、`is_temporary`が必須化）
- 追従した非凍結テスト: `test_purchase_edit.py`（新シグネチャへ。`test_review_focus_1_and_ptf_012_*`は`created_at`保持と`unit`・`buffer_days`の置換へ）、`test_purchase_ptf_post.py`（`put_purchase`直接呼び出し2箇所に`unit="パック"`・`buffer_days=0`を追加。期待は不変）

### Refactor・回帰

- 実行コマンド（`backend/`）: `ruff check .`、`ruff format --check .`、`pytest -m "not integration" -q`、上記integration
- 結果: ruff check・format --check 通過、unit 79 passed、integration 180 passed
- 未実行の検証と理由: `bun run build`はTask 3・4（`EditPurchaseDialog.tsx`が旧7項目未満の`PurchasePutRequest`を構築している型エラー）で解消するため未通過。フロントエンドのテストはTask 3以降

## TDD Green Gate

- [ ] Valid Redを確認した、または正当なRed例外を記録した
- [ ] テストを緩和せずGreenになった
- [ ] 凍結済みTDDテストがRed記録時から変更されていない
- [ ] 承認済みの最小TDDテストがリファクタ後もGreenである
- [ ] Contract ID、仕様ID、Test Case IDの対応を維持した
- [ ] TDD候補外のTest Case IDを実装後テストへ引き継いだ
- [ ] 論理テストケースの参照版が変わっていない、または再承認した
