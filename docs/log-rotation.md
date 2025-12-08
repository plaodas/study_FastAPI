# ログ回転（詳細）

このドキュメントは `entrypoint.sh` に実装された簡易ログ回転の挙動と運用上の注意、及びローカルでの簡易テスト手順をまとめています。

概要
- 対象: コンテナ内の `/app/logs/*.log`（ホストの `backend/logs` にマウントされる想定）。
- 動作: サイズやインターバルでログをスナップし、gzip 圧縮してタイムスタンプ付きファイルとして保存します。

環境変数
- `STARTUP_ROTATE_MAX_BYTES` — 回転閾値（バイト、デフォルト `5242880` = 5MB）
- `STARTUP_ROTATE_KEEP` — 保存するアーカイブ数（デフォルト `7`）
- `STARTUP_ROTATE_INTERVAL` — 回転チェック間隔（秒、デフォルト `300`）

簡易テスト
- 事前: ホストに Python がインストールされていること
- ルートから次を実行してログを大きく生成し、backend を再起動して回転が行われるか確認します。

```powershell
python .\tools\test_rotation.py
docker compose -f .\compose.yaml restart backend
docker compose -f .\compose.yaml exec backend ls -la /app/logs
```

運用上の注意
- 本番では専用ツール（`logrotate`、Docker ログドライバ、ログ集約）を推奨します。  
- ローテーション対象の stdout リダイレクトなどは Compose 設定に依存するため、ログ出力先が `/app/logs` になっていることを確認してください。

トラブルシュート
- 回転が期待通り動かない場合は、`backend/logs` のパーミッションと所有権、及び `entrypoint.sh` の実行ログを確認してください。
