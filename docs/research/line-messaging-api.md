# LINE Messaging API 調査メモ

調査日: 2026-10-26。LINE公式ドキュメントへ直接アクセスできなかったため、Web検索の結果（公式ページの抜粋を含む）から整理した。仕様作成時に各リンク先の最新内容を再確認すること。

## 本アプリへの当てはめ（見積もり）

- 通知は平日1日1通のまとめpushとする方針なので、月に約22通となる。無料のコミュニケーションプラン（月200通まで）に収まる
- 購入報告ボタン（postback）への応答はreplyメッセージで返せば通数に数えない。pushで返すと通数に数える
- Webhookの送信元IPは公開されていないため、IP制限ではなく署名検証で真正性を確認する

## 確認できたこと

### チャネルの作成

- Messaging APIのチャネルは、LINE公式アカウントを作成し、LINE Official Account Managerの「設定 > Messaging API」で有効化して作る
- LINE公式アカウントを削除すると、紐づくMessaging APIチャネルも削除される

### 料金（日本）

- コミュニケーションプラン: 月額無料で、無料メッセージは月200通まで。上限を超えると送信がエラーになり、メッセージは送られない
- ライトプラン: 月額5,000円（税別）で、月5,000通まで
- スタンダードプラン: 月30,000通まで。超過分は1通最大3円
- 通数は受信者数で数える。1回のリクエストに複数のメッセージオブジェクトを含めても、通数は変わらない
- replyメッセージは通数に含めない。pushメッセージは含める
- ブロックしている、または存在しないuserIdへの送信は数えない

### Webhookの署名検証

- LINEプラットフォームは、リクエストボディをチャネルシークレットでHMAC-SHA256署名し、`x-line-signature`ヘッダーで送る
- サーバーは受け取った生のボディ（パース後に再シリアライズしたものではない）から同じ値を計算して比較する
- 送信元IPは公開されていないため、IPの許可リストには頼れない

### 再送と重複

- イベントには`webhookEventId`と`deliveryContext.isRedelivery`がある
- 処理済みの`webhookEventId`を保存してスキップする方法が考えられる。ただし、再送時にIDが変わらないことを明言した公式記述は見つかっていない。仕様作成時にWebhookイベントのリファレンスで確認する
- 利用者による二重押しは別のイベントになるため、postbackの`data`に通知ID等を含め、在庫更新側で冪等にする必要がある

### postbackアクション

- `data`: 最大300文字。postbackイベントの`postback.data`としてWebhookに届く
- `displayText`: 最大300文字。押したときに利用者の発言としてトークに表示される
- `label`: 最大20文字（画像カルーセルでは12文字）
- 文字数は書記素クラスタ単位で数える

### チャネルアクセストークン

- v2.1: JWT（RS256、RSA 2048bit鍵）で発行する。有効期間は30日で、1チャネルあたり30個まで発行できる
- ステートレス: 有効期間は15分で、発行数の上限はない。発行後に取り消せない
- どちらを推奨するかの公式記述は見つかっていない。Lambdaからの1日1回の送信であれば、どちらでも運用できる見込み

## 未確認（仕様作成時に確認する）

- replyトークンの有効期間
- 自分のuserIdの取得方法（LINE Developersコンソールの表示、またはfollowイベントから取得）
- 長期のチャネルアクセストークンを使い続けてよいか、使うべきか
- 購入報告の2通りのボタンに関わる上限: ボタンテンプレートのアクション数（4つまでと想定）、クイックリプライの選択肢数（13個までと想定）、1通のFlex Messageに載せられる品目数
- Webhookに応答を返す期限と、失敗時の再送条件（再送設定の有無）

## 出典

- [Messaging APIの料金](https://developers.line.biz/ja/docs/messaging-api/pricing/)
- [How message counts are calculated in the Messaging API](https://developers.line.biz/en/tips/2026/05/28/how-to-count-messages/)
- [Messaging APIを始めよう](https://developers.line.biz/ja/docs/messaging-api/getting-started/)
- [Receive messages (webhook)](https://developers.line.biz/en/docs/messaging-api/receiving-messages/)
- [Verify webhook signature](https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/)
- [Actions](https://developers.line.biz/en/docs/messaging-api/actions/)
- [Channel access token](https://developers.line.biz/en/docs/basics/channel-access-token/)
- [Issue channel access token v2.1](https://developers.line.biz/en/docs/messaging-api/generate-json-web-token/)
- [LINE Messaging APIのテンプレートメッセージをまとめてみる（アクションオブジェクト編）](https://dev.classmethod.jp/articles/line-messaging-api-action-object/)
- [LINE公式アカウントの料金プラン（LINEヤフー for Business）](https://www.lycbiz.com/jp/column/line-official-account/technique/20200204/)
