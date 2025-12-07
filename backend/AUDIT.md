 # 監査スキーマ（`item_audit`）

目的
- `items` に関連する不変の監査イベント（作成・更新・削除など）を保存します。
- 柔軟性のためにイベントの生ペイロードを `payload`（JSONB）に保持しつつ、頻繁にクエリされるフィールドは型付きカラムとして昇格させ、インデックスや検索を高速化します。

テーブル: `item_audit`
- `id` (integer, PK)
- `item_id` (integer, nullable): 関連する `items.id`（該当する場合）
- `action` (string): 例: `create`, `update`, `delete`
- `payload` (JSON/JSONB): イベントのフルペイロード（元データとメタデータ）
- `created_at` (timestamp with timezone): イベント発生時刻（デフォルト `now()`）
- `user_id` (string, nullable): 操作者の識別子（インデックス用に `payload` から昇格）
- `ip` (string, nullable): クライアント IP（`payload` から昇格）
- `method` (string, nullable): HTTP メソッド（`payload` から昇格）
- `user_agent` (text, nullable): User-Agent ヘッダ（利便性のためにカラム化）
- `request_path` (string, nullable): リクエストパス

マイグレーションで作成するインデックス
- `ix_item_audit_user_id` (`user_id`)
- `ix_item_audit_ip` (`ip`)
- `ix_item_audit_method` (`method`)
- `ix_item_audit_created_at` (`created_at`)

なぜフィールドをカラム化するのか
- JSONB は柔軟ですがインデックスや検索が遅くなりがちです。`user_id`、`ip`、`method`、時間範囲など、頻繁にフィルタ／集計されるフィールドは型付きカラムにしておくと、クエリ性能とインデックス効率が向上します。

クエリ例

- ユーザの最近の監査イベントを取得:
```sql
SELECT * FROM item_audit
WHERE user_id = '42'
ORDER BY created_at DESC
LIMIT 50;
```

- 過去24時間の IP ごとの作成数カウント:
```sql
SELECT ip, count(*)
FROM item_audit
WHERE action = 'create'
  AND created_at >= now() - interval '24 hours'
GROUP BY ip
ORDER BY count DESC
LIMIT 50;
```

- `/items` への POST リクエストを抽出:
```sql
SELECT id, item_id, payload, created_at
FROM item_audit
WHERE request_path = '/items' AND method = 'POST'
ORDER BY created_at DESC
LIMIT 100;
```

- デバッグ用に JSON 中身を調べる:
```sql
SELECT payload->>'name' AS name, payload->>'user_id' AS user_id, created_at
FROM item_audit
WHERE action = 'create'
ORDER BY created_at DESC
LIMIT 100;
```

運用メモ
- バックフィル: マイグレーションで型付きカラムを追加しただけでは既存レコードは更新されません。履歴データが必要なら `payload` から新しいカラムへコピーするバックフィルを計画してください。軽微なデータセットなら一括 UPDATE で済みますが、大量データの場合はバッチ処理を推奨します。
- ストレージ: `user_agent` は長い値が入る可能性があるため `text` 型にしていますが、ストレージ増加に注意してください。
- インデックス: 実際のクエリパターンに基づきインデックスを選んでください。過剰なインデックスは書き込みコストを増やします。

セキュリティ & 本番運用の指針
- 本番ではクライアント任意のヘッダ（例: `X-User-Id`）を信頼して `user_id` を決めないでください。認証基盤（OAuth/OIDC/JWT や社内 SSO）と連携し、検証済みトークンやセッションから `user_id` を取得してください。
- `payload` に機密情報や個人情報（PII）を保存する場合は、保存前にマスキング・サニタイズするか、暗号化ポリシーを検討してください。
- 監査の書き込み量が多くなる場合はレート制御や専用の監査パイプライン（キューやバッチ処理）を検討してください。

次のステップ
- 既存レコードのバックフィルが必要なら、私がバックフィル用の Alembic マイグレーション（安全なトランザクション・バッチ処理）を作成できます。
- `user_id` を整数にして `users` テーブルとの外部キー制約を追加する場合は、追加マイグレーションとアプリ側の変更が必要です。

必要なら、バックフィルの実行手順やテスト手順も作成します。
