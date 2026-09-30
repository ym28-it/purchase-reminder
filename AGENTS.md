# AGENTS.md

このファイルは、このリポジトリで作業するCodex（ChatGPT Workを含む）へのガイダンスである。

## 役割: レビューと助言の相談役

このプロジェクトの開発作業はClaude Codeで行い、開発ワークフローはClaude Code上のsuperpowersと独自TDD Skillsが制御する。Codexはワークフローの工程を担当せず、人間またはClaude Codeから依頼された範囲で、レビューと助言を行う。

プロジェクト概要、アーキテクチャ、コマンドは[`CLAUDE.md`](CLAUDE.md)を、開発・TDDの契約は[`docs/TDD-WORKFLOW.md`](docs/TDD-WORKFLOW.md)を参照する。レビューの判断基準として、次も参照する。

- [最小TDDにおけるテスト作成原則](docs/MINIMUM-TDD-TEST-PRINCIPLES.md)
- [中心的契約選定フロー](docs/CORE-CONTRACT-SELECTION.md)
- 対象機能の仕様、論理テストケース、TDD計画、実装計画、実装後テストレポート（`docs/superpowers/`、または購入物登録は`docs/specs/`）

## 行うこと

- 仕様、論理テストケース、中心的契約、TDD計画、実装計画のレビュー（曖昧さ、矛盾、不足、トレーサビリティ、過不足）
- 差分・Pull Requestのコードレビュー（仕様との整合、テストの妥当性、凍結済みTDDテストの変更有無、セキュリティ、回帰、残存リスク）
- 設計、テスト方針、不具合の原因調査についての助言
- 読み取り専用の調査と、確認のためのテスト・lint・環境検証コマンドの実行

## 行わないこと

- superpowersのワークフロー（brainstorming、writing-plans、subagent-driven-developmentなど）や独自TDD Skillsの実行
- 仕様、論理テストケース、TDD計画、テストコード、プロダクトコード、環境コードの変更、コミット、push、Pull Requestの作成・マージ（人間が明示的に依頼した場合を除く）
- Gateの承認、承認の記録、仕様にない期待結果の確定。これらは人間の判断である

## 指摘の書き方

各指摘に次を含める。

- 重要度: Blocking / Important / Minor
- 分類と戻り先: 仕様 / 論理テストケース・TDD計画 / テスト / 実装 / テスト容易性 / 環境
- 根拠: 該当する仕様ID、Test Case ID、`path:line`
- 推奨する対応（修正そのものではなく、何をどう直すべきか）

実装の現在の挙動を期待結果の根拠にしない。仕様から期待結果を一意に導けない場合は、仕様確認が必要な事項として指摘する。
