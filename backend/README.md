# Backend 開発メモ

このファイルはバックエンド固有の開発・マイグレーション・テスト手順をまとめた簡易ドキュメントです。詳細なテスト手順は `../docs/testing.md` を参照してください。

起動（ローカル・Docker）

```powershell
# ルートから backend イメージをビルドして起動
docker compose -f .\compose.yaml build backend
docker compose -f .\compose.yaml up -d backend
```

マイグレーション

```powershell
# backend コンテナ内で Alembic を実行
docker compose -f .\compose.yaml exec backend sh -c "alembic stamp head && alembic upgrade head"
```

主要な環境変数（抜粋）

以下は `backend/.env.example` の主要な設定項目の抜粋です。実際の運用では秘密情報を `.env` や Secrets で適切に管理してください。

- `DATABASE_URL` — DB 接続文字列（例: `postgresql://user:pass@db:5432/appdb`）
- `ENV_FILE` — env ファイルのパス（デフォルト `.env`）
- `INTEGRATION_TEST` — 統合テスト用フラグ（`0`/`1`）
- `DATABASE_URL_TEST` — Compose のテストラン用（`compose.test.yml` でルート `.env` の `DATABASE_URL_TEST` を参照します）。
	- Note: `backend/.env` should not duplicate this; keep Compose interpolation keys in the repo root `.env`.
- `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` — 認証関連
- `ALLOWED_ORIGINS`, `BACKEND_BASE_URL` — CORS / フロントエンド設定
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_ECHO` — DB 接続チューニング
- `LOG_LEVEL`, `SENTRY_DSN` — ロギング / テレメトリ
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_DEFAULT`, `REDIS_URL` — レート制限 / キャッシュ
- `FORBIDDEN_WORDS`, `VALIDATION_RULES`, `AUDIT_ENABLED`, `AUDIT_TABLE` — バリデーション / 監査
- `PYTHONPATH`, `PORT` — エントリポイント関連
- `STARTUP_ROTATE_MAX_BYTES`, `STARTUP_ROTATE_KEEP`, `STARTUP_ROTATE_INTERVAL` — ログ回転設定

テスト
- ユニット/統合テストの詳細は `../docs/testing.md` を参照してください。

デバッグのコツ
- モジュールのインポート確認: `python -c "import app.main; print('IMPORT_OK')"` をコンテナ内で実行して下さい。
 

環境ファイルに関する注意

- `docker compose` の変数補間はルートの `.env` を使いますが、アプリ自体は `ENV_FILE`（デフォルト `.env`）で指定したファイルを読みます。本リポジトリでは `compose.yaml` が `ENV_FILE=.env` を `backend` に渡すため、コンテナ内の `/app/.env`（ホストの `backend/.env`）がアプリのランタイム設定ソースになります。
- そのため同じキーがルート `.env` と `backend/.env` に重複している場合、どちらを編集するか混乱が生じます。推奨方針:
	- Compose 用（DB のユーザ/パスやイメージ補間）はルート `.env` に置く。
	- アプリのランタイム設定（ロギング、認証、アプリ固有のフラグ等）は `backend/.env` に置く。
	- 単一ファイルにまとめたい場合は、`compose.yaml` でルート `.env` を `/app/.env` にマウントするか、`ENV_FILE` を適切に設定してください（機密管理に注意）。

