# マイグレーション（詳細）

このファイルには Alembic を使ったマイグレーションの適用手順や、コンテナ内での実行例を記載します。

基本的な手順

1. イメージをビルドして backend を起動

```powershell
docker compose -f .\compose.yaml build backend
docker compose -f .\compose.yaml up -d backend
```

2. マイグレーションを適用（backend コンテナ内）

```powershell
docker compose -f .\compose.yaml exec backend sh -c "alembic stamp head && alembic upgrade head"
```

CI / 統合テストでの利用
- 統合テスト用の Compose override（例: `compose.test.yml`）を用意し、`DATABASE_URL` をテスト DB に上書きします。
- テスト実行前にマイグレーションを適用することで、テスト用 DB を最新状態にします。

例（統合テスト用）

```powershell
docker compose -f compose.yaml -f compose.test.yml up -d --build backend
docker compose -f compose.yaml -f compose.test.yml exec backend sh -c "alembic upgrade head"
```

注意
- `alembic stamp head` はスキップする場合があり、既存の alembic バージョンの扱いによっては手動対応が必要です。
- 本番デプロイではマイグレーションの前にバックアップを取得する等の運用手順を入れてください。
