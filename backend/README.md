# Backend

FastAPI + DynamoDB（boto3経由）で構築する購入リマインダーAPI。

## ディレクトリ構成

```
app/
├── api/            # HTTP層：ルーティングと入出力の定義のみ
│   ├── deps.py         # 共通Depends（認証ユーザー取得など）
│   ├── purchase.py     # /purchases 系のFastAPIルーター
│   └── schemas/         # リクエスト/レスポンスのPydanticモデル（API契約）
│       └── purchase.py
├── services/       # ユースケース層：domainとmodelsを組み合わせて処理のパイプラインを組み立てる
│   ├── purchase_service.py
│   └── notification_service.py
├── domain/         # コアビジネスロジック（FastAPI/boto3に依存しない純粋なPython）
│   ├── purchase.py     # Purchaseエンティティ、消費速度・在庫から補充タイミングを計算するロジック
│   └── exception.py    # ドメイン例外
├── models/         # 永続化層：DynamoDBアイテムのスキーマとアクセス処理
│   └── purchase.py
├── auth/           # Cognito JWT検証など認証関連の処理
│   └── cognito.py
├── utils/          # ドメインに依存しない汎用ヘルパー
└── core/           # 設定・共通初期化（環境変数、boto3クライアントなど）
    └── config.py
```

## 各層の責務と依存の向き

依存は `api → services → domain / models` の一方向。逆方向の依存（domainがapiやservicesを知る、など）は作らない。

- **api**: HTTPのリクエスト/レスポンスの入出力のみを扱う。ビジネスロジックは書かず、servicesの呼び出しに徹する
- **services**: 1ユースケース＝1関数を目安に処理のパイプラインを組み立てるオーケストレーション層。domainのロジックとmodelsの永続化を呼び出して繋ぐだけで、自身はビジネスルールを持たない
- **domain**: 「消費速度と在庫から購入タイミングを計算する」といった核心のビジネスルールとエンティティ。フレームワークやDBを一切知らないため、単体テストが書きやすい
- **models**: DynamoDBのテーブル定義・読み書きに専念する永続化層。domainのエンティティとDBアイテムの変換もここで行う
- **auth**: Cognitoトークンの検証など認証まわり。apiのDependsとして横断的に利用される
- **utils**: ドメイン知識を含まない汎用処理のみを置く（何でも置き場にしない）
- **core**: 設定値やクライアントの初期化を集約し、他層が直接環境変数やboto3クライアントを扱わずに済むようにする

## テスト構成

```
tests/
├── unit/         # domain / services を中心にモックでテスト
└── integration/  # DynamoDB Localなどを使ったmodels層・API結合テスト
```

フロントエンドを含むE2E（ブラウザ経由の結合テスト）はPlaywrightで行い、リポジトリ直下の`e2e/`に置く。
