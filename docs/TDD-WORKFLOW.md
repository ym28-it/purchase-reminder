# TDDワークフロー（superpowers連携）

## 1. 目的と位置づけ

開発ワークフロー全体（要件の対話、設計・仕様の作成、実装計画、タスク実行、コードレビュー、ブランチの完了）は[superpowers](https://github.com/obra/superpowers)が制御する。この文書は、そのうちTDDとテストに関わる部分だけを、このプロジェクト独自の制御に置き換える契約を定める。

独自に制御する範囲は次のとおり。

1. 承認済み仕様から、実装に依存しない論理テストケースを作成する
2. 中心的契約を選定し、最小TDDテストセットを計画する
3. Baselineを記録する
4. Valid Redを確認し、TDDテストを凍結する
5. 凍結済みテストを変更せずにGreenにする
6. 実装後テスト（カバレッジ分析、追加テスト、統合テスト、E2E、全体検証）

実装を先に書き、その実装に合わせて仕様やテストを後付けしない。実装前のTDDは網羅的なテストスイートではなく、承認済みの中心的契約を実行可能なガードレールへ変換するものである。網羅性は実装後テストで補う。

テストの選定・品質・最小性には[最小TDDにおけるテスト作成原則](./MINIMUM-TDD-TEST-PRINCIPLES.md)を、中心的契約の抽出と承認には[中心的契約選定フロー](./CORE-CONTRACT-SELECTION.md)を適用する。

## 2. superpowersとの組み合わせ

```
superpowers:brainstorming                 仕様（design doc）を作成・人間が承認
        ↓
[独自] design-tdd-tests                    論理テストケース・中心的契約・Baseline・最小TDD計画を作成・人間が承認
        ↓
superpowers:writing-plans                  TDD計画を参照した実装計画を作成・人間が承認し実行方式を選択
        ↓
superpowers:subagent-driven-development    計画のタスクを順に実行（またはexecuting-plans）
  ├ Redタスク   → [独自] create-tdd-tests      TDDテスト作成・Valid Red・凍結
  ├ Greenタスク → [独自] implement-tdd-slice   凍結済みテストを変えずにGreen
  └ 検証タスク  → [独自] verify-feature-slice  実装後テスト・実装後テストレポート
        ↓
superpowers 最終コードレビュー（requesting-code-review）
        ↓
superpowers:verification-before-completion → superpowers:finishing-a-development-branch
        ↓
人間がマージ（Slice Complete）を判断
```

### 2.1 superpowersより優先する規則

`CLAUDE.md`とこの文書はsuperpowersのSkillより優先する。次の点でsuperpowersの既定動作を置き換える。

- **`superpowers:test-driven-development`は使用しない。** superpowersのSkill（`executing-plans`、`subagent-driven-development`、`systematic-debugging`など）がこのSkillの読み込みやRed-Greenを指示した場合は、この文書と独自Skillsを適用する。「失敗するテストのないプロダクトコードを書かない」という規則は適用せず、TDD計画で選定した中心的契約だけを実装前にテストし、それ以外は実装後テストで検証する。
- **期待動作を裁定しない。** `subagent-driven-development`はタスク実行中の曖昧さを制御役がRulingとして決めて進めるが、仕様・論理テストケース・期待結果・凍結済みTDDテストに関わる判断はRulingの対象外とする。仕様から期待結果を一意に導けない場合は実行を停止し、人間へ戻す（`BLOCKED_SPEC`）。Rulingは実装方法、ファイル配置、命名など、期待動作を変えない事項に限る。
- **TDDテストを凍結する。** Valid Red記録後、Greenタスクの実装者とレビュー指摘の修正者はTDDテストと期待値を変更しない。変更が必要に見える場合は停止し、Redタスクまたは仕様へ差し戻す。
- **環境障害をRedや実装欠陥に数えない。** 環境スモークが失敗した場合は`ENVIRONMENT_FAILURE`として停止し、`setup-test-environment`で環境を確認・修復する。

## 3. 成果物

新規機能の成果物は、superpowersの既定配置である`docs/superpowers/specs/`へ、仕様（design doc）と同じ日付・トピックを接頭辞として置く。

| ファイル | 作成者 | 責務 |
|---|---|---|
| `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` | superpowers:brainstorming | 機能仕様。最上位のsource of truth |
| `docs/superpowers/specs/YYYY-MM-DD-<topic>-test-cases.md` | design-tdd-tests | 実装非依存の論理テストケース全体。期待動作の唯一の真実 |
| `docs/superpowers/specs/YYYY-MM-DD-<topic>-tdd-plan.md` | design-tdd-tests（実行記録はcreate-tdd-tests / implement-tdd-slice） | 中心的契約、Baseline、最小TDDテストセット、Red/Green記録 |
| `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` | superpowers:writing-plans | 実装計画。TDD計画をTest Case ID・Contract IDで参照する |
| `docs/superpowers/specs/YYYY-MM-DD-<topic>-post-test-report.md` | verify-feature-slice | 実装後テストと全Test Case IDの消化状況 |

テンプレートは[最小TDDテスト計画](./templates/minimum-tdd-test-plan.md)と[実装後テストレポート](./templates/post-implementation-test-report.md)を使用する。

superpowers導入前に作成した`docs/specs/<feature-slug>*.md`（購入物登録）は、その配置のまま同じ契約で扱う。

### 3.1 仕様に求める追加要件

brainstormingで作成する仕様には、superpowersの既定内容に加えて次を含める。

- 各要件に`<PREFIX>-<3桁連番>`の仕様IDを付ける
- スライスの開始点と終了点、観測可能な振る舞い、正常時と失敗時の状態、対象外、受け入れ条件
- 確認事項をBlocking / Important / Deferredに分類し、Blockingを0件にしてから承認する

### 3.2 論理テストケースを唯一の真実にする

論理テストケースは「何を保証するか」だけを扱う。

- Test Case ID（`<spec-id>-TC<連番>`）
- 対応仕様ID
- 前提
- 操作
- 期待結果

関数名、エンドポイント名、コンポーネント名などの実装詳細を書かない。すべての仕様IDに1件以上のTest Case IDを対応させ、すべてのTest Case IDを仕様IDへ追跡可能にする。

TDD計画、実装計画、実装後テストレポートは派生文書であり、期待結果を独自に定義または変更しない。Test Case IDで参照し、テストレベル、実テストの場所、Red例外、実行結果、対象外理由などの実行情報だけを追加する。期待結果の変更が必要な場合は、仕様と論理テストケースへ戻り、人間の再承認を得る。

### 3.3 参照版を固定する

TDD計画、実装計画、実装後テストレポートには、参照した論理テストケースのファイルパスとコミットSHAを記録する。参照後に論理テストケースが変更された場合、影響するCore Contract Gate、Test Plan Gate、実装計画、実装後テスト分析を無効として再確認する。

## 4. Gate

| Gate | 判定者 | 条件 |
|---|---|---|
| Specification Gate | 人間 | superpowers:brainstormingの仕様レビューで承認。Blocking確認事項0件 |
| Logical Test Case Gate | 人間 | 仕様とのトレーサビリティを持つ論理テストケース全体を承認 |
| Core Contract Gate | 人間 | 全論理テストケースのスクリーニング結果と中心的契約・対応Test Case IDを承認 |
| Test Plan Gate | 人間 | Baseline記録後、最小TDDテストセットを承認 |
| 実装計画の承認 | 人間 | superpowers:writing-plansの計画レビューで承認し、実行方式を選択。これをTDD開始指示とみなす |
| Red Gate | Redタスクのレビュー | 5.5の条件を満たし、TDDテストを凍結 |
| TDD Green Gate | Greenタスクのレビュー | 5.6の条件を満たす |
| Completion Gate | 検証タスクのレビュー | 5.7の条件を満たす |
| Slice Complete | 人間 | 最終コードレビューと証跡を確認し、finishing-a-development-branchでマージを判断 |

Characterization Test、既存テストによる保護、純粋なリファクタリングではRed Gateを省略できるが、原則書に定める例外理由をTDD計画へ記録する。

## 5. 手順

### 5.1 論理テストケース（design-tdd-tests）

仕様承認後、brainstormingからwriting-plansへ進む前に`design-tdd-tests`を実行する。

- 承認済み仕様から、正常系、境界値、異常系、認可、状態、重大な並行性を導出する
- 機械的に導出できるケースはまとめて提示してよい。判断が分かれる境界値、排他条件、失敗時の状態は1件ずつ人間と決める
- 仕様の曖昧さや矛盾を見つけたら推測で補完せず、仕様へ戻す

### 5.2 中心的契約（design-tdd-tests）

[最小TDDテスト計画テンプレート](./templates/minimum-tdd-test-plan.md)からTDD計画をDraftで作成し、[中心的契約選定フロー](./CORE-CONTRACT-SELECTION.md)に従って全論理テストケースをスクリーニングする。候補外ケースには理由と実装後の検証先を記録する。Core Contract Gate通過前に、最小TDDテストセット、テストコード、実装コードを確定しない。

### 5.3 Baselineと最小TDDテストセット（design-tdd-tests）

Baselineは、既存失敗と今回のRed・回帰を区別するための技術的チェックである。関連する既存テスト、Lint、型チェック、ビルドを実行し、基準コミットSHA、コマンド、結果、既存失敗、実行しなかった検証と理由をTDD計画へ記録する。分離できない既存失敗は、先に修正するか既存問題として扱うかを人間と決める。

承認済み中心的契約から、変更目的、重大反例、代表回帰を識別する必要最小限のテストを選ぶ。既存テストで十分に保証できる場合は、新規テストを形式的に追加せず既存テストIDと根拠を記録する。

### 5.4 実装計画への組み込み（superpowers:writing-plans）

writing-plansは次の規則で計画を作る。

- 計画ヘッダーの`Spec`に仕様を、あわせて論理テストケースとTDD計画のパスと参照コミットを記載する
- TDD対象の中心的契約ごとに、**Redタスク**（`create-tdd-tests`でテスト作成・Valid Red記録）と、それに続く**Greenタスク**（`implement-tdd-slice`で実装）を分ける。Redタスクの`Expected`は「承認済み契約の未実装による失敗」とする
- TDD計画にないテストを、実装前テストとして計画に追加しない。TDD対象外の実装はGreenタスクまたは独立タスクに含め、検証は実装後テストへ送る
- 計画の最後に**検証タスク**（`verify-feature-slice`）を置く
- 各テストのステップにTest Case IDとContract IDを記載する

`subagent-driven-development`では各タスクを新しいサブエージェントが実行するため、Redを書いたコンテキストとGreenを実装するコンテキスト、実装後テストのコンテキストは自然に分離される。`executing-plans`を選んだ場合も、Redタスク、Greenタスク、検証タスクは担当Skillの変更境界を守る。

### 5.5 Red（create-tdd-tests）

1. 環境スモークとBaselineを実行し、既知でない失敗がないことを確認する
2. 選定済みTest Case IDをテストコードへ翻訳し、テスト名またはメタデータからTest Case IDへ遡れるようにする
3. 対象テストを実行し、次をすべて満たすValid Redを記録する
   - 対象TDDテストが失敗する
   - 失敗理由が承認済み契約の未実装である
   - 収集失敗、import失敗、環境・fixture・mockの不備による失敗ではない
   - 差分にプロダクトコードが混在していない
4. コマンド、終了コード、失敗したassertion、件数、SHAをTDD計画の実行記録へ追記する
5. 凍結するテストファイルとコミットSHAを記録する

誤ったテストは`INVALID_RED`または`BLOCKED_TEST`として同じRedタスクで修正し、Red Gateを再判定する。

### 5.6 Green（implement-tdd-slice）

1. 凍結済みテストがRed記録時から変更されていないことを確認する
2. 仕様を満たす最小のプロダクト実装を行い、テストを緩和せずリファクタする
3. 次を確認してTDD計画へ記録する
   - 対象TDDテストがGreen
   - 影響範囲の回帰テストがGreen
   - lint、format、型チェック、buildの対象項目が完了
   - 凍結済みTDDテストに変更がない
   - 仕様外の挙動や無関係な変更がない
   - コマンド、件数、終了コード、SHA

### 5.7 実装後テスト（verify-feature-slice）

すべてのGreenタスクの完了後、[実装後テストレポートテンプレート](./templates/post-implementation-test-report.md)から実装後テストレポートを作成する。

1. TDD計画で候補外または実装後へ送ったTest Case IDを引き継ぐ
2. 実装全体を読み、line / branch coverageを取得して、未実行の分岐、境界値、エラー処理、状態遷移、時刻・乱数・UUID、永続化前後の整合性、認証・認可・ユーザー分離、レイヤー間の変換、実装中に判明したリスクを調査する
3. 未カバー箇所を分類する

   | 分類 | 扱い |
   |---|---|
   | Critical | 必ずテストを追加する |
   | Important | 原則追加する。追加しない場合は理由を記録する |
   | Low risk | カバレッジ率だけを目的に追加しなくてよい |
   | Unreachable / Generated | 除外理由を記録する |
   | Specification gap | 期待結果を決めず、仕様確認へ戻る |

4. 欠陥を最も速く、決定的に、原因を特定しやすいレベルへテストを追加する

   | 検証対象 | 優先するテスト |
   |---|---|
   | 計算、ビジネスルール、不変条件 | 単体テスト |
   | UIの入力、表示、状態 | コンポーネントテスト |
   | DynamoDBの実際の読み書き | DynamoDB Localを使う統合テスト |
   | HTTP契約と永続化の接続 | API統合テスト |
   | ユーザー操作から最終状態まで | 少数の代表E2E |

   同じ契約を複数レベルで無意味に重複検証しない。全境界値や全バリデーションをE2Eへ重複させない。

5. 対象テスト、全単体・コンポーネントテスト、全統合テスト、E2E、Backend / FrontendのLintとformat check、型チェック、Frontend buildを実行し、結果を記録する。失敗した検証をskip、削除、期待値の緩和によって通過させない。実行できない検証は、内容、理由、影響、後続対応を記録する
6. 全Test Case IDを、TDD、単体、コンポーネント、統合、E2E、既存テスト、または根拠付き対象外のいずれかへ割り当てる

Completion Gateは次をすべて満たしたときに通過する。

- 全必須テストと回帰テストがGreen
- 必須の静的検査とbuildが完了
- 全Test Case IDの対応が記録済みで、未割り当てがない
- Criticalな未カバー箇所が残っていない
- 未検証項目、Deferred、既知制約、残存リスクが明示済み
- 実装後テストレポートが対象SHAと整合
- 未承認の仕様変更、テスト緩和、範囲外変更がない

新しい利用者向け振る舞いや、仕様から期待結果を導けないケースは、実装後テストだけで確定しない。仕様と論理テストケースへ戻り、人間の再承認を得る。

### 5.8 最終レビューと完了

Completion Gate通過後、superpowersの最終コードレビューへ進む。レビュー依頼には、仕様、論理テストケース、TDD計画、実装後テストレポートのパスを含め、次も確認対象とする。

- 仕様とTest Case IDとテストコードのトレーサビリティ
- Valid Red（または承認済みRed例外）とGreenの証跡
- 凍結済みTDDテストが変更されていないこと
- 全Test Case IDの結果またはDeferred理由

その後`superpowers:verification-before-completion`と`superpowers:finishing-a-development-branch`へ進み、人間がマージを判断する。

## 6. 差し戻し

| 発見した問題 | 戻り先 | 再実行する範囲 |
|---|---|---|
| 要求、仕様、受け入れ条件、期待結果の不足・矛盾 | 人間と仕様（brainstorming）・`design-tdd-tests` | 影響する仕様・論理テストケース・TDD計画・実装計画を再承認し、Red以降を再実行 |
| テストの誤り、不足、過剰制約 | Redタスク（`create-tdd-tests`） | テスト修正後、Red Gate以降を再実行 |
| 実装が承認済み仕様・テストを満たさない | Greenタスク（`implement-tdd-slice`） | Green Gate以降を再実行 |
| テスト容易性のためプロダクト境界の変更が必要 | 人間と仕様 | 変更を承認後、影響する最も早い工程から再実行 |
| テスト環境、依存取得、起動、fixtureの失敗 | `setup-test-environment` | 同じ工程を再開。Valid Redや実装欠陥に数えない |

上流成果物を変更した場合、それに依存する下流の承認とGateは有効とみなさない。

## 7. 既存の未テスト実装にテストを追加する（retrofit）

既存実装へのretrofitでは、純粋なTDDの順序を再現できない。次を守る。

1. 実装コードを正解とみなさず、README、仕様、API契約など独立した情報源から期待動作の仮説を作る
2. 実装を読み、仮説との不一致と未定義動作を確認事項として整理する
3. 人間と仕様を確定し、以後は新規機能と同じ手順で論理テストケース、中心的契約、TDD計画を承認する
4. テスト失敗を、実装のバグまたは仕様理解の違いに分類する。仕様理解の違いであれば仕様と論理テストケースへ戻って再承認する

Characterization Testは追加時点からGreenでよいが、現在の挙動という理由だけで正しい仕様として固定しない。

## 8. 局所変更

superpowers:brainstormingがBoundedと分類した変更、不具合修正、外部挙動を変えないリファクタリング、UI改善、テスト・依存関係・CI・インフラ・文書の保守では、論理テストケースとTDD計画のファイルを作らなくてよい。その場合も次を守る。

- チャット上の設計で、保証する振る舞い、テストレベル、Red例外の有無を示し、人間の承認を得る
- テストの選定と品質は[最小TDDにおけるテスト作成原則](./MINIMUM-TDD-TEST-PRINCIPLES.md)に従う
- 不具合修正では、再発防止テストのValid Redを確認してから修正する（`superpowers:systematic-debugging`で原因を特定した後）
- 変更の影響がレイヤー境界を越える場合だけ、必要な統合テストやE2Eを追加する

## 9. Skills

| Skill | 担当 | 変更してよいもの |
|---|---|---|
| `design-tdd-tests` | 論理テストケース、中心的契約、Baseline、最小TDD計画 | 論理テストケース、TDD計画 |
| `create-tdd-tests` | Redタスク | テストコード、fixture/helper、最小テスト設定、TDD計画のRed記録 |
| `implement-tdd-slice` | Greenタスク | プロダクトコード、プロダクト設定、TDD計画のGreen記録 |
| `verify-feature-slice` | 検証タスク | テストコード（凍結済みTDDテストを除く）、fixture/helper、最小テスト設定、実装後テストレポート |
| `setup-test-environment` | テスト環境の確認・修復 | 環境コード（Gate再実行と人間の再承認が必要） |

各Skillは担当範囲外の問題を修正せず、定義済みの戻り先へ返して停止する。
