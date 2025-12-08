# 監査ログのバックフィル（item_audit）

このファイルは `README.md` の監査関連の詳細（バックフィル用 SQL 等）を収録しています。

目的
- 既存の `item_audit` レコードで typed カラム（`user_id`, `ip`, `method`, `user_agent`, `request_path`）が NULL の場合、`payload` 内の値をコピーして埋めるための安全な手順を示します。

手順（例）

1. DB コンテナに入る

```powershell
docker compose -f .\compose.yaml exec -T db bash
psql -U user -d appdb
```

2. 安全なバックフィル SQL

```sql
UPDATE item_audit SET
    user_id = COALESCE(user_id, payload ->> 'user_id'),
    ip = COALESCE(ip, payload ->> 'ip'),
    method = COALESCE(method, payload ->> 'method'),
    user_agent = COALESCE(user_agent, payload ->> 'user_agent'),
    request_path = COALESCE(request_path, payload ->> 'request_path')
WHERE payload IS NOT NULL
  AND (user_id IS NULL OR ip IS NULL OR method IS NULL OR user_agent IS NULL OR request_path IS NULL);

-- 変更結果を確認
SELECT id, item_id, payload::text, user_id, ip, method, request_path FROM item_audit WHERE id = <対象ID>;
```

注意
- 大規模な更新を行う場合はトランザクションとバッチ処理を検討してください（例: LIMIT/OFFSET や cursor ベースで分割して実行）。
- 本番環境で実行する前に必ずバックアップを取得してください。
