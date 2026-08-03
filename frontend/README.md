# Frontend

React + TypeScript + Vite。Biomeをlinter/formatterとして使用。

## ディレクトリ構成

```
src/
├── api/          # バックエンドへのHTTPクライアント（fetchラッパー、エンドポイント別関数、レスポンス型）
├── components/   # 特定の画面・機能に依存しない再利用可能なUIパーツ
├── features/     # 画面・機能単位のまとまり（例: 購入一覧、購入登録フォーム）
├── hooks/        # カスタムフック（状態管理やAPI呼び出しのラップ）
├── assets/       # 画像・アイコンなどの静的アセット
├── App.tsx
└── main.tsx
```

## 各ディレクトリの責務

- **api**: バックエンドAPIへの通信のみを担当。UIロジックは含めない
- **components**: ボタンやカードのような、特定の画面・機能に依存しない汎用UIパーツ
- **features**: 画面・機能単位でまとまったコンポーネント。componentsやapi、hooksを組み合わせて画面を構成する
- **hooks**: 状態管理やAPI呼び出しをラップするカスタムフック（例: usePurchases）
- **assets**: 画像・アイコンなどの静的ファイル
