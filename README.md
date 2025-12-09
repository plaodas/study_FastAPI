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
# FastAPI + Next.js サンプルプロジェクト

このリポジトリは FastAPI バックエンド（Postgres）と Next.js フロントエンドを Docker Compose で動かすサンプル構成です。バックエンドは `backend/`、フロントエンドは `frontend/` にあります。

**主要機能**
- FastAPI バックエンド（`backend/`）
- Next.js フロントエンド（`frontend/`）
- PostgreSQL（Compose ボリュームで永続化）
- 起動時のバックアップ復元と Alembic マイグレーション自動適用
- リクエストバリデーション・禁止語フィルタ（ミドルウェア）
- 簡易ログ回転（`entrypoint.sh`）

## クイックスタート
Docker と Docker Compose がある環境でルートから:

- ビルド・起動（PowerShell の例）:
```
docker compose -f .\compose.yaml build backend
docker compose -f .\compose.yaml up -d
```

- ログ確認:
```
docker compose -f .\compose.yaml logs -f backend
```

- デフォルトポート: フロントエンド `http://localhost:3000`、バックエンド `http://localhost:8000`（`compose.yaml` の設定に依存）

## バックアップと復元（概要）
- `db/backups/latest.sql` をマウントしておくと起動時に復元を試行します。  
- フルダンプの復元は環境によって失敗する場合があるため、部分復元やダンプのクリーンアップを推奨します。詳細手順は `docs/backup-restore.md` へ移動可能です。

## マイグレーション
- Alembic を使用。エントリポイントで `alembic stamp head` → `alembic upgrade head` を実行します。

詳しい手順や CI/統合テストでの利用例は `docs/migration.md` を参照してください。

## 監査（Audit）概要
- 操作ログは `item_audit` テーブルへ記録。`POST /items` で同期的に監査レコードを作成します。  
- 保存される主な項目: `item_id`, `action`, `payload`, `user_id`, `ip`, `method`, `user_agent`, `request_path`。  
- 実装上の変更点: 手書き SQL から SQLAlchemy Core の `insert().values(...).returning(...)` に移行し、パラメータのバインドと型の問題を回避しています。詳細なバックフィル手順は `docs/audit-backfill.md` に移すことを推奨します。

## ログ回転（概要）
- `entrypoint.sh` が `/app/logs` 内の `*.log` を簡易ローテーションします（gzip圧縮、タイムスタンプ付与）。  
- 環境変数で閾値と保持数を設定可能（例: `STARTUP_ROTATE_MAX_BYTES`, `STARTUP_ROTATE_KEEP`, `STARTUP_ROTATE_INTERVAL`）。本番では専用ツールの使用を推奨します。

詳細な実装とローカルでのテスト手順は `docs/log-rotation.md` を参照してください。

## 検証/テスト（最小コマンド例）
- コンテナ内でインポート確認:
```
docker compose -f .\compose.yaml exec backend python -c "import app.main; print('IMPORT_OK')"
```

- 単発の API 呼び出し（バックエンド内から）:
```
docker compose -f .\compose.yaml exec backend python -c "import http.client, json; conn=http.client.HTTPConnection('127.0.0.1',8000); conn.request('POST','/items', json.dumps({'name':'refactor-check'}), {'Content-Type':'application/json','X-User-Id':'verify-user'}); print(conn.getresponse().status)"
```

- 統合テストや追加の検証コマンドは `docs/testing.md` へ移行推奨。
詳細なユニット／統合テストの手順、テスト用 DB の作成や削除、CI の例は `docs/testing.md` を参照してください。

## CI / 運用メモ（短く）
- `.github/workflows/ci.yml` に `unit-tests` と `integration-tests` を配置。テスト DB の設定やデバッグ手順は CI 内の注釈を参照してください。  
- 機密情報は `compose.yaml` に直書きしないで、`Secrets` または専用管理を利用してください。

CI の失敗時のログ収集やローカルでの再現手順は `docs/ci-debug.md` を参照してください。

## 開発環境（補足）
- `pydantic-settings` があれば型付き設定を利用します。なくても環境変数ベースで動作します。詳細は `backend/.env.example`。

バックエンド固有の開発手順、マイグレーションの実行例、テストの早見表は `backend/README.md` を確認してください。

## 環境ファイル (重要)

- Compose の変数補間: `docker compose` はリポジトリルートの `.env`（`./.env`）を起動時に読み込み、`compose.yaml` 内の `${...}` を展開します。例: `POSTGRES_USER` や `DATABASE_URL` の補間はルート `.env` に依存します。
- アプリのランタイム設定: アプリケーション（pydantic）は `ENV_FILE` 環境変数で指定されたファイル（デフォルト `.env`）を起動時に読み込みます。本リポジトリの `compose.yaml` は `ENV_FILE=.env` を `backend` サービスに渡すため、コンテナ内の `/app/.env`（ホストの `backend/.env`）がアプリの設定ソースになります。

このため、同じ設定が「ルートの `.env`」と「`backend/.env`」の両方に存在すると重複になります。運用上の推奨:

- 明確に分ける: Compose 用変数（DB ユーザ/パス、ボリュームなど）はルート `.env`、アプリ固有のランタイム設定（ロギング、認証、アプリ内のフラグ等）は `backend/.env` に置く。  
- 単一ソースを使いたい場合: ルート `.env` をコンテナにマウントしてアプリ側でも使わせる（例: `- ./.env:/app/.env:ro` を `backend.volumes` に追加）か、`ENV_FILE` をルートパスに合わせて変更してください（セキュリティに注意）。
- ドキュメント化: 新しい `backend/README.md` と `docs/` に環境変数の説明を追加済みです。どちらが正なのか運用ルールをチームで決めてください。

---

必要なら、詳細コマンドや長い SQL 例は `docs/` 以下へ分割してリンクを追加します（希望があれば私が分割して `docs/` を作成します）。
設定は `compose.yaml` の `backend` サービスで環境変数として変更できます:

- `STARTUP_ROTATE_MAX_BYTES` — 回転閾値（バイト、デフォルト `5242880` = 5MB）
