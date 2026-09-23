# 購入物登録・一覧反映 TDD計画

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `docs/specs/purchase-create.md`（PURC-001〜PURC-019） |
| 論理テストケースSSOT | `docs/specs/purchase-create-test-cases.md` |
| 論理テストケースの参照コミット | `69a00dc62c32ec80af59a7ad5875e564d039d57e` |
| 変更単位 | 購入物を1件登録し、現在の利用者に永続化して一覧へ反映する |
| 文書状態 | Test Plan Approved |

論理テストケースの期待結果をこの文書で再定義しない。期待結果はTest Case IDを通じてSSOTを参照する。

## 機能目的

利用者が購入時期を管理する物品を登録し、登録した内容を同じ利用者の一覧で確認できるようにする。登録情報は後続の購入時期計算、通知、在庫修正の基礎データとなる。

## 対象範囲

- 対象: 登録画面の開始、有効入力の送信、APIによる検証、現在の利用者への永続化、作成結果の応答、一覧の再取得と表示、入力不正・重複・通信失敗時の振る舞い
- 対象外: 編集、削除、在庫の消費・補充、購入予定計算、通知、検索、並べ替え、ページネーション、カテゴリ候補管理、Cognito認証自体の実装、本番AWSへのデプロイ

## 仕様不足・判断保留

現時点で中心的契約の選定を妨げるBlockingな仕様不足は確認されていない。

| ID | 不足情報 | 影響する契約・Test Case ID | 分類 | 必要な確認 | 状態 |
|---|---|---|---|---|---|
| GAP-001 | 認証主体のテスト時注入方法 | PURC-CORE-003 | Important | FastAPIのdependency overrideで現在利用者を差し替える。Cognito自体は対象外とする | Resolved |
| GAP-002 | WorkとClaude Codeで同じDynamoDB Local環境を再現する必要がある | PURC-CORE-001, PURC-CORE-003, PURC-CORE-004 | Important | PR #19のMaven Wrapper・POM・共通ランナーを両環境で連続2回検証し、Environment Gateを再承認する。証跡は`docs/test-environment-gate-evidence.md`を参照する | Reopened |
| GAP-003 | Frontend buildに必要な`src/routeTree.gen`が基準コミットに存在せず、buildが失敗する | PURC-CORE-001, PURC-CORE-002 | Important | 今回のRedとは分離する。Green Gateまでに生成手順または生成物を整備し、buildを成功させる | Open |

GAP-002は旧CloudFront方式では、Environment Gate検証済みSHA `2983f363565f09cf364dfd0d6ae20c7846c3cc01`で解消済みだった。PR #19で依存取得経路をMaven Centralへ変更するため再オープンし、Work・Claude Codeでの再検証と人間再承認後に再度Resolvedとする。
テストエージェントは機能テストのRed確認前に環境スモークを実行し、失敗した場合は
機能契約の不成立ではなく`ENVIRONMENT_FAILURE`として停止する。

GAP-003は仕様上の期待結果を変えないため、Core Contract GateのBlocking事項にはしない。

## 中心的契約

| Contract ID | 契約 | 仕様ID | 対応Test Case ID | 該当する選定条件 | 既存保護 | TDD適格性・Red例外 | AIの判定 |
|---|---|---|---|---|---|---|---|
| PURC-CORE-001 | 有効な入力による登録操作が、現在の利用者に紐づく1件の永続化と、最新状態を再取得した一覧表示まで一気通貫で成立する | PURC-001, PURC-002, PURC-005, PURC-006, PURC-008, PURC-009, PURC-011, PURC-012 | PURC-001-TC1, PURC-002-TC1, PURC-005-TC1, PURC-006-TC1, PURC-008-TC1, PURC-008-TC2, PURC-008-TC3, PURC-009-TC1, PURC-009-TC2, PURC-011-TC1, PURC-012-TC1 | 1, 2, 4, 5 | 直接保護なし | 適格。API・永続化統合とFrontendコンポーネント統合で識別する | Approved |
| PURC-CORE-002 | フロントエンドとAPIが同じ入力領域を守り、仕様外の値を補正せず拒否し、不正な購入物を永続化しない | PURC-003, PURC-004 | PURC-003-TC1, PURC-003-TC2, PURC-003-TC3, PURC-004-TC1, PURC-004-TC2, PURC-004-TC3, PURC-004-TC4, PURC-004-TC5, PURC-004-TC6, PURC-004-TC7, PURC-004-TC8, PURC-004-TC9, PURC-004-TC10, PURC-004-TC11, PURC-004-TC12 | 3, 4, 5 | 直接保護なし | 適格。全境界値を事前TDDへ入れず、変更目的と重大反例を代表ケースで識別する | Approved |
| PURC-CORE-003 | 所有者はクライアント入力ではなくサーバー側の現在利用者から決まり、登録・一覧取得の両方で他利用者へデータが混在または移転しない | PURC-007, PURC-019 | PURC-007-TC1, PURC-019-TC1, PURC-019-TC2 | 3, 4, 5 | 直接保護なし | 適格。認証基盤そのものではなく、確定済みの利用者識別結果を境界入力として検証する | Approved |
| PURC-CORE-004 | 同一利用者の名前・カテゴリ完全一致を、同時要求を含め永続化境界で1件に制限し、異なる表記または異なる利用者のデータは誤って重複扱いしない | PURC-014 | PURC-014-TC1, PURC-014-TC2, PURC-014-TC3, PURC-014-TC4, PURC-014-TC5, PURC-014-TC6, PURC-014-TC7, PURC-014-TC8 | 3, 4, 5 | 直接保護なし | 適格。同時要求の重大反例と利用者スコープの代表回帰を分けて識別する | Approved |

選定条件:

1. 失敗すると機能目的を達成できない
2. 必要な既存・新規レイヤーを通る主要正常系である
3. 影響が大きい、または修復困難な状態を防ぐ
4. 新設・変更され、既存テストで十分に保証されない
5. 実装方式が変わっても維持すべき観測可能な振る舞いである

## 候補を4契約にまとめた理由

- `PURC-CORE-001`は、この垂直スライスの開始点から終了点までを代表する変更目的である。
- `PURC-CORE-002`は、クライアント検証の迂回による不正データの永続化を防ぐ境界契約である。
- `PURC-CORE-003`は、利用者間の情報漏えい・所有権逸脱を防ぐ重大契約である。
- `PURC-CORE-004`は、後から安全に修復しにくい重複データと競合登録を防ぐ重大契約である。
- APIレスポンス、永続化、一覧反映は個別の中心契約へ分割せず、主要正常系の観測点として`PURC-CORE-001`へまとめる。
- 個々の境界値や表記差は独立した中心契約ではなく、`PURC-CORE-002`または`PURC-CORE-004`を詳しく検証する論理ケースとして扱う。

## TDD候補外と実装後テストへの引き継ぎ

| Test Case ID | 候補外の理由 | 暫定的な検証先 |
|---|---|---|
| PURC-002-TC2 | 初期値は重要だが主要正常系や重大なデータ不整合を単独で代表しない | Component |
| PURC-006-TC2 | 複数IDの一意性はシステム生成契約の詳細な反例であり、中心経路を増やさず後続で検証できる | Integration |
| PURC-010-TC1, PURC-010-TC2 | 成功後のモーダル状態と再オープン時の初期化はUI状態の詳細である | Component / E2E |
| PURC-012-TC2, PURC-012-TC3, PURC-012-TC4 | 一時購入表示の両極性と成功通知非表示は一覧表示の詳細である | Component / E2E |
| PURC-013-TC1, PURC-013-TC2 | 二重操作防止は重要だが、永続化上の重複防止は`PURC-CORE-004`で先に固定する。UIのloading状態は後続で検証する | Component / E2E |
| PURC-015-TC1 | 失敗時の入力維持は重要なUI回復性だが、機能目的・重大な永続化リスクの中心ではない | Component / E2E |
| PURC-016-TC1, PURC-016-TC2 | 原因別表示はAPI契約を利用者向け表示へ変換する詳細である | Component / Integration |
| PURC-017-TC1, PURC-017-TC2 | 共通エラーと内部情報の非表示は失敗経路の詳細であり、実装されたエラー変換を見て補完する方が適切である | Component / Integration / E2E |
| PURC-018-TC1, PURC-018-TC2 | 自動再送禁止と手動再試行はクライアント状態・通信経路の詳細である | Component / E2E |

候補外にしても仕様上の契約が消えるわけではない。最終的な検証先と結果は実装後テストレポートで確定する。

## 全論理テストケースのスクリーニング確認

全53件を次のいずれかへ割り当てた。

- `PURC-CORE-001`: 11件
- `PURC-CORE-002`: 15件
- `PURC-CORE-003`: 3件
- `PURC-CORE-004`: 8件
- TDD候補外・実装後引き継ぎ: 16件

合計: 53件。判断保留または未割り当てはない。

## Core Contract Gate

- [x] 論理テストケースの参照コミットを記録した
- [x] すべての論理テストケースをスクリーニングした
- [x] 機能目的を代表する契約が含まれている
- [x] 許容できない重大リスクが含まれている
- [x] 網羅目的の詳細を中心的契約へ含めていない
- [x] 各契約の仕様IDとTest Case IDが正しい
- [x] 候補外の理由と暫定的な検証先が記録されている
- [x] AIが仕様上の判断を暗黙に追加していない
- [x] Blockingな判断保留が残っていない
- [x] 人間が中心的契約と対応Test Case IDを承認した

### 承認記録

- 承認したContract ID: `PURC-CORE-001`, `PURC-CORE-002`, `PURC-CORE-003`, `PURC-CORE-004`
- 修正・除外した候補: なし
- 承認者: ym28-it
- 承認日: 2026-09-17
- 備考: Workチャット上で計画案を承認。Core Contract Gate通過として記録する。

Core Contract Gate通過前に、最小TDDテストセット、テストコード、実装コードを確定しない。

## Baseline

Core Contract Gate通過後、プロダクトコードとテストコードを変更していない`main`で確認した。

- 基準コミットSHA: `69a00dc62c32ec80af59a7ad5875e564d039d57e`
- 実行日: 2026-09-17
- 既存失敗を今回の変更から分離できるか: Yes

| 対象 | 実行コマンド | 結果 | 判定 |
|---|---|---|---|
| Backend依存関係 | `uv sync --frozen` | Pass | Python 3.14環境とロック済み依存関係を使用できる |
| Backend tests | `uv run pytest -q` | Pass（53 passed） | 既存テストはすべて成功 |
| Backend lint | `uv run ruff check .` | Pass | 既存失敗なし |
| Backend format | `uv run ruff format --check .` | Pass（38 files） | 既存失敗なし |
| Frontend依存関係 | `bun install --frozen-lockfile` | Pass | Work環境では`npx -y bun`でBun 1.4.2を起動 |
| Frontend tests | `bun run test --run` | Fail（No test files found） | テスト失敗ではなく、既存Frontendテストが0件であることによる終了コード1 |
| Frontend lint | `bun run lint` | Pass（36 files） | 既存失敗なし |
| Frontend format | `bun run format:check` | Pass（31 files） | 既存失敗なし |
| Frontend build | `bun run build` | Fail | `src/routeTree.gen`未生成と、それに伴うroute型エラー。今回のRedより前から存在する |
| DynamoDB Local統合 | `docker compose`を用いる統合検証 | Not run | Work環境にDockerコマンドが存在しない |

### Baselineの扱い

- Backend既存テスト、Backend/FrontendのLint・formatは今回のRedおよび回帰判定に利用できる。
- Frontend testの終了コード1はテスト未作成によるものであり、新しいTDDテスト追加後は通常のPass/Failで判定する。
- Frontend buildの既存失敗は今回追加するテストのValid Redとして扱わない。Green Gateまでに別途解消する。
- DynamoDB Localを使う統合テストはこの環境では実行していない。テストエージェントはRed確認前に実行可能性を確認する。
- 基準コミット以後に`main`のプロダクトコードまたはテスト基盤が変わった場合、Test Plan Gate承認前にBaselineを再実行する。
- PR #19はテスト基盤を変更するため、上表は履歴として保持し、Maven方式のEnvironment GateとBaselineで更新する。

## 既存テストによる保護

| Contract ID | 既存テスト | Baseline結果 | 十分か | 新規テスト | 根拠 |
|---|---|---|---|---|---|
| PURC-CORE-001 | なし | Backendの無関係なモデル単体テスト53件のみPass | No | Add | API登録、永続化、再取得、Frontend一覧反映を検証する既存テストがない |
| PURC-CORE-002 | なし | Frontendテスト0件。BackendにもPurchaseスキーマテストなし | No | Add | FrontendとAPI双方の入力領域を保証できない |
| PURC-CORE-003 | なし | 認証依存と利用者分離を検証する既存テストなし | No | Add | クライアント入力による所有者変更と他利用者一覧への混在を検出できない |
| PURC-CORE-004 | なし | 名前・カテゴリの重複と同時要求を検証する既存テストなし | No | Add | 現在の条件付き書き込みはUUIDキーの重複だけを防ぎ、名前・カテゴリ重複を保護していない |

## 最小TDDテストセット

以下をTest Plan Gateの承認候補とする。実テスト名はTest Case IDへ追跡可能にし、同じ行に記載した複数IDを1つのシナリオで検証してよい。

| Plan ID | Test Case ID | Contract ID | 役割 | テストレベル | 実テスト予定場所 | 変更前の期待状態 | 選定根拠 |
|---|---|---|---|---|---|---|---|
| PURC-TDD-001 | PURC-005-TC1, PURC-008-TC1, PURC-008-TC2, PURC-008-TC3, PURC-009-TC1, PURC-004-TC12 | PURC-CORE-001, PURC-CORE-002 | 変更目的 | API・永続化統合 | `backend/tests/integration/api/test_purchase_create.py` | Red | 現在利用者として`speed=0`を含む有効入力をPOSTし、201応答とレスポンス契約を確認後、GETで同じID・内容を再取得する。現在はAPIが`speed=0`を拒否するため、契約不成立によるRedを期待する |
| PURC-TDD-002 | PURC-011-TC1, PURC-012-TC1, PURC-004-TC12 | PURC-CORE-001, PURC-CORE-002 | 変更目的 | Frontendコンポーネント統合 | `frontend/src/features/Purchase.test.tsx` | Red | `speed=0`を含む有効入力を画面から登録し、成功後の再取得結果として名前・カテゴリ・消費スピード・在庫が一覧に表示されることを検証する。現在は`speed=0`が送信できず、一覧にも消費スピードがない |
| PURC-TDD-003 | PURC-003-TC1 | PURC-CORE-002 | 重大反例 | Frontendコンポーネント | `frontend/src/features/CreatePurchaseDialog.test.tsx` | Red | 代表的な仕様違反として空白文字だけの名前を入力し、項目エラーが表示され登録要求が送信されないことを検証する。残りの境界値は実装後テストへ引き継ぐ |
| PURC-TDD-004 | PURC-003-TC2 | PURC-CORE-002 | 重大反例 | API・永続化統合 | `backend/tests/integration/api/test_purchase_create.py` | Red | APIへ空白文字だけの名前を直接送信し、422、項目識別可能なエラー、永続化なしを検証する。クライアント検証を迂回しても不正データが残らないことを固定する |
| PURC-TDD-005 | PURC-007-TC1, PURC-019-TC2 | PURC-CORE-003 | 重大反例 | API・永続化統合 | `backend/tests/integration/api/test_purchase_create.py` | Green（Red例外） | 利用者Aの要求へ利用者BのIDを混入してもAに保存され、Bの一覧へ表示されないことを検証する。既存のdependencyとリクエストスキーマが満たす可能性が高いretrofitの代表回帰として、最初からGreenなら証跡を記録する |
| PURC-TDD-006 | PURC-014-TC8 | PURC-CORE-004 | 重大反例 | API・DynamoDB統合 | `backend/tests/integration/api/test_purchase_create.py` | Red | 同一利用者・同一名前・同一カテゴリの同時要求で1件だけが201、残りが409となり、永続状態も1件であることを検証する。競合時にも破れない永続化制約を要求する |
| PURC-TDD-007 | PURC-014-TC7 | PURC-CORE-004 | 代表回帰 | API・DynamoDB統合 | `backend/tests/integration/api/test_purchase_create.py` | Green（Red例外） | 異なる利用者は同じ名前・カテゴリをそれぞれ登録できることを検証する。重複防止の実装で利用者スコープを失う回帰を防ぐ。現実装では最初からGreenとなる可能性が高い |

### 最小性の根拠

- `PURC-CORE-001`は、APIから永続化・再取得までと、UI登録から一覧反映までの2つの接続点で識別する。事前TDDでPlaywright環境まで新設するより、欠陥箇所を特定しやすい2テストへ分ける。
- `PURC-CORE-002`はFrontendとAPIの独立した検証が仕様で要求されるため、それぞれ最低1つの不正入力を置く。正常系では、仕様決定上重要で現実装と異なる`speed=0`を`PURC-TDD-001`と`PURC-TDD-002`で兼ねる。
- `PURC-CORE-003`は、所有者の決定と一覧分離を1つの複合シナリオで識別する。
- `PURC-CORE-004`は、同時重複を防ぐ制約と、制約を利用者単位に限定する回帰が独立しているため2テストとする。
- 文字数上限、すべての数値境界、表記差、失敗時UI状態などは中心契約を追加で識別しないため、実装後テストへ残す。
- ブラウザから実DynamoDBまでの代表正常系E2Eは省略しない。TDD Green後、`PURC-009-TC2`を含む実装後テストとして追加する。

### Red例外

- `PURC-TDD-005`と`PURC-TDD-007`は、新しい制約を実装する際に壊しやすい既存挙動を固定する代表回帰である。retrofitのため、最初からGreenでも正当なRed例外とする。
- Red例外はテストエージェントの推測で確定しない。対象テストを変更前コードで実行し、期待どおりGreenである証跡をTDD実行記録へ残す。
- その他のテストが最初からGreenになった場合は自動的に例外扱いせず、既存実装が契約全体を満たすか確認して`INVALID_RED`とする。追加のRed例外判断が必要なら仕様エージェントと人間へ戻す。

## Test Plan Gate

- [x] Baselineを確認し、既存失敗を分離した
- [x] すべての承認済み中心的契約に保護方針がある
- [x] 各テストが対応するContract IDとTest Case IDを持つ
- [x] 最小テストセットが変更目的と重大リスクを識別できる
- [x] 既存テストで省略する場合の根拠がある（今回は既存保護による新規テスト省略なし）
- [x] Red例外の理由が妥当である
- [x] 実装詳細を不必要に固定していない
- [x] 人間がテストコード作成を承認した

### 承認記録

- 承認者: ym28-it
- 承認日: 2026-09-18
- 備考: Workチャット上で最小TDDテストセットを承認。7項目、Red例外、GAP-002の実行前提、E2Eの実装後テストへの引き継ぎを含めてTest Plan Gate通過として記録する。

## TDD実行記録

Core Contract GateおよびTest Plan Gate通過後にテストエージェントが記録する。

## TDD Green Gate

- [ ] Valid Redを確認した、または正当なRed例外を記録した
- [ ] テストを緩和せずGreenになった
- [ ] 承認済みの最小TDDテストがリファクタ後もGreenである
- [ ] Contract ID、仕様ID、Test Case IDの対応を維持した
- [ ] TDD候補外のTest Case IDを実装後テストへ引き継いだ
- [ ] 論理テストケースの参照版が変わっていない、または再承認した
