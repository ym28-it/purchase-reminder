# <変更名> 実装後テストレポート

## メタデータ

| 項目 | 値 |
|---|---|
| 対応仕様 | `<仕様ファイルと仕様ID>` |
| TDDテスト計画 | `<test-planファイル>` |
| 対象スライス | <開始点から終了点> |
| 状態 | Draft / Reviewed / Approved |
| 確認者 | <人間> |
| 確認日 | YYYY-MM-DD |

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

| ID | 箇所・契約 | 分類 | リスク | 対応 | 仕様上の根拠 |
|---|---|---|---|---|---|
| GAP-001 |  | Critical / Important / Low risk / Unreachable / Generated / Specification gap |  | Add test / Justified / Spec confirmation |  |

## 追加した単体・コンポーネントテスト

| Test Case ID | テストレベル | 検証する契約・リスク | 追加理由 | 結果 |
|---|---|---|---|---|
|  | Unit / Component |  |  | Pass / Fail |

## 統合テスト

| Test Case ID | 接続する境界 | 前提 | 操作 | 観測可能な期待結果 | 結果 |
|---|---|---|---|---|---|
|  |  |  |  |  | Pass / Fail |

## E2E

| Test Case ID | ユーザーフロー | 前提 | 操作 | 観測可能な期待結果 | 結果 |
|---|---|---|---|---|---|
|  |  |  |  |  | Pass / Fail |

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

## Slice Complete

- [ ] 実装した垂直スライスが仕様の開始点から終了点まで成立する
- [ ] Criticalな未カバー箇所が残っていない
- [ ] Importantな未カバー箇所をテストしたか、残す理由を記録した
- [ ] 必要な単体・コンポーネント・統合・E2Eを実行した
- [ ] 全体回帰、Lint、型チェック、ビルドを確認した
- [ ] 未実行の検証と残存リスクを明示した
- [ ] 人間がテスト内容と結果を確認した
