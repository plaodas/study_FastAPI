# Contributing

このリポジトリへ貢献いただきありがとうございます。ここでは特に「統合テスト（Postgres）」の実行方法と、Pull Request 上で統合テストを走らせる手順を簡潔にまとめます。

## 統合テスト（Postgres）をローカルで実行する
1. テスト用データベースを作成します（Compose の Postgres サービスを利用する例）:
   ```powershell
   docker compose exec db psql -U user -d postgres -c "CREATE DATABASE appdb_test;"
   ```
2. テスト用 backend を起動します（`compose.test.yml` を使う）:
   ```powershell
   docker compose -f compose.yaml -f compose.test.yml up -d --build backend
   ```
3. Postgres 用のテストを実行します（例: 環境変数を渡す）:
   ```powershell
   docker compose exec -e TEST_POSTGRES_DSN="postgresql+psycopg2://user:password@db:5432/appdb_test" backend sh -c "pytest -q /app/tests/test_audit_service_postgres.py -v"
   ```

注: `compose.test.yml` にプレースホルダ値があります。実行時には `user`/`password`/`db` を Compose 設定に合わせてください。

## Pull Request 上で統合テストを実行する
- デフォルトでは PR に重い統合テストは自動で走りません。PR 上で統合ジョブを実行したい場合、PR にラベル `run-integration` を付与してください。
- ラベルの付け方:
  - GitHub UI: PR の右側メニューの `Labels` から `run-integration` を追加。
  - CLI: `gh` を使う場合は `gh pr edit <number> --add-label run-integration` を実行できます。

## CI（GitHub Actions）についての注意
- Integration ジョブは以下の条件で実行されます:
  - push
  - workflow_dispatch（手動実行）
  - pull_request で `run-integration` ラベルが付与されている場合
- CI は `TEST_POSTGRES_DSN` を参照して Postgres テストを実行します。機密情報は GitHub Secrets / CI 環境で管理してください。`compose.test.yml` の値は例示です。

## よくある問題と対処
- psycopg2 の import エラー: `backend/requirements.txt` に `psycopg2-binary` が含まれていることを確認してください。CI では `libpq-dev` 等のシステムパッケージも必要になります（Workflow に記載済み）。
- 接続エラー: ホスト名（`db` / `localhost`）、ポート、ユーザ名／パスワードを Compose 設定や CI のサービス設定に合わせてください。
- テーブルが見つからない: 本テストは `item_audit` テーブルを自動で作成するコードを含みますが、他のテストは Alembic マイグレーションを前提にしている可能性があります。その場合は `alembic upgrade head` を実行してください。

## さらに助けが必要な場合
テスト実行でエラーが出たら、該当する pytest 出力や CI のログ（抜粋）をこの PR に貼ってください。こちらで解析して修正案を出します。

---
短い手順と注意点に絞っています。必要なら実行スクリプトやラベル自動追加用 GitHub Action のテンプレートも追加できます。
