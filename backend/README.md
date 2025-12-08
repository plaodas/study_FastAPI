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

環境変数
- `ENV_FILE` — env ファイルのパス（デフォルト `.env`）
- `INTEGRATION_TEST` — 統合テスト用のフラグ（`1` または `true`）
- `DATABASE_URL` — DB 接続文字列（Compose で上書き可能）

テスト
- ユニット/統合テストの詳細は `../docs/testing.md` を参照してください。

デバッグのコツ
- モジュールのインポート確認: `python -c "import app.main; print('IMPORT_OK')"` をコンテナ内で実行して下さい。
