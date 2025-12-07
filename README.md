# FastAPI + Next.js サンプルプロジェクト

このリポジトリは、FastAPI バックエンド（Postgres）と Next.js フロントエンドを Docker Compose で動かすサンプル構成です。

**主要機能**
- FastAPI バックエンド（`backend/`）
- Next.js フロントエンド（`frontend/`）
- PostgreSQL データベース（Compose ボリュームで永続化）
- 起動時にバックアップからの復元と Alembic マイグレーション自動適用
- リクエストのバリデーションと禁止語フィルタ（ミドルウェア）
- スタートアップログと uvicorn ログの簡易ローテーション（entrypoint に実装）

## 開発・起動方法
Docker と Docker Compose がインストールされている環境で以下を実行します。

PowerShell の例:
```powershell
# イメージをビルドしてバックエンドを起動
docker compose -f .\compose.yaml build backend
docker compose -f .\compose.yaml up -d

# ログを確認する
docker compose -f .\compose.yaml logs -f backend
```

フロントエンドは `http://localhost:3000`、バックエンドは `http://localhost:8000` で公開されます（`compose.yaml` のポート設定による）。

## バックアップと復元
- `db/backups/latest.sql` をコンテナの `/backups/latest.sql` にマウントしておくと、コンテナ起動時に DB に `alembic_version` テーブルが無ければ復元が試行されます。
- フルダンプの復元はデータの状態によって失敗することがあるため、部分復元（特定テーブルのみ）やダンプの事前クリーンアップを推奨します。

## マイグレーション
- Alembic を使用しています。エントリポイントで `alembic stamp head` → `alembic upgrade head` を実行して DB を最新化します。

## ログ回転（重要）
バックエンドの `entrypoint.sh` により、`/app/logs`（ホストでは `backend/logs`）内の `*.log` ファイルを対象に簡易ローテーションを行います。

- 回転対象のファイル例: `startup.log`, `uvicorn.log`。
- 回転ファイルは gzip 圧縮され、`<basename>-YYYYmmddTHHMMSSZ.log.gz` の形式で保存されます。

設定は `compose.yaml` の `backend` サービスで環境変数として変更できます:
- `STARTUP_ROTATE_MAX_BYTES` — 回転閾値（バイト、デフォルト `5242880` = 5MB）
- `STARTUP_ROTATE_KEEP` — 保存するアーカイブ数（デフォルト `7`）
- `STARTUP_ROTATE_INTERVAL` — 回転チェック間隔（秒、デフォルト `300`）

uvicorn の stdout/stderr は `compose.yaml` の `command` で `/app/logs/uvicorn.log` にリダイレクトされるように設定してあるため、entrypoint の回転で扱われます。

### 簡易テスト
ルートから次のスクリプトで回転確認ができます（ホストに Python が必要）:

```powershell
python .\tools\test_rotation.py
```

テストは `startup.log` と `uvicorn.log` を大きくして `backend` を再起動し、回転済みの `.log.gz` ファイルが生成されるか確認します。

## 追加メモ / 運用上の注意
- 現在のローテーションはシンプルな実装です。本番では `logrotate`、専用のログドライバ（例: Docker `json-file` の `max-size`/`max-file`）やログ集約サービス（Fluentd/Vector/Logstash → S3/Elasticsearch）を検討してください。
- 環境変数は `compose.yaml` にインラインで記載されていますが、機密情報は環境変数管理（Vault / Docker secrets / Kubernetes secrets 等）を使ってください。

---
この README は `README-rotation.md` の内容を統合したものです。さらに詳しい運用手順や PR を希望する場合は指示してください。
