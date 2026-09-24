# 買い物リマインダー

## 解決したい問題

買い物をするときに

- 何を
- いつ
- どれくらい
買うのかを忘れてしまう

## 概要

定期的に購入するものを消費頻度と現在の在庫を登録する

消費しきる前に購入するタイミングを通知する

通知では、

- 何を
- どれくらい
買うのかを通知する

また、買い物計画を確認できるようにする

加えて、在庫の修正や消費頻度の修正ができるようにする

## 設計

### データベース

purchase

- UUID
ID
- name
買うものの名前
- category
カテゴリ
- speed
消費スピード
- stock
在庫
- is_temporary
  定期購入しないもの

### インフラ

AWS

- S3+CloudFront
  静的コンテンツ配信
- API Gateway
  リクエストの受付
- Lambda
  バックエンド(LWA)
- ECR
  バックエンドのビルドイメージ管理
- DynamoDB
  DB
- Cognito
  認証
- Route53
  DNSとドメイン
- ACM
  証明書発行

### Tech Stack

- Python: FastAPI
- uv
- TypeScript: React
- bun
- DynamoDB

## 実装上の挑戦

1. CognitoによるJWT認証
2. Terraformを最初から使う
3. テスト自動化（E2E、統合テストなど）＋テスト基盤構築
4. CI/CDパイプライン構築
5. 型の連動
  バックエンド：DBスキーマからAPIエンドポイントまでの連動
  フロントエンド：バックエンドのOpenAPIからエンドポイントのレスポンススキーマ生成（できれば）

## 環境構築

デプロイはコンテナイメージで行う。そのため、バックエンドの開発環境はDockerコンテナで管理する。

Environment Gateは、POSIXシェルを持つLinux（WSL2を含む）またはmacOSで実行する。WindowsネイティブのPowerShell / `cmd.exe`は対象外とし、WindowsではWSL2内で実行する。コミット済みの`bin/mise`がmise 2026.9.12を`mise.jdx.dev`から取得してSHA-256を検証し、リポジトリ内の`.mise/`へ配置する。Python 3.14.7、uv 0.12.18、Temurin Java 17はルートの`mise.toml`から導入するため、system側のmise、Python、Javaには依存しない。

```bash
# Linux / WSL2 / macOSで実行する（miseの事前導入は不要）
bash scripts/setup_host_prerequisites.sh --install
bash scripts/setup_host_prerequisites.sh --check
```

以降のEnvironment Gateコマンドは`./bin/mise exec --`（`backend/`からは`../bin/mise exec --`）経由で実行し、選択済みの`PATH`と`JAVA_HOME`を引き継ぐ。`mise exec`による未導入ツールの自動取得は無効化しており、`--install`が明示したPython、uv、Java以外をEnvironment Gate中に導入しない。これら3ツールはクラウド環境での同時展開を避けるため`mise install --jobs=1`で逐次導入する。OS別package manager、system Python、グローバルJava/Mavenには依存しない。Mavenは固定Maven Wrapperを使うためmiseにもグローバルにも導入しない。mise自体を更新する場合は、別バージョンを実行時指定せず、新しい固定バージョンとchecksumを含む`bin/mise`を再生成して専用PRで検証する。

### 開発環境

- フロントエンド
bunを使用する
Vite + React
ローカル直起動
CORS許可設定
Biomeをリンタ・フォーマッターとして利用

- バックエンド
Docker Composeで管理
Dockerfileはdev/本番でマルチステージ分割
boto3利用
Pydanticによるスキーマ定義
ローカルのコードをコンテナにマウントして利用
ローカルのコードが正
DynamoDB LocalをCompose上に追加し、実AWSに触れない
認証は実際のCognito User Poolに接続する

### 本番環境

フロントエンドはビルドしたコードをS3にCDで自動デプロイ
デプロイ時にCloudFrontのキャッシュ無効化（invalidation）を実行
バックエンドはコンテナイメージをビルドしてECRにpush
LambdaがECRイメージを参照してデプロイ
シークレット・環境変数はSSM Parameter Storeで管理
インフラはTerraform管理
