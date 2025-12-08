# CI / デバッグ（詳細）

このドキュメントは GitHub Actions 等の CI で失敗が起きた際のログ取得やローカルでの再現手順、一般的なデバッグ手順をまとめた補助資料です。

基本方針
- CI での失敗はまずアーティファクト（`integration-results.xml`、ログファイル等）を集めて原因を切り分けます。

GitHub Actions での確認
- ワークフローの対象ジョブを選び、`Jobs` -> 該当ジョブ -> `Artifacts` をダウンロードします。  
- ジョブの `Logs` からエラートレースや失敗コマンドを確認します。

ローカルでの再現
- CI の設定（`compose.yaml` / `compose.test.yml` / 環境変数）をローカルで再現して、同じコマンドを実行してみます。  

例: 統合テストの再現コマンド（PowerShell）

```powershell
docker compose -f compose.yaml -f compose.test.yml up -d --build backend db
docker compose -f compose.yaml -f compose.test.yml exec backend sh -c "alembic upgrade head"
docker compose -f compose.yaml -f compose.test.yml exec -e INTEGRATION_TEST=1 backend sh -c "pytest -q /app/tests -q"
```

ログ収集のヒント
- `docker compose logs --no-color --timestamps backend > backend-logs.txt` のようにログをファイルへ出力して差分を確認すると便利です。
- テスト失敗時は `pytest --maxfail=1 -k <testname> -vv` のように絞って実行し、失敗箇所の再現を早めます。

追加アーティファクト
- CI ジョブに `integration-failure-artifacts` 等を追加しておくと、失敗時に自動でログや結果を保存できます。  

注意
- CI 用の DB 接続文字列等の Secrets はローカルで再現する際に `compose.test.yml` や `.env.test` で上書きして下さい。  
