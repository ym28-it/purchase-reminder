# E2E

Playwrightによるフルスタックのエンドツーエンドテスト。

frontend（ブラウザで操作する対象）とbackend（実際のAPI）の両方を起動した状態で、ユーザー操作を通してシステム全体の振る舞いを検証する。単体のPythonプロセスやfetchモックでは検証できない、画面操作からDB更新までの一連の流れを対象とする。

そのため`backend/`や`frontend/`の配下ではなく、リポジトリ直下に独立したディレクトリとして置いている。

## テストケースの作り方（Playwright MCP）

テストケースはソースコードだけを読んで推測で書くのではなく、Playwright MCPを使ってAI（Claude Code）が実際にアプリをブラウザ操作しながら生成する。

理由: このリポジトリのフロントエンドは実装がまだ薄く、DOM構造やセレクタ、画面遷移が固まっていない。実際に動かして確認しながら書かないと、存在しない要素を前提にした壊れたテストになりやすい。

### 前提

- `.mise.toml`で管理されているnode/bunが使える状態（`mise install`済み）
- `docker-compose up`でfrontend/backend/DynamoDB Localを起動できる状態
- 認証は[環境構築](../README.md#開発環境)の方針どおり実際のCognito User Poolに接続するため、ローカルでテストを操作する際もテスト用ユーザーの認証情報が必要（本番User Poolとは別に用意する）

### セットアップ手順

1. Playwright MCPサーバーをClaude Codeに登録する（プロジェクトスコープ、リポジトリ直下で実行）

   ```sh
   claude mcp add playwright npx @playwright/mcp@latest
   ```

   `.mcp.json`がリポジトリ直下に生成される。チームで共有する設定なのでコミットする。

2. Claude Code内で`/mcp`を実行し、`playwright`が接続済みであることを確認する

3. アプリを起動する

   ```sh
   docker-compose up
   ```

   frontendはローカル直起動の方針のため、別途`frontend/`で`bun run dev`も実行する（詳細は[frontend/README.md](../frontend/README.md)）

4. Claude Codeに対して「〇〇の画面を操作してテストケースを書いて」のように依頼する。Claude CodeがPlaywright MCP経由で実際にブラウザを開き、画面遷移・要素の状態・APIレスポンスを確認しながら、Playwrightのテストコード（`.spec.ts`）をこのディレクトリ配下に生成する

### 生成後のテスト実行

MCP経由の操作はテストケースを「書く」ための手段であり、生成された`.spec.ts`自体は通常の`@playwright/test`で実行する。実行用のセットアップ（`package.json`、設定ファイルなど）は別途このディレクトリに追加する。
