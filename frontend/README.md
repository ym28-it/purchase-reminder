# Frontend

React + TypeScript + Vite。Biomeをlinter/formatterとして使用。

## Tech Stack

- **フレームワーク**: React + TypeScript + Vite（bunで管理）
- **Lint/Format**: Biome
- **APIクライアント**: fetch + [TanStack Query](https://tanstack.com/query) + [openapi-fetch](https://openapi-ts.dev/openapi-fetch/)
  - backendのOpenAPIスキーマから型を生成し、`api/`層で利用する（型の連動については[CLAUDE.md](../CLAUDE.md)参照）
  - 型生成は[openapi-typescript](https://openapi-ts.dev/)を使用。起動中のdevサーバー（`http://localhost:8000/openapi.json`）から`bun run gen:api`で手動生成し、生成ファイルはgitにコミットする。生成漏れ対策（CIでの差分チェックなど）は運用に慣れてから導入する
- **ルーティング**: [TanStack Router](https://tanstack.com/router)
  - TanStack Queryと同エコシステムで、ルートパラメータ/検索パラメータまで型推論されるタイプセーフなルーティングを採用
- **UI**: [shadcn/ui](https://ui.shadcn.com/) + [Radix](https://www.radix-ui.com/) + [Tailwind CSS](https://tailwindcss.com/)
- **フォーム/バリデーション**: [react-hook-form](https://react-hook-form.com/) + [zod](https://zod.dev/)
  - Zodスキーマは学習目的もあり手書きする。役割はフォーム入力のバリデーションに限定し、APIレスポンスの型は（Zodでパースせず）openapi-fetch経由の生成型をそのまま使う。Pydantic（backend）とのスキーマ定義の重複がフォーム以外に広がらないようにするための切り分け
- **テスト**: [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/react)
- **認証**: [oidc-client-ts](https://github.com/authts/oidc-client-ts)（+ [react-oidc-context](https://github.com/authts/react-oidc-context)）
  - CognitoのHosted UIをOIDCプロバイダとして扱い、Authorization Code + PKCEフローで認証する。AWS専用のAmplifyではなく標準的なOIDCクライアントを採用し、OAuth/OIDCの流れそのものを理解する学習目的を優先
  - トークンはSPA側（メモリ/ブラウザストレージ）で保持する方針。BFF（メモリ保持のアクセストークン＋httpOnly Cookieでのリフレッシュトークン管理）はセキュリティ上より堅牢だが、セッション管理用のストアやCookieのドメイン設計、CSRF対策など追加インフラが必要になり、README記載の「静的配信＋ステートレスLambda」構成には過剰なため見送り

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
