# テスト実行（ユニット / 統合）

このドキュメントはテストの詳細手順をまとめたものです。`README.md` の「検証/テスト」節の詳細を移動しています。

依存インストール（backend コンテナ内）

```powershell
cd backend
pip install -r requirements.txt
```

ユニットテスト実行（コンテナ内）

```powershell
docker compose exec backend sh -c "pytest -q /app/tests -q"
```

統合テストの準備（テスト用 DB 作成）

```powershell
docker compose exec db psql -U user -d postgres -c "CREATE DATABASE appdb_test;"
# または
if (-not (docker compose exec db psql -U user -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname = 'appdb_test'" | Select-String "1")) {
    docker compose exec db psql -U user -d postgres -c "CREATE DATABASE appdb_test"
}
```

統合テストの実行（例）

```powershell
docker compose -f compose.yaml -f compose.test.yml up -d --build backend
docker compose -f compose.yaml -f compose.test.yml exec backend sh -c "alembic upgrade head"
docker compose -f compose.yaml -f compose.test.yml exec -e INTEGRATION_TEST=1 backend sh -c "pytest -q /app/tests/test_integration_postgres.py::test_integration_postgres -q"
docker compose -f compose.yaml -f compose.test.yml down
```

テスト用 DB の削除

```powershell
docker compose exec db psql -U user -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='appdb_test' AND pid <> pg_backend_pid();"
docker compose exec db psql -U user -d postgres -c "DROP DATABASE IF EXISTS appdb_test;"
```

注意
- CI では `DATABASE_URL` を Secrets 経由で扱うことを推奨します。
