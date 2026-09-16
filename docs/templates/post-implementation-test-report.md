# <機能名> 実装後テストレポート

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `<仕様ファイルと仕様ID>` |
| 論理テストケースSSOT | `<論理テストケースファイル>` |
| 論理テストケースの参照コミット | `<commit SHA>` |
| TDD計画 | `<tdd-planファイル>` |
| TDD Greenコミット | `<commit SHA>` |
| 対象スライス | <開始点から終了点> |
| 状態 | Draft / Reviewed / Approved |
| 確認者 | <人間> |
| 確認日 | YYYY-MM-DD |

論理テストケースの期待結果をこの文書で再定義しない。期待結果はTest Case IDを通じてSSOTを参照する。

## 入力と引き継ぎ

### TDDからの引き継ぎ

| Test Case ID | TDDでの扱い | 実装後に必要な確認 |
|---|---|---|
|  | TDD済み / 候補外 / 既存テスト / 対象外候補 |  |

### 実装分析で新たに見つかった観点

| ID | 観点 | 種別 | 仕様・Test Case ID上の根拠 | 対応 |
|---|---|---|---|---|
| IMPL-RISK-001 |  | 分岐 / 境界 / エラー / 状態遷移 / 接続 / セキュリティ |  | Add test / Justified / Spec confirmation |

新しい利用者向け振る舞い、または既存仕様から期待結果を一意に導けない観点は、この文書だけで確定しない。仕様と論理テストケースへ戻り、人間の再承認を得る。

外部契約を追加しない実装固有のリスクは `IMPL-RISK-<3桁連番>` で記録できる。ただし、実装コードの現在の挙動を期待結果の根拠にしない。

## 実装した処理フロー

<ユーザー操作または入力から、API・ドメイン・永続化・出力までの流れを記述する。>

## 実装範囲

- Frontend:
- API:
- Services / Domain:
- Persistence:
- External systems:
- 対象外:

## カバレッジ

### 実行条件

- コマンド:
- 対象:
- ツール:

### 結果

| 対象 | Line | Branch | 備考 |
|---|---:|---:|---|
|  |  |  |  |

カバレッジ率は未検証箇所の発見に使用し、数値だけを完了条件にしない。

## 未カバー箇所の評価

| ID | 箇所・契約 | 分類 | リスク | 対応 | 仕様・Test Case ID上の根拠 |
|---|---|---|---|---|---|
| GAP-001 |  | Critical / Important / Low risk / Unreachable / Generated / Specification gap |  | Add test / Justified / Spec confirmation |  |

Specification gapでは期待結果を推測せず、仕様と論理テストケースへ戻る。

## 追加した単体・コンポーネントテスト

| Test Case ID / Risk ID | テストレベル | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
|  | Unit / Component |  |  | Pass / Fail |

## 統合テスト

| Test Case ID / Risk ID | 接続する境界 | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
|  |  |  |  | Pass / Fail |

## E2E

| Test Case ID / Risk ID | ユーザーフロー | 実テスト | 追加理由 | 結果 |
|---|---|---|---|---|
|  |  |  |  | Pass / Fail |

各表では前提、操作、期待結果を再記述せず、論理Test Case IDまたは根拠を記録した実装リスクIDを参照する。

## 論理テストケースの消化確認

承認済み論理テストケースのすべてのTest Case IDを記載する。

| Test Case ID | 最終的な検証先 | 実テスト・証跡 | 結果 | 対象外理由 |
|---|---|---|---|---|
|  | TDD / Unit / Component / Integration / E2E / 既存テスト / 対象外 |  | Pass / Fail / Not run |  |

- TDDと実装後テストの両方で検証する場合は、重複する理由を記録する
- どこにも割り当てられていないTest Case IDを残さない
- 対象外は、仕様上不要になった根拠または検証しないリスク判断を記録する
- 期待結果が変わった場合は、この表で調整せず論理テストケースへ戻る

## 全体検証

| 検証 | コマンド | 結果 | 備考 |
|---|---|---|---|
| Backend tests |  | Pass / Fail / Not run |  |
| Frontend tests |  | Pass / Fail / Not run |  |
| Integration |  | Pass / Fail / Not run |  |
| E2E |  | Pass / Fail / Not run |  |
| Backend lint / format |  | Pass / Fail / Not run |  |
| Frontend lint / format |  | Pass / Fail / Not run |  |
| Type check |  | Pass / Fail / Not run |  |
| Build |  | Pass / Fail / Not run |  |
| Infrastructure validation |  | Pass / Fail / Not run |  |

## 未実行・残存リスク

| 項目 | 理由 | 影響 | 後続対応 |
|---|---|---|---|
|  |  |  |  |

## Slice Complete Gate

- [ ] 実装した垂直スライスが仕様の開始点から終了点まで成立する
- [ ] 論理テストケースの参照コミットを記録した
- [ ] すべての論理Test Case IDに検証先または対象外理由がある
- [ ] Criticalな未カバー箇所が残っていない
- [ ] Importantな未カバー箇所をテストしたか、残す理由を記録した
- [ ] 必要な単体・コンポーネント・統合・E2Eを実行した
- [ ] 全体回帰、Lint、型チェック、ビルドを確認した
- [ ] 未実行の検証と残存リスクを明示した
- [ ] 仕様または論理テストケースの変更時に影響する承認を取り直した
- [ ] 人間がテスト内容、実行結果、対象外理由、残存リスクを確認した
