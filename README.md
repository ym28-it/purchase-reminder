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

### 利用形態

- 利用者は自分一人のみ。仕事帰りの買い物で買い忘れを防ぐことが目的
- 通知と購入報告はLINEで行う。Webアプリとしても使えるようにし、PCのブラウザからも開ける
- メール通知は使わない

### 通知・認証の方針（採用済み・未実装）

- **通知**: EventBridge Schedulerを平日夕方（例: 16:30）に起動し、Lambdaが「次の買い物までに切れるもの」を計算してLINE Messaging APIでpushする。1日1通のまとめ通知とする
- **購入報告**: 通知メッセージのボタン（postback）を押すとLINE WebhookからAPI Gateway経由でLambdaが在庫を更新する。Webhookは署名検証と二重押し対策（冪等性）を行う。デフォルト数量以外はWebアプリで修正する
- **Webアプリ**: 既存のReact画面をLIFFアプリとして使う。LINE内ブラウザでもPC・スマホの通常ブラウザでも開け、未ログイン時は`liff.login()`でLINEログインする
- **認証**: CognitoではなくLINE Login（LIFFのIDトークン）を使う。バックエンドでIDトークンを検証し、自分のLINE userIdだけを許可する。通知先と認証の識別子が同じuserIdになる
- **補充タイミングの判定**: 在庫が尽きる日ではなく、次の買い物までに切れるかで判定する。在庫は「最終更新時の在庫 − 消費スピード × 経過日数」で自動計算し、利用者の操作は「買った」の報告を基本とする
- PWA / Web Pushは採用しない（iOSで通知アクションが使えず、購入報告をアプリ内で行う必要があるため）
- 実装は垂直スライスで進める: ①購入タイミングのドメインロジック ②LINE通知と購入報告 ③LINE Login（LIFF）認証への切り替え
- LIFFの通常ブラウザでの動作とLINEの無料メッセージ枠は、仕様作成時に公式ドキュメントで確認する

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
- EventBridge Scheduler
  定期通知の起動
- LINE Messaging API / LINE Login（LIFF）
  通知、購入報告、認証（AWS外のサービス）
- Route53 / ACM（任意）
  独自ドメインを使う場合のみ。CloudFrontの標準URLでもLIFFは動く想定

### Tech Stack

- Python: FastAPI
- uv
- TypeScript: React
- bun
- DynamoDB

## 実装上の挑戦

1. LINE Login（LIFFのIDトークン）によるバックエンド認証とLINE Webhookの署名検証
2. Terraformを最初から使う
3. テスト自動化（E2E、統合テストなど）＋テスト基盤構築
4. CI/CDパイプライン構築
5. 型の連動
  バックエンド：DBスキーマからAPIエンドポイントまでの連動
  フロントエンド：バックエンドのOpenAPIからエンドポイントのレスポンススキーマ生成（できれば）

## 環境構築

デプロイはコンテナイメージで行う。そのため、バックエンドの開発環境はDockerコンテナで管理する。

Environment Gateは、POSIXシェルを持つLinux（WSL2を含む）またはmacOSで実行する。WindowsネイティブのPowerShell / `cmd.exe`は対象外とし、WindowsではWSL2内で実行する。コミット済みの`bin/mise`がmise 2026.9.12を`mise.jdx.dev`から取得してSHA-256を検証し、リポジトリ内の`.mise/`へ配置する。miseはuv 0.12.18とTemurin Java 17を導入し、uvは`.python-version`で固定したPython 3.14.7を`.mise/uv-python/`へ導入するため、system側のmise、Python、Javaには依存しない。

```bash
# Linux / WSL2 / macOSで実行する（miseの事前導入は不要）
bash scripts/setup_host_prerequisites.sh --install
bash scripts/setup_host_prerequisites.sh --check
```

以降のEnvironment Gateコマンドは`./bin/mise exec --`（`backend/`からは`../bin/mise exec --`）経由で実行し、`UV_MANAGED_PYTHON=1`、リポジトリローカルのPython格納先、選択済みの`PATH`と`JAVA_HOME`を引き継ぐ。`mise exec`による未導入ツールの自動取得は無効化している。`--install`はuvとJavaを`mise install --jobs=1`で逐次導入した後、uvでPython 3.14.7を導入する。`--check`はネットワーク取得を行わず、uv管理Pythonだけを検証する。OS別package manager、system Python、グローバルJava/Mavenには依存しない。Mavenは固定Maven Wrapperを使うためmiseにもグローバルにも導入しない。mise自体を更新する場合は、別バージョンを実行時指定せず、新しい固定バージョンとchecksumを含む`bin/mise`を再生成して専用PRで検証する。

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
認証はLINE Loginに接続する（LIFF導入までは`dev-user`固定の仮実装）

### 本番環境

フロントエンドはビルドしたコードをS3にCDで自動デプロイ
デプロイ時にCloudFrontのキャッシュ無効化（invalidation）を実行
バックエンドはコンテナイメージをビルドしてECRにpush
LambdaがECRイメージを参照してデプロイ
シークレット・環境変数はSSM Parameter Storeで管理
インフラはTerraform管理
