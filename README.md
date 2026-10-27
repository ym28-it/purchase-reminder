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
- LINEは通知と購入報告の受け皿として使う。買い物計画の確認や在庫・消費スピードの修正はWebアプリ（PC・スマホのブラウザ）で行う
- メール通知は使わない

### 通知・認証の方針（採用済み・未実装）

- **通知**: EventBridge Schedulerを平日夕方（例: 16:30）に起動し、Lambdaが「次の買い物までに切れるもの」を計算してLINE Messaging APIでpushする。1日1通のまとめ通知とする
- **購入報告**: 通知メッセージのボタン（postback）を押すとLINE WebhookからAPI Gateway経由でLambdaが在庫を更新する。品目ごとに次の2通りを用意する
  - 「買った」: デフォルト数量で購入を報告する（1タップで完了）
  - 「数量を指定して買った」: 押すとreplyで数量ボタン（クイックリプライ）を返し、選んだ数量で購入を報告する
  - postbackの`data`に品目ID・数量・通知IDを含め、サーバー側で会話の状態を持たない。返事はreplyで返し、無料メッセージの通数を消費しない
  - Webhookは`x-line-signature`の署名検証と二重押し・再送対策（冪等性）を行う。数量ボタンにない数量や在庫・消費スピードの修正はWebアプリで行う
- **LINE側の本人確認**: Webhookの送信者（LINE userId）が登録済みの自分のuserIdであることを確認する。通知先のuserIdとチャネルの秘密情報はSSM Parameter Storeで管理する。利用者が一人のため、CognitoユーザーとLINE userIdの紐づけ機能は作らず設定値で固定する
- **Webアプリの認証**: Cognito User Pool（マネージドログイン）でログインし、バックエンドはCognitoのJWTを検証する。LINEログイン（LIFF）は使わない
- **補充タイミングの判定**: 在庫が尽きる日ではなく、次の買い物までに切れるかで判定する。在庫は「最終更新時の在庫 − 消費スピード × 経過日数」で自動計算し、利用者の操作は「買った」の報告を基本とする
- PWA / Web Pushは採用しない（iOSで通知アクションが使えず、購入報告をアプリ内で行う必要があるため）
- 実装は垂直スライスで進める: ①購入タイミングのドメインロジック ②LINE通知と購入報告 ③Cognito認証（`dev-user`固定の仮実装からの置き換え）
- LINE Messaging APIの調査結果は[docs/research/line-messaging-api.md](docs/research/line-messaging-api.md)にまとめる。仕様作成時に公式ドキュメントで最新の内容を再確認する

### 将来の認証方式（学習目的を含む）

Cognitoで動かした後、学習を兼ねて次の方式を順に検討する。いずれも採用前に仕様化し、Cognito認証を壊さない形で追加する。

- **OAuth 2.0 / OpenID Connect**: CognitoにGoogleなどの外部IdPをフェデレーションし、認可コードフロー＋PKCEの流れを理解する
- **パスキー（WebAuthn）**: Cognitoのパスキー対応を使うか、`py_webauthn`などで登録・認証フローを自前実装して仕組みを学ぶ
- **LINEログイン**: 通知と同じLINEアカウントでログインする方式。LIFFとIDトークン検証を試す

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
  Webアプリの認証
- EventBridge Scheduler
  定期通知の起動
- Route53
  DNSとドメイン
- ACM
  証明書発行

AWS外

- LINE Messaging API
  通知と購入報告（Webhook）

### Tech Stack

- Python: FastAPI
- uv
- TypeScript: React
- bun
- DynamoDB

## 実装上の挑戦

1. CognitoによるJWT認証とLINE Webhookの署名検証
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
認証は実際のCognito User Poolに接続する（導入までは`dev-user`固定の仮実装）

### 本番環境

フロントエンドはビルドしたコードをS3にCDで自動デプロイ
デプロイ時にCloudFrontのキャッシュ無効化（invalidation）を実行
バックエンドはコンテナイメージをビルドしてECRにpush
LambdaがECRイメージを参照してデプロイ
シークレット・環境変数はSSM Parameter Storeで管理
インフラはTerraform管理
