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

## 監査 (Audit)
バックエンドでは `item_audit` テーブルに操作の監査ログを記録します。現在の実装では `POST /items` によるアイテム作成時に同期的に監査レコードを挿入します。

- 記録される主な項目:
	- `item_id`: 対象アイテムの ID
	- `action`: 実行された操作（例: `create`）
	- `payload`: 操作に関連するデータ（JSON）
	- `user_id`, `ip`, `method`, `user_agent`, `request_path`（可能な場合）

- 実装上の挙動:
	- リクエストヘッダ `X-User-Id` があれば `user_id` に保存します（将来の認証導入時に連携予定）。
	- クライアント IP は `X-Forwarded-For` ヘッダを優先して取得します。
	- 監査は同期的に DB に書き込まれます（将来的に負荷対策で非同期キューに切り替える予定）。

### 監査の実装変更（重要）

- 変更点: `item_audit` への挿入を手書き SQL テンプレートから SQLAlchemy Core の `insert().values(...).returning(...)` に切り替えました。
	- 理由: 手書きの SQL で Postgres の型キャスト（例: `::json`）と SQLAlchemy のプレースホルダが混在するとバインド時に構文エラーやパラメータ不整合を起こすためです。Core の挿入を使うことで JSON 等のパラメータが確実にバインドされ、typed カラム（`user_id`, `ip`, `method`, `user_agent`, `request_path`）へ値が確実に書き込まれるようになりました。

### 万一 typed カラムが NULL の行がある場合のバックフィル手順

1. DB コンテナに入る:

```powershell
docker compose -f .\compose.yaml exec -T db bash
psql -U user -d appdb
```

2. payload に格納された値から typed カラムへコピーする SQL（安全なバックフィル）:

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

3. 補足: 上記は既存の行を運用で修正するための手順です。今回のアプリ側変更により新規挿入時には typed カラムが確実に書き込まれますが、古い NULL データが残っている場合はこの SQL を実行してバックフィルしてください。

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

## 検証コマンド（開発用）

開発中にコンテナ上で変更のインポート確認やエンドツーエンドの簡易検証を行うためのコマンド例です。

PowerShell（Compose ファイルがルートの `compose.yaml` の場合）:

```powershell
# コンテナ内でモジュールが正しくインポートできるか確認
docker compose -f .\compose.yaml exec backend python -c "import app.main; print('IMPORT_OK')"

# backend コンテナ内から POST /items を叩いて作成を検証
docker compose -f .\compose.yaml exec backend python -c "import http.client, json; conn=http.client.HTTPConnection('127.0.0.1',8000); conn.request('POST','/items', json.dumps({'name':'refactor-check'}), {'Content-Type':'application/json','X-User-Id':'verify-user'}); r=conn.getresponse(); print('STATUS', r.status); print(r.read().decode())"

# ホストから curl で叩く例（ローカルでポートを公開している場合）
curl -v -X POST http://localhost:8000/items -H "Content-Type: application/json" -d '{"name":"refactor-check"}'

# DB 内の最新の item_audit 行を確認する（psql を使う例）
docker compose -f .\compose.yaml exec db psql -U user -d appdb -c "SELECT id,item_id,action,payload->>'user_id' AS user_id,payload->>'ip' AS ip,method,user_agent,request_path FROM item_audit ORDER BY id DESC LIMIT 1;"
```

備考:
- `X-User-Id` ヘッダはテスト用の任意ヘッダで、監査の `user_id` に保存されます。
- Compose ファイルのパスやサービス名が異なる場合は適宜 `-f` オプションやサービス名を調整してください。

## テストの実行方法（ユニット / 統合）

以下はこのリポジトリでよく使うテスト実行手順です。Windows PowerShell の例を示します。

## CI ワークフローについて（補足）

このリポジトリには `.github/workflows/ci.yml` を追加しており、ワークフローは以下のように構成されています。

- `unit-tests` ジョブ: 依存をインストールしてユニットテストを素早く実行します。プルリクの初期フィードバックに有効です。
- `integration-tests` ジョブ: Postgres サービスを立ち上げ、`alembic upgrade head` でマイグレーションを適用した後に統合テストを実行します。`unit-tests` の成功後に走るよう設定されています。

失敗時のデバッグ方法:
- Actions の実行結果ページで対象ワークフローを選び、失敗したジョブをクリックしてください。
- `Artifacts` セクションに `integration-failure-artifacts` 等が表示されていれば、ダウンロードして `integration-results.xml` や `backend/logs/*` を確認できます。

手動トリガー:
- GitHub の Actions タブから `CI` を選び、`Run workflow` で `workflow_dispatch` による手動実行が可能です。

セキュリティ注意:
- 現在のワークフローはテスト用 DB のために `user/pass` をそのまま使用します。必要に応じて `Secrets` に切り替え、`DATABASE_URL` 等を `secrets.*` 経由で渡すことを推奨します。
# 注意: `backend/Dockerfile` に `ENV PYTHONPATH=/app` を設定済みのため、最新イメージを使えば
# 追加で `export` する必要はありません。環境によっては明示的に設定する必要があります。

```powershell
# 推奨（ENV が設定されたコンテナを使う場合）
docker compose exec backend sh -c "pytest -q /app/tests -q"

# 古いイメージや人力で実行する場合（コンテナ内で PYTHONPATH をセットしたいとき）
docker compose exec backend sh -c "export PYTHONPATH=/app; pytest -q /app/tests -q"
```

- 統合テスト（テスト専用 DB を使う — Compose override を利用）

```powershell

# テスト用 DB を作成（存在しない場合）
docker compose exec db psql -U user -d postgres -c "CREATE DATABASE appdb_test;"
# PowerShellでDB未存在確認も同時に行う
if (-not (docker compose exec db psql -U user -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname = 'appdb_test'" | Select-String "1")) {
    docker compose exec db psql -U user -d postgres -c "CREATE DATABASE appdb_test"
}

# オーバーライド付きで backend を起動（compose.test.yml を使って DATABASE_URL を appdb_test に上書き）
docker compose -f compose.yaml -f compose.test.yml up -d --build backend

# マイグレーションを適用（backend コンテナ内）
docker compose -f compose.yaml -f compose.test.yml exec backend sh -c "alembic upgrade head"

# 統合テストを実行（`INTEGRATION_TEST=1` を渡すことで該当テストが有効になります）
# 注意: `compose.test.yml` 側で `DATABASE_URL` をテスト DB に上書きしている想定です。
docker compose -f compose.yaml -f compose.test.yml exec -e INTEGRATION_TEST=1 backend sh -c "pytest -q /app/tests/test_integration_postgres.py::test_integration_postgres -q"

# テストが終わったらテスト用 backend を停止
docker compose -f compose.yaml -f compose.test.yml down
```

## テスト用 DB (`appdb_test`) の削除コマンド

テスト用 DB を削除する場合（接続が残っているとエラーになるため、接続を切ってから削除します）:

```powershell

# まず実行中の接続を切る
docker compose exec db psql -U user -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='appdb_test' AND pid <> pg_backend_pid();"

# DB を削除
docker compose exec db psql -U user -d postgres -c "DROP DATABASE IF EXISTS appdb_test;"
```

## Optional: Config library and test env

- This project can optionally use `pydantic-settings` for typed configuration. If installed, the application will prefer it for `backend/app/config.py`. If it's not installed, the app falls back to environment-variable based config so it still runs.

- To enable full typed settings, install dependencies in `backend`:

```powershell
cd backend
pip install -r requirements.txt
```

- Environment switches used by the app:
	- `ENV_FILE` — optional path to an env file (default is `.env`). Useful for selecting `.env.test` when running integration tests.
	- `INTEGRATION_TEST` — set to `1` (or `true`) to enable integration-test specific code paths.
	- Complex environment variables (lists/dicts): when using `pydantic-settings`, environment variables that map to complex types (e.g. `List[str]` or `Dict[...]`) should be provided as JSON (recommended). The application includes compatibility parsing for comma-separated lists, but JSON is more reliable. See `backend/.env.example` for examples.

See `backend/.env.example` for a ready-to-use sample of environment variables used by the backend.

- Example: run integration tests with compose override (as shown above) and ensure the override sets `DATABASE_URL` and `INTEGRATION_TEST=1` so the backend and Alembic use the test database.

